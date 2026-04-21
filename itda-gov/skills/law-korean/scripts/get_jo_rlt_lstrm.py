from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_jo_rlt_lstrm_md
from lstrm_api import get_article_legal_term_relations

_MAX_ARTICLE_CONTENT_CHARS = 30000
_DEFAULT_MAX_ITEMS = 20


def _truncate_content(content: str) -> str:
    if len(content) <= _MAX_ARTICLE_CONTENT_CHARS:
        return content
    total = len(content)
    return (
        content[:_MAX_ARTICLE_CONTENT_CHARS]
        + f"\n\n[... 이하 생략 (전체 {total:,}자 중 {_MAX_ARTICLE_CONTENT_CHARS:,}자 표시)]"
    )


def _apply_limits(detail: dict, summary_only: bool, max_items: int) -> tuple[dict, int]:
    result = dict(detail)
    content = detail.get("article_content", "")
    result["article_content"] = "" if summary_only else _truncate_content(content)
    terms = [dict(term) for term in detail.get("linked_terms", [])]
    total = len(terms)
    if total > max_items:
        terms = terms[:max_items]
    result["linked_terms"] = terms
    return result, total


def _print_text(detail: dict) -> None:
    print(f"[{detail.get('law_name', '')} 제{detail.get('article_number', '')}조]")
    print(f"법령ID: {detail.get('law_id', '')}")
    print(f"JO: {detail.get('jo', '')}")
    print(f"연계 용어 개수: {detail.get('term_count', 0)}")
    print()
    content = detail.get("article_content", "")
    if content:
        print(content)
        print()

    for term in detail.get("linked_terms", []):
        print(f"- {term.get('term_name', '')}")
        print(
            f"  용어구분: {term.get('term_type_name', '')} ({term.get('term_type_code', '')})"
        )
        print(f"  MST: {term.get('mst', '')}")
        if term.get("note"):
            print(f"  비고: {term.get('note', '')}")
        print()


def _print_limit_notice(total: int, limit: int, fmt: str) -> None:
    if total <= limit:
        return
    if fmt == "json":
        print(
            f"\n# 총 {total}개 용어 중 {limit}개 표시. 전체 조회: --max-items 값 확대",
            file=sys.stderr,
        )
    elif fmt == "md":
        print(
            f"\n> 총 {total}개 용어 중 {limit}개 표시. 전체 조회: `--max-items` 값 확대"
        )
    else:
        print(
            f"\n[총 {total}개 용어 중 {limit}개 표시. 전체 조회: --max-items 값 확대]"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 조문-법령용어 연계를 조회합니다."
    )
    parser.add_argument("--id", required=True, help="법령 ID")
    parser.add_argument("--jo", required=True, help="조문 JO")
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
    parser.add_argument(
        "--summary-only",
        action="store_true",
        default=False,
        dest="summary_only",
        help="조문 본문 없이 메타데이터만 출력합니다",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=_DEFAULT_MAX_ITEMS,
        dest="max_items",
        help=f"최대 표시 용어 수 (기본: {_DEFAULT_MAX_ITEMS})",
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
        detail = get_article_legal_term_relations(
            law_id=args.id,
            jo=args.jo,
            oc=oc,
            no_cache=args.no_cache,
        )
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    max_items = max(1, args.max_items)
    detail, total = _apply_limits(detail, args.summary_only, max_items)

    if args.format == "json":
        print(json.dumps(detail, ensure_ascii=False, indent=2))
        _print_limit_notice(total, max_items, "json")
    elif args.format == "md":
        print(format_jo_rlt_lstrm_md(detail, summary_only=args.summary_only))
        _print_limit_notice(total, max_items, "md")
    else:
        _print_text(detail)
        _print_limit_notice(total, max_items, "text")

    return 0


if __name__ == "__main__":
    sys.exit(main())
