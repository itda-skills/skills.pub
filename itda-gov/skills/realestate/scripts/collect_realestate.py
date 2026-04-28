#!/usr/bin/env python3
"""부동산 실거래가 수집 CLI — 국토교통부 공공데이터.

매매·전월세 실거래가를 지역·월 단위로 조회.

사용법:
    python3 scripts/collect_realestate.py trade --region "강남구" --year-month 202601
    python3 scripts/collect_realestate.py rent --region "강남구" --year-month 202601 --summary
    python3 scripts/collect_realestate.py regions
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import env_loader
import realestate_api

# 공공데이터포털 API 키 환경변수
_KEY_VAR = "KO_DATA_API_KEY"

_SETUP_GUIDE = (
    "KO_DATA_API_KEY가 설정되지 않았습니다.\n\n"
    "공공데이터포털 API 키 발급 방법:\n"
    "  1. https://www.data.go.kr 회원가입\n"
    "  2. '국토교통부 아파트 매매 실거래 정보' 활용 신청\n"
    "  3. 발급된 일반 인증키(Decoding) 사용\n\n"
    "설정 방법 (택 1):\n"
    '  claude config set env.KO_DATA_API_KEY "발급받은_인증키"\n'
    "  또는 .env 파일에: KO_DATA_API_KEY=발급받은_인증키\n"
)


def _get_api_key(cli_arg: str | None = None) -> str:
    """공공데이터포털 API 키 해석."""
    return env_loader.resolve_api_key(_KEY_VAR, cli_arg, _SETUP_GUIDE, normalize=True)


def _normalize_common_fields(item: dict[str, str]) -> dict[str, Any]:
    """매매·전월세 공통 필드를 snake_case로 정규화.

    아파트 응답은 단지명을 ``aptNm``, 오피스텔 응답은 ``offiNm`` 으로 반환한다.
    소비자 입장에서 동일 키(``apt_nm``)로 노출되도록 둘 중 존재하는 값을 사용한다.
    """
    return {
        "apt_nm": (item.get("aptNm") or item.get("offiNm") or "").strip(),
        "exclu_use_ar": item.get("excluUseAr", "").strip(),
        "deal_year": item.get("dealYear", "").strip(),
        "deal_month": item.get("dealMonth", "").strip(),
        "deal_day": item.get("dealDay", "").strip(),
        "floor": item.get("floor", "").strip(),
        "build_year": item.get("buildYear", "").strip(),
        "umd_nm": item.get("umdNm", "").strip(),
        "jibun": item.get("jibun", "").strip(),
    }


def _normalize_trade_item(item: dict[str, str]) -> dict[str, Any]:
    """API 응답 필드명을 snake_case로 정규화 (매매).

    Args:
        item: API 원본 항목.

    Returns:
        정규화된 딕셔너리.
    """
    return {
        **_normalize_common_fields(item),
        "deal_amount": realestate_api.parse_amount(item.get("dealAmount", "0")),
    }


def _normalize_rent_item(item: dict[str, str]) -> dict[str, Any]:
    """API 응답 필드명을 snake_case로 정규화 (전월세).

    Args:
        item: API 원본 항목.

    Returns:
        정규화된 딕셔너리.
    """
    return {
        **_normalize_common_fields(item),
        "deposit": realestate_api.parse_amount(item.get("deposit", "0")),
        "monthly_rent": realestate_api.parse_amount(item.get("monthlyRent", "0")),
    }


def _resolve_region(args: argparse.Namespace) -> tuple[str, str]:
    """args에서 (lawd_cd, region_label) 튜플 반환."""
    if args.lawd_cd:
        return args.lawd_cd, args.lawd_cd
    return realestate_api.resolve_lawd_cd(args.region), args.region


def cmd_trade(args: argparse.Namespace) -> int:
    """매매 실거래가 조회."""
    api_key = _get_api_key(args.api_key)
    lawd_cd, region = _resolve_region(args)

    data = realestate_api.fetch_trade(
        api_key, lawd_cd, args.year_month,
        prop_type=args.type,
        rows=args.rows,
    )

    # 정규화
    items = [_normalize_trade_item(item) for item in data["items"]]

    # 단지명 필터
    if args.name:
        name_lower = args.name.lower()
        items = [i for i in items if name_lower in i["apt_nm"].lower()]

    result: dict[str, Any] = {
        "status": "ok",
        "region": region,
        "lawd_cd": lawd_cd,
        "year_month": args.year_month,
        "type": args.type,
        "count": len(items),
        "results": items,
    }

    # 요약 통계 추가
    if args.summary:
        # 원본 items의 dealAmount 기준으로 summary 계산
        result["summary"] = realestate_api.compute_summary(
            data["items"], amount_field="dealAmount"
        )

    if args.format == "table":
        _print_trade_table(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def cmd_rent(args: argparse.Namespace) -> int:
    """전월세 실거래가 조회."""
    api_key = _get_api_key(args.api_key)
    lawd_cd, region = _resolve_region(args)

    data = realestate_api.fetch_rent(
        api_key, lawd_cd, args.year_month,
        prop_type=args.type,
        rows=args.rows,
    )

    # 정규화
    items = [_normalize_rent_item(item) for item in data["items"]]

    # 단지명 필터
    if args.name:
        name_lower = args.name.lower()
        items = [i for i in items if name_lower in i["apt_nm"].lower()]

    result: dict[str, Any] = {
        "status": "ok",
        "region": region,
        "lawd_cd": lawd_cd,
        "year_month": args.year_month,
        "type": args.type,
        "count": len(items),
        "results": items,
    }

    # 요약 통계 (전세는 deposit 기준)
    if args.summary:
        result["summary"] = realestate_api.compute_summary(
            data["items"], amount_field="deposit"
        )

    if args.format == "table":
        _print_rent_table(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


def cmd_regions(args: argparse.Namespace) -> int:
    """내장 법정동코드 매핑 테이블 출력 (API 키 불필요)."""
    regions_list = [
        {"name": name, "lawd_cd": code}
        for name, code in sorted(realestate_api._LAWD_CD_MAP.items())
    ]

    result: dict[str, Any] = {
        "status": "ok",
        "count": len(regions_list),
        "regions": regions_list,
    }

    if getattr(args, "format", "json") == "table":
        print(f"\n법정동코드 매핑 목록 ({len(regions_list)}건)\n")
        print(f"{'지역명':<25} {'코드':<8}")
        print("-" * 35)
        for r in regions_list:
            print(f"{r['name']:<25} {r['lawd_cd']:<8}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


# --- 테이블 출력 헬퍼 ---

def _print_trade_table(result: dict[str, Any]) -> None:
    """매매 실거래가를 테이블로 출력."""
    region = result.get("region", "")
    year_month = result.get("year_month", "")
    count = result.get("count", 0)

    print(f"\n{region} 매매 실거래가 ({year_month}) — {count}건\n")
    print(f"{'단지명':<20} {'면적':<8} {'금액(만원)':<12} {'층':<5} {'계약일':<12}")
    print("-" * 60)
    for item in result.get("results", [])[:30]:
        nm = item.get("apt_nm", "")[:20]
        ar = item.get("exclu_use_ar", "")
        amt = f"{item.get('deal_amount', 0):,}"
        floor_str = item.get("floor", "")
        day = f"{item.get('deal_year', '')}.{item.get('deal_month', '')}.{item.get('deal_day', '')}"
        print(f"{nm:<20} {ar:<8} {amt:<12} {floor_str:<5} {day:<12}")
    if count > 30:
        print(f"... 외 {count - 30}건")

    summary = result.get("summary")
    if summary:
        print(f"\n  평균: {summary['avg']:,}만원  중위: {summary['median']:,}만원  "
              f"최고: {summary['max']:,}만원  최저: {summary['min']:,}만원")


def _print_rent_table(result: dict[str, Any]) -> None:
    """전월세 실거래가를 테이블로 출력."""
    region = result.get("region", "")
    year_month = result.get("year_month", "")
    count = result.get("count", 0)

    print(f"\n{region} 전월세 실거래가 ({year_month}) — {count}건\n")
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


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서 생성."""
    parser = argparse.ArgumentParser(
        description="부동산 실거래가 수집 — 국토교통부 공공데이터",
    )
    parser.add_argument(
        "--api-key", default=None, help="공공데이터포털 API 키 (직접 전달)"
    )
    parser.add_argument(
        "--format", choices=["json", "table"], default="json",
        help="출력 형식 (기본: json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # trade — 공통 옵션 헬퍼
    def _add_common_args(p: argparse.ArgumentParser) -> None:
        """trade/rent 공통 옵션 추가."""
        p.add_argument("--year-month", required=True, help="계약년월 (YYYYMM, 예: 202601)")
        p.add_argument("--region", default=None, help="한글 지역명 (예: 강남구)")
        p.add_argument("--lawd-cd", default=None, help="법정동코드 직접 지정 (5자리)")
        p.add_argument(
            "--type", choices=["apt", "offi"], default="apt",
            help="부동산 유형: apt(아파트, 기본) / offi(오피스텔)",
        )
        p.add_argument("--name", default=None, help="단지명 부분 일치 필터")
        p.add_argument("--summary", action="store_true", help="요약 통계 포함")
        p.add_argument("--rows", type=int, default=100, help="페이지당 건수 (기본: 100)")

    # trade
    p_trade = sub.add_parser("trade", help="매매 실거래가 조회")
    _add_common_args(p_trade)

    # rent
    p_rent = sub.add_parser("rent", help="전월세 실거래가 조회")
    _add_common_args(p_rent)

    # regions
    sub.add_parser("regions", help="지역명-법정동코드 목록 출력 (API 키 불필요)")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command in ("trade", "rent"):
            # region 또는 lawd_cd 중 하나 필수
            if not getattr(args, "region", None) and not getattr(args, "lawd_cd", None):
                print(json.dumps(
                    {"status": "error", "error": "args",
                     "detail": "--region 또는 --lawd-cd 중 하나를 지정하세요."},
                    ensure_ascii=False,
                ))
                return 1
            return cmd_trade(args) if args.command == "trade" else cmd_rent(args)

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
    except realestate_api.RealEstateAPIError as e:
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
