"""detail.py - 상품 상세 조회 (goods __NEXT_DATA__, 무인증).

goods/<no> HTML의 `<script id="__NEXT_DATA__">JSON</script>`에서
props.pageProps.product를 파싱한다. 검색결과(search v4 item)엔 없는
배송타입(deliveryTypeInfos)·판매자(sellerName)·재고임박(isLowStock) 등을 포함한다.

price 진입점(get_price)은 product_no면 곧장 goods 상세, --name이면
products.search_products로 첫 결과의 no를 찾은 뒤 goods 상세를 조회한다.
이름 조회 시 search의 match_type(semantic_retry 여부)을 전파해 "정확 매칭이
아니라 추천 상품의 상세"임을 투명하게 알린다(정확성 원칙).
"""
from __future__ import annotations

import json
import re
from typing import Any

from errors import ArgumentError, EmptyResultError, KurlyFetchError
from api import DEFAULT_USER_AGENT, goods_url
from http_util import http_get_text

#: goods HTML의 Next.js 데이터 스크립트. SSR된 상품 데이터가 들어 있다.
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S
)


def _to_int(raw: Any) -> int | None:
    """정수 변환(실패/None → None)."""
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _dig(obj: Any, *keys: str) -> Any:
    """중첩 dict를 안전하게 따라간다. 중간에 dict가 아니면 None."""
    cur = obj
    for key in keys:
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return None
    return cur


def _extract_next_data(html: str, url: str) -> Any:
    """goods HTML에서 __NEXT_DATA__ JSON을 추출·파싱한다.

    Raises:
        KurlyFetchError: 스크립트 태그가 없거나 JSON 파싱 실패(구조 변경).
    """
    match = _NEXT_DATA_RE.search(html)
    if not match:
        raise KurlyFetchError(
            f"상품 상세를 파싱할 수 없습니다 (__NEXT_DATA__ 없음): {url}"
        )
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise KurlyFetchError(
            f"상품 상세 JSON 파싱에 실패했습니다 ({exc.msg}): {url}"
        ) from exc


def _parse_product(product: dict[str, Any], product_no: Any) -> dict[str, Any]:
    """props.pageProps.product를 출력용 상세 스키마로 정규화한다.

    가격 우선순위(라이브 실측): discountedPrice(>0) > showablePrices.salesPrice >
    basePrice. couponDiscountedPrice는 조건부라 현재가 계산에 쓰지 않고 별도 표시만 한다.
    """
    base = _to_int(product.get("basePrice"))
    sales = _to_int(_dig(product, "showablePrices", "salesPrice"))
    disc = _to_int(product.get("discountedPrice"))
    disc = disc if disc else None
    coupon = _to_int(product.get("couponDiscountedPrice"))
    current = disc if disc else (sales if sales else base)

    delivery_types: list[str] = []
    dts = product.get("deliveryTypeInfos")
    if isinstance(dts, list):
        delivery_types = [
            d.get("shortDescription")
            for d in dts
            if isinstance(d, dict) and d.get("shortDescription")
        ]

    tags: list[str] = []
    raw_tags = product.get("tags")
    if isinstance(raw_tags, list):
        tags = [t.get("name") for t in raw_tags if isinstance(t, dict) and t.get("name")]

    no = product.get("no") if product.get("no") is not None else product_no
    return {
        "product_no": no,
        "name": product.get("name") or "",
        "short_description": product.get("shortDescription") or None,
        "seller_name": product.get("sellerName") or None,
        "brand": _dig(product, "brandInfo", "nameGate", "name"),
        "price": current,
        "base_price": base,
        "discounted_price": disc,
        "coupon_discounted_price": coupon,
        "currency": "KRW",
        "sold_out": bool(product.get("isSoldOut")),
        "purchasable": bool(product.get("isPurchaseStatus")),
        "low_stock": bool(product.get("isLowStock")),
        "stock_threshold": _to_int(product.get("stockThreshold")),
        "restock_notify": bool(product.get("canRestockNotify")),
        "free_delivery": bool(product.get("isFreeDelivery")),
        "delivery_types": delivery_types,
        "tags": tags,
        "link": goods_url(no) if no is not None else None,
    }


def get_detail(
    product_no: Any,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """상품 번호(no)로 goods 상세를 조회한다.

    Args:
        product_no: 상품 번호. 빈 값 → ArgumentError(exit 2).
        timeout / user_agent / throttle: http_util로 전달.

    Returns:
        정규화된 상세 dict(배송타입·판매자·재고임박 포함).

    Raises:
        ArgumentError: product_no가 비었을 때.
        EmptyResultError: 상품 미발견/성인인증 필요(비로그인 조회 불가) → exit 3.
        KurlyFetchError: __NEXT_DATA__ 부재/파싱 실패 → exit 1.
        AntiBotBlockError: 403/429 → exit 4.
    """
    if product_no is None or str(product_no).strip() == "":
        raise ArgumentError("상품 번호를 입력해주세요.")
    url = goods_url(product_no)
    html = http_get_text(url, timeout=timeout, user_agent=user_agent, throttle=throttle)
    next_data = _extract_next_data(html, url)
    product = _dig(next_data, "props", "pageProps", "product")
    if not isinstance(product, dict) or product.get("no") is None:
        if _dig(next_data, "props", "pageProps", "adultVerificationFailed"):
            raise EmptyResultError(
                f"성인 인증이 필요한 상품이라 비로그인 조회할 수 없습니다: {product_no}"
            )
        raise EmptyResultError(f"상품 상세를 찾을 수 없습니다: {product_no}")
    return _parse_product(product, product_no)


def get_price(
    product_no: Any = None,
    product_name: str | None = None,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """product_no 또는 상품명으로 가격·상세를 조회한다.

    product_no → goods 상세 직접 조회. product_name → search v4 첫 결과의 no →
    goods 상세. 이름 조회 결과에는 resolved_from_name과 match_type(검색이
    semantic_retry였는지)을 덧붙여 "정확 매칭 상세"인지 "추천 상품 상세"인지 알린다.

    Args:
        product_no: 상품 번호(no).
        product_name: 상품명 (product_no가 없을 때 사용).
        timeout / user_agent / throttle: http_util로 전달.

    Returns:
        정규화된 상세 dict. 이름 조회면 resolved_from_name·match_type 포함.

    Raises:
        ArgumentError: product_no·product_name 둘 다 없을 때.
        EmptyResultError: 상품 미발견.
    """
    if not product_no and not product_name:
        raise ArgumentError("상품 번호 또는 상품명을 입력해주세요.")

    if product_no:
        return get_detail(
            product_no, timeout=timeout, user_agent=user_agent, throttle=throttle
        )

    # 이름 조회: search → 첫 결과 no → goods 상세.
    from products import search_products

    result = search_products(
        product_name or "",
        page=1,
        page_size=10,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    if result["count"] == 0:
        raise EmptyResultError(f"상품을 찾을 수 없습니다: {product_name}")
    first = result["products"][0]
    detail = get_detail(
        first["id"], timeout=timeout, user_agent=user_agent, throttle=throttle
    )
    detail["resolved_from_name"] = product_name
    detail["match_type"] = result["match_type"]
    return detail
