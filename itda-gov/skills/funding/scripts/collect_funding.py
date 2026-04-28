#!/usr/bin/env python3
"""정부 지원사업 수집 CLI — K-Startup 공공데이터.

창업 및 중소기업 지원사업 공고를 검색하여 JSON/Table로 출력.

사용법:
    python3 scripts/collect_funding.py search --keyword "AI"
    python3 scripts/collect_funding.py search --keyword "스타트업" --active
    python3 scripts/collect_funding.py overview --keyword "청년창업" --year 2026
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import env_loader
import funding_api

# 공공데이터포털 API 키 환경변수
_KEY_VAR = "KO_DATA_API_KEY"

_SETUP_GUIDE = (
    "KO_DATA_API_KEY가 설정되지 않았습니다.\n\n"
    "공공데이터포털 API 키 발급 방법:\n"
    "  1. https://www.data.go.kr 회원가입\n"
    "  2. 'K-Startup 통합공고 지원사업' 활용 신청\n"
    "  3. 발급된 일반 인증키(Decoding) 사용\n\n"
    "설정 방법 (택 1):\n"
    '  claude config set env.KO_DATA_API_KEY "발급받은_인증키"\n'
    "  또는 .env 파일에: KO_DATA_API_KEY=발급받은_인증키\n"
)


def _get_api_key(cli_arg: str | None = None) -> str:
    """공공데이터포털 API 키 해석."""
    return env_loader.resolve_api_key(_KEY_VAR, cli_arg, _SETUP_GUIDE, normalize=True)


def cmd_search(args: argparse.Namespace) -> int:
    """지원사업 공고 검색."""
    api_key = _get_api_key(args.api_key)

    data = funding_api.search_announcements(
        api_key,
        keyword=args.keyword,
        active_only=args.active,
        field=args.field,
        from_date=args.from_date,
        to_date=args.to_date,
        rows=args.rows,
    )

    items = data.get("items", [])

    result: dict[str, Any] = {
        "status": "ok",
        "keyword": args.keyword,
        "count": len(items),
        "results": items,
    }

    if args.format == "table":
        _print_search_table(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def cmd_overview(args: argparse.Namespace) -> int:
    """통합공고 사업 현황 조회."""
    api_key = _get_api_key(args.api_key)

    data = funding_api.get_business_overview(
        api_key,
        keyword=args.keyword,
        year=args.year,
        rows=args.rows,
    )

    items = data.get("items", [])

    result: dict[str, Any] = {
        "status": "ok",
        "keyword": args.keyword,
        "count": len(items),
        "results": items,
    }

    if args.year:
        result["year"] = args.year

    if args.format == "table":
        _print_overview_table(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


# --- 테이블 출력 헬퍼 ---

def _print_search_table(result: dict[str, Any]) -> None:
    """공고 검색 결과를 테이블로 출력."""
    keyword = result.get("keyword", "")
    count = result.get("count", 0)

    print(f"\n지원사업 공고 검색: '{keyword}' — {count}건\n")
    print(f"{'공고명':<40} {'분야':<12} {'접수기간':<22} {'모집':<6}")
    print("-" * 82)

    for item in result.get("results", [])[:20]:
        nm = str(item.get("biz_pbanc_nm", ""))[:38]
        field = str(item.get("supt_biz_clsfc", ""))[:10]
        bgng = str(item.get("pbanc_rcpt_bgng_dt", ""))
        end = str(item.get("pbanc_rcpt_end_dt", ""))
        period = f"{bgng}~{end}" if bgng else "-"
        status = "Y" if item.get("rcrt_prgs_yn") == "Y" else "N"
        print(f"{nm:<40} {field:<12} {period:<22} {status:<6}")

    if count > 20:
        print(f"... 외 {count - 20}건")


def _print_overview_table(result: dict[str, Any]) -> None:
    """통합공고 사업 현황을 테이블로 출력."""
    keyword = result.get("keyword", "")
    count = result.get("count", 0)

    print(f"\n통합공고 사업 현황: '{keyword}' — {count}건\n")
    print(f"{'사업명':<40} {'분야':<12} {'연도':<6}")
    print("-" * 62)

    for item in result.get("results", [])[:20]:
        nm = str(item.get("biz_nm", item.get("pbanc_nm", "")))[:38]
        field = str(item.get("supt_biz_clsfc", ""))[:10]
        year = str(item.get("biz_enyy", ""))
        print(f"{nm:<40} {field:<12} {year:<6}")

    if count > 20:
        print(f"... 외 {count - 20}건")


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서 생성.

    공용 옵션(--api-key, --format)을 parents 패턴으로 등록하여
    서브커맨드 앞/뒤 양쪽 위치에서 모두 동작하도록 한다 (REQ-1).

    구현 주의사항:
    - 서브파서 공용 옵션은 default=None/SUPPRESS로 두어 메인 파서 값을 덮어쓰지 않도록 한다.
    - main()에서 서브커맨드 뒤 값이 None이면 메인 파서에서 파싱된 값을 사용한다.
    """
    # 메인 파서: 서브커맨드 앞 위치 공용 옵션 (REQ-1.2, 하위 호환)
    parser = argparse.ArgumentParser(
        description="정부 지원사업 수집 — K-Startup 공공데이터",
    )
    parser.add_argument(
        "--api-key", default=None, dest="api_key",
        help="공공데이터포털 API 키 (직접 전달)",
    )
    parser.add_argument(
        "--format", choices=["json", "table"], default="json",
        help="출력 형식 (기본: json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # 서브파서 공용 옵션은 default=argparse.SUPPRESS로 두어 메인 파서 값을 보존한다
    # argparse.SUPPRESS: 지정하지 않으면 Namespace에 속성 자체를 추가하지 않음 →
    # setattr fallback으로 메인 파서 기본값이 유지됨
    def _add_common(p: argparse.ArgumentParser) -> None:
        """서브파서에 공용 옵션 추가 (SUPPRESS default로 메인 파서 값 보존)."""
        p.add_argument(
            "--api-key", default=argparse.SUPPRESS, dest="api_key",
            help="공공데이터포털 API 키 (직접 전달)",
        )
        p.add_argument(
            "--format", choices=["json", "table"], default=argparse.SUPPRESS,
            help="출력 형식 (기본: json)",
        )

    # search: 서브커맨드 뒤 위치 허용 (REQ-1.1)
    p_search = sub.add_parser("search", help="지원사업 공고 검색")
    _add_common(p_search)
    p_search.add_argument("--keyword", required=True, help="검색 키워드")
    p_search.add_argument("--active", action="store_true", help="모집 중인 공고만 조회")
    p_search.add_argument("--field", default=None, help="지원 분야 필터 (예: 사업화, R&D)")
    p_search.add_argument("--from-date", default=None, dest="from_date",
                          help="접수 시작일 하한 (YYYYMMDD)")
    p_search.add_argument("--to-date", default=None, dest="to_date",
                          help="접수 종료일 상한 (YYYYMMDD)")
    p_search.add_argument("--rows", type=int, default=100, help="조회 건수 (기본: 100)")

    # overview: 서브커맨드 뒤 위치 허용 (REQ-1.1)
    p_overview = sub.add_parser("overview", help="통합공고 사업 현황 조회")
    _add_common(p_overview)
    p_overview.add_argument("--keyword", required=True, help="검색 키워드")
    p_overview.add_argument("--year", default=None, help="사업 연도 (예: 2026)")
    p_overview.add_argument("--rows", type=int, default=100, help="조회 건수 (기본: 100)")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        commands = {
            "search": cmd_search,
            "overview": cmd_overview,
        }
        return commands[args.command](args)

    except env_loader.MissingAPIKeyError as e:
        print(json.dumps(
            {"status": "error", "error": "config", "detail": str(e)},
            ensure_ascii=False,
        ))
        return 1
    except funding_api.FundingAPIError as e:
        print(json.dumps(
            {"status": "error", "error": "api", "detail": str(e)},
            ensure_ascii=False,
        ))
        return 1
    except ValueError as e:
        print(json.dumps(
            {"status": "error", "error": "args", "detail": str(e)},
            ensure_ascii=False,
        ))
        return 2


if __name__ == "__main__":
    sys.exit(main())
