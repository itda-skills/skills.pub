from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import (
    format_date,
    format_old_and_new_search_md,
    print_results_table,
)
from old_and_new_api import search_old_and_new


def _print_table(results: list[dict]) -> None:
    headers = [
        "신구법명",
        "공포일자",
        "시행일자",
        "제개정구분",
        "소관부처",
        "법령종류",
        "ID",
    ]
    rows = [
        [
            r.get("comparison_name", ""),
            format_date(r.get("promulgation_date", "")),
            format_date(r.get("effective_date", "")),
            r.get("revision_type", ""),
            r.get("ministry_name", ""),
            r.get("law_type", ""),
            r.get("comparison_id", ""),
        ]
        for r in results
    ]
    print_results_table(headers, rows)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 신구법 목록을 검색합니다."
    )
    parser.add_argument("--query", required=True, help="검색어")
    parser.add_argument(
        "--display", type=int, default=20, help="결과 수 (기본: 20, 최대: 100)"
    )
    parser.add_argument("--page", type=int, default=1, help="페이지 번호 (기본: 1)")
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
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        oc = resolve_oc(args.oc)
    except MissingOCError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    try:
        results = search_old_and_new(
            query=args.query,
            oc=oc,
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
        print(format_old_and_new_search_md(results))
    else:
        if not results:
            print("검색 결과가 없습니다.")
            return 0
        _print_table(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
