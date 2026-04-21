"""CLI script for retrieving Korean law articles via 법제처 DRF Open API.

Usage:
    python3 get_law.py --id 009682
    python3 get_law.py --name "근로기준법"
    python3 get_law.py --name "근로기준법" --article 60
    python3 get_law.py --name "근로기준법" --article "76조의2"
    python3 get_law.py --name "형법" --toc
    python3 get_law.py --name "근로기준법" --format md
    python3 get_law.py --name "형법" --toc --format md
    python3 get_law.py --name "근로기준법" --no-cache
"""
from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError
from law_api import LawAPIError, get_law_detail, resolve_law_id, resolve_oc
from law_formatter import format_law_md

# 한 번에 출력하는 최대 조문 수 (--article / --toc 미사용 시)
_MAX_ARTICLES = 50

# 단일 조문의 최대 출력 글자 수
_MAX_ARTICLE_CHARS = 30000


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _truncate_article_content(content: str) -> str:
    """조문 내용이 _MAX_ARTICLE_CHARS를 초과하면 잘라서 반환한다."""
    if len(content) <= _MAX_ARTICLE_CHARS:
        return content
    return content[:_MAX_ARTICLE_CHARS] + f"\n\n[내용이 너무 깁니다. {len(content):,}자 중 {_MAX_ARTICLE_CHARS:,}자만 표시합니다.]"


def _apply_limits(detail: dict, apply_article_limit: bool) -> tuple[dict, int]:
    """조문 개수 제한 및 내용 길이 제한을 적용한다.

    Returns:
        (제한 적용된 detail, 원본 전체 조문 수)
    """
    articles = detail.get("articles", [])
    total = len(articles)

    # 내용 길이 제한 적용
    truncated_articles = []
    for art in articles:
        art = dict(art)
        art["content"] = _truncate_article_content(art.get("content", ""))
        truncated_articles.append(art)

    if apply_article_limit and total > _MAX_ARTICLES:
        truncated_articles = truncated_articles[:_MAX_ARTICLES]

    result = dict(detail)
    result["articles"] = truncated_articles
    return result, total


def _print_text(detail: dict, toc_only: bool = False) -> None:
    """Print law detail in human-readable text format."""
    law_name = detail.get("law_name", "")
    articles = detail.get("articles", [])

    if law_name:
        print(f"[{law_name}]")
        print()

    if toc_only:
        for art in articles:
            num = art.get("article_number", "")
            title = art.get("title", "")
            if num and title:
                print(f"  제{num}조 ({title})")
            elif num:
                print(f"  제{num}조")
        return

    for art in articles:
        num = art.get("article_number", "")
        title = art.get("title", "")
        content = art.get("content", "")

        if num and title:
            print(f"제{num}조 ({title})")
        elif num:
            print(f"제{num}조")

        if content:
            print(content)
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 법령 본문 또는 특정 조문을 조회합니다."
    )
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("--id", help="법령 ID (숫자)")
    id_group.add_argument("--name", help="법령명 (검색 후 첫 결과 사용)")
    parser.add_argument(
        "--article",
        default=None,
        help="조문 번호 (예: 60, 76조의2, 제14조의3)",
    )
    parser.add_argument(
        "--toc",
        action="store_true",
        default=False,
        help="조문 목록만 출력 (제목만, 본문 제외)",
    )
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
    """CLI entry point. Returns 0 on success, 1 on error."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        oc = resolve_oc(args.oc)
    except MissingOCError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    # 법령 ID 결정
    if args.name:
        try:
            law_id = resolve_law_id(args.name, oc=oc)
        except LawAPIError as exc:
            print(f"오류: {exc}", file=sys.stderr)
            return 1
    else:
        law_id = args.id

    # 법령 상세 조회
    try:
        detail = get_law_detail(law_id, article_no=args.article, oc=oc, no_cache=args.no_cache)
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    # 조문 개수/길이 제한 적용 (--article 또는 --toc 사용 시 제한 없음)
    apply_limit = not args.article and not args.toc
    detail, total = _apply_limits(detail, apply_limit)
    limited_count = len(detail.get("articles", []))

    # 출력
    if args.format == "json":
        print(json.dumps(detail, ensure_ascii=False, indent=2))
        if apply_limit and total > _MAX_ARTICLES:
            print(f"\n# 총 {total}개 조문 중 {_MAX_ARTICLES}개 표시. 전체 조회: --article 또는 --toc 사용",
                  file=sys.stderr)
    elif args.format == "md":
        print(format_law_md(detail, toc_only=args.toc))
        if apply_limit and total > _MAX_ARTICLES:
            print(f"\n> 총 {total}개 조문 중 {_MAX_ARTICLES}개 표시. 전체 조회: `--toc` 또는 `--article` 사용")
    else:
        _print_text(detail, toc_only=args.toc)
        if apply_limit and total > _MAX_ARTICLES:
            print(f"\n[총 {total}개 조문 중 {_MAX_ARTICLES}개 표시. 전체 조회: --toc 또는 --article 사용]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
