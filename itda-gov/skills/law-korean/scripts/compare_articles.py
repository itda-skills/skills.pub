from __future__ import annotations

import argparse
import difflib
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError, get_law_detail, search_laws
from law_formatter import format_compare_articles_md

_DEFAULT_MAX_DIFF_LINES = 80


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="두 법령의 특정 조문을 비교합니다.")

    left_group = parser.add_mutually_exclusive_group(required=True)
    left_group.add_argument("--left-id", help="좌측 법령 ID")
    left_group.add_argument("--left-name", help="좌측 법령명")

    right_group = parser.add_mutually_exclusive_group(required=True)
    right_group.add_argument("--right-id", help="우측 법령 ID")
    right_group.add_argument("--right-name", help="우측 법령명")

    parser.add_argument("--left-article", required=True, help="좌측 조문 번호")
    parser.add_argument("--right-article", required=True, help="우측 조문 번호")
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
        help="조문 본문과 raw diff 없이 요약만 출력합니다",
    )
    parser.add_argument(
        "--max-diff-lines",
        type=int,
        default=_DEFAULT_MAX_DIFF_LINES,
        dest="max_diff_lines",
        help=f"최대 표시 diff 줄 수 (기본: {_DEFAULT_MAX_DIFF_LINES})",
    )
    return parser


def _resolve_law_target(law_id: str | None, law_name: str | None, oc: str) -> str:
    if law_name:
        results = search_laws(law_name, oc=oc, display=20)
        for result in results:
            if result.get("law_name") == law_name:
                return str(result.get("law_id", ""))
        raise LawAPIError(f"법령을 찾을 수 없습니다: '{law_name}'")
    return str(law_id)


def _fetch_article(
    law_id: str, article_no: str, oc: str, no_cache: bool, side_label: str
) -> dict[str, str]:
    detail = get_law_detail(law_id, article_no=article_no, oc=oc, no_cache=no_cache)
    articles = detail.get("articles", [])
    if not articles:
        law_name = detail.get("law_name", f"ID {law_id}")
        raise LawAPIError(
            f"{side_label} 조문을 찾을 수 없습니다: {law_name} 제{article_no}조"
        )

    article = articles[0]
    return {
        "law_name": detail.get("law_name", ""),
        "article_number": article.get("article_number", article_no),
        "title": article.get("title", ""),
        "content": article.get("content", ""),
    }


def _render_diff(left_text: str, right_text: str) -> list[str]:
    return list(
        difflib.unified_diff(
            left_text.splitlines(),
            right_text.splitlines(),
            fromfile="left",
            tofile="right",
            lineterm="",
        )
    )


def _summarize_diff(diff_lines: list[str]) -> dict[str, int]:
    added_lines = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    removed_lines = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )
    return {
        "added_lines": added_lines,
        "removed_lines": removed_lines,
    }


def _build_compare_result(left: dict[str, str], right: dict[str, str]) -> dict:
    diff_lines = _render_diff(left.get("content", ""), right.get("content", ""))
    return {
        "left": left,
        "right": right,
        "diff_lines": diff_lines,
        "diff_summary": _summarize_diff(diff_lines),
        "has_diff": bool(diff_lines),
    }


def _apply_summary_only(result: dict, summary_only: bool) -> dict:
    if not summary_only:
        return result

    updated = dict(result)
    updated["left"] = dict(result.get("left", {}))
    updated["right"] = dict(result.get("right", {}))
    updated["left"]["content"] = ""
    updated["right"]["content"] = ""
    updated["diff_lines"] = []
    return updated


def _apply_diff_limit(result: dict, max_diff_lines: int) -> dict:
    updated = dict(result)
    diff_lines = list(result.get("diff_lines", []))
    updated["diff_total_lines"] = len(diff_lines)
    if len(diff_lines) > max_diff_lines:
        updated["diff_lines"] = diff_lines[:max_diff_lines]
        updated["diff_truncated"] = True
    else:
        updated["diff_lines"] = diff_lines
        updated["diff_truncated"] = False
    return updated


def _print_text(result: dict) -> None:
    left = result["left"]
    right = result["right"]
    diff_summary = result.get("diff_summary", {})

    print(f"[left] {left.get('law_name', '')} 제{left.get('article_number', '')}조")
    if left.get("title"):
        print(f"제목: {left.get('title', '')}")
    print(left.get("content", ""))
    print()
    print(f"[right] {right.get('law_name', '')} 제{right.get('article_number', '')}조")
    if right.get("title"):
        print(f"제목: {right.get('title', '')}")
    print(right.get("content", ""))
    print()
    print(
        f"[diff 요약] 추가 {diff_summary.get('added_lines', 0)}줄 / 삭제 {diff_summary.get('removed_lines', 0)}줄"
    )
    if not result.get("diff_lines") and result.get("has_diff"):
        print("[diff 생략 (--summary-only)]")
        return
    print("[diff]")

    diff_lines = result.get("diff_lines", [])
    if diff_lines:
        for line in diff_lines:
            print(line)
        if result.get("diff_truncated"):
            print(
                f"[총 {result.get('diff_total_lines', 0)}줄 diff 중 {len(diff_lines)}줄만 표시. 전체 조회: --max-diff-lines 값 확대]"
            )
    else:
        print("[차이 없음]")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        oc = resolve_oc(args.oc)
    except MissingOCError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    try:
        try:
            left_law_id = _resolve_law_target(args.left_id, args.left_name, oc)
        except LawAPIError as exc:
            raise LawAPIError(f"좌측 {exc}") from exc

        try:
            right_law_id = _resolve_law_target(args.right_id, args.right_name, oc)
        except LawAPIError as exc:
            raise LawAPIError(f"우측 {exc}") from exc

        left = _fetch_article(left_law_id, args.left_article, oc, args.no_cache, "좌측")
        right = _fetch_article(
            right_law_id, args.right_article, oc, args.no_cache, "우측"
        )
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    result = _apply_summary_only(_build_compare_result(left, right), args.summary_only)
    result = _apply_diff_limit(result, max(1, args.max_diff_lines))

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(format_compare_articles_md(result, summary_only=args.summary_only))
    else:
        _print_text(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
