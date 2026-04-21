"""CLI script for searching Korean laws via 법제처 DRF Open API.

Usage:
    python3 search_law.py --query "근로기준법"
    python3 search_law.py --query "연차휴가" --search-body
    python3 search_law.py --query "개인정보" --display 20 --format json
    python3 search_law.py --query "화관법" --format md  # 약어 자동 인식
    python3 search_law.py --query "법령" --strict        # 정확 매칭만
    python3 search_law.py --query "법령" --no-cache      # 캐시 우회
"""
from __future__ import annotations

import argparse
import json
import sys

from env_loader import MissingOCError
from law_api import LawAPIError, resolve_oc, smart_search
from law_formatter import format_search_md


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _format_date(raw: str) -> str:
    """Format YYYYMMDD to YYYY-MM-DD, return raw if not 8 digits."""
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw


def _print_table(results: list[dict]) -> None:
    """Print results as a simple aligned text table."""
    if not results:
        return

    # 컬럼 헤더
    headers = ["법령명", "법령종류", "소관부처", "시행일자", "법령ID"]
    keys = ["law_name", "law_type", "ministry", "enforcement_date", "law_id"]

    # 행 수집 (시행일자 변환)
    rows: list[list[str]] = []
    for r in results:
        row = [
            r.get("law_name", ""),
            r.get("law_type", ""),
            r.get("ministry", ""),
            _format_date(r.get("enforcement_date", "")),
            r.get("law_id", ""),
        ]
        rows.append(row)

    # 컬럼 너비 계산 (CJK = 2)
    def display_width(text: str) -> int:
        w = 0
        for ch in text:
            w += 2 if ord(ch) > 127 else 1
        return w

    col_widths = [display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], display_width(cell))

    def pad(text: str, width: int) -> str:
        dw = display_width(text)
        return text + " " * (width - dw)

    # 헤더 출력
    header_line = "  ".join(pad(h, col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))

    for row in rows:
        print("  ".join(pad(cell, col_widths[i]) for i, cell in enumerate(row)))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="법제처 Open API로 법령을 검색합니다."
    )
    parser.add_argument("--query", required=True, help="검색어 (법령명, 약어, 또는 키워드)")
    parser.add_argument(
        "--search-body",
        action="store_true",
        default=False,
        dest="search_body",
        help="본문 내용 검색 (기본: 법령명 검색)",
    )
    parser.add_argument(
        "--display",
        type=int,
        default=10,
        help="결과 수 (기본: 10, 최대: 100)",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="페이지 번호 (기본: 1)",
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
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="폴백 없이 정확 매칭만 수행합니다 (약어 변환/본문 검색 비활성화)",
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

    try:
        results = smart_search(
            query=args.query,
            oc=oc,
            search_body=args.search_body,
            display=args.display,
            page=args.page,
            strict=args.strict,
            no_cache=args.no_cache,
        )
    except LawAPIError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.format == "md":
        print(format_search_md(results))
    else:
        if not results:
            print("검색 결과가 없습니다.")
            return 0
        _print_table(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
