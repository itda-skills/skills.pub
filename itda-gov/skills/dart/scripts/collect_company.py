#!/usr/bin/env python3
"""기업 정보 수집 CLI — DART 전자공시시스템.

경쟁사 분석용 기업 정보를 수집하여 JSON/Table로 출력.

사용법:
    python3 scripts/collect_company.py search --name "삼성전자"
    python3 scripts/collect_company.py info --corp-code 00126380
    python3 scripts/collect_company.py finance --corp-code 00126380 --year 2024
    python3 scripts/collect_company.py employees --corp-code 00126380 --year 2024
    python3 scripts/collect_company.py profile --name "삼성전자" --year 2024
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import dart_api
import env_loader

# DART API 키 환경변수
_KEY_VAR = "DART_API_KEY"

_SETUP_GUIDE = (
    "DART_API_KEY가 설정되지 않았습니다.\n\n"
    "DART 인증키 발급 방법:\n"
    "  1. https://opendart.fss.or.kr 회원가입\n"
    "  2. 인증키 발급 (즉시 발급, 40자리)\n\n"
    "설정 방법 (택 1):\n"
    '  claude config set env.DART_API_KEY "발급받은_인증키"\n'
    "  또는 .env 파일에: DART_API_KEY=발급받은_인증키\n"
)

# corpCode.xml 캐시 경로
_OLD_CACHE_PATH = ".itda-skills/dart-corp-codes.xml"
_cache_path: str | None = None


def _get_cache_path() -> str:
    """환경에 따라 캐시 경로를 결정한다 (lazy 해석)."""
    global _cache_path  # noqa: PLW0603
    if _cache_path is not None:
        return _cache_path
    from pathlib import Path

    from itda_path import resolve_cache_dir
    cache_dir = resolve_cache_dir("dart")
    new_path = str(cache_dir / "corp-codes.xml")
    # 이전 경로 마이그레이션
    if Path(_OLD_CACHE_PATH).exists() and not Path(new_path).exists():
        try:
            Path(_OLD_CACHE_PATH).rename(new_path)
        except OSError:
            pass
    _cache_path = new_path
    return _cache_path


def _get_api_key(cli_arg: str | None = None) -> str:
    """DART API 키 해석."""
    return env_loader.resolve_api_key(_KEY_VAR, cli_arg, _SETUP_GUIDE)


def cmd_search(args: argparse.Namespace) -> int:
    """회사명으로 고유번호 검색."""
    api_key = _get_api_key(args.api_key)
    results = dart_api.find_corp_code(api_key, args.name, cache_path=_get_cache_path())

    if not results:
        print(json.dumps(
            {"status": "ok", "query": args.name, "count": 0, "results": []},
            ensure_ascii=False, indent=2,
        ))
        return 0

    # 상장사 우선 정렬 (stock_code가 있는 기업 먼저)
    results.sort(key=lambda x: (0 if x.get("stock_code") else 1, x["corp_name"]))

    if args.format == "table":
        _print_search_table(results, args.name)
    else:
        print(json.dumps(
            {"status": "ok", "query": args.name, "count": len(results), "results": results},
            ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """기업개황 조회."""
    api_key = _get_api_key(args.api_key)
    data = dart_api.get_company_info(api_key, args.corp_code)

    if args.format == "table":
        _print_info_table(data)
    else:
        print(json.dumps(
            {"status": "ok", **data}, ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_finance(args: argparse.Namespace) -> int:
    """재무제표 주요계정 조회."""
    api_key = _get_api_key(args.api_key)
    reprt_code = dart_api.REPRT_CODES.get(args.report, "11011")

    statements = dart_api.get_financial_statements(
        api_key, args.corp_code, args.year, reprt_code,
    )
    key_items = dart_api.filter_key_financials(statements, args.fs_div)

    if args.format == "table":
        _print_finance_table(key_items, args.year)
    else:
        print(json.dumps(
            {"status": "ok", "corp_code": args.corp_code, "year": args.year,
             "report": args.report, "fs_div": args.fs_div,
             "count": len(key_items), "items": key_items},
            ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_employees(args: argparse.Namespace) -> int:
    """직원현황 조회."""
    api_key = _get_api_key(args.api_key)
    reprt_code = dart_api.REPRT_CODES.get(args.report, "11011")

    data = dart_api.get_employee_status(
        api_key, args.corp_code, args.year, reprt_code,
    )

    if args.format == "table":
        _print_employee_table(data)
    else:
        print(json.dumps(
            {"status": "ok", "corp_code": args.corp_code, "year": args.year,
             "count": len(data), "items": data},
            ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    """기업 프로필 종합 조회 (기업개황 + 재무 + 직원).

    회사명으로 검색 → 첫 번째 결과의 corp_code로 종합 조회.
    """
    api_key = _get_api_key(args.api_key)

    # 1. 회사명으로 corp_code 검색
    matches = dart_api.find_corp_code(api_key, args.name, cache_path=_get_cache_path())
    if not matches:
        print(json.dumps(
            {"status": "error", "error": "not_found",
             "detail": f"'{args.name}'에 해당하는 기업을 찾을 수 없습니다."},
            ensure_ascii=False,
        ))
        return 1

    # 상장사 우선
    matches.sort(key=lambda x: (0 if x.get("stock_code") else 1))
    corp = matches[0]
    corp_code = corp["corp_code"]

    # 2. 기업개황
    try:
        company_info = dart_api.get_company_info(api_key, corp_code)
    except dart_api.DARTAPIError as e:
        company_info = {"error": str(e)}

    # 3. 재무제표
    reprt_code = dart_api.REPRT_CODES.get(args.report, "11011")
    try:
        statements = dart_api.get_financial_statements(
            api_key, corp_code, args.year, reprt_code,
        )
        financials = dart_api.filter_key_financials(statements)
    except dart_api.DARTAPIError as e:
        financials = [{"error": str(e)}]

    # 4. 직원현황
    try:
        employees = dart_api.get_employee_status(
            api_key, corp_code, args.year, reprt_code,
        )
    except dart_api.DARTAPIError as e:
        employees = [{"error": str(e)}]

    profile: dict[str, Any] = {
        "status": "ok",
        "corp_code": corp_code,
        "corp_name": corp.get("corp_name", ""),
        "stock_code": corp.get("stock_code", ""),
        "year": args.year,
        "company_info": company_info,
        "financials": financials,
        "employees": employees,
    }

    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


# --- 테이블 출력 헬퍼 ---

def _print_search_table(results: list[dict[str, str]], query: str) -> None:
    """검색 결과를 테이블로 출력."""
    print(f"\n검색: '{query}' — {len(results)}건\n")
    print(f"{'고유번호':<12} {'회사명':<20} {'종목코드':<10}")
    print("-" * 42)
    for r in results[:20]:  # 최대 20건
        code = r.get("corp_code", "")
        name = r.get("corp_name", "")
        stock = r.get("stock_code", "") or "-"
        print(f"{code:<12} {name:<20} {stock:<10}")
    if len(results) > 20:
        print(f"... 외 {len(results) - 20}건")


def _print_info_table(data: dict[str, Any]) -> None:
    """기업개황을 테이블로 출력."""
    fields = [
        ("회사명", "corp_name"), ("대표자", "ceo_nm"),
        ("업종코드", "induty_code"), ("설립일", "est_dt"),
        ("주소", "adres"), ("홈페이지", "hm_url"),
        ("법인구분", "corp_cls"), ("종목코드", "stock_code"),
    ]
    print()
    for label, key in fields:
        val = data.get(key, "-") or "-"
        print(f"  {label:<10}: {val}")
    print()


def _print_finance_table(items: list[dict[str, str]], year: str) -> None:
    """재무 핵심 계정을 테이블로 출력."""
    print(f"\n재무제표 주요계정 ({year}년)\n")
    print(f"{'계정명':<20} {'당기':<20} {'전기':<20}")
    print("-" * 60)
    for item in items:
        name = item.get("account_nm", "")
        curr = _format_amount(item.get("thstrm_amount", ""))
        prev = _format_amount(item.get("frmtrm_amount", ""))
        print(f"{name:<20} {curr:<20} {prev:<20}")
    print()


def _print_employee_table(items: list[dict[str, Any]]) -> None:
    """직원현황을 테이블로 출력."""
    print("\n직원현황\n")
    for item in items:
        dept = item.get("fo_bbm", "전체") or "전체"
        sex = item.get("sexdstn", "")
        total = item.get("sm", "-")
        tenure = item.get("avrg_cnwk_sdytrn", "-")
        salary = _format_amount(item.get("jan_salary_am", ""))
        print(f"  {dept} ({sex}): {total}명, 평균 근속 {tenure}년, 평균 급여 {salary}")
    print()


def _format_amount(val: str) -> str:
    """금액 문자열을 읽기 쉬운 형식으로 변환 (예: 1234567890 → 12억 3,456만)."""
    if not val or val == "-":
        return "-"
    try:
        num = int(val.replace(",", ""))
    except ValueError:
        return val

    if abs(num) >= 1_0000_0000:  # 1억 이상
        billions = num / 1_0000_0000
        return f"{billions:,.0f}억"
    elif abs(num) >= 1_0000:  # 1만 이상
        ten_thousands = num / 1_0000
        return f"{ten_thousands:,.0f}만"
    return f"{num:,}"


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서 생성."""
    parser = argparse.ArgumentParser(
        description="기업 정보 수집 — DART 전자공시시스템",
    )
    parser.add_argument(
        "--api-key", default=None, help="DART API 키 (직접 전달)"
    )
    parser.add_argument(
        "--format", choices=["json", "table"], default="json",
        help="출력 형식 (기본: json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="회사명으로 고유번호 검색")
    p_search.add_argument("--name", "-n", required=True, help="회사명 (부분 일치)")

    # info
    p_info = sub.add_parser("info", help="기업개황 조회")
    p_info.add_argument("--corp-code", "-c", required=True, help="8자리 고유번호")

    # finance
    p_fin = sub.add_parser("finance", help="재무제표 주요계정 조회")
    p_fin.add_argument("--corp-code", "-c", required=True, help="8자리 고유번호")
    p_fin.add_argument("--year", "-y", required=True, help="사업연도 (예: 2024)")
    p_fin.add_argument(
        "--report", "-r", choices=list(dart_api.REPRT_CODES.keys()),
        default="annual", help="보고서 유형 (기본: annual)",
    )
    p_fin.add_argument(
        "--fs-div", choices=["CFS", "OFS"], default="CFS",
        help="연결(CFS)/개별(OFS) (기본: CFS)",
    )

    # employees
    p_emp = sub.add_parser("employees", help="직원현황 조회")
    p_emp.add_argument("--corp-code", "-c", required=True, help="8자리 고유번호")
    p_emp.add_argument("--year", "-y", required=True, help="사업연도")
    p_emp.add_argument(
        "--report", "-r", choices=list(dart_api.REPRT_CODES.keys()),
        default="annual", help="보고서 유형",
    )

    # profile (종합)
    p_prof = sub.add_parser("profile", help="기업 프로필 종합 조회")
    p_prof.add_argument("--name", "-n", required=True, help="회사명")
    p_prof.add_argument("--year", "-y", required=True, help="사업연도")
    p_prof.add_argument(
        "--report", "-r", choices=list(dart_api.REPRT_CODES.keys()),
        default="annual", help="보고서 유형",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        commands = {
            "search": cmd_search,
            "info": cmd_info,
            "finance": cmd_finance,
            "employees": cmd_employees,
            "profile": cmd_profile,
        }
        return commands[args.command](args)

    except env_loader.MissingAPIKeyError as e:
        print(json.dumps(
            {"status": "error", "error": "config", "detail": str(e)},
            ensure_ascii=False,
        ))
        return 1
    except dart_api.DARTAPIError as e:
        print(json.dumps(
            {"status": "error", "error": "api", "detail": str(e),
             "error_code": e.error_code},
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
