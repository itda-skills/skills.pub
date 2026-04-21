#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_etf_detail.py - 네이버 금융 개별 ETF 기술적 분석 스크립트.

Usage:
    # macOS/Linux
    python3 fetch_etf_detail.py --code 069500 [--days 365] [--indicators all] [--format table|json]

    # Windows
    py -3 fetch_etf_detail.py --code 069500

Options:
    --code        필수. 6자리 ETF 종목 코드
    --days        히스토리 일수 (기본: 365, 52주 고저 정확도를 위해 365 이상 권장)
    --indicators  계산할 지표 (ma,rsi,macd,bb,atr,all 중 콤마 구분, 기본: all)
    --format      출력 형식 (table|json, 기본: table)

Requirements:
    Python 3.10+
    외부 의존성 없음 (표준 라이브러리만 사용)
"""

import os
import sys

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 이상이 필요합니다.")

import argparse
import ast
import datetime
import json
import math
import re

import urllib.error
import urllib.request

# fetch_etf 모듈 임포트 (ETF 이름 조회용)
sys.path.insert(0, os.path.dirname(__file__))
try:
    import fetch_etf as _fetch_etf_module
except ImportError:
    _fetch_etf_module = None

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

OHLCV_API_URL = (
    "https://fchart.stock.naver.com/siseJson.nhn"
    "?symbol={code}&requestType=1&startTime={start}&endTime={end}&timeframe=day"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

TIMEOUT_SECONDS = 15

# 응답 크기 상한 (10MB) - DoS 방어
MAX_RESPONSE_SIZE = 10 * 1024 * 1024

# 유효한 지표 이름
VALID_INDICATORS = {"ma", "rsi", "macd", "bb", "atr"}

# 종목 코드 정규식 (6자리 숫자)
CODE_PATTERN = re.compile(r"^\d{6}$")


# ---------------------------------------------------------------------------
# 순수 Python 기술 지표 헬퍼 함수
# ---------------------------------------------------------------------------

def _sma(values: list[float], window: int) -> list[float | None]:
    """단순 이동평균 (SMA).

    Args:
        values: 가격 리스트
        window: 윈도우 크기

    Returns:
        SMA 리스트. 윈도우 미만 인덱스는 None.
    """
    result: list[float | None] = [None] * len(values)
    for i in range(window - 1, len(values)):
        result[i] = sum(values[i - window + 1:i + 1]) / window
    return result


def _ema(values: list[float], window: int) -> list[float | None]:
    """지수 이동평균 (EMA).

    초기값 = 첫 window개의 SMA.
    이후: EMA = (close - prev_EMA) * multiplier + prev_EMA

    Args:
        values: 가격 리스트
        window: 윈도우 크기

    Returns:
        EMA 리스트. 초기 window-1 인덱스는 None.
    """
    result: list[float | None] = [None] * len(values)
    if len(values) < window:
        return result

    multiplier = 2.0 / (window + 1)
    # 초기값: 첫 window개의 SMA
    result[window - 1] = sum(values[:window]) / window
    for i in range(window, len(values)):
        prev = result[i - 1]
        if prev is None:
            result[i] = None
        else:
            result[i] = (values[i] - prev) * multiplier + prev
    return result


def _rsi(closes: list[float], window: int = 14) -> list[float | None]:
    """Wilder's RSI.

    - 가격 변동(delta) 계산
    - 초기 평균 상승/하락 = 첫 window개의 단순 평균
    - 이후: 평활화 평균 = (prev_avg * (window - 1) + current) / window
    - RSI = 100 - (100 / (1 + avg_gain / avg_loss))

    Args:
        closes: 종가 리스트
        window: RSI 기간 (기본: 14)

    Returns:
        RSI 리스트. 초기 window 인덱스는 None.
    """
    result: list[float | None] = [None] * len(closes)
    if len(closes) < window + 1:
        return result

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # 초기 평균 상승/하락 (첫 window개)
    gains = [d if d > 0 else 0.0 for d in deltas[:window]]
    losses = [abs(d) if d < 0 else 0.0 for d in deltas[:window]]
    avg_gain = sum(gains) / window
    avg_loss = sum(losses) / window

    # 첫 RSI (인덱스 window)
    if avg_loss == 0:
        result[window] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[window] = 100.0 - (100.0 / (1.0 + rs))

    # 이후 Wilder's 평활화
    for i in range(window + 1, len(closes)):
        delta = deltas[i - 1]
        gain = delta if delta > 0 else 0.0
        loss = abs(delta) if delta < 0 else 0.0
        avg_gain = (avg_gain * (window - 1) + gain) / window
        avg_loss = (avg_loss * (window - 1) + loss) / window
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))

    return result


def _macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[float | None]]:
    """MACD + Signal + Histogram.

    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(MACD Line, signal)
    Histogram = MACD Line - Signal Line

    Args:
        closes: 종가 리스트
        fast: 빠른 EMA 기간 (기본: 12)
        slow: 느린 EMA 기간 (기본: 26)
        signal: 시그널 EMA 기간 (기본: 9)

    Returns:
        {"macd": [...], "signal": [...], "hist": [...]}
    """
    n = len(closes)
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    macd_line: list[float | None] = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]  # type: ignore[operator]

    # 유효한 MACD 값만 추출해 시그널 EMA 계산
    valid_macd = [v for v in macd_line if v is not None]
    if len(valid_macd) < signal:
        return {"macd": macd_line, "signal": [None] * n, "hist": [None] * n}

    # 시그널 라인: MACD 유효 구간에 EMA 적용
    first_valid = next(i for i, v in enumerate(macd_line) if v is not None)
    macd_values_from_first = [v for v in macd_line[first_valid:] if v is not None]
    # 전체 macd_line을 연속 float로 처리
    macd_contiguous = [v if v is not None else 0.0 for v in macd_line]
    signal_full = _ema(macd_contiguous, signal)

    # None 마스크: macd_line이 None인 구간은 signal도 None
    signal_line: list[float | None] = [None] * n
    hist_line: list[float | None] = [None] * n
    macd_valid_start = first_valid + signal - 1
    for i in range(macd_valid_start, n):
        if macd_line[i] is not None and signal_full[i] is not None:
            signal_line[i] = signal_full[i]
            hist_line[i] = macd_line[i] - signal_full[i]  # type: ignore[operator]

    return {"macd": macd_line, "signal": signal_line, "hist": hist_line}


def _bollinger(
    closes: list[float],
    window: int = 20,
    num_std: float = 2.0,
) -> dict[str, list[float | None]]:
    """Bollinger Bands.

    Middle = SMA(window)
    표준편차 = sqrt(sum((x - mean)^2) / window) (모분산 기준)
    Upper = Middle + num_std * std
    Lower = Middle - num_std * std
    %B = (close - Lower) / (Upper - Lower)

    Args:
        closes: 종가 리스트
        window: 기간 (기본: 20)
        num_std: 표준편차 배수 (기본: 2.0)

    Returns:
        {"upper": [...], "middle": [...], "lower": [...], "pct_b": [...]}
    """
    n = len(closes)
    upper: list[float | None] = [None] * n
    middle: list[float | None] = [None] * n
    lower: list[float | None] = [None] * n
    pct_b: list[float | None] = [None] * n

    for i in range(window - 1, n):
        window_vals = closes[i - window + 1:i + 1]
        mean = sum(window_vals) / window
        variance = sum((x - mean) ** 2 for x in window_vals) / window
        std = math.sqrt(variance)
        m = mean
        u = mean + num_std * std
        l = mean - num_std * std
        middle[i] = m
        upper[i] = u
        lower[i] = l
        denom = u - l
        if denom != 0:
            pct_b[i] = (closes[i] - l) / denom
        else:
            pct_b[i] = None

    return {"upper": upper, "middle": middle, "lower": lower, "pct_b": pct_b}


def _atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    window: int = 14,
) -> list[float | None]:
    """Average True Range (ATR).

    True Range = max(high - low, |high - prev_close|, |low - prev_close|)
    초기 ATR = 첫 window개 TR의 단순 평균
    이후: ATR = (prev_ATR * (window - 1) + current_TR) / window

    Args:
        highs: 고가 리스트
        lows: 저가 리스트
        closes: 종가 리스트
        window: 기간 (기본: 14)

    Returns:
        ATR 리스트. 초기 window 인덱스까지는 None.
    """
    n = len(closes)
    result: list[float | None] = [None] * n
    if n < window + 1:
        return result

    # True Range 계산 (인덱스 1부터)
    tr_values: list[float] = []
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr_values.append(max(hl, hc, lc))

    # 초기 ATR (인덱스 window: tr_values[0..window-1] 평균)
    initial_atr = sum(tr_values[:window]) / window
    result[window] = initial_atr

    # 이후 Wilder's 평활화
    prev_atr = initial_atr
    for i in range(window + 1, n):
        curr_atr = (prev_atr * (window - 1) + tr_values[i - 1]) / window
        result[i] = curr_atr
        prev_atr = curr_atr

    return result


# ---------------------------------------------------------------------------
# OHLCV 데이터 파싱
# ---------------------------------------------------------------------------

def parse_naver_ohlcv(response_text: str) -> list[dict]:
    """
    네이버 금융 OHLCV 응답 텍스트를 list[dict]로 파싱.

    응답 형식: JavaScript-like 배열
    각 행: ["YYYYMMDD","open","high","low","close","volume"]

    Args:
        response_text: API 응답 텍스트

    Returns:
        list[dict] with keys: date, open, high, low, close, volume
    """
    response_text = response_text.strip()

    if response_text == "[]" or not response_text:
        return []

    # JavaScript 배열을 Python 리스트로 파싱
    rows = _parse_js_array(response_text)

    if not rows:
        return []

    records = []
    for row in rows:
        if len(row) < 6:
            continue
        try:
            records.append({
                "date": str(row[0]).strip(),
                "open": float(str(row[1]).strip().replace(",", "")),
                "high": float(str(row[2]).strip().replace(",", "")),
                "low": float(str(row[3]).strip().replace(",", "")),
                "close": float(str(row[4]).strip().replace(",", "")),
                "volume": float(str(row[5]).strip().replace(",", "")),
            })
        except (ValueError, IndexError):
            continue

    records = sorted(records, key=lambda r: r["date"])
    return records


def _parse_js_array(text: str) -> list:
    """
    JavaScript-like 배열 텍스트를 Python 리스트로 변환.

    네이버 응답은 유효한 JSON이 아닐 수 있으므로
    정규식 또는 ast.literal_eval로 파싱.
    """
    # @MX:WARN: ast.literal_eval 사용 - 과도하게 큰 입력 시 DoS 가능
    # @MX:REASON: 응답 크기 상한(MAX_RESPONSE_SIZE)으로 방어
    if len(text) > MAX_RESPONSE_SIZE:
        return []

    # 방법 1: ast.literal_eval 시도 (Python 리터럴 변환)
    try:
        result = ast.literal_eval(text)
        if isinstance(result, list):
            return result
    except (ValueError, SyntaxError):
        pass

    # 방법 2: 정규식으로 개별 행 추출
    rows = []
    for match in re.finditer(r'\[([^\[\]]+)\]', text):
        inner = match.group(0)
        try:
            # 내부 배열을 Python 리스트로 파싱
            parsed = ast.literal_eval(inner)
            if isinstance(parsed, list) and len(parsed) >= 6:
                rows.append(parsed)
        except (ValueError, SyntaxError):
            # 문자열 분리 시도
            inner_text = match.group(1)
            parts = re.findall(r'"([^"]*)"', inner_text)
            if len(parts) >= 6:
                rows.append(parts)

    return rows


# ---------------------------------------------------------------------------
# HTTP 데이터 페치
# ---------------------------------------------------------------------------

def fetch_ohlcv(code: str, days: int = 120) -> list[dict]:
    """
    네이버 금융에서 ETF OHLCV 데이터를 페치.

    Args:
        code: ETF 종목 코드 (예: "069500")
        days: 히스토리 일수 (기본: 120)

    Returns:
        list[dict] with OHLCV data

    Raises:
        urllib.error.URLError: HTTP 요청 실패 시
    """
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)

    url = OHLCV_API_URL.format(
        code=code,
        start=start_date.strftime("%Y%m%d"),
        end=end_date.strftime("%Y%m%d"),
    )

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        raw = resp.read()

        # 응답 크기 상한 체크 (DoS 방어 — 전체 텍스트 처리 전에 검사)
        if len(raw) > MAX_RESPONSE_SIZE:
            raise ValueError(
                f"응답이 너무 큽니다: {len(raw):,} bytes "
                f"(상한: {MAX_RESPONSE_SIZE:,} bytes)"
            )

        charset = resp.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset)

    return parse_naver_ohlcv(text)


# ---------------------------------------------------------------------------
# 기술 지표 계산
# ---------------------------------------------------------------------------

def parse_indicator_list(indicators_str: str) -> set:
    """지표 문자열을 세트로 파싱.

    Args:
        indicators_str: 콤마 구분 지표 문자열 (예: "ma,rsi") 또는 "all".

    Returns:
        지표 이름 세트. "all"이면 전체 지표 세트 반환.
    """
    if indicators_str.strip().lower() == "all":
        return VALID_INDICATORS.copy()
    requested = {s.strip().lower() for s in indicators_str.split(",")}
    return requested & VALID_INDICATORS


def calculate_indicators(data: list[dict], selected: set | None = None) -> dict:
    """
    OHLCV list[dict]에서 기술 지표를 계산.

    계산 지표:
    - SMA(20), SMA(60)
    - RSI(14)
    - MACD(12, 26, 9)
    - Bollinger Bands(20, 2)
    - ATR(14)
    - 52주 최고/최저

    Args:
        data: list[dict] OHLCV 데이터. 각 dict: date, open, high, low, close, volume
        selected: 계산할 지표 세트. None이면 전체 계산.

    Returns:
        지표 값 딕셔너리
    """
    if selected is None:
        selected = VALID_INDICATORS.copy()
    result: dict[str, float | None] = {
        "current_price": None,
        "sma20": None,
        "sma60": None,
        "rsi14": None,
        "macd": None,
        "macd_signal": None,
        "macd_hist": None,
        "bb_upper": None,
        "bb_middle": None,
        "bb_lower": None,
        "bb_pct_b": None,
        "atr14": None,
        "week52_high": None,
        "week52_low": None,
    }

    if not data:
        return result

    closes = [row["close"] for row in data]
    highs = [row["high"] for row in data]
    lows = [row["low"] for row in data]

    # 현재가 (마지막 종가)
    result["current_price"] = closes[-1]

    # SMA(20)
    if "ma" in selected and len(data) >= 20:
        sma20_series = _sma(closes, 20)
        val = sma20_series[-1]
        result["sma20"] = None if (val is None or math.isnan(val)) else val

    # SMA(60)
    if "ma" in selected and len(data) >= 60:
        sma60_series = _sma(closes, 60)
        val = sma60_series[-1]
        result["sma60"] = None if (val is None or math.isnan(val)) else val

    # RSI(14)
    if "rsi" in selected and len(data) >= 15:
        rsi_series = _rsi(closes, 14)
        val = rsi_series[-1]
        result["rsi14"] = None if (val is None or math.isnan(val)) else val

    # MACD(12, 26, 9)
    if "macd" in selected and len(data) >= 26:
        macd_result = _macd(closes, fast=12, slow=26, signal=9)
        macd_val = macd_result["macd"][-1]
        macd_sig_val = macd_result["signal"][-1]
        macd_hist_val = macd_result["hist"][-1]
        result["macd"] = None if _is_nan(macd_val) else macd_val
        result["macd_signal"] = None if _is_nan(macd_sig_val) else macd_sig_val
        result["macd_hist"] = None if _is_nan(macd_hist_val) else macd_hist_val

    # Bollinger Bands(20, 2)
    if "bb" in selected and len(data) >= 20:
        bb_result = _bollinger(closes, window=20, num_std=2.0)
        result["bb_upper"] = None if _is_nan(bb_result["upper"][-1]) else bb_result["upper"][-1]
        result["bb_middle"] = None if _is_nan(bb_result["middle"][-1]) else bb_result["middle"][-1]
        result["bb_lower"] = None if _is_nan(bb_result["lower"][-1]) else bb_result["lower"][-1]
        result["bb_pct_b"] = None if _is_nan(bb_result["pct_b"][-1]) else bb_result["pct_b"][-1]

    # ATR(14)
    if "atr" in selected and len(data) >= 15:
        atr_series = _atr(highs, lows, closes, 14)
        val = atr_series[-1]
        result["atr14"] = None if _is_nan(val) else val

    # 52주 최고/최저 (252 거래일 또는 전체 데이터)
    week52_window = min(len(data), 252)
    week52_closes = closes[-week52_window:]
    result["week52_high"] = max(week52_closes)
    result["week52_low"] = min(week52_closes)

    return result


def _is_nan(val) -> bool:
    """값이 None 또는 NaN인지 확인."""
    if val is None:
        return True
    try:
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------------------
# 신호 판단
# ---------------------------------------------------------------------------

def generate_signals(indicators: dict) -> dict:
    """
    지표 값을 기반으로 매매 신호를 판단.

    Rules:
    - RSI > 70: 과매수, RSI < 30: 과매도, else: 중립
    - Price > SMA20 > SMA60: 상승추세, Price < SMA20 < SMA60: 하락추세
    - MACD > Signal: 매수 모멘텀, MACD < Signal: 매도 모멘텀
    - Bollinger %B > 1: 상단 돌파, %B < 0: 하단 돌파

    Args:
        indicators: calculate_indicators() 반환 딕셔너리

    Returns:
        신호 딕셔너리
    """
    signals = {}

    # RSI 신호
    rsi = indicators.get("rsi14")
    if rsi is not None:
        if rsi > 70:
            signals["rsi_signal"] = "과매수"
        elif rsi < 30:
            signals["rsi_signal"] = "과매도"
        else:
            signals["rsi_signal"] = "중립"
    else:
        signals["rsi_signal"] = "N/A"

    # 추세 신호
    price = indicators.get("current_price")
    sma20 = indicators.get("sma20")
    sma60 = indicators.get("sma60")

    if price is not None and sma20 is not None and sma60 is not None:
        if price > sma20 > sma60:
            signals["trend_signal"] = "상승추세"
        elif price < sma20 < sma60:
            signals["trend_signal"] = "하락추세"
        else:
            signals["trend_signal"] = "횡보"
    else:
        signals["trend_signal"] = "N/A"

    # MACD 신호
    macd = indicators.get("macd")
    macd_sig = indicators.get("macd_signal")

    if macd is not None and macd_sig is not None:
        if macd > macd_sig:
            signals["macd_signal_label"] = "매수 모멘텀"
        else:
            signals["macd_signal_label"] = "매도 모멘텀"
    else:
        signals["macd_signal_label"] = "N/A"

    # 볼린저 밴드 신호
    bb_pct_b = indicators.get("bb_pct_b")

    if bb_pct_b is not None:
        if bb_pct_b > 1:
            signals["bb_signal"] = "상단 돌파"
        elif bb_pct_b < 0:
            signals["bb_signal"] = "하단 돌파"
        else:
            signals["bb_signal"] = "밴드 내"
    else:
        signals["bb_signal"] = "N/A"

    return signals


# ---------------------------------------------------------------------------
# 출력 형식
# ---------------------------------------------------------------------------

def format_table(code: str, name: str, indicators: dict, signals: dict) -> str:
    """
    기술 분석 결과를 Markdown 테이블 형식으로 출력.

    Args:
        code: ETF 종목 코드
        name: ETF 이름
        indicators: 지표 딕셔너리
        signals: 신호 딕셔너리

    Returns:
        Markdown 형식 문자열
    """
    lines = []
    lines.append(f"## {name} ({code}) 기술적 분석")
    lines.append("")
    lines.append("| 지표 | 값 | 신호 |")
    lines.append("|------|-----|------|")

    # 현재가
    cp = indicators.get("current_price")
    cp_str = f"{cp:,.0f}" if cp is not None else "N/A"
    lines.append(f"| 현재가 | {cp_str} | - |")

    # SMA(20)
    sma20 = indicators.get("sma20")
    sma20_str = f"{sma20:,.0f}" if sma20 is not None else "N/A"
    sma20_sig = _ma_signal_text(cp, sma20, "MA20")
    lines.append(f"| SMA(20) | {sma20_str} | {sma20_sig} |")

    # SMA(60)
    sma60 = indicators.get("sma60")
    sma60_str = f"{sma60:,.0f}" if sma60 is not None else "N/A"
    sma60_sig = _ma_signal_text(cp, sma60, "MA60")
    lines.append(f"| SMA(60) | {sma60_str} | {sma60_sig} |")

    # RSI(14)
    rsi = indicators.get("rsi14")
    rsi_str = f"{rsi:.1f}" if rsi is not None else "N/A"
    rsi_sig = signals.get("rsi_signal", "N/A")
    rsi_range = f" ({_rsi_range(rsi)})" if rsi is not None else ""
    lines.append(f"| RSI(14) | {rsi_str} | {rsi_sig}{rsi_range} |")

    # MACD
    macd = indicators.get("macd")
    macd_str = f"{macd:+.1f}" if macd is not None else "N/A"
    macd_sig_label = signals.get("macd_signal_label", "N/A")
    lines.append(f"| MACD | {macd_str} | {macd_sig_label} |")

    # MACD Signal
    macd_signal = indicators.get("macd_signal")
    macd_signal_str = f"{macd_signal:+.1f}" if macd_signal is not None else "N/A"
    lines.append(f"| MACD Signal | {macd_signal_str} | - |")

    # 볼린저 상단
    bb_upper = indicators.get("bb_upper")
    bb_upper_str = f"{bb_upper:,.0f}" if bb_upper is not None else "N/A"
    lines.append(f"| 볼린저 상단 | {bb_upper_str} | - |")

    # 볼린저 하단
    bb_lower = indicators.get("bb_lower")
    bb_lower_str = f"{bb_lower:,.0f}" if bb_lower is not None else "N/A"
    bb_sig = signals.get("bb_signal", "N/A")
    lines.append(f"| 볼린저 하단 | {bb_lower_str} | {bb_sig} |")

    # ATR(14)
    atr = indicators.get("atr14")
    atr_str = f"{atr:.1f}" if atr is not None else "N/A"
    lines.append(f"| ATR(14) | {atr_str} | - |")

    # 52주 최고
    w52h = indicators.get("week52_high")
    w52h_str = f"{w52h:,.0f}" if w52h is not None else "N/A"
    w52h_diff = _pct_diff_text(cp, w52h) if (cp and w52h) else "-"
    lines.append(f"| 52주 최고 | {w52h_str} | {w52h_diff} |")

    # 52주 최저
    w52l = indicators.get("week52_low")
    w52l_str = f"{w52l:,.0f}" if w52l is not None else "N/A"
    w52l_diff = _pct_diff_text(cp, w52l) if (cp and w52l) else "-"
    lines.append(f"| 52주 최저 | {w52l_str} | {w52l_diff} |")

    # 종합 판단
    lines.append("")
    lines.append("### 종합 판단")

    trend = signals.get("trend_signal", "N/A")
    trend_detail = _trend_detail(cp, sma20, sma60)
    lines.append(f"- 추세: {_trend_kr(trend)} ({trend_detail})")

    rsi_summary = f"중립 구간 ({rsi:.1f})" if rsi is not None and 30 <= rsi <= 70 else (f"{rsi_sig} ({rsi:.1f})" if rsi is not None else "N/A")
    lines.append(f"- RSI: {rsi_summary}")

    momentum = signals.get("macd_signal_label", "N/A")
    momentum_detail = _momentum_detail(macd, macd_signal)
    lines.append(f"- 모멘텀: {momentum_detail} ({momentum})")

    return "\n".join(lines)


def _ma_signal_text(price, ma, label):
    """이동평균 신호 텍스트 생성."""
    if price is None or ma is None:
        return "N/A"
    if price > ma:
        return f"현재가 > {label} ✅"
    return f"현재가 < {label} ⚠️"


def _rsi_range(rsi):
    """RSI 범위 텍스트."""
    if rsi is None:
        return ""
    if rsi > 70:
        return "과매수 구간"
    elif rsi < 30:
        return "과매도 구간"
    return "30-70"


def _pct_diff_text(current, target):
    """현재가 대비 목표 가격의 차이 비율 텍스트."""
    if not current or not target or current == 0:
        return "-"
    diff = (current - target) / target * 100
    return f"{diff:+.1f}%"


def _trend_kr(trend):
    """추세 신호 한글 변환."""
    mapping = {"상승추세": "상승", "하락추세": "하락", "횡보": "횡보"}
    return mapping.get(trend, trend)


def _trend_detail(price, sma20, sma60):
    """추세 상세 설명."""
    if price is None or sma20 is None or sma60 is None:
        return "데이터 부족"
    if price > sma20 > sma60:
        return "현재가 > SMA20 > SMA60"
    elif price < sma20 < sma60:
        return "현재가 < SMA20 < SMA60"
    return "혼재"


def _momentum_detail(macd, macd_signal):
    """모멘텀 상세 설명."""
    if macd is None or macd_signal is None:
        return "N/A"
    return "양수" if macd > macd_signal else "음수"


def format_json(code: str, name: str, indicators: dict, signals: dict) -> str:
    """
    기술 분석 결과를 JSON 형식으로 출력.

    Args:
        code: ETF 종목 코드
        name: ETF 이름
        indicators: 지표 딕셔너리
        signals: 신호 딕셔너리

    Returns:
        JSON 형식 문자열
    """
    output = {
        "code": code,
        "name": name,
        "indicators": {k: v for k, v in indicators.items()},
        "signals": signals,
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    """CLI 인수 파서 생성."""
    parser = argparse.ArgumentParser(
        description="네이버 금융 ETF 기술적 분석",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--code",
        required=True,
        help="6자리 ETF 종목 코드 (예: 069500)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="히스토리 일수 (기본: 365, 52주 고저 정확도를 위해 365 이상 권장)",
    )
    parser.add_argument(
        "--indicators",
        default="all",
        help="계산할 지표 (ma,rsi,macd,bb,atr 또는 all, 기본: all)",
    )
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
        help="출력 형식 (table|json, 기본: table)",
    )
    return parser


def get_etf_name(code: str) -> str:
    """ETF 이름을 fetch_etf 모듈의 전체 목록에서 조회.

    Args:
        code: ETF 종목코드 (예: "069500").

    Returns:
        ETF 이름 문자열. 조회 실패 시 "ETF({code})" 반환.
    """
    # @MX:NOTE: fetch_etf 모듈 임포트 실패 시 폴백
    if _fetch_etf_module is None:
        return f"ETF({code})"
    try:
        items = _fetch_etf_module.fetch_etf_list(etf_type=0)
        for item in items:
            if item.get("itemcode") == code:
                return item.get("itemname", f"ETF({code})")
    except Exception:
        pass
    return f"ETF({code})"


def validate_code(code: str) -> str:
    """종목 코드 형식 검증.

    Args:
        code: 입력된 종목 코드.

    Returns:
        검증된 종목 코드.

    Raises:
        ValueError: 6자리 숫자가 아닌 경우.
    """
    if not CODE_PATTERN.match(code):
        raise ValueError(f"종목 코드는 6자리 숫자여야 합니다: '{code}'")
    return code


def main():
    """메인 실행 함수."""
    parser = build_arg_parser()
    args = parser.parse_args()

    code = args.code
    days = args.days
    output_format = args.format

    # 종목 코드 검증
    try:
        code = validate_code(code)
    except ValueError as e:
        print(f"[입력 오류] {e}", file=sys.stderr)
        sys.exit(1)

    # 지표 선택 파싱
    selected = parse_indicator_list(args.indicators)
    if not selected:
        print(
            f"[입력 오류] 유효한 지표가 없습니다: '{args.indicators}' "
            f"(사용 가능: {','.join(sorted(VALID_INDICATORS))} 또는 all)",
            file=sys.stderr,
        )
        sys.exit(1)

    # 데이터 페치
    try:
        data = fetch_ohlcv(code, days=days)
    except urllib.error.HTTPError as e:
        print(f"HTTP 오류: {e}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"네트워크 오류: {e}", file=sys.stderr)
        sys.exit(1)

    if not data:
        print(f"데이터를 가져올 수 없습니다: {code}", file=sys.stderr)
        sys.exit(1)

    # 지표 계산 (선택된 지표만)
    indicators = calculate_indicators(data, selected=selected)

    # 신호 판단
    signals = generate_signals(indicators)

    # ETF 이름 조회
    etf_name = get_etf_name(code)

    # 출력
    if output_format == "json":
        print(format_json(code, etf_name, indicators, signals))
    else:
        print(format_table(code, etf_name, indicators, signals))


if __name__ == "__main__":
    main()
