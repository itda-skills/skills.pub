"""행정규칙 검색 CLI — 법제처 DRF Open API (target=admrul).

SPEC: SPEC-LAW-004 FR-022

사용법:
    python3 search_admrul.py --query "개인정보"
    python3 search_admrul.py --query "지침" --kind 고시
    python3 search_admrul.py --query "지침" --format json
    python3 search_admrul.py --query "지침" --format md
    python3 search_admrul.py --query "지침" --no-cache
"""
from __future__ import annotations

import argparse
import json
import sys

from admrul_api import search_admin_rules
from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_admrul_search_md, format_date, print_results_table


def _print_table(results: list[dict]) -> None:
    """행정규칙 검색 결과를 정렬된 텍스트 테이블로 출력한다."""
    headers = ["행정규칙명", "종류", "소관부처", "발령일자", "ID"]
    rows = [
        [
            r.get("rule_name", ""),
            r.get("rule_type", ""),
            r.get("ministry_name", ""),
            format_date(r.get("issue_date", "")),
            r.get("rule_id", ""),
        ]
        for r in results
    ]
    print_results_table(headers, rows)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 행정규칙을 검색합니다."
    )
    parser.add_argument("--query", required=True, help="검색어")
    parser.add_argument(
        "--search-body",
        action="store_true",
        default=False,
        dest="search_body",
        help="본문 내용 검색 (기본: 행정규칙명 검색)",
    )
    parser.add_argument(
        "--kind",
        default=None,
        help="행정규칙 종류 (예: 훈령, 예규, 고시, 공고, 지침, 기타)",
    )
    parser.add_argument(
        "--ministry",
        default=None,
        help="소관부처명 (예: 고용노동부, 개인정보보호위원회)",
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
        results = search_admin_rules(
            query=args.query,
            oc=oc,
            search_body=args.search_body,
            ministry=args.ministry,
            kind=args.kind,
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
        print(format_admrul_search_md(results))
    else:
        if not results:
            print("검색 결과가 없습니다.")
            return 0
        _print_table(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
