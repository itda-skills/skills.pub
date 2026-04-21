"""행정규칙 상세 조회 CLI — 법제처 DRF Open API (target=admrul).

SPEC: SPEC-LAW-004 FR-023

사용법:
    python3 get_admrul.py --id R001
    python3 get_admrul.py --id R001 --format json
    python3 get_admrul.py --id R001 --format md
    python3 get_admrul.py --id R001 --no-cache
"""
from __future__ import annotations

import argparse
import json
import sys

from admrul_api import get_admin_rule_detail
from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_admrul_detail_md, format_date


def _print_text(detail: dict) -> None:
    """행정규칙 상세 정보를 텍스트 형식으로 출력한다."""
    rule_name = detail.get("rule_name", "")
    if rule_name:
        print(f"[{rule_name}]")
        print()

    rule_type = detail.get("rule_type", "")
    ministry = detail.get("ministry_name", "")
    issue_date = format_date(detail.get("issue_date", ""))
    issue_no = detail.get("issue_no", "")
    effective_date = format_date(detail.get("effective_date", ""))

    if rule_type:
        print(f"종류: {rule_type}")
    if ministry:
        print(f"소관부처: {ministry}")
    if issue_date:
        print(f"발령일자: {issue_date}")
    if issue_no:
        print(f"발령번호: {issue_no}")
    if effective_date:
        print(f"시행일자: {effective_date}")
    print()

    content = detail.get("content", "")
    if content:
        print("[내용]")
        print(content)
        print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 행정규칙 상세 정보를 조회합니다."
    )
    parser.add_argument("--id", required=True, help="행정규칙ID")
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
        detail = get_admin_rule_detail(args.id, oc=oc, no_cache=args.no_cache)
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(detail, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(format_admrul_detail_md(detail))
    else:
        _print_text(detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
