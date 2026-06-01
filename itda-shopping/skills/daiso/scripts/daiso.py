#!/usr/bin/env python3
"""daiso.py - 다이소 조회 CLI 진입점 (REQ-010).

서브커맨드 5종:
  products  <query>                          상품 검색 (무인증)
  price     (<product_id> | --name <상품명>)  가격/상세 (무인증)
  stores    (<keyword> | --sido S ...)        매장 검색 (무인증)
  inventory <product_id> ...                  재고 조회 (온라인+주변+매장별, AES)
  display-location <product_id> <store_code>  진열 위치 (AES)

공통 옵션(parents): --format {json,markdown} / --output PATH / --timeout SEC
                    / --throttle SEC / --user-agent UA

exit code는 errors.py 상수를 따른다(0 성공, 1 일반, 2 인자, 3 대상없음,
4 차단, 5 미지원, 6 인증). 모든 출력 오류는 stderr.

cross-platform: `python3 daiso.py ...` / Windows `py -3 daiso.py ...`.
"""
from __future__ import annotations

import argparse
import sys

# Python 3.10 미만 차단 (NFR-1).
if sys.version_info < (3, 10):
    sys.stderr.write("이 스킬은 Python 3.10 이상이 필요합니다.\n")
    raise SystemExit(1)

from errors import ArgumentError, DaisoError, DaisoFetchError, EmptyResultError  # noqa: E402
import api  # noqa: E402
import output as output_mod  # noqa: E402
import products as products_mod  # noqa: E402
import stores as stores_mod  # noqa: E402
import inventory as inventory_mod  # noqa: E402
import inventory_by_name as inventory_by_name_mod  # noqa: E402
import display_location as display_location_mod  # noqa: E402


def _emit(command: str, data: object, args: argparse.Namespace) -> None:
    """결과를 렌더링해 stdout 또는 --output 파일로 내보낸다.

    --output 경로 쓰기 실패(OSError: 없는 디렉터리·권한 등)는 traceback 누출 대신
    DaisoFetchError(exit 1)로 변환해 main()이 일관 처리한다.
    """
    text = output_mod.render(command, data, args.format)
    if getattr(args, "output", None):
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text)
                fh.write("\n")
        except OSError as exc:
            raise DaisoFetchError(f"결과 파일 쓰기 실패: {args.output} ({exc})") from exc
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")


def _resolve_coords(args: argparse.Namespace) -> tuple[float, float]:
    """--lat/--lng를 해석한다.

    둘 다 지정 또는 둘 다 미지정만 허용한다(하나만 → ArgumentError exit 2). 하나만 주고
    반대쪽을 서울 기본값으로 섞으면 "부산 위도 + 서울 경도" 같은 틀린 위치 조회가 되므로
    이를 막는다(codex P1). 둘 다 미지정이면 서울시청 기본 좌표.
    """
    if (args.lat is None) != (args.lng is None):
        raise ArgumentError("--lat 와 --lng 는 함께 지정해야 합니다.")
    lat = args.lat if args.lat is not None else stores_mod.DEFAULT_LAT
    lng = args.lng if args.lng is not None else stores_mod.DEFAULT_LNG
    return lat, lng


# ---------------------------------------------------------------------------
# 서브커맨드 핸들러
# ---------------------------------------------------------------------------


def _handle_products(args: argparse.Namespace) -> int:
    data = products_mod.search_products(
        args.query,
        page=args.page,
        page_size=args.page_size,
        timeout=args.timeout,
        user_agent=args.user_agent,
        throttle=args.throttle,
    )
    _emit("products", data, args)
    return 0 if data.get("count", 0) > 0 else EmptyResultError.exit_code


def _handle_price(args: argparse.Namespace) -> int:
    data = products_mod.get_price(
        product_id=args.product_id,
        product_name=args.name,
        timeout=args.timeout,
        user_agent=args.user_agent,
        throttle=args.throttle,
    )
    _emit("price", data, args)
    return 0


def _handle_stores(args: argparse.Namespace) -> int:
    # HF-2: stores 공개 계약은 keyword/지역(sido/gugun/dong) 중 하나 필수.
    #   lat/lng는 기본값이 서울좌표라 사용자 명시 여부를 구분할 수 없으므로 가드에서
    #   보지 않는다 → `daiso stores --lat .. --lng ..`(키워드 없이)도 exit 2.
    #   (좌표-only 매장조회는 find_stores 내부 API 전용 분기 — HF-1.)
    if not (args.keyword or args.sido or args.gugun or args.dong):
        raise ArgumentError("검색어(keyword) 또는 지역(--sido 등)을 입력해주세요.")
    lat, lng = _resolve_coords(args)
    data = stores_mod.find_stores(
        keyword=args.keyword,
        sido=args.sido,
        gugun=args.gugun,
        dong=args.dong,
        lat=lat,
        lng=lng,
        limit=args.limit,
        timeout=args.timeout,
        user_agent=args.user_agent,
        throttle=args.throttle,
    )
    _emit("stores", data, args)
    return 0 if data.get("count", 0) > 0 else EmptyResultError.exit_code


def _handle_inventory(args: argparse.Namespace) -> int:
    """매장별 재고 조회(AES, REQ-004).

    온라인 재고 + 주변 매장 + 매장별 정확 수량(AES)을 병합한다. cryptography
    미설치/인증 거부 시 매장별 수량만 graceful degrade(auth.performed=False)되고,
    온라인 재고·주변 매장은 정상 반환된다(REQ-007 — 전체 실패 금지).
    출력의 store_inventory.auth에 인증 수행 여부를 항상 명시한다(투명성).

    AuthError(전면 실패)·ArgumentError·AntiBotBlock·FetchError 등은 main()의
    상위 except가 errors.py exit_code로 매핑한다(6/2/4/1).
    """
    lat, lng = _resolve_coords(args)
    data = inventory_mod.check_inventory(
        args.product_id,
        keyword=args.keyword or "",
        lat=lat,
        lng=lng,
        page_size=args.page_size,
        timeout=args.timeout,
        user_agent=args.user_agent,
        throttle=args.throttle,
    )
    _emit("inventory", data, args)
    return 0


def _handle_inventory_by_name(args: argparse.Namespace) -> int:
    """상품명 기반 재고 통합 조회(SPEC-SHOPPING-DAISO-002, §7).

    상품 검색 → exact-only 게이트 → (고신뢰 시) 재고 통합. 인자 검증(exit 2):
      - query 빈값 → ArgumentError.
      - --lat/--lng XOR(하나만 지정) → ArgumentError.
      - --product-limit ∉ 1..20 / --page-size ∉ 1..50 → ArgumentError.
    3상태(고신뢰/모호=needs_selection/위치미해결=needs_location)는 전부 exit 0.
    상품 후보 0건은 find_inventory_by_name이 EmptyResultError를 raise → main이 exit 3.
    AuthError 등은 build_store_inventory 내부에서 degrade되어 전파되지 않는다.
    """
    if not args.query or not args.query.strip():
        raise ArgumentError("상품명(query)을 입력해주세요.")
    # lat/lng는 함께 지정해야 한다(price의 product_id/--name 상호배타와 동형 가드).
    if (args.lat is None) != (args.lng is None):
        raise ArgumentError("--lat 와 --lng 는 함께 지정해야 합니다.")
    if not (1 <= args.product_limit <= 20):
        raise ArgumentError("--product-limit 은 1~20 범위여야 합니다.")
    if not (1 <= args.page_size <= 50):
        raise ArgumentError("--page-size 는 1~50 범위여야 합니다.")

    data = inventory_by_name_mod.find_inventory_by_name(
        args.query,
        store_query=args.keyword or "",
        lat=args.lat,
        lng=args.lng,
        product_limit=args.product_limit,
        page_size=args.page_size,
        timeout=args.timeout,
        user_agent=args.user_agent,
        throttle=args.throttle,
    )
    _emit("inventory-by-name", data, args)
    return 0


def _handle_display_location(args: argparse.Namespace) -> int:
    """매장 내 진열 위치 조회(AES, REQ-005).

    순수 AES 기능 — degrade 불가. AuthError는 main() 상위 except에서 exit 6으로
    매핑된다. 진열 위치가 없으면(빈 결과) exit 3(EmptyResult)으로 종료한다.
    """
    data = display_location_mod.get_display_location(
        args.product_id,
        args.store_code,
        timeout=args.timeout,
        user_agent=args.user_agent,
        throttle=args.throttle,
    )
    _emit("display-location", data, args)
    return 0 if data.get("has_location") else EmptyResultError.exit_code


# ---------------------------------------------------------------------------
# 파서 구성
# ---------------------------------------------------------------------------


def _positive_int(raw: str) -> int:
    """양의 정수 검증 (page/page-size/limit 등, 1 이상). 위반 시 argparse exit 2."""
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"정수여야 합니다: {raw!r}") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("1 이상이어야 합니다.")
    return value


def _positive_float(raw: str) -> float:
    """양의 유한 실수 검증 (timeout/throttle, 0 초과·inf/nan 거부)."""
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"숫자여야 합니다: {raw!r}") from exc
    if not (value > 0) or value == float("inf"):
        raise argparse.ArgumentTypeError("0보다 큰 유한값이어야 합니다.")
    return value


def _positive_throttle(raw: str) -> float:
    """--throttle 값 검증 (≤0 오류) — _positive_float 별칭(메시지 호환)."""
    return _positive_float(raw)


def _finite_float(raw: str) -> float:
    """유한 실수 검증 (nan/inf 거부). 좌표가 JSON body로 NaN 새는 것 방지."""
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"숫자여야 합니다: {raw!r}") from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise argparse.ArgumentTypeError("유한한 숫자여야 합니다.")
    return value


def _latitude(raw: str) -> float:
    """위도 검증 (-90~90, 유한)."""
    value = _finite_float(raw)
    if not (-90.0 <= value <= 90.0):
        raise argparse.ArgumentTypeError("위도는 -90~90 범위여야 합니다.")
    return value


def _longitude(raw: str) -> float:
    """경도 검증 (-180~180, 유한)."""
    value = _finite_float(raw)
    if not (-180.0 <= value <= 180.0):
        raise argparse.ArgumentTypeError("경도는 -180~180 범위여야 합니다.")
    return value


def _build_parser() -> argparse.ArgumentParser:
    """argparse 파서를 구성한다 (공통 옵션 parents 패턴)."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="출력 형식 (기본: json)",
    )
    common.add_argument("--output", metavar="PATH", help="결과를 저장할 파일 경로")
    common.add_argument(
        "--timeout", type=_positive_float, default=30.0, metavar="SEC", help="요청 타임아웃 초 (기본: 30, 0 초과)"
    )
    common.add_argument(
        "--throttle",
        type=_positive_throttle,
        default=0.5,
        metavar="SEC",
        help="호출 간 최소 지연 초 (기본: 0.5, 0보다 커야 함)",
    )
    common.add_argument(
        "--user-agent",
        default=api.DEFAULT_USER_AGENT,
        metavar="UA",
        help="User-Agent 헤더 (기본: 프로브 검증 UA)",
    )

    parser = argparse.ArgumentParser(
        prog="daiso",
        description="다이소 상품·재고·매장 조회 CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # products ---------------------------------------------------------------
    p_products = sub.add_parser(
        "products", parents=[common], help="키워드로 상품 검색 (무인증)"
    )
    p_products.add_argument("query", help="검색어")
    p_products.add_argument("--page", type=_positive_int, default=1, help="페이지 번호 (기본: 1, ≥1)")
    p_products.add_argument(
        "--page-size", type=_positive_int, default=30, dest="page_size", help="페이지당 결과 수 (기본: 30, ≥1)"
    )
    p_products.set_defaults(func=_handle_products)

    # price ------------------------------------------------------------------
    p_price = sub.add_parser(
        "price", parents=[common], help="상품 ID 또는 상품명으로 가격/상세 (무인증)"
    )
    p_price.add_argument("product_id", nargs="?", help="상품 ID (PD_NO)")
    p_price.add_argument("--name", help="상품명 (product_id 미지정 시)")
    p_price.set_defaults(func=_handle_price)

    # stores -----------------------------------------------------------------
    p_stores = sub.add_parser(
        "stores", parents=[common], help="키워드 또는 지역으로 매장 검색 (무인증)"
    )
    p_stores.add_argument("keyword", nargs="?", help="매장명/주소 키워드")
    p_stores.add_argument("--sido", help="시/도 (예: 서울)")
    p_stores.add_argument("--gugun", help="구/군 (예: 강남구)")
    p_stores.add_argument("--dong", help="동 (예: 역삼동)")
    # lat/lng는 기본 None — 둘 다 지정/둘 다 미지정만 허용(핸들러 XOR 가드). 미지정 시 서울시청.
    p_stores.add_argument("--lat", type=_latitude, default=None, help="위도 (--lng와 함께, 기본: 서울시청)")
    p_stores.add_argument("--lng", type=_longitude, default=None, help="경도 (--lat와 함께, 기본: 서울시청)")
    p_stores.add_argument("--limit", type=_positive_int, default=50, help="최대 매장 수 (기본: 50, ≥1)")
    p_stores.set_defaults(func=_handle_stores)

    # inventory --------------------------------------------------------------
    p_inventory = sub.add_parser(
        "inventory", parents=[common], help="상품 재고 조회 (온라인+주변+매장별, AES)"
    )
    p_inventory.add_argument("product_id", help="상품 ID (PD_NO)")
    p_inventory.add_argument("--keyword", help="매장 검색어 (매장명/주소)")
    # lat/lng는 기본 None — 둘 다 지정/둘 다 미지정만 허용(핸들러 XOR 가드). 미지정 시 서울시청.
    p_inventory.add_argument("--lat", type=_latitude, default=None, help="위도 (--lng와 함께, 기본: 서울시청)")
    p_inventory.add_argument("--lng", type=_longitude, default=None, help="경도 (--lat와 함께, 기본: 서울시청)")
    p_inventory.add_argument(
        "--page-size", type=_positive_int, default=30, dest="page_size", help="페이지당 매장 수 (기본: 30, ≥1)"
    )
    p_inventory.set_defaults(func=_handle_inventory)

    # inventory-by-name ------------------------------------------------------
    p_ibn = sub.add_parser(
        "inventory-by-name",
        parents=[common],
        help="상품명 + 대강 위치로 검색·(고신뢰 시)재고 통합 조회 (AES)",
    )
    p_ibn.add_argument("query", help="상품 검색어")
    p_ibn.add_argument("--keyword", help="위치 키워드 (역명/동네/매장명)")
    # lat/lng는 기본 None — 둘 다 지정/둘 다 미지정만 허용(핸들러에서 XOR 가드).
    p_ibn.add_argument("--lat", type=_latitude, default=None, help="위도 (--lng와 함께)")
    p_ibn.add_argument("--lng", type=_longitude, default=None, help="경도 (--lat와 함께)")
    p_ibn.add_argument(
        "--product-limit",
        type=int,
        default=5,
        dest="product_limit",
        help="상품 후보 수 (1~20, 기본: 5)",
    )
    p_ibn.add_argument(
        "--page-size",
        type=int,
        default=10,
        dest="page_size",
        help="재고 매장 표시 수 (1~50, 기본: 10)",
    )
    p_ibn.set_defaults(func=_handle_inventory_by_name)

    # display-location -------------------------------------------------------
    p_display = sub.add_parser(
        "display-location", parents=[common], help="매장 내 진열 위치 (AES)"
    )
    p_display.add_argument("product_id", help="상품 ID (PD_NO)")
    p_display.add_argument("store_code", help="매장 코드 (strCd)")
    p_display.set_defaults(func=_handle_display_location)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점. 반환값은 프로세스 exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # price: product_id·--name 둘 다 없으면 인자 오류(exit 2).
    if args.command == "price" and not args.product_id and not args.name:
        sys.stderr.write("상품 ID 또는 --name 을 입력해주세요.\n")
        return ArgumentError.exit_code

    try:
        return args.func(args)
    except DaisoError as exc:
        sys.stderr.write(f"{exc}\n")
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
