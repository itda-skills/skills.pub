"""법령 체계도 조회 CLI — 법제처 DRF Open API (target=lsStmd).

SPEC: SPEC-LAW-004 FR-026

사용법:
    python3 get_law_tree.py --id 9682
    python3 get_law_tree.py --name "근로기준법"
    python3 get_law_tree.py --id 9682 --format md
    python3 get_law_tree.py --id 9682 --no-cache
"""
from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError, resolve_law_id
from law_formatter import format_law_tree_md, format_law_tree_text
from law_tree_api import get_law_tree


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 법령 체계도를 조회합니다."
    )
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("--id", help="법령 ID (숫자)")
    id_group.add_argument("--name", help="법령명 (검색 후 첫 결과 사용)")
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
    """CLI 진입점. 성공 시 0, 오류 시 1을 반환한다."""
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

    # 체계도 조회
    try:
        tree = get_law_tree(law_id=law_id, oc=oc, no_cache=args.no_cache)
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(tree, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(format_law_tree_md(tree))
    else:
        print(format_law_tree_text(tree))

    return 0


if __name__ == "__main__":
    sys.exit(main())
