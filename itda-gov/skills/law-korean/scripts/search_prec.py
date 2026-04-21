"""판례 검색 CLI — 법제처 DRF Open API (target=prec).

SPEC: SPEC-LAW-004 FR-020

사용법:
    python3 search_prec.py --query "임금청구"
    python3 search_prec.py --query "손해배상" --court 대법원
    python3 search_prec.py --query "임금" --date-from 20200101 --date-to 20211231
    python3 search_prec.py --query "임금" --format json
    python3 search_prec.py --query "임금" --format md
    python3 search_prec.py --query "임금" --no-cache
"""
from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_date, format_prec_search_md, print_results_table
from prec_api import search_precedents


def _print_table(results: list[dict]) -> None:
    """판례 검색 결과를 정렬된 텍스트 테이블로 출력한다."""
    headers = ["판례명", "사건번호", "법원명", "선고일자", "판례ID"]
    rows = [
        [
            r.get("case_name", ""),
            r.get("case_no", ""),
            r.get("court_name", ""),
            format_date(r.get("decision_date", "")),
            r.get("prec_id", ""),
        ]
        for r in results
    ]
    print_results_table(headers, rows)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 판례를 검색합니다."
    )
    parser.add_argument("--query", required=True, help="검색어 (판례명 또는 키워드)")
    parser.add_argument(
        "--search-body",
        action="store_true",
        default=False,
        dest="search_body",
        help="본문 내용 검색 (기본: 판례명 검색)",
    )
    parser.add_argument(
        "--court",
        default=None,
        help="법원명 (예: 대법원, 헌법재판소, 각급법원)",
    )
    parser.add_argument(
        "--date-from",
        default=None,
        dest="date_from",
        help="선고일자 시작 (YYYYMMDD)",
    )
    parser.add_argument(
        "--date-to",
        default=None,
        dest="date_to",
        help="선고일자 종료 (YYYYMMDD)",
    )
    parser.add_argument(
        "--case-no",
        default=None,
        dest="case_no",
        help="사건번호 필터",
    )
    parser.add_argument(
        "--display",
        type=int,
        default=20,
        help="결과 수 (기본: 20, 최대: 100)",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="페이지 번호 (기본: 1)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "md"],
        default="table",
        help="출력 형식 (table/json/md, 기본: table)",
    )
    parser.add_argument(
        "--oc",
        default=None,
        help="법제처 OC (사용자 ID). 기본: LAW_API_OC 환경변수 또는 'test'",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        dest="no_cache",
        help="캐시를 사용하지 않고 항상 API를 직접 호출합니다",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점. 성공 시 0, 오류 시 1을 반환한다."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        oc = resolve_oc(args.oc)
    except MissingOCError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    try:
        results = search_precedents(
            query=args.query,
            oc=oc,
            search_body=args.search_body,
            court=args.court,
            date_from=args.date_from,
            date_to=args.date_to,
            case_no=args.case_no,
            display=args.display,
            page=args.page,
            no_cache=args.no_cache,
        )
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(format_prec_search_md(results))
    else:
        if not results:
            print("검색 결과가 없습니다.")
            return 0
        _print_table(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
