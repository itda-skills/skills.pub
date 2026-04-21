#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_etf.py - ETF price query script for Naver Finance JSONP API.

Usage:
    # macOS/Linux
    python3 scripts/fetch_etf.py --type 0 [--top 30] [--sort desc] [--format table|json|csv]

    # Windows
    python scripts/fetch_etf.py --type 0

Requirements:
    Python 3 stdlib only (no pip dependencies).
"""

import sys

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 이상이 필요합니다.")

import argparse
import csv
import io
import json
import random
import re
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_URL = "https://finance.naver.com/api/sise/etfItemList.nhn"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

TIMEOUT_SECONDS = 10

# ETF type name mapping
ETF_TYPE_NAMES = {
    0: "전체",
    1: "국내 시장지수",
    2: "국내 업종/테마",
    3: "국내 파생",
    4: "해외 주식",
    5: "원자재",
    6: "채권",
    7: "기타",
}

# risefall code to display symbol mapping
RISEFALL_SYMBOLS = {
    "1": "▲",
    "2": "▼",
    "3": "-",
}

# Valid ETF type range
ETF_TYPE_MIN = 0
ETF_TYPE_MAX = 7


# ---------------------------------------------------------------------------
# Core utilities
# ---------------------------------------------------------------------------


def parse_jsonp(text):
    """Strip JSONP callback wrapper and return parsed JSON object.

    The Naver Finance API returns responses in the form:
        window.__jindo2_callback._NNN({...});

    This function removes the wrapper and returns the inner JSON as a dict.

    Args:
        text: Raw JSONP response string.

    Returns:
        Parsed JSON object (dict or list).

    Raises:
        ValueError: If the text is empty or the inner JSON is malformed.
    """
    if not text or not text.strip():
        raise ValueError("Empty JSONP response")

    # Remove everything up to and including the first '('
    # and remove the trailing ')' with optional ';' and whitespace
    json_str = re.sub(r"^[^(]*\(|\)\s*;?\s*$", "", text.strip())

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON from JSONP response: {exc}") from exc


# @MX:ANCHOR: fetch_etf_list - fan_in >= 3 (fetch_etf.py, compare_etf.py, fetch_etf_detail.py)
# @MX:REASON: 핵심 데이터 소스 함수, 변경 시 모든 의존 모듈에 영향
def fetch_etf_list(etf_type=0, sort_order="desc", timeout=TIMEOUT_SECONDS):
    """Fetch ETF list from Naver Finance API.

    Args:
        etf_type: ETF category code (0-7).
        sort_order: Sort direction, "desc" or "asc".
        timeout: HTTP request timeout in seconds.

    Returns:
        List of ETF item dicts from the API response.

    Raises:
        urllib.error.URLError: On network failure.
        ValueError: On JSONP/JSON parse failure.
    """
    # Generate random callback name to mimic browser behavior
    callback = f"window.__jindo2_callback._{random.randint(100, 9999)}"

    params = urllib.parse.urlencode(
        {
            "etfType": etf_type,
            "targetColumn": "market_sum",
            "sortOrder": sort_order,
            "_callback": callback,
        }
    )
    url = f"{API_URL}?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        raw = resp.read().decode(charset)

    data = parse_jsonp(raw)
    return data.get("result", {}).get("etfItemList", [])


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _risefall_symbol(code):
    """Convert risefall code string to a display symbol.

    Args:
        code: "1" (rise), "2" (fall), "3" (flat), or anything else.

    Returns:
        "▲", "▼", "-", or the raw code if unknown.
    """
    return RISEFALL_SYMBOLS.get(str(code), str(code))


def _fmt_number(value, precision=0):
    """Format a numeric value with comma separators.

    Args:
        value: Numeric value to format.
        precision: Decimal places (0 = integer).

    Returns:
        Formatted string with commas, e.g. "1,234,567".
    """
    try:
        if precision == 0:
            return f"{int(value):,}"
        return f"{float(value):,.{precision}f}"
    except (TypeError, ValueError):
        return str(value)


def format_table(items, top_n=30, show_premium=False):
    """Format ETF items as a Markdown table.

    Args:
        items: List of ETF item dicts.
        top_n: Maximum number of rows to include.
        show_premium: If True, add premium/discount rate column.

    Returns:
        Markdown table string.
    """
    if show_premium:
        header = "| 종목코드 | 종목명 | 현재가 | NAV | 괴리율 | 신호 | 등락 | 등락률(%) | 거래량 | 시가총액 | 3개월 수익률(%) |"
        separator = "|---|---|---:|---:|---:|:---:|:---:|---:|---:|---:|---:|"
    else:
        header = "| 종목코드 | 종목명 | 현재가 | NAV | 등락 | 등락률(%) | 거래량 | 시가총액 | 3개월 수익률(%) |"
        separator = "|---|---|---:|---:|:---:|---:|---:|---:|---:|"

    rows = [header, separator]
    for item in items[:top_n]:
        code = item.get("itemcode", "")
        name = item.get("itemname", "")
        now_val = _fmt_number(item.get("nowVal", 0))
        nav = _fmt_number(item.get("nav", 0), precision=2)
        change_val = _fmt_number(item.get("changeVal", 0))
        change_rate = item.get("changeRate", "0")
        symbol = _risefall_symbol(item.get("risefall", "3"))
        quant = _fmt_number(item.get("quant", 0))
        market_sum = _fmt_number(item.get("marketSum", 0))
        three_month = item.get("threeMonthEarnRate", "0")

        change_display = f"{symbol}{change_val} ({change_rate}%)"

        if show_premium:
            rate = calc_premium_rate(item.get("nowVal", 0), item.get("nav", 0))
            rate_str, signal = premium_label(rate)
            rows.append(
                f"| {code} | {name} | {now_val} | {nav} | {rate_str} | {signal} | "
                f"{change_display} | {change_rate} | {quant} | {market_sum} | {three_month} |"
            )
        else:
            rows.append(
                f"| {code} | {name} | {now_val} | {nav} | {change_display} | "
                f"{change_rate} | {quant} | {market_sum} | {three_month} |"
            )

    return "\n".join(rows)


def format_json(items, top_n=30, show_premium=False):
    """Format ETF items as a JSON array string.

    Args:
        items: List of ETF item dicts.
        top_n: Maximum number of items to include.
        show_premium: If True, add premium/discount fields.

    Returns:
        JSON string.
    """
    result = items[:top_n]
    if show_premium:
        enriched = []
        for item in result:
            item_copy = dict(item)
            rate = calc_premium_rate(item.get("nowVal", 0), item.get("nav", 0))
            item_copy["premiumRate"] = round(rate, 4) if rate is not None else None
            _, signal = premium_label(rate)
            item_copy["premiumSignal"] = signal
            enriched.append(item_copy)
        result = enriched
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_csv(items, top_n=30, show_premium=False):
    """Format ETF items as CSV text.

    Args:
        items: List of ETF item dicts.
        top_n: Maximum number of rows to include.
        show_premium: If True, add premium/discount columns.

    Returns:
        CSV string with header row.
    """
    fieldnames = [
        "itemcode",
        "itemname",
        "nowVal",
        "nav",
        "changeVal",
        "changeRate",
        "risefall",
        "quant",
        "marketSum",
        "threeMonthEarnRate",
    ]

    if show_premium:
        fieldnames.insert(4, "premiumRate")
        fieldnames.insert(5, "premiumSignal")

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for item in items[:top_n]:
        row = dict(item)
        if show_premium:
            rate = calc_premium_rate(item.get("nowVal", 0), item.get("nav", 0))
            row["premiumRate"] = round(rate, 4) if rate is not None else ""
            _, signal = premium_label(rate)
            row["premiumSignal"] = signal
        writer.writerow(row)

    return output.getvalue()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def calc_premium_rate(now_val, nav):
    """Calculate premium/discount rate of ETF market price vs NAV.

    Args:
        now_val: Current market price.
        nav: Net Asset Value.

    Returns:
        Premium/discount rate as float percentage, or None if NAV is invalid.
    """
    try:
        now_val = float(now_val)
        nav = float(nav)
        if nav == 0:
            return None
        return ((now_val - nav) / nav) * 100
    except (TypeError, ValueError):
        return None


def premium_label(rate):
    """Return a human-readable label for a premium/discount rate.

    Args:
        rate: Premium/discount rate percentage (float or None).

    Returns:
        Tuple of (formatted_rate_str, signal_label).
    """
    if rate is None:
        return ("N/A", "")
    formatted = f"{rate:+.2f}%"
    abs_rate = abs(rate)
    if abs_rate >= 1.0:
        signal = "⚠️ 경고"
    elif abs_rate >= 0.5:
        signal = "주의"
    else:
        signal = "정상"
    return (formatted, signal)


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        argparse.Namespace with parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Fetch ETF price list from Naver Finance."
    )
    parser.add_argument(
        "--type",
        type=int,
        default=0,
        choices=list(range(ETF_TYPE_MIN, ETF_TYPE_MAX + 1)),
        metavar=f"{ETF_TYPE_MIN}-{ETF_TYPE_MAX}",
        help=(
            "ETF category: 0=전체, 1=국내시장지수, 2=국내업종/테마, "
            "3=국내파생, 4=해외주식, 5=원자재, 6=채권, 7=기타 (default: 0)"
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        metavar="N",
        help="Show top N items (default: 30)",
    )
    parser.add_argument(
        "--sort",
        default="desc",
        choices=["desc", "asc"],
        help="Sort order by market cap: desc or asc (default: desc)",
    )
    parser.add_argument(
        "--format",
        default="table",
        choices=["table", "json", "csv"],
        help="Output format: table, json, or csv (default: table)",
    )
    parser.add_argument(
        "--premium",
        action="store_true",
        help="Show premium/discount rate (NAV vs market price) column",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Main entry point for the CLI.

    Args:
        argv: Argument list. If None, reads from sys.argv.
    """
    args = parse_args(argv)

    # Ensure UTF-8 output on Windows
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except AttributeError:
            pass  # Python < 3.7 fallback

    etf_type_name = ETF_TYPE_NAMES.get(args.type, str(args.type))

    try:
        items = fetch_etf_list(etf_type=args.type, sort_order=args.sort)
    except urllib.error.URLError as exc:
        print(
            f"[Network Error] Failed to connect to Naver Finance API.\n"
            f"오류: {exc.reason if hasattr(exc, 'reason') else exc}\n"
            f"Tip: Check your internet connection and try again."
        )
        sys.exit(1)
    except TimeoutError as exc:
        print(
            f"[Timeout Error] Request timed out after {TIMEOUT_SECONDS} seconds.\n"
            f"오류: {exc}\n"
            f"Tip: Try again later."
        )
        sys.exit(1)
    except ValueError as exc:
        raw_hint = str(exc)[:200]
        print(
            f"[Parse Error] Failed to parse API response.\n"
            f"오류: {exc}\n"
            f"Raw response (partial): {raw_hint}"
        )
        sys.exit(1)

    fmt = args.format
    show_premium = args.premium
    if fmt == "json":
        output = format_json(items, top_n=args.top, show_premium=show_premium)
    elif fmt == "csv":
        output = format_csv(items, top_n=args.top, show_premium=show_premium)
    else:
        premium_label_str = " (괴리율 포함)" if show_premium else ""
        header = (
            f"## ETF 시세 - {etf_type_name} "
            f"(시가총액 {args.sort.upper()}, 상위 {args.top}개){premium_label_str}\n"
        )
        output = header + format_table(
            items, top_n=args.top, show_premium=show_premium
        )

    print(output)


if __name__ == "__main__":
    main()
