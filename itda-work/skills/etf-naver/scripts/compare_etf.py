#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_etf.py - 멀티 ETF 비교 및 섹터 로테이션 분석 스크립트 (네이버 금융).

Usage:
    # 섹터 로테이션 분석
    python3 compare_etf.py --sectors 1,2,4,5,6

    # ETF 직접 비교
    python3 compare_etf.py --codes 069500,360750,148070

    # 포트폴리오 리밸런싱
    python3 compare_etf.py --portfolio "069500:30,360750:40,148070:30"

    # Windows
    python compare_etf.py --sectors 1,2,4

Requirements:
    Python 3 stdlib only. fetch_etf 모듈을 동일 디렉토리에서 임포트.
"""

import sys

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 이상이 필요합니다.")

import argparse
import csv
import io
import json
import os
import urllib.error as urllib_error_module

# ---------------------------------------------------------------------------
# fetch_etf 모듈 임포트 (동일 디렉토리)
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.dirname(__file__))
import fetch_etf  # noqa: E402

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

ETF_TYPE_NAMES = fetch_etf.ETF_TYPE_NAMES

# 섹터 자금흐름 방향
FLOW_INFLOW = "유입 ▲"
FLOW_OUTFLOW = "유출 ▼"
FLOW_NEUTRAL = "보합 -"

# 리밸런싱 액션
ACTION_SELL = "매도 필요"
ACTION_BUY = "매수 필요"
ACTION_HOLD = "유지"

# 편차 임계값 (%)
DEVIATION_THRESHOLD = 5.0


# ---------------------------------------------------------------------------
# 유틸리티 함수
# ---------------------------------------------------------------------------


def parse_portfolio(portfolio_str):
    """포트폴리오 문자열을 (코드, 목표비중) 튜플 리스트로 파싱.

    Args:
        portfolio_str: "CODE:TARGET_PCT,CODE:TARGET_PCT,..." 형식 문자열.

    Returns:
        [(code, target_pct), ...] 형식의 리스트.

    Raises:
        ValueError: 형식이 잘못된 경우.
    """
    if not portfolio_str or not portfolio_str.strip():
        raise ValueError("빈 포트폴리오 문자열입니다.")

    result = []
    for part in portfolio_str.split(","):
        part = part.strip()
        if ":" not in part:
            raise ValueError(
                f"잘못된 포트폴리오 형식: '{part}' (예: CODE:30)"
            )
        code, pct_str = part.split(":", 1)
        code = code.strip()
        pct_str = pct_str.strip()
        try:
            pct = float(pct_str)
        except ValueError:
            raise ValueError(
                f"목표비중이 숫자가 아닙니다: '{pct_str}' (코드: {code})"
            )
        result.append((code, pct))

    # 비중 합계 검증 (경고만, 에러는 아님)
    total = sum(pct for _, pct in result)
    if abs(total - 100.0) > 0.1:
        print(
            f"[경고] 목표 비중 합계가 100%가 아닙니다: {total:.1f}%",
            file=sys.stderr,
        )

    return result


def calc_flow_direction(avg_change_rate, total_quant, median_quant):
    """섹터 자금흐름 방향을 판단.

    Args:
        avg_change_rate: 평균 등락률 (float).
        total_quant: 해당 섹터 총거래량.
        median_quant: 전체 섹터 중위 거래량 (비교 기준).

    Returns:
        "유입 ▲", "유출 ▼", "보합 -" 중 하나.
    """
    if avg_change_rate < 0:
        return FLOW_OUTFLOW
    if avg_change_rate > 0 and total_quant >= median_quant:
        return FLOW_INFLOW
    return FLOW_NEUTRAL


def calc_sector_metrics(items, top_n=3):
    """섹터 내 상위 N개 ETF의 집계 지표를 계산.

    Args:
        items: ETF 아이템 딕셔너리 리스트.
        top_n: 상위 몇 개 ETF를 사용할지.

    Returns:
        {"avg_change_rate": float, "total_quant": int, "total_market_sum": int}
    """
    selected = items[:top_n]
    if not selected:
        return {"avg_change_rate": 0.0, "total_quant": 0, "total_market_sum": 0}

    rates = []
    total_quant = 0
    total_market_sum = 0

    for item in selected:
        try:
            rates.append(float(item.get("changeRate", 0)))
        except (TypeError, ValueError):
            rates.append(0.0)
        try:
            total_quant += int(item.get("quant", 0))
        except (TypeError, ValueError):
            pass
        try:
            total_market_sum += int(item.get("marketSum", 0))
        except (TypeError, ValueError):
            pass

    avg_change_rate = sum(rates) / len(rates) if rates else 0.0

    return {
        "avg_change_rate": avg_change_rate,
        "total_quant": total_quant,
        "total_market_sum": total_market_sum,
    }


# ---------------------------------------------------------------------------
# Feature A: 섹터 로테이션 분석
# ---------------------------------------------------------------------------


def run_sector_analysis(sectors, top_n=3, fmt="table"):
    """섹터별 ETF 성과를 비교하여 자금흐름 방향을 분석.

    Args:
        sectors: 분석할 섹터 타입 번호 리스트 (예: [1, 2, 4]).
        top_n: 각 섹터에서 시가총액 상위 N개 ETF 사용.
        fmt: 출력 형식 ("table", "json", "csv").

    Returns:
        분석 결과 문자열.
    """
    sector_results = []

    for sector_type in sectors:
        items = fetch_etf.fetch_etf_list(etf_type=sector_type)
        sector_name = ETF_TYPE_NAMES.get(sector_type, str(sector_type))
        metrics = calc_sector_metrics(items, top_n=top_n)

        sector_results.append({
            "sector_type": sector_type,
            "sector_name": sector_name,
            "avg_change_rate": round(metrics["avg_change_rate"], 2),
            "total_quant": metrics["total_quant"],
            "total_market_sum": metrics["total_market_sum"],
            # flow_direction은 중위값 계산 후 채움
            "flow_direction": None,
        })

    # 중위 거래량 계산 (자금흐름 판단 기준)
    quants = [r["total_quant"] for r in sector_results]
    if quants:
        sorted_quants = sorted(quants)
        mid = len(sorted_quants) // 2
        if len(sorted_quants) % 2 == 0 and len(sorted_quants) > 1:
            median_quant = (sorted_quants[mid - 1] + sorted_quants[mid]) / 2
        else:
            median_quant = sorted_quants[mid]
    else:
        median_quant = 0

    for r in sector_results:
        r["flow_direction"] = calc_flow_direction(
            r["avg_change_rate"], r["total_quant"], median_quant
        )

    if fmt == "json":
        return _format_sector_json(sector_results)
    if fmt == "csv":
        return _format_sector_csv(sector_results)
    return _format_sector_table(sector_results)


def _format_sector_table(sector_results):
    """섹터 분석 결과를 마크다운 테이블로 포맷."""
    lines = ["## 섹터 로테이션 분석", ""]
    header = "| 섹터 | 평균등락률(%) | 총거래량 | 총시가총액 | 자금흐름 |"
    separator = "|------|-------------|---------|-----------|---------|"
    lines.append(header)
    lines.append(separator)

    for r in sector_results:
        rate_sign = "+" if r["avg_change_rate"] >= 0 else ""
        row = (
            f"| {r['sector_name']} "
            f"| {rate_sign}{r['avg_change_rate']:.2f} "
            f"| {_fmt_number(r['total_quant'])} "
            f"| {_fmt_number(r['total_market_sum'])} "
            f"| {r['flow_direction']} |"
        )
        lines.append(row)

    # 자금흐름 요약
    lines.append("")
    lines.append("### 자금 흐름 판단")

    inflow_sectors = [r for r in sector_results if r["flow_direction"] == FLOW_INFLOW]
    outflow_sectors = [r for r in sector_results if r["flow_direction"] == FLOW_OUTFLOW]

    if inflow_sectors:
        best = max(inflow_sectors, key=lambda x: x["avg_change_rate"])
        lines.append(
            f"- 가장 강한 유입: {best['sector_name']} ({best['avg_change_rate']:+.2f}%)"
        )
    else:
        lines.append("- 가장 강한 유입: 없음")

    if outflow_sectors:
        worst = min(outflow_sectors, key=lambda x: x["avg_change_rate"])
        lines.append(
            f"- 가장 큰 유출: {worst['sector_name']} ({worst['avg_change_rate']:+.2f}%)"
        )
    else:
        lines.append("- 가장 큰 유출: 없음")

    return "\n".join(lines)


def _format_sector_json(sector_results):
    """섹터 분석 결과를 JSON으로 포맷."""
    return json.dumps(sector_results, ensure_ascii=False, indent=2)


def _format_sector_csv(sector_results):
    """섹터 분석 결과를 CSV로 포맷."""
    fieldnames = [
        "sector_type", "sector_name", "avg_change_rate",
        "total_quant", "total_market_sum", "flow_direction",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for r in sector_results:
        writer.writerow(r)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Feature B: ETF vs ETF 비교
# ---------------------------------------------------------------------------

# @MX:ANCHOR: fetch_etf 모듈의 유틸리티 함수 재사용 (DRY)
# @MX:REASON: 중복 구현 제거, 단일 소스 유지
_fmt_number = fetch_etf._fmt_number
_calc_premium_rate = fetch_etf.calc_premium_rate


def run_codes_comparison(codes, fmt="table"):
    """특정 ETF 코드들을 나란히 비교.

    Args:
        codes: 비교할 ETF 종목코드 리스트.
        fmt: 출력 형식 ("table", "json", "csv").

    Returns:
        비교 결과 문자열.
    """
    all_items = fetch_etf.fetch_etf_list(etf_type=0)
    code_set = set(codes)
    selected = [item for item in all_items if item.get("itemcode") in code_set]

    # 코드 순서 유지
    code_order = {code: i for i, code in enumerate(codes)}
    selected.sort(key=lambda x: code_order.get(x.get("itemcode", ""), 999))

    # 프리미엄/괴리율 계산하여 추가
    enriched = []
    for item in selected:
        item_copy = dict(item)
        rate = _calc_premium_rate(item.get("nowVal", 0), item.get("nav", 0))
        item_copy["premiumRate"] = round(rate, 4) if rate is not None else None
        item_copy["premiumRateStr"] = (
            f"{rate:+.2f}%" if rate is not None else "N/A"
        )
        enriched.append(item_copy)

    if fmt == "json":
        return _format_codes_json(enriched)
    if fmt == "csv":
        return _format_codes_csv(enriched)
    return _format_codes_table(enriched)


def _format_codes_table(items):
    """ETF 비교를 가로 방향 마크다운 테이블로 포맷."""
    if not items:
        return "## ETF 비교 분석\n\n조회 결과가 없습니다."

    names = [item.get("itemname", item.get("itemcode", "N/A")) for item in items]
    header = "| 항목 | " + " | ".join(names) + " |"
    separator = "|------|" + "---|" * len(items)

    rows_data = [
        ("현재가", [_fmt_number(item.get("nowVal", 0)) for item in items]),
        ("NAV", [_fmt_number(item.get("nav", 0), precision=2) for item in items]),
        ("괴리율", [item.get("premiumRateStr", "N/A") for item in items]),
        ("등락률", [f"{item.get('changeRate', '0')}%" for item in items]),
        ("거래량", [_fmt_number(item.get("quant", 0)) for item in items]),
        ("시가총액", [_fmt_number(item.get("marketSum", 0)) for item in items]),
        ("3개월수익률", [f"{item.get('threeMonthEarnRate', '0')}%" for item in items]),
    ]

    lines = ["## ETF 비교 분석", "", header, separator]
    for label, values in rows_data:
        row = f"| {label} | " + " | ".join(values) + " |"
        lines.append(row)

    return "\n".join(lines)


def _format_codes_json(items):
    """ETF 비교 결과를 JSON으로 포맷."""
    return json.dumps(items, ensure_ascii=False, indent=2)


def _format_codes_csv(items):
    """ETF 비교 결과를 CSV로 포맷."""
    if not items:
        return ""
    fieldnames = [
        "itemcode", "itemname", "nowVal", "nav", "premiumRate",
        "changeVal", "changeRate", "quant", "marketSum", "threeMonthEarnRate",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for item in items:
        writer.writerow(item)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Feature C: 포트폴리오 리밸런싱
# ---------------------------------------------------------------------------


def run_portfolio_rebalancing(portfolio_str, fmt="table"):
    """현재 배분 대 목표 배분을 비교하여 리밸런싱 가이드 제공.

    Args:
        portfolio_str: "CODE:TARGET_PCT,CODE:TARGET_PCT,..." 형식 문자열.
        fmt: 출력 형식 ("table", "json", "csv").

    Returns:
        리밸런싱 결과 문자열.

    Raises:
        ValueError: 포트폴리오 형식이 잘못된 경우.
    """
    targets = parse_portfolio(portfolio_str)
    codes = [code for code, _ in targets]

    all_items = fetch_etf.fetch_etf_list(etf_type=0)
    code_set = set(codes)
    selected = [item for item in all_items if item.get("itemcode") in code_set]

    # 선택된 ETF의 총 시가총액 합산 (현재비중 추정 기준)
    def _safe_int(val: object) -> int:
        try:
            return int(val)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0

    total_market_sum = sum(_safe_int(item.get("marketSum", 0)) for item in selected)

    # 코드별 현재비중 계산 (시가총액 비율 기준 추정값 — 실제 보유 비중과 다를 수 있음)
    weight_map = {}
    name_map = {}
    for item in selected:
        code = item.get("itemcode", "")
        market_sum = _safe_int(item.get("marketSum", 0))
        weight_map[code] = (
            (market_sum / total_market_sum * 100) if total_market_sum > 0 else 0.0
        )
        name_map[code] = item.get("itemname", code)

    # 코드 순서 유지하여 결과 생성
    result_items = []
    for code, target_pct in targets:
        current_weight = weight_map.get(code, 0.0)
        deviation = current_weight - target_pct

        if deviation > DEVIATION_THRESHOLD:
            action = ACTION_SELL
        elif deviation < -DEVIATION_THRESHOLD:
            action = ACTION_BUY
        else:
            action = ACTION_HOLD

        result_items.append({
            "code": code,
            "name": name_map.get(code, code),
            "target_weight": round(target_pct, 1),
            "current_weight": round(current_weight, 1),
            "deviation": round(deviation, 1),
            "action": action,
        })

    if fmt == "json":
        return _format_portfolio_json(result_items)
    if fmt == "csv":
        return _format_portfolio_csv(result_items)
    return _format_portfolio_table(result_items)


def _format_portfolio_table(items):
    """포트폴리오 리밸런싱 결과를 마크다운 테이블로 포맷."""
    lines = ["## 포트폴리오 리밸런싱", ""]
    lines.append(
        "> **주의**: 현재비중은 네이버 API 시가총액 기준 추정값입니다. "
        "실제 보유 수량/금액 기반 비중과 다를 수 있습니다."
    )
    lines.append("")
    header = "| 종목코드 | 종목명 | 목표비중 | 현재비중(추정) | 편차 | 액션 |"
    separator = "|------|---------|---------|---------|------|------|"
    lines.append(header)
    lines.append(separator)

    for item in items:
        code = item["code"]
        name = item["name"]
        target = f"{item['target_weight']:.1f}%"
        current = f"{item['current_weight']:.1f}%"
        dev = item["deviation"]
        dev_str = f"{dev:+.1f}%"
        action = item["action"]

        # 편차 5% 초과 시 경고 표시
        if abs(dev) > DEVIATION_THRESHOLD:
            action_display = f"⚠️ {action}"
        else:
            action_display = action

        row = (
            f"| {code} | {name} | {target} | {current} | {dev_str} | {action_display} |"
        )
        lines.append(row)

    return "\n".join(lines)


def _format_portfolio_json(items):
    """포트폴리오 결과를 JSON으로 포맷."""
    return json.dumps(items, ensure_ascii=False, indent=2)


def _format_portfolio_csv(items):
    """포트폴리오 결과를 CSV로 포맷."""
    fieldnames = [
        "code", "name", "target_weight", "current_weight", "deviation", "action"
    ]
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for item in items:
        writer.writerow(item)
    return output.getvalue()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    """CLI 인수를 파싱.

    Args:
        argv: 인수 리스트 (None이면 sys.argv[1:] 사용).

    Returns:
        argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        description="멀티 ETF 비교 및 섹터 로테이션 분석 (네이버 금융)."
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--sectors",
        type=lambda s: [int(x.strip()) for x in s.split(",")],
        metavar="1,2,4",
        help="분석할 섹터 타입 번호 (쉼표 구분, 예: 1,2,4,5,6)",
    )
    mode_group.add_argument(
        "--codes",
        type=lambda s: [x.strip() for x in s.split(",")],
        metavar="069500,360750",
        help="비교할 ETF 종목코드 (쉼표 구분)",
    )
    mode_group.add_argument(
        "--portfolio",
        metavar="069500:30,360750:40",
        help="포트폴리오 리밸런싱: CODE:목표비중(%) 형식 (쉼표 구분)",
    )
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json", "csv"],
        help="출력 형식: table, json, csv (기본값: table)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        metavar="N",
        help="섹터 모드에서 섹터당 상위 N개 ETF (기본값: 3)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """CLI 진입점.

    Args:
        argv: 인수 리스트. None이면 sys.argv에서 읽음.
    """
    args = parse_args(argv)

    # --sectors, --codes, --portfolio 중 하나는 필수
    if args.sectors is None and args.codes is None and args.portfolio is None:
        print(
            "[입력 오류] --sectors, --codes, --portfolio 중 정확히 하나를 지정해야 합니다.",
            file=sys.stderr,
        )
        sys.exit(2)

    # UTF-8 출력 (Windows 대응)
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except AttributeError:
            pass

    try:
        if args.sectors is not None:
            output = run_sector_analysis(
                sectors=args.sectors, top_n=args.top, fmt=args.format
            )
        elif args.codes is not None:
            output = run_codes_comparison(codes=args.codes, fmt=args.format)
        else:
            output = run_portfolio_rebalancing(
                portfolio_str=args.portfolio, fmt=args.format
            )
    except ValueError as exc:
        print(f"[입력 오류] {exc}", file=sys.stderr)
        sys.exit(1)
    except (urllib_error_module.URLError, OSError) as exc:
        print(f"[네트워크 오류] {exc}", file=sys.stderr)
        sys.exit(1)

    print(output)


if __name__ == "__main__":
    main()
