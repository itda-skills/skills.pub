from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_lstrm_rlt_jo_md
from lstrm_api import get_legal_term_article_relations

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
    articles = []
    source_articles = detail.get("linked_articles", [])
    total = len(source_articles)
    for article in source_articles:
        item = dict(article)
        content = item.get("article_content", "")
        item["article_content"] = "" if summary_only else _truncate_content(content)
        articles.append(item)
    if total > max_items:
        articles = articles[:max_items]
    result["linked_articles"] = articles
    return result, total


def _print_text(detail: dict) -> None:
    print(f"[{detail.get('term_name', '')}]")
    if detail.get("note"):
        print(f"비고: {detail.get('note', '')}")
    print(f"연계 조문 개수: {detail.get('article_count', 0)}")
    print()

    for article in detail.get("linked_articles", []):
        print(
            f"[{article.get('law_name', '')} 제{article.get('article_number', '')}조]"
        )
        print(
            f"용어구분: {article.get('term_type_name', '')} ({article.get('term_type_code', '')})"
        )
        print(f"법령ID: {article.get('law_id', '')}")
        print(f"JO: {article.get('jo', '')}")
        content = article.get("article_content", "")
        if content:
            print(content)
        print()


def _print_limit_notice(total: int, limit: int, fmt: str) -> None:
    if total <= limit:
        return
    if fmt == "json":
        print(
            f"\n# 총 {total}개 조문 중 {limit}개 표시. 전체 조회: --max-items 값 확대",
            file=sys.stderr,
        )
    elif fmt == "md":
        print(
            f"\n> 총 {total}개 조문 중 {limit}개 표시. 전체 조회: `--max-items` 값 확대"
        )
    else:
        print(
            f"\n[총 {total}개 조문 중 {limit}개 표시. 전체 조회: --max-items 값 확대]"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 법령용어-조문 연계를 조회합니다."
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
        help=f"최대 표시 조문 수 (기본: {_DEFAULT_MAX_ITEMS})",
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
        detail = get_legal_term_article_relations(
            mst=args.mst,
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
        print(format_lstrm_rlt_jo_md(detail, summary_only=args.summary_only))
        _print_limit_notice(total, max_items, "md")
    else:
        _print_text(detail)
        _print_limit_notice(total, max_items, "text")

    return 0


if __name__ == "__main__":
    sys.exit(main())
