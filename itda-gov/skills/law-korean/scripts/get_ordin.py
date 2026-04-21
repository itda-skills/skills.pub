"""자치법규 상세 조회 CLI — 법제처 DRF Open API (target=ordin).

SPEC: SPEC-LAW-004 FR-025

사용법:
    python3 get_ordin.py --id O001
    python3 get_ordin.py --id O001 --format json
    python3 get_ordin.py --id O001 --format md
    python3 get_ordin.py --id O001 --no-cache
"""
from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_date, format_ordin_detail_md
from ordin_api import get_ordinance_detail


def _print_text(detail: dict) -> None:
    """자치법규 상세 정보를 텍스트 형식으로 출력한다."""
    ordin_name = detail.get("ordin_name", "")
    if ordin_name:
        print(f"[{ordin_name}]")
        print()

    ordin_type = detail.get("ordin_type", "")
    org = detail.get("org_name", "")
    promulgate_date = format_date(detail.get("promulgate_date", ""))
    effective_date = format_date(detail.get("effective_date", ""))

    if ordin_type:
        print(f"종류: {ordin_type}")
    if org:
        print(f"기관명: {org}")
    if promulgate_date:
        print(f"공포일자: {promulgate_date}")
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
        description="법제처 Open API로 자치법규 상세 정보를 조회합니다."
    )
    parser.add_argument("--id", required=True, help="자치법규ID")
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
        detail = get_ordinance_detail(args.id, oc=oc, no_cache=args.no_cache)
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(detail, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(format_ordin_detail_md(detail))
    else:
        _print_text(detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
