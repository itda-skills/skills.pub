from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_date, format_old_and_new_detail_md
from old_and_new_api import get_old_and_new_detail


def _print_detail_section(
    detail: dict, prefix: str, label: str, article_label: str
) -> None:
    print(f"[{label}]")
    print(f"법령ID: {detail.get(f'{prefix}_law_id', '')}")
    print(f"법령일련번호: {detail.get(f'{prefix}_mst', '')}")
    print(f"공포일자: {format_date(detail.get(f'{prefix}_promulgation_date', ''))}")
    print(f"공포번호: {detail.get(f'{prefix}_promulgation_no', '')}")
    print(f"시행일자: {format_date(detail.get(f'{prefix}_effective_date', ''))}")
    print(f"현행여부: {detail.get(f'{prefix}_current', '')}")
    print(f"제개정구분: {detail.get(f'{prefix}_revision_type', '')}")
    print(f"법종구분: {detail.get(f'{prefix}_law_type', '')}")
    print()

    articles = detail.get(f"{prefix}_articles", [])
    if articles:
        print(f"[{article_label}]")
        for article in articles:
            print(article)
            print()


def _print_text(detail: dict) -> None:
    law_name = detail.get("new_law_name") or detail.get("old_law_name")
    if law_name:
        print(f"[{law_name}]")
        print()

    _print_detail_section(detail, "old", "구법", "구조문")
    _print_detail_section(detail, "new", "신법", "신조문")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 신구법 상세를 조회합니다."
    )
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("--id", help="신구법ID")
    id_group.add_argument("--mst", help="신구법일련번호")
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
        detail = get_old_and_new_detail(
            comparison_id=args.id,
            mst=args.mst,
            oc=oc,
            no_cache=args.no_cache,
        )
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(detail, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(format_old_and_new_detail_md(detail))
    else:
        _print_text(detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
