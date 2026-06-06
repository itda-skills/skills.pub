"""products.py - 상품 검색 (search v4, 무인증).

마켓컬리 통합검색 v4(SEARCH_V4)를 호출해 상품 목록과 메타(총계·추천대체 여부)를
정규화한다. 응답 구조(라이브 실측):
  data.listSections[0].data.items[]  → 상품 배열
  data.meta.pagination.total         → 총 결과 수 (count v3 별도 호출 불필요)
  data.meta.isSemanticRetryResult    → True면 정확 매칭 실패 → 의미유사 추천으로 대체
  data.meta.actualKeyword            → 실제 사용된 검색어

가격 우선순위(라이브 실측): discountedPrice(>0)가 있으면 현재가, 없으면 salesPrice.
할인 없는 상품은 discountedPrice=null·discountRate=0.0이다.
"""
from __future__ import annotations

from typing import Any

from errors import ArgumentError
from api import SEARCH_V4, DEFAULT_USER_AGENT, goods_url
from http_util import http_get_json


def _to_int(raw: Any) -> int | None:
    """정수 변환(실패/None → None). 가격·번호 필드용."""
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _extract_items_and_meta(data: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """search v4 응답에서 (items, meta)를 안전하게 추출한다.

    구조가 기대와 다르면 ([], {})를 반환한다(graceful). listSections는 섹션
    배열이며, 각 섹션의 data.items[]를 모아 하나의 상품 리스트로 평탄화한다.
    """
    if not isinstance(data, dict):
        return [], {}
    d = data.get("data")
    if not isinstance(d, dict):
        return [], {}
    meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
    items: list[dict[str, Any]] = []
    sections = d.get("listSections")
    if isinstance(sections, list):
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            sd = sec.get("data")
            if isinstance(sd, dict) and isinstance(sd.get("items"), list):
                items.extend(x for x in sd["items"] if isinstance(x, dict))
    return items, meta


def _price_fields(item: dict[str, Any]) -> tuple[int | None, int | None, int | None, float]:
    """(base_price, discounted_price, current_price, discount_rate)를 계산한다.

    discountedPrice가 0/None이면 할인 없음 → salesPrice가 현재가.
    discount_rate는 float(없으면 0.0).
    """
    base = _to_int(item.get("salesPrice"))
    disc = _to_int(item.get("discountedPrice"))
    disc = disc if disc else None  # 0도 할인 없음으로 취급
    current = disc if disc else base
    try:
        rate = float(item.get("discountRate"))
    except (TypeError, ValueError):
        rate = 0.0
    return base, disc, current, rate


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    """listSections items 항목을 출력용 product 스키마로 정규화한다.

    매핑(라이브 실측 키): no→id, name, shortDescription→short_description,
    salesPrice/discountedPrice→base_price/discounted_price/price, discountRate→discount_rate,
    isSoldOut→sold_out, productViewStatus=='BUY_POSSIBLE'/isPurchaseStatus→purchasable,
    isOnlyAdult→adult_only, reviewCount, listImageUrl→image_url, link=goods/{no}.
    """
    base, disc, current, rate = _price_fields(item)
    no = item.get("no")
    purchasable = item.get("productViewStatus") == "BUY_POSSIBLE" or bool(
        item.get("isPurchaseStatus")
    )
    return {
        "id": no,
        "name": item.get("name") or "",
        "short_description": item.get("shortDescription") or None,
        "price": current,
        "base_price": base,
        "discounted_price": disc,
        "discount_rate": rate,
        "currency": "KRW",
        "sold_out": bool(item.get("isSoldOut")),
        "purchasable": purchasable,
        "adult_only": bool(item.get("isOnlyAdult")),
        "review_count": item.get("reviewCount"),
        "image_url": item.get("listImageUrl") or None,
        "link": goods_url(no) if no is not None else None,
    }


def search_products(
    query: str,
    page: int = 1,
    page_size: int = 30,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """키워드로 마켓컬리 상품을 검색한다.

    Args:
        query: 검색어. 빈 문자열/공백만 → ArgumentError(exit 2).
        page: 페이지 번호(1-base). search v4 `page`.
        page_size: 표시할 상품 수(서버 perPage는 96 고정 — 클라이언트 절단).
        timeout / user_agent / throttle: http_util로 전달.

    Returns:
        {query, actual_keyword, match_type, page, total_count, count, products:[...]}.
        match_type: "exact"(정확 매칭) | "semantic_retry"(매칭 실패 → 의미유사 추천 대체).
        결과 0건이면 count=0, products=[] (exit 3 처리는 CLI 책임).

    Raises:
        ArgumentError: query가 비었을 때.
        AntiBotBlockError / KurlyFetchError: http_util에서 전파.
    """
    if not query or not query.strip():
        raise ArgumentError("검색어를 입력해주세요.")

    params = {"keyword": query, "page": page}
    data = http_get_json(
        SEARCH_V4,
        params,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    items, meta = _extract_items_and_meta(data)
    products = [_normalize_item(x) for x in items]
    if page_size is not None and page_size > 0:
        products = products[:page_size]

    pagination = meta.get("pagination") if isinstance(meta.get("pagination"), dict) else {}
    total = _to_int(pagination.get("total")) or 0
    semantic = bool(meta.get("isSemanticRetryResult"))

    return {
        "query": query,
        "actual_keyword": meta.get("actualKeyword") or query,
        "match_type": "semantic_retry" if semantic else "exact",
        "page": page,
        "total_count": total,
        "count": len(products),
        "products": products,
    }
