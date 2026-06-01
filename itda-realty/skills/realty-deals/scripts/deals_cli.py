#!/usr/bin/env python3
"""부동산 실거래가 통합 수집 CLI — 국토교통부 공공데이터 12유형.

기존 itda-gov/skills/realestate의 상위호환 대체.
페이지네이션 절단 버그 교정 + 12유형 확장 + 다월 수집.

사용법:
    python3 scripts/deals_cli.py collect --region "강남구" \\
        --start-month 202601 --end-month 202606 --type apt_trade

    python3 scripts/deals_cli.py regions
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import env_loader
from data_go_client import RealEstateAPIError
from deals_collector import (
    ENDPOINT_MAP,
    build_envelope,
    collect_deals_range,
    compute_summary,
    normalize_rent_item,
    normalize_trade_item,
)
from lawd_codes import LAWD_CD_MAP, resolve_lawd_cd

# 공공데이터포털 API 키 환경변수
_KEY_VAR = "KO_DATA_API_KEY"

_SETUP_GUIDE = (
    "KO_DATA_API_KEY가 설정되지 않았습니다.\n\n"
    "공공데이터포털 API 키 발급 방법:\n"
    "  1. https://www.data.go.kr 회원가입\n"
    "  2. 원하는 실거래가 서비스 활용 신청 (12유형 각각 독립 신청)\n"
    "  3. 발급된 일반 인증키(Decoding) 사용\n\n"
    "설정 방법 (택 1):\n"
    '  claude config set env.KO_DATA_API_KEY "발급받은_인증키"\n'
    "  또는 .env 파일에: KO_DATA_API_KEY=발급받은_인증키\n"
    "\n"
    "활용신청 URL (서비스별 개별 신청):\n"
    "  아파트 매매: https://www.data.go.kr/data/15126469/openapi.do\n"
    "  아파트 전월세: https://www.data.go.kr/data/15126474/openapi.do\n"
)


def _get_api_key(cli_arg: str | None = None) -> str:
    """공공데이터포털 API 키 해석."""
    return env_loader.resolve_api_key(_KEY_VAR, cli_arg, _SETUP_GUIDE, normalize=True)


def _resolve_region(args: argparse.Namespace) -> tuple[str, str]:
    """args에서 (lawd_cd, region_label) 튜플 반환."""
    if getattr(args, "lawd_cd", None):
        return args.lawd_cd, args.lawd_cd
    return resolve_lawd_cd(args.region), args.region


def cmd_collect(args: argparse.Namespace) -> int:
    """실거래가 수집 명령."""
    api_key = _get_api_key(getattr(args, "api_key", None))
    lawd_cd, region = _resolve_region(args)

    ep = ENDPOINT_MAP[args.type]
    deal_type = ep["deal_type"]

    raw_items = collect_deals_range(
        api_key=api_key,
        lawd_cd=lawd_cd,
        start_ymd=args.start_month,
        end_ymd=args.end_month,
        endpoint_key=args.type,
    )

    # 정규화
    if deal_type == "trade":
        items = [normalize_trade_item(i) for i in raw_items]
        amount_field_raw = "dealAmount"
    else:
        items = [normalize_rent_item(i) for i in raw_items]
        amount_field_raw = "deposit"

    # 단지명 필터
    if getattr(args, "name", None):
        name_lower = args.name.lower()
        items = [i for i in items if name_lower in i["apt_nm"].lower()]

    # 요약 통계
    summary = None
    if getattr(args, "summary", False):
        summary = compute_summary(raw_items, amount_field=amount_field_raw)

    envelope = build_envelope(
        status="ok",
        region=region,
        items=items,
        lawd_cd=lawd_cd,
        start_month=args.start_month,
        end_month=args.end_month,
        type=args.type,
        summary=summary,
    )

    if getattr(args, "format", "json") == "table":
        _print_table(envelope, deal_type)
    else:
        print(json.dumps(envelope, ensure_ascii=False, indent=2))

    return 0


def cmd_regions(args: argparse.Namespace) -> int:
    """내장 법정동코드 매핑 테이블 출력 (API 키 불필요)."""
    regions_list = [
        {"name": name, "lawd_cd": code}
        for name, code in sorted(LAWD_CD_MAP.items())
    ]
    result: dict[str, Any] = {
        "status": "ok",
        "count": len(regions_list),
        "regions": regions_list,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _print_table(result: dict[str, Any], deal_type: str) -> None:
    """테이블 형식으로 출력."""
    region = result.get("region", "")
    count = result.get("count", 0)
    start_m = result.get("start_month", "")
    end_m = result.get("end_month", "")
    label = "매매" if deal_type == "trade" else "전월세"

    print(f"\n{region} {label} 실거래가 ({start_m}~{end_m}) — {count}건\n")
    if deal_type == "trade":
        print(f"{'단지명':<20} {'면적':<8} {'금액(만원)':<12} {'층':<5} {'계약일':<12}")
        print("-" * 60)
        for item in result.get("results", [])[:30]:
            nm = item.get("apt_nm", "")[:20]
            ar = item.get("exclu_use_ar", "")
            amt = f"{item.get('deal_amount', 0):,}"
            floor_str = item.get("floor", "")
            day = f"{item.get('deal_year', '')}.{item.get('deal_month', '')}.{item.get('deal_day', '')}"
            print(f"{nm:<20} {ar:<8} {amt:<12} {floor_str:<5} {day:<12}")
    else:
        print(f"{'단지명':<20} {'면적':<8} {'보증금(만원)':<14} {'월세':<8} {'계약일':<12}")
        print("-" * 65)
        for item in result.get("results", [])[:30]:
            nm = item.get("apt_nm", "")[:20]
            ar = item.get("exclu_use_ar", "")
            dep = f"{item.get('deposit', 0):,}"
            rent = f"{item.get('monthly_rent', 0):,}"
            day = f"{item.get('deal_year', '')}.{item.get('deal_month', '')}.{item.get('deal_day', '')}"
            print(f"{nm:<20} {ar:<8} {dep:<14} {rent:<8} {day:<12}")

    if count > 30:
        print(f"... 외 {count - 30}건")

    summary = result.get("summary")
    if summary:
        print(f"\n  평균: {summary['avg']:,}만원  중위: {summary['median']:,}만원")


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서 생성."""
    parser = argparse.ArgumentParser(
        description="부동산 실거래가 통합 수집 (국토교통부 공공데이터 12유형)",
    )
    parser.add_argument("--api-key", default=None, help="공공데이터포털 API 키")
    parser.add_argument(
        "--format", choices=["json", "table"], default="json",
        help="출력 형식 (기본: json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # collect
    p_collect = sub.add_parser("collect", help="실거래가 수집 (단일/다월)")
    p_collect.add_argument("--start-month", required=True, help="시작 연월 (YYYYMM)")
    p_collect.add_argument("--end-month", required=True, help="종료 연월 (YYYYMM)")
    p_collect.add_argument("--region", default=None, help="한글 지역명 (예: 강남구)")
    p_collect.add_argument("--lawd-cd", default=None, help="법정동코드 직접 지정 (5자리)")
    p_collect.add_argument(
        "--type",
        choices=list(ENDPOINT_MAP.keys()),
        default="apt_trade",
        help="엔드포인트 유형 (기본: apt_trade)",
    )
    p_collect.add_argument("--name", default=None, help="단지명 부분 일치 필터")
    p_collect.add_argument("--summary", action="store_true", help="요약 통계 포함")

    # regions
    sub.add_parser("regions", help="지역명-법정동코드 목록 출력 (API 키 불필요)")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "collect":
            if not getattr(args, "region", None) and not getattr(args, "lawd_cd", None):
                print(json.dumps(
                    {"status": "error", "error": "args",
                     "detail": "--region 또는 --lawd-cd 중 하나를 지정하세요."},
                    ensure_ascii=False,
                ))
                return 1
            return cmd_collect(args)
        elif args.command == "regions":
            return cmd_regions(args)
        else:
            parser.print_help()
            return 2

    except env_loader.MissingAPIKeyError as e:
        print(json.dumps(
            {"status": "error", "error": "config", "detail": str(e)},
            ensure_ascii=False,
        ))
        return 1
    except RealEstateAPIError as e:
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
        return 1


if __name__ == "__main__":
    sys.exit(main())
