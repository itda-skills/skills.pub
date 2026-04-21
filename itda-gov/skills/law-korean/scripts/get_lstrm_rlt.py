from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_lstrm_rlt_md
from lstrm_api import get_legal_term_relations


def _print_text(detail: dict) -> None:
    print(f"[{detail.get('term_name', '')}]")
    if detail.get("note"):
        print(f"비고: {detail.get('note', '')}")
    print(f"연계 개수: {detail.get('relation_count', 0)}")
    print()

    for relation in detail.get("relations", []):
        print(f"- {relation.get('everyday_term_name', '')}")
        print(
            f"  관계: {relation.get('relation_name', '')} ({relation.get('relation_code', '')})"
        )
        print(f"  MST: {relation.get('related_mst', '')}")
        print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 법령용어 관계를 조회합니다."
    )
    parser.add_argument("--mst", required=True, help="법령용어 MST")
    parser.add_argument(
        "--format",
        choices=["text", "json", "md"],
        default="text",
        help="출력 형식 (text/json/md, 기본: text)",
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
        detail = get_legal_term_relations(
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
        print(format_lstrm_rlt_md(detail))
    else:
        _print_text(detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
