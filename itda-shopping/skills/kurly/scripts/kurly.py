#!/usr/bin/env python3
"""kurly.py - 마켓컬리 조회 CLI 진입점.

서브커맨드 2종:
  products <query>                          상품 검색 (search v4, 무인증)
  price (<product_no> | --name <상품명>)     가격/상세 (goods __NEXT_DATA__, 무인증)

공통 옵션(parents): --format {json,markdown} / --output PATH / --timeout SEC
                    / --throttle SEC / --user-agent UA

exit code는 errors.py 상수를 따른다(0 성공, 1 일반, 2 인자, 3 결과없음, 4 차단).
모든 출력 오류는 stderr.

cross-platform: `python3 kurly.py ...` / Windows `py -3 kurly.py ...`.
"""
from __future__ import annotations

import argparse
import sys

# Python 3.10 미만 차단.
if sys.version_info < (3, 10):
    sys.stderr.write("이 스킬은 Python 3.10 이상이 필요합니다.\n")
    raise SystemExit(1)

from errors import ArgumentError, KurlyError, KurlyFetchError, EmptyResultError  # noqa: E402
import api  # noqa: E402
import output as output_mod  # noqa: E402
import products as products_mod  # noqa: E402
import detail as detail_mod  # noqa: E402


def _emit(command: str, data: object, args: argparse.Namespace) -> None:
    """결과를 렌더링해 stdout 또는 --output 파일로 내보낸다.

    --output 경로 쓰기 실패(OSError)는 traceback 누출 대신 KurlyFetchError(exit 1)로
    변환해 main()이 일관 처리한다.
    """
    text = output_mod.render(command, data, args.format)
    if getattr(args, "output", None):
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(text)
                fh.write("\n")
        except OSError as exc:
            raise KurlyFetchError(f"결과 파일 쓰기 실패: {args.output} ({exc})") from exc
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")


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
    data = detail_mod.get_price(
        product_no=args.product_no,
        product_name=args.name,
        timeout=args.timeout,
        user_agent=args.user_agent,
        throttle=args.throttle,
    )
    _emit("price", data, args)
    return 0


# ---------------------------------------------------------------------------
# 파서 구성
# ---------------------------------------------------------------------------


def _positive_int(raw: str) -> int:
    """양의 정수 검증 (page/page-size, 1 이상). 위반 시 argparse exit 2."""
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
        "--timeout",
        type=_positive_float,
        default=30.0,
        metavar="SEC",
        help="요청 타임아웃 초 (기본: 30, 0 초과)",
    )
    common.add_argument(
        "--throttle",
        type=_positive_float,
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
        prog="kurly",
        description="마켓컬리 상품 검색·가격 조회 CLI (비로그인 공개 표면, 조회 전용)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # products --------------------------------------------------------------
    p_products = sub.add_parser(
        "products", parents=[common], help="키워드로 상품 검색 (무인증)"
    )
    p_products.add_argument("query", help="검색어")
    p_products.add_argument(
        "--page", type=_positive_int, default=1, help="페이지 번호 (기본: 1, ≥1)"
    )
    p_products.add_argument(
        "--page-size",
        type=_positive_int,
        default=30,
        dest="page_size",
        help="표시할 상품 수 (기본: 30, ≥1, 서버 perPage 96 고정)",
    )
    p_products.set_defaults(func=_handle_products)

    # price -----------------------------------------------------------------
    p_price = sub.add_parser(
        "price", parents=[common], help="상품 번호 또는 상품명으로 가격/상세 (무인증)"
    )
    p_price.add_argument("product_no", nargs="?", help="상품 번호 (no)")
    p_price.add_argument("--name", help="상품명 (product_no 미지정 시)")
    p_price.set_defaults(func=_handle_price)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점. 반환값은 프로세스 exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # price: product_no·--name 둘 다 없으면 인자 오류(exit 2).
    if args.command == "price" and not args.product_no and not args.name:
        sys.stderr.write("상품 번호 또는 --name 을 입력해주세요.\n")
        return ArgumentError.exit_code

    try:
        return args.func(args)
    except KurlyError as exc:
        sys.stderr.write(f"{exc}\n")
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
