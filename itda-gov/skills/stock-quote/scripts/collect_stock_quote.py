#!/usr/bin/env python3
"""주식시세 수집 CLI — 금융위원회 주식시세정보 (data.go.kr 15094808).

사용법:
    python3 scripts/collect_stock_quote.py quote 삼성전자
    python3 scripts/collect_stock_quote.py quote 005930 --format csv
    python3 scripts/collect_stock_quote.py history 005930 --from 2026-05-01 --to 2026-05-14
    python3 scripts/collect_stock_quote.py search 삼성 --format table
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime, timedelta
from typing import Any

import env_loader
import stock_quote_api

# API 키 환경변수
_KEY_VAR = "KO_DATA_API_KEY"

# 활용신청 안내 URL
_APPLY_URL = "https://www.data.go.kr/data/15094808/openapi.do"

# 설정 오류 안내 메시지
_SETUP_GUIDE = (
    "KO_DATA_API_KEY가 설정되지 않았습니다.\n\n"
    "주식시세정보 API 키 발급 방법:\n"
    f"  1. {_APPLY_URL} 접속\n"
    "  2. 동일 data.go.kr 계정으로 15094808 활용신청(자동승인) 필요\n"
    "  3. 발급된 키로 환경변수 설정:\n"
    '     claude config set env.KO_DATA_API_KEY "발급받은_키"\n'
    "  또는 .env 파일에: KO_DATA_API_KEY=발급받은_키\n"
)

# 고정 디스클레이머 (P-6, 자본시장법 §6·§17·§101·§176·§178·§178의2·§445)
# SPEC §3 불변 고정 문구 — 이 문자열은 절대 변경하지 않는다 (AC-6).
# 출처(15094808)·비실시간(T+1) 정보는 source·data_recency 필드에 별도 제공.
# @MX:WARN: [AUTO] 모든 출력 경로에 disclaimer를 부착하는 지점.
# @MX:REASON: 자본시장법 §178 등 규제 대응. 정상/에러/ambiguous 모든 경로에 누락 없이 첨부 필요.
_DISCLAIMER = "정보 제공이며 투자자문이 아님, 투자판단·책임은 본인"

# 출처 — 15094808 출처 및 비실시간 정보를 포함 (SPEC 정보 손실 없음)
_SOURCE = "금융위원회 주식시세정보 (data.go.kr 15094808)"


def _print_footer(prefix: str = "") -> None:
    """non-JSON 출력 공통 footer — 출처·비실시간·고정 디스클레이머 일관 부착 (P-5/P-6, MEDIUM #5)."""
    print(f"{prefix}출처: {_SOURCE}")
    print(f"{prefix}데이터: 일 1회 갱신 · 비실시간 (기준일자 basDt 기준)")
    print(f"{prefix}주의: {_DISCLAIMER}")


def _get_api_key(cli_arg: str | None = None) -> str:
    """API 키 해석."""
    return env_loader.resolve_api_key(_KEY_VAR, cli_arg, _SETUP_GUIDE)


def _to_yyyymmdd(date_str: str) -> str:
    """YYYY-MM-DD → YYYYMMDD 변환.

    Args:
        date_str: YYYY-MM-DD 형식 날짜.

    Returns:
        YYYYMMDD 형식 문자열.

    Raises:
        ValueError: 형식 불일치.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            f"날짜 형식이 올바르지 않습니다: '{date_str}'. YYYY-MM-DD 형식으로 입력하세요."
        ) from exc
    return dt.strftime("%Y%m%d")


def _to_end_bas_dt(date_str: str) -> str:
    """--to 날짜를 API endBasDt 파라미터로 변환 (+1일, inclusive UX).

    API endBasDt는 미포함(exclusive)이므로 --to 날짜에 +1일 적용.

    Args:
        date_str: YYYY-MM-DD 형식 종료일 (inclusive).

    Returns:
        YYYYMMDD 형식 +1일 문자열.
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    return dt.strftime("%Y%m%d")


def _make_envelope(
    status: str,
    *,
    data: dict | None = None,
    bas_dt: str | None = None,
    candidates: list | None = None,
    error: str | None = None,
    **extra: Any,
) -> dict:
    """출력 envelope 생성 — 모든 경로에 disclaimer/source 부착.

    Args:
        status: "ok" | "ambiguous" | "error".
        data: 시세 item 딕셔너리 (resolved 시).
        bas_dt: 기준일자 (data_recency 포함 시).
        candidates: ambiguous 후보 목록.
        error: 에러 타입 문자열.
        **extra: 추가 필드.

    Returns:
        envelope 딕셔너리.
    """
    envelope: dict[str, Any] = {
        "status": status,
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }

    if data is not None:
        envelope.update(data)

    if bas_dt:
        envelope["data_recency"] = (
            f"기준일자 {bas_dt} 시세 · 일 1회 갱신 · 비실시간"
        )

    if candidates is not None:
        envelope["candidates"] = candidates

    if error is not None:
        envelope["error"] = error

    envelope.update(extra)
    return envelope


def _write_csv(rows: list[dict], headers: list[str]) -> None:
    """rows를 UTF-8 BOM CSV로 stdout에 출력.

    RFC 4180 준수: \\r\\n 줄바꿈, 헤더 행 포함, QUOTE_MINIMAL.
    엑셀 한글 호환을 위해 UTF-8 BOM 선행 출력.
    테스트 환경(StringIO)에서도 동작하도록 print로 BOM 출력.
    """
    # BOM 출력: 실제 stdout은 buffer를 통해, StringIO mock은 print로
    bom = "﻿"
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=headers,
        extrasaction="ignore",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\r\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    content = bom + buf.getvalue()
    print(content, end="")


def cmd_quote(args: argparse.Namespace) -> int:
    """현재가 조회 (quote 서브커맨드).

    단일 종목 resolve 후 시세 반환. ambiguous/not_found도 정상 응답으로 처리.
    """
    try:
        api_key = _get_api_key(getattr(args, "api_key", None))
    except Exception:
        result = _make_envelope(
            "error",
            error="config",
            message=f"KO_DATA_API_KEY 미설정. 활용신청: {_APPLY_URL}",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        resolved = stock_quote_api.resolve_ticker(api_key, args.ticker)
    except stock_quote_api.StockAPIError as exc:
        result = _make_envelope("error", error="api_error", message=str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    if resolved["status"] == "error":
        result = _make_envelope(
            "error",
            error=resolved.get("error_type", "not_found"),
            message=f"'{resolved.get('query', args.ticker)}'에 해당하는 종목을 찾을 수 없습니다.",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if resolved["status"] == "ambiguous":
        result = _make_envelope(
            "ambiguous",
            candidates=resolved["candidates"],
            message=f"'{resolved.get('query', args.ticker)}'가 복수 종목과 일치합니다. 종목코드로 다시 조회하세요.",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # resolved
    bas_dt = resolved.get("basDt", "")
    item_data = {k: v for k, v in resolved.items() if k != "status"}
    result = _make_envelope("ok", data=item_data, bas_dt=bas_dt)

    fmt = getattr(args, "format", "json")
    if fmt == "csv":
        fields = [
            "srtnCd", "itmsNm", "mrktCtg", "basDt",
            "clpr", "vs", "fltRt", "mkp", "hipr", "lopr",
            "trqu", "trPrc", "lstgStCnt", "mrktTotAmt",
            "source", "data_recency", "disclaimer",
        ]
        _write_csv([result], fields)
    elif fmt == "table":
        _print_quote_table(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """과거 시세 조회 (history 서브커맨드).

    --from/--to 범위 조회. --to는 inclusive (API에 +1일 전달).
    """
    try:
        api_key = _get_api_key(getattr(args, "api_key", None))
    except Exception:
        result = _make_envelope(
            "error",
            error="config",
            message=f"KO_DATA_API_KEY 미설정. 활용신청: {_APPLY_URL}",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    # 종목 단일 확정 — quote와 동일하게 resolve_ticker 경유 (ambiguous 혼입 방지)
    try:
        resolved = stock_quote_api.resolve_ticker(api_key, args.ticker)
    except stock_quote_api.StockAPIError as exc:
        result = _make_envelope("error", error="api_error", message=str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if resolved["status"] == "error":
        result = _make_envelope(
            "error",
            error=resolved.get("error_type", "not_found"),
            message=f"'{resolved.get('query', args.ticker)}'에 해당하는 종목을 찾을 수 없습니다.",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if resolved["status"] == "ambiguous":
        result = _make_envelope(
            "ambiguous",
            candidates=resolved["candidates"],
            message=f"'{resolved.get('query', args.ticker)}'가 복수 종목과 일치합니다. 종목코드로 다시 조회하세요.",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    _srtn_cd = resolved.get("srtnCd", "")

    # 날짜 검증 — ValueError를 envelope로 (AC-6: traceback 금지)
    try:
        begin_bas_dt = _to_yyyymmdd(args.date_from)
        end_bas_dt = _to_end_bas_dt(args.date_to)
    except ValueError as exc:
        result = _make_envelope("error", error="validation", message=str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        resp = stock_quote_api.get_stock_price(
            api_key,
            like_srtn_cd=_srtn_cd,
            begin_bas_dt=begin_bas_dt,
            end_bas_dt=end_bas_dt,
            rows=1000,
        )
    except stock_quote_api.StockAPIError as exc:
        result = _make_envelope("error", error="api_error", message=str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    items = resp["items"]
    if not items:
        result = _make_envelope(
            "error",
            error="not_found",
            message=f"'{args.ticker}' 과거 시세를 찾을 수 없습니다.",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    result = _make_envelope(
        "ok",
        ticker=args.ticker,
        date_from=args.date_from,
        date_to=args.date_to,
        count=len(items),
        items=items,
    )

    fmt = getattr(args, "format", "json")
    if fmt == "csv":
        fields = [
            "basDt", "srtnCd", "itmsNm", "mrktCtg",
            "clpr", "vs", "fltRt", "mkp", "hipr", "lopr",
            "trqu", "trPrc", "lstgStCnt", "mrktTotAmt",
        ]
        _write_csv(items, fields)
        _print_footer("# ")
    elif fmt == "table":
        _print_history_table(items, args.ticker)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """종목 검색 (search 서브커맨드).

    종목명 부분 일치로 목록 반환.
    """
    try:
        api_key = _get_api_key(getattr(args, "api_key", None))
    except Exception:
        result = _make_envelope(
            "error",
            error="config",
            message=f"KO_DATA_API_KEY 미설정. 활용신청: {_APPLY_URL}",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    try:
        resp = stock_quote_api.get_stock_price(
            api_key,
            like_itms_nm=args.keyword,
            rows=100,
        )
    except stock_quote_api.StockAPIError as exc:
        result = _make_envelope("error", error="api_error", message=str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    items = resp["items"]
    # dedupe by srtnCd
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        code = item.get("srtnCd", "")
        if code not in seen:
            seen.add(code)
            unique.append(item)

    result = _make_envelope(
        "ok",
        keyword=args.keyword,
        count=len(unique),
        results=unique,
    )

    fmt = getattr(args, "format", "json")
    if fmt == "csv":
        fields = ["srtnCd", "itmsNm", "mrktCtg", "basDt", "clpr", "trqu"]
        _write_csv(unique, fields)
        _print_footer("# ")
    elif fmt == "table":
        _print_search_table(unique, args.keyword)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# --- 테이블 출력 헬퍼 ---

def _print_quote_table(item: dict) -> None:
    """시세를 테이블로 출력."""
    print(f"\n[{item.get('itmsNm', '')}] {item.get('mrktCtg', '')} — {item.get('basDt', '')}\n")
    fields = [
        ("종가", "clpr"), ("시가", "mkp"), ("고가", "hipr"), ("저가", "lopr"),
        ("대비", "vs"), ("등락률", "fltRt"), ("거래량", "trqu"),
    ]
    for label, key in fields:
        val = item.get(key, "-")
        print(f"  {label:<8}: {val}")
    print(f"\n  {item.get('data_recency', '')}")
    _print_footer()
    print()


def _print_history_table(items: list[dict], ticker: str) -> None:
    """과거 시세를 테이블로 출력."""
    print(f"\n[{ticker}] 과거 시세 — {len(items)}건\n")
    print(f"{'기준일자':<12} {'종가':>10} {'시가':>10} {'고가':>10} {'저가':>10} {'등락률':>8}")
    print("-" * 60)
    for item in sorted(items, key=lambda x: x.get("basDt", ""), reverse=True):
        print(
            f"{item.get('basDt',''):<12} "
            f"{item.get('clpr',''):>10} "
            f"{item.get('mkp',''):>10} "
            f"{item.get('hipr',''):>10} "
            f"{item.get('lopr',''):>10} "
            f"{item.get('fltRt',''):>8}"
        )
    _print_footer()
    print()


def _print_search_table(items: list[dict], keyword: str) -> None:
    """검색 결과를 테이블로 출력."""
    print(f"\n'{keyword}' 검색 — {len(items)}건\n")
    print(f"{'단축코드':<10} {'종목명':<20} {'시장':<8} {'기준일자':<12} {'종가':>10}")
    print("-" * 62)
    for item in items:
        print(
            f"{item.get('srtnCd',''):<10} "
            f"{item.get('itmsNm',''):<20} "
            f"{item.get('mrktCtg',''):<8} "
            f"{item.get('basDt',''):<12} "
            f"{item.get('clpr',''):>10}"
        )
    _print_footer()
    print()


def _add_common(p: argparse.ArgumentParser) -> None:
    """공용 옵션을 파서에 추가.

    argparse.SUPPRESS로 기본값을 설정하지 않아 메인 파서 set_defaults가
    서브파서 기본값을 덮어쓰지 않도록 한다 (REQ 패턴).
    """
    p.add_argument(
        "--api-key",
        dest="api_key",
        default=argparse.SUPPRESS,
        help="KO_DATA_API_KEY 직접 지정",
    )
    p.add_argument(
        "--format",
        choices=["json", "table", "csv"],
        default=argparse.SUPPRESS,
        help="출력 형식 (기본: json)",
    )


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서 생성.

    --format 등 공용 옵션이 서브커맨드 앞/뒤 양쪽에서 동작하도록
    _add_common() + SUPPRESS + set_defaults 패턴 적용.
    """
    parser = argparse.ArgumentParser(
        description="주식시세 수집 — 금융위원회 주식시세정보 (data.go.kr 15094808)",
    )
    parser.set_defaults(api_key=None, format="json")
    _add_common(parser)

    sub = parser.add_subparsers(dest="command", required=True)

    # quote 서브커맨드
    p_quote = sub.add_parser("quote", help="현재가 조회")
    _add_common(p_quote)
    p_quote.add_argument("ticker", help="종목코드(6자리) 또는 종목명")

    # history 서브커맨드
    p_history = sub.add_parser("history", help="과거 시세 조회")
    _add_common(p_history)
    p_history.add_argument("ticker", help="종목코드(6자리) 또는 종목명")
    p_history.add_argument("--from", dest="date_from", required=True, help="시작일 (YYYY-MM-DD)")
    p_history.add_argument("--to", dest="date_to", required=True, help="종료일 포함 (YYYY-MM-DD)")

    # search 서브커맨드
    p_search = sub.add_parser("search", help="종목 검색")
    _add_common(p_search)
    p_search.add_argument("keyword", help="종목명 검색어 (부분 일치)")

    return parser


_COMMAND_MAP = {
    "quote": cmd_quote,
    "history": cmd_history,
    "search": cmd_search,
}


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점.

    Args:
        argv: 커맨드라인 인자 목록. None이면 sys.argv[1:] 사용.

    Returns:
        종료 코드 (0 정상, 1 오류).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _COMMAND_MAP.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    # AC-6/P-6 최후 안전망: 어떤 예외도 traceback 대신 disclaimer envelope로.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — CLI 경계
        _safety = _make_envelope("error", error="unexpected", message=str(exc))
        print(json.dumps(_safety, ensure_ascii=False, indent=2))
        sys.exit(1)
