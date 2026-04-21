#!/usr/bin/env python3
"""국가통계 수집 CLI — KOSIS 국가통계포털.

제안서/사업계획서에 필요한 통계 데이터를 수집하여 JSON/Table로 출력.

사용법:
    python3 scripts/collect_stats.py search --keyword "인구"
    python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1B04005N --period year --recent 3
    python3 scripts/collect_stats.py data --org-id 101 --tbl-id DT_1B04005N --start 2020 --end 2024
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import env_loader
import kosis_api

# KOSIS API 키 환경변수
_KEY_VAR = "KOSIS_API_KEY"

_SETUP_GUIDE = (
    "KOSIS_API_KEY가 설정되지 않았습니다.\n\n"
    "KOSIS 인증키 발급 방법:\n"
    "  1. https://kosis.kr 회원가입\n"
    "  2. https://kosis.kr/openapi/ 에서 서비스 신청 (자동 승인)\n\n"
    "설정 방법 (택 1):\n"
    '  claude config set env.KOSIS_API_KEY "발급받은_인증키"\n'
    "  또는 .env 파일에: KOSIS_API_KEY=발급받은_인증키\n"
)


def _get_api_key(cli_arg: str | None = None) -> str:
    """KOSIS API 키 해석."""
    return env_loader.resolve_api_key(_KEY_VAR, cli_arg, _SETUP_GUIDE)


def cmd_search(args: argparse.Namespace) -> int:
    """키워드로 통계표 검색."""
    api_key = _get_api_key(args.api_key)
    results = kosis_api.search_statistics(
        api_key, args.keyword, result_count=args.count,
    )

    if args.format == "table":
        _print_search_table(results, args.keyword)
    else:
        output: list[dict[str, str]] = []
        for r in results:
            output.append({
                "org_id": r.get("ORG_ID", ""),
                "org_name": r.get("ORG_NM", ""),
                "tbl_id": r.get("TBL_ID", ""),
                "tbl_name": r.get("TBL_NM", ""),
                "stat_name": r.get("STAT_NM", ""),
                "period_range": f"{r.get('STRT_PRD_DE', '')}~{r.get('END_PRD_DE', '')}",
            })
        print(json.dumps(
            {"status": "ok", "keyword": args.keyword, "count": len(output), "results": output},
            ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    """통계자료 조회."""
    api_key = _get_api_key(args.api_key)
    prd_se = kosis_api.PERIOD_CODES.get(args.period, "Y")

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "org_id": args.org_id,
        "tbl_id": args.tbl_id,
        "itm_id": args.item or "ALL",
        "obj_l1": args.obj1 or "ALL",
        "obj_l2": args.obj2 or "",
        "prd_se": prd_se,
    }

    if args.recent:
        kwargs["new_est_prd_cnt"] = args.recent
    else:
        if args.start:
            kwargs["start_prd_de"] = args.start
        if args.end:
            kwargs["end_prd_de"] = args.end

    raw_data = kosis_api.get_statistics_data(**kwargs)
    summarized = kosis_api.summarize_data(raw_data)

    if args.format == "table":
        _print_data_table(summarized)
    else:
        print(json.dumps(
            {"status": "ok", "org_id": args.org_id, "tbl_id": args.tbl_id,
             "count": len(summarized), "data": summarized},
            ensure_ascii=False, indent=2,
        ))
    return 0


# --- 테이블 출력 헬퍼 ---

def _print_search_table(results: list[dict[str, Any]], keyword: str) -> None:
    """검색 결과를 테이블로 출력."""
    print(f"\n통계표 검색: '{keyword}' — {len(results)}건\n")
    print(f"{'기관':<8} {'orgId':<8} {'tblId':<20} {'통계표명':<50}")
    print("-" * 86)
    for r in results:
        org = r.get("ORG_NM", "")[:6]
        org_id = r.get("ORG_ID", "")
        tbl_id = r.get("TBL_ID", "")
        tbl_nm = r.get("TBL_NM", "")[:48]
        print(f"{org:<8} {org_id:<8} {tbl_id:<20} {tbl_nm:<50}")
    print()


def _print_data_table(data: list[dict[str, Any]]) -> None:
    """통계 데이터를 테이블로 출력."""
    if not data:
        print("\n(데이터 없음)\n")
        return

    # 테이블명 출력
    tbl_name = data[0].get("table_name", "") if data else ""
    if tbl_name:
        print(f"\n{tbl_name}\n")

    print(f"{'시점':<10} {'분류':<15} {'항목':<20} {'값':>15} {'단위':<6}")
    print("-" * 66)
    for row in data:
        period = row.get("period", "")
        cat = (row.get("category", "") or "")[:13]
        item = (row.get("item_name", "") or "")[:18]
        val = row.get("value")
        unit = row.get("unit", "")
        val_str = f"{val:,.0f}" if val is not None else "-"
        print(f"{period:<10} {cat:<15} {item:<20} {val_str:>15} {unit:<6}")
    print()


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서 생성."""
    parser = argparse.ArgumentParser(
        description="국가통계 수집 — KOSIS 국가통계포털",
    )
    parser.add_argument("--api-key", default=None, help="KOSIS API 키")
    parser.add_argument(
        "--format", choices=["json", "table"], default="json",
        help="출력 형식 (기본: json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="키워드로 통계표 검색")
    p_search.add_argument("--keyword", "-k", required=True, help="검색 키워드")
    p_search.add_argument("--count", "-n", type=int, default=10, help="결과 수 (기본 10)")

    # data
    p_data = sub.add_parser("data", help="통계자료 조회")
    p_data.add_argument("--org-id", required=True, help="기관 코드 (예: 101)")
    p_data.add_argument("--tbl-id", required=True, help="통계표 ID (예: DT_1B04005N)")
    p_data.add_argument("--item", default=None, help="항목 ID (기본: ALL)")
    p_data.add_argument("--obj1", default=None, help="1차 분류값 (기본: ALL)")
    p_data.add_argument("--obj2", default=None, help="2차 분류값")
    p_data.add_argument(
        "--period", "-p", choices=list(kosis_api.PERIOD_CODES.keys()),
        default="year", help="수록주기 (기본: year)",
    )
    p_data.add_argument("--start", default=None, help="시작 시점 (예: 2020)")
    p_data.add_argument("--end", default=None, help="종료 시점 (예: 2024)")
    p_data.add_argument("--recent", type=int, default=None, help="최근 N개 시점")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        commands = {"search": cmd_search, "data": cmd_data}
        return commands[args.command](args)

    except env_loader.MissingAPIKeyError as e:
        print(json.dumps(
            {"status": "error", "error": "config", "detail": str(e)},
            ensure_ascii=False,
        ))
        return 1
    except kosis_api.KOSISAPIError as e:
        print(json.dumps(
            {"status": "error", "error": "api", "detail": str(e),
             "error_code": e.error_code},
            ensure_ascii=False,
        ))
        return 1


if __name__ == "__main__":
    sys.exit(main())
