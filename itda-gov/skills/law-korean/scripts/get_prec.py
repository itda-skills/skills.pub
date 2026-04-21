"""판례 상세 조회 CLI — 법제처 DRF Open API (target=prec).

SPEC: SPEC-LAW-004 FR-021

사용법:
    python3 get_prec.py --id AAA001
    python3 get_prec.py --id AAA001 --summary-only
    python3 get_prec.py --id AAA001 --format json
    python3 get_prec.py --id AAA001 --format md
    python3 get_prec.py --id AAA001 --no-cache
"""
from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError, resolve_oc
from law_api import LawAPIError
from law_formatter import format_date, format_prec_detail_md
from prec_api import get_precedent_detail

# 판례내용 최대 출력 글자 수
_MAX_FULL_TEXT_CHARS = 30000


def _apply_limits(detail: dict) -> dict:
    """판례내용이 _MAX_FULL_TEXT_CHARS를 초과하면 잘라서 반환한다."""
    full_text = detail.get("full_text", "")
    if len(full_text) <= _MAX_FULL_TEXT_CHARS:
        return detail
    total = len(full_text)
    truncated = full_text[:_MAX_FULL_TEXT_CHARS]
    truncated += f"\n\n[... 이하 생략 (전체 {total:,}자 중 {_MAX_FULL_TEXT_CHARS:,}자 표시)]"
    return {**detail, "full_text": truncated}


def _print_text(detail: dict, summary_only: bool = False) -> None:
    """판례 상세 정보를 텍스트 형식으로 출력한다."""
    case_name = detail.get("case_name", "")
    if case_name:
        print(f"[{case_name}]")
        print()

    case_no = detail.get("case_no", "")
    court = detail.get("court_name", "")
    date = format_date(detail.get("decision_date", ""))
    if case_no:
        print(f"사건번호: {case_no}")
    if court:
        print(f"법원명: {court}")
    if date:
        print(f"선고일자: {date}")
    print()

    summary = detail.get("summary", "")
    if summary:
        print("[판시사항]")
        print(summary)
        print()

    reasoning = detail.get("reasoning", "")
    if reasoning:
        print("[판결요지]")
        print(reasoning)
        print()

    if summary_only:
        return

    ref_articles = detail.get("ref_articles", "")
    if ref_articles:
        print("[참조조문]")
        print(ref_articles)
        print()

    ref_cases = detail.get("ref_cases", "")
    if ref_cases:
        print("[참조판례]")
        print(ref_cases)
        print()

    full_text = detail.get("full_text", "")
    if full_text:
        print("[판례내용]")
        print(full_text)
        print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 판례 상세 정보를 조회합니다."
    )
    parser.add_argument("--id", required=True, help="판례일련번호")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        default=False,
        dest="summary_only",
        help="판시사항+판결요지만 출력 (판례내용 제외)",
    )
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
        detail = get_precedent_detail(args.id, oc=oc, no_cache=args.no_cache)
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    # 길이 제한 적용
    detail = _apply_limits(detail)

    if args.format == "json":
        print(json.dumps(detail, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(format_prec_detail_md(detail, summary_only=args.summary_only))
    else:
        _print_text(detail, summary_only=args.summary_only)

    return 0


if __name__ == "__main__":
    sys.exit(main())
