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
import csv
import io
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
        if args.format == "csv":
            _write_csv([], ["corp_code", "corp_name", "corp_name_eng", "stock_code"])
        else:
            print(json.dumps(
                {"status": "ok", "query": args.name, "count": 0, "results": []},
                ensure_ascii=False, indent=2,
            ))
        return 0

    # 상장사 우선 정렬 (stock_code가 있는 기업 먼저)
    results.sort(key=lambda x: (0 if x.get("stock_code") else 1, x["corp_name"]))

    if args.format == "csv":
        _write_csv(results, ["corp_code", "corp_name", "corp_name_eng", "stock_code", "modify_date"])
    elif args.format == "table":
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

    if args.format == "csv":
        _info_fields = [
            "corp_name", "ceo_nm", "induty_code", "est_dt",
            "adres", "hm_url", "corp_cls", "stock_code",
        ]
        _write_csv([{k: data.get(k, "") for k in _info_fields}], _info_fields)
    elif args.format == "table":
        _print_info_table(data)
    else:
        print(json.dumps(
            {"status": "ok", **data}, ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_finance(args: argparse.Namespace) -> int:
    """재무제표 주요계정 조회.

    --year 미지정 시 find_latest_report()로 자동 폴백.
    prefer 옵션에 따라 사업/반기/분기 폴백 범위 결정.
    """
    api_key = _get_api_key(args.api_key)
    reprt_code = dart_api.REPRT_CODES.get(args.report, "11011")

    year = getattr(args, "year", None)
    prefer = getattr(args, "prefer", "annual")

    if not year:
        # REQ-DART-004-001: 자동 폴백 — prefer에 따라 범위 결정
        report_info = dart_api.find_latest_report(api_key, args.corp_code, prefer=prefer)
        year = report_info["bsns_year"]
        report_type = report_info.get("report_type", "annual")
        # stderr 메시지: 어떤 보고서 채택됐는지 명시 (UX 모호성 방지)
        _type_labels = {
            "annual": "사업보고서",
            "half": "반기보고서",
            "q1": "1분기보고서",
            "q3": "3분기보고서",
        }
        label = _type_labels.get(report_type, report_type)
        print(
            f"[자동 폴백] {label} {year} 사용 (rcept_no={report_info['rcept_no']})",
            file=sys.stderr,
        )

    statements = dart_api.get_financial_statements(
        api_key, args.corp_code, year, reprt_code,
    )
    key_items = dart_api.filter_key_financials(statements, args.fs_div)

    if args.format == "csv":
        _write_csv(
            [{"account_nm": i["account_nm"], "thstrm_amount": i["thstrm_amount"],
              "frmtrm_amount": i["frmtrm_amount"], "currency": i.get("currency", "KRW")}
             for i in key_items],
            ["account_nm", "thstrm_amount", "frmtrm_amount", "currency"],
        )
    elif args.format == "table":
        _print_finance_table(key_items, year)
    else:
        print(json.dumps(
            {"status": "ok", "corp_code": args.corp_code, "year": year,
             "report": args.report, "fs_div": args.fs_div,
             "count": len(key_items), "items": key_items},
            ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_disclosure(args: argparse.Namespace) -> int:
    """공시 목록 조회 (REQ-001).

    list.json 호출 → rcept_no, report_nm, rcept_dt, flr_nm, corp_name 출력.
    status=013(결과 없음)은 정상 케이스로 처리.
    """
    api_key = _get_api_key(args.api_key)

    result = dart_api.list_disclosures(
        api_key,
        args.corp_code,
        args.bgn,
        args.end,
        pblntf_ty=getattr(args, "type", None) or None,
        page_no=args.page,
        page_count=args.page_count,
    )

    items = result.get("list", [])
    total = int(result.get("total_count", len(items)))

    if args.format == "csv":
        _write_csv(
            items,
            ["rcept_no", "report_nm", "rcept_dt", "flr_nm", "corp_name"],
        )
    elif args.format == "table":
        _print_disclosure_table(items, total)
    else:
        msg = "조회된 공시 없음" if not items else "ok"
        print(json.dumps(
            {"status": "ok", "corp_code": args.corp_code,
             "total_count": total, "count": len(items),
             "message": msg, "items": items},
            ensure_ascii=False, indent=2,
        ))
    return 0


def cmd_business(args: argparse.Namespace) -> int:
    """사업보고서 텍스트 추출 (REQ-002/003).

    --rcept-no 미지정 + --corp-code만 → 최신 사업보고서 자동 폴백.
    """
    api_key = _get_api_key(args.api_key)

    rcept_no = getattr(args, "rcept_no", None)

    if not rcept_no:
        # REQ-003: 자동 폴백
        report_info = dart_api.find_latest_business_report(api_key, args.corp_code)
        rcept_no = report_info["rcept_no"]
        bsns_year = report_info["bsns_year"]
        print(
            f"[자동 폴백] 사업보고서 {bsns_year} 사용 (rcept_no={rcept_no})",
            file=sys.stderr,
        )

    text = dart_api.get_document_text(
        api_key,
        rcept_no,
        section_pattern=getattr(args, "section", None) or None,
        max_chars=args.max_chars,
    )

    if args.format == "csv":
        section = getattr(args, "section", None) or ""
        _write_csv(
            [{"rcept_no": rcept_no, "section": section, "content": text}],
            ["rcept_no", "section", "content"],
        )
    else:
        print(text)
    return 0


def cmd_employees(args: argparse.Namespace) -> int:
    """직원현황 조회."""
    api_key = _get_api_key(args.api_key)
    reprt_code = dart_api.REPRT_CODES.get(args.report, "11011")

    data = dart_api.get_employee_status(
        api_key, args.corp_code, args.year, reprt_code,
    )

    if args.format == "csv":
        _write_csv(
            data,
            ["fo_bbm", "sexdstn", "rgllbr_co", "cnttk_co", "sm",
             "avrg_cnwk_sdytrn", "jan_salary_am"],
        )
    elif args.format == "table":
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

    if args.format == "csv":
        # profile CSV: 기업개황 필드를 단일 행으로
        info_fields = ["corp_name", "ceo_nm", "induty_code", "est_dt",
                       "adres", "hm_url", "corp_cls", "stock_code"]
        row = {k: company_info.get(k, "") for k in info_fields}
        row["corp_code"] = corp_code
        row["year"] = args.year
        _write_csv([row], ["corp_code", "year"] + info_fields)
    else:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


# --- CSV 출력 헬퍼 ---

def _write_csv(rows: list[dict], headers: list[str]) -> None:
    """rows를 UTF-8 BOM CSV로 stdout에 출력.

    RFC 4180 준수: \\r\\n 줄바꿈, 헤더 행 포함, QUOTE_MINIMAL.
    엑셀 한글 호환을 위해 UTF-8 BOM(\\xef\\xbb\\xbf) 선행 출력.

    Args:
        rows: 출력할 딕셔너리 목록.
        headers: CSV 헤더 컬럼명 목록.
    """
    # BOM 출력 (엑셀 한글 호환)
    sys.stdout.buffer.write('﻿'.encode('utf-8'))
    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=headers,
        extrasaction='ignore',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator='\r\n',
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


# --- compare 커맨드 ---

# 기업 비교에서 표시할 단위: 백만 원
_MILLION = 1_000_000


def _format_compare_amount(val: str, currency: str = "KRW") -> str:
    """비교 테이블용 금액 포맷: 원본 값 + 천 단위 콤마 + 백만 단위.

    Args:
        val: 금액 문자열 (원 단위).
        currency: 통화 코드.

    Returns:
        "258,935,488M KRW" 형식의 문자열. 파싱 불가 시 원본 반환.
    """
    if not val or val == "-":
        return "-"
    try:
        num = int(val.replace(",", ""))
    except ValueError:
        return val
    millions = num // _MILLION
    suffix = f"M {currency}" if currency != "KRW" else "M KRW"
    return f"{millions:,}{suffix}"


def cmd_compare(args: argparse.Namespace) -> int:
    """다기업 재무 비교 커맨드.

    --names 또는 --corp-codes로 기업 지정, --year와 --accounts로 조회.
    """
    api_key = _get_api_key(args.api_key)
    reprt_code = dart_api.REPRT_CODES.get(getattr(args, "report", "annual"), "11011")

    # 기업 코드 목록 결정
    corp_codes: list[str] = []
    corp_names: dict[str, str] = {}  # corp_code → 표시 이름

    if getattr(args, "corp_codes", None):
        for code in args.corp_codes.split(","):
            code = code.strip()
            if code:
                corp_codes.append(code)
                corp_names[code] = code
    elif getattr(args, "names", None):
        for name in args.names.split(","):
            name = name.strip()
            if not name:
                continue
            matches = dart_api.find_corp_code(api_key, name, cache_path=_get_cache_path())
            if not matches:
                print(f"[경고] '{name}' 검색 결과 없음 — 스킵", file=sys.stderr)
                continue
            # 상장사 우선, 2+건이면 첫 결과 + 경고
            matches.sort(key=lambda x: (0 if x.get("stock_code") else 1))
            if len(matches) > 1:
                print(
                    f"[경고] '{name}' 검색 결과 {len(matches)}건 — '{matches[0]['corp_name']}' 채택",
                    file=sys.stderr,
                )
            corp = matches[0]
            corp_codes.append(corp["corp_code"])
            corp_names[corp["corp_code"]] = corp["corp_name"]

    # 계정 목록 결정
    accounts_str = getattr(args, "accounts", None)
    if accounts_str:
        accounts = [a.strip() for a in accounts_str.split(",") if a.strip()]
    else:
        accounts = list(dart_api.KEY_ACCOUNTS)

    # 비교 조회
    data = dart_api.compare_financials(api_key, corp_codes, args.year, accounts, reprt_code)

    if args.format == "csv":
        _print_compare_csv(data, corp_codes, corp_names, accounts, args.year)
    elif args.format == "table":
        _print_compare_table(data, corp_codes, corp_names, accounts, args.year, args.report)
    else:
        print(json.dumps(
            {"status": "ok", "year": args.year, "report": getattr(args, "report", "annual"),
             "corp_codes": corp_codes, "accounts": accounts, "data": data},
            ensure_ascii=False, indent=2,
        ))
    return 0


def _print_compare_table(
    data: dict[str, dict],
    corp_codes: list[str],
    corp_names: dict[str, str],
    accounts: list[str],
    year: str,
    report: str = "annual",
) -> None:
    """비교 결과 테이블 출력."""
    _report_labels = {
        "annual": "사업보고서",
        "half": "반기보고서",
        "q1": "1분기보고서",
        "q3": "3분기보고서",
    }
    label = _report_labels.get(report, report)
    names = [corp_names.get(c, c) for c in corp_codes]

    print(f"\n비교 — {year}년 {label} (CFS)\n")
    col_w = 20
    name_w = col_w * len(corp_codes)
    header = f"{'계정':<16}" + "".join(f"{n:<{col_w}}" for n in names)
    print(header)
    print("-" * (16 + col_w * len(corp_codes)))

    for acct in accounts:
        row = f"{acct:<16}"
        for corp_code in corp_codes:
            corp_data = data.get(corp_code, {})
            acct_data = corp_data.get(acct)
            if acct_data:
                amt = _format_compare_amount(
                    acct_data.get("thstrm_amount", ""),
                    acct_data.get("currency", "KRW"),
                )
            else:
                amt = "-"
            row += f"{amt:<{col_w}}"
        print(row)
    print()


def _print_compare_csv(
    data: dict[str, dict],
    corp_codes: list[str],
    corp_names: dict[str, str],
    accounts: list[str],
    year: str,
) -> None:
    """비교 결과 CSV 출력: (account, corp_code, corp_name, thstrm_amount, currency)."""
    rows = []
    for acct in accounts:
        for corp_code in corp_codes:
            corp_data = data.get(corp_code, {})
            acct_data = corp_data.get(acct) or {}
            rows.append({
                "account": acct,
                "corp_code": corp_code,
                "corp_name": corp_names.get(corp_code, corp_code),
                "year": year,
                "thstrm_amount": acct_data.get("thstrm_amount", ""),
                "currency": acct_data.get("currency", ""),
            })
    _write_csv(rows, ["account", "corp_code", "corp_name", "year", "thstrm_amount", "currency"])


# --- 테이블 출력 헬퍼 ---

def _print_disclosure_table(items: list[dict[str, Any]], total: int) -> None:
    """공시 목록을 테이블로 출력."""
    if not items:
        print("\n조회된 공시 없음\n")
        return
    print(f"\n공시 목록 — {total}건\n")
    print(f"{'접수번호':<16} {'보고서명':<30} {'접수일':<10} {'제출인':<15} {'회사명':<20}")
    print("-" * 95)
    for item in items:
        rcept_no = item.get("rcept_no", "")
        report_nm = item.get("report_nm", "")[:28]
        rcept_dt = item.get("rcept_dt", "")
        flr_nm = item.get("flr_nm", "")[:13]
        corp_name = item.get("corp_name", "")[:18]
        print(f"{rcept_no:<16} {report_nm:<30} {rcept_dt:<10} {flr_nm:<15} {corp_name:<20}")
    print()


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
    """CLI 인자 파서 생성.

    공용 옵션(--api-key, --format)을 _add_common() 헬퍼로 메인 파서와 모든 서브파서에
    동시 등록하여 서브커맨드 앞/뒤 양쪽 위치에서 모두 동작하도록 한다 (REQ-1).

    구현 주의사항:
    - 서브파서 공용 옵션은 default=argparse.SUPPRESS로 두어 메인 파서 기본값을 보존한다.
    - parents=[common] 패턴 사용 금지 — default 충돌 문제 (plan.md Risk-2 참고).
    """
    # 메인 파서: 서브커맨드 앞 위치 공용 옵션 (REQ-1.2, 하위 호환)
    parser = argparse.ArgumentParser(
        description="기업 정보 수집 — DART 전자공시시스템",
    )
    parser.add_argument(
        "--api-key", default=None, dest="api_key", help="DART API 키 (직접 전달)",
    )
    parser.add_argument(
        "--format", choices=["json", "table", "csv"], default="json",
        help="출력 형식 (기본: json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # 서브파서 공용 옵션은 default=argparse.SUPPRESS로 두어 메인 파서 기본값을 보존한다.
    # SUPPRESS: 미지정 시 Namespace에 속성을 추가하지 않으므로 메인 파서 기본값이 유지됨.
    def _add_common(p: argparse.ArgumentParser) -> None:
        """서브파서에 공용 옵션 추가 (SUPPRESS default로 메인 파서 값 보존)."""
        p.add_argument(
            "--api-key", default=argparse.SUPPRESS, dest="api_key",
            help="DART API 키 (직접 전달)",
        )
        p.add_argument(
            "--format", choices=["json", "table", "csv"], default=argparse.SUPPRESS,
            help="출력 형식 (기본: json)",
        )

    # search
    p_search = sub.add_parser("search", help="회사명으로 고유번호 검색")
    _add_common(p_search)
    p_search.add_argument("--name", "-n", required=True, help="회사명 (부분 일치)")

    # info
    p_info = sub.add_parser("info", help="기업개황 조회")
    _add_common(p_info)
    p_info.add_argument("--corp-code", "-c", required=True, help="8자리 고유번호")

    # finance
    p_fin = sub.add_parser("finance", help="재무제표 주요계정 조회")
    _add_common(p_fin)
    p_fin.add_argument("--corp-code", "-c", required=True, help="8자리 고유번호")
    p_fin.add_argument(
        "--year", "-y", default=None,
        help="사업연도 (예: 2024). 미지정 시 최신 사업보고서 자동 선택",
    )
    p_fin.add_argument(
        "--report", "-r", choices=list(dart_api.REPRT_CODES.keys()),
        default="annual", help="보고서 유형 (기본: annual)",
    )
    p_fin.add_argument(
        "--fs-div", choices=["CFS", "OFS"], default="CFS",
        help="연결(CFS)/개별(OFS) (기본: CFS)",
    )
    p_fin.add_argument(
        "--prefer", choices=["annual", "latest"], default="annual",
        help="폴백 범위: annual=사업보고서만, latest=분기·반기 포함 (기본: annual)",
    )

    # disclosure
    p_disc = sub.add_parser("disclosure", help="공시 목록 조회")
    _add_common(p_disc)
    p_disc.add_argument("--corp-code", "-c", required=True, help="8자리 고유번호")
    p_disc.add_argument("--bgn", required=True, help="시작일 (YYYYMMDD)")
    p_disc.add_argument("--end", required=True, help="종료일 (YYYYMMDD)")
    p_disc.add_argument("--type", default=None, help="공시 유형 (A=정기, B=주요사항, None=전체)")
    p_disc.add_argument("--page", type=int, default=1, help="페이지 번호 (기본: 1)")
    p_disc.add_argument("--page-count", type=int, default=10, dest="page_count",
                        help="페이지당 건수 (기본: 10, 최대: 100)")

    # business
    p_biz = sub.add_parser("business", help="사업보고서 텍스트 추출")
    _add_common(p_biz)
    p_biz_group = p_biz.add_mutually_exclusive_group(required=True)
    p_biz_group.add_argument("--rcept-no", dest="rcept_no", default=None,
                             help="접수번호 (14자리). 미지정 시 --corp-code로 자동 검색")
    p_biz_group.add_argument("--corp-code", "-c", dest="corp_code", default=None,
                             help="8자리 고유번호. --rcept-no 없을 때 자동 폴백용")
    p_biz.add_argument("--section", default=None, help="추출할 섹션 정규식 (예: '사업의 내용')")
    p_biz.add_argument("--max-chars", type=int, default=5000, dest="max_chars",
                       help="최대 출력 문자수 (기본: 5000, 0=무제한)")

    # employees
    p_emp = sub.add_parser("employees", help="직원현황 조회")
    _add_common(p_emp)
    p_emp.add_argument("--corp-code", "-c", required=True, help="8자리 고유번호")
    p_emp.add_argument("--year", "-y", required=True, help="사업연도")
    p_emp.add_argument(
        "--report", "-r", choices=list(dart_api.REPRT_CODES.keys()),
        default="annual", help="보고서 유형",
    )

    # profile (종합)
    p_prof = sub.add_parser("profile", help="기업 프로필 종합 조회")
    _add_common(p_prof)
    p_prof.add_argument("--name", "-n", required=True, help="회사명")
    p_prof.add_argument("--year", "-y", required=True, help="사업연도")
    p_prof.add_argument(
        "--report", "-r", choices=list(dart_api.REPRT_CODES.keys()),
        default="annual", help="보고서 유형",
    )

    # compare
    p_cmp = sub.add_parser("compare", help="다기업 재무 비교")
    _add_common(p_cmp)
    p_cmp_group = p_cmp.add_mutually_exclusive_group(required=True)
    p_cmp_group.add_argument(
        "--names", default=None,
        help="회사명 (쉼표 구분, 예: '삼성전자,LG전자')",
    )
    p_cmp_group.add_argument(
        "--corp-codes", dest="corp_codes", default=None,
        help="8자리 고유번호 (쉼표 구분, 예: '00126380,00401731')",
    )
    p_cmp.add_argument("--year", "-y", required=True, help="사업연도 (예: 2024)")
    p_cmp.add_argument(
        "--accounts", default=None,
        help="계정명 (쉼표 구분, 기본: 매출액/영업이익/당기순이익/자산총계)",
    )
    p_cmp.add_argument(
        "--report", "-r", choices=list(dart_api.REPRT_CODES.keys()),
        default="annual", help="보고서 유형 (기본: annual)",
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
            "disclosure": cmd_disclosure,
            "business": cmd_business,
            "compare": cmd_compare,
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
