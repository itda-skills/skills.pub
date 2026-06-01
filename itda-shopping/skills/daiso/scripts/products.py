"""products.py - 상품 검색·가격 조회 (REQ-001 / REQ-002, 무인증).

ref-daiso `tools/searchProducts.ts`(fetchProducts) + `tools/getPriceInfo.ts`
(fetchProductById/fetchProductByName)를 파이썬으로 포팅한다.

엔드포인트: SEARCH_PRODUCTS (GET, FindStoreGoods). 응답 구조는
`{resultSet: {result: [{totalSize, resultDocuments: [...]}]}}` (envelope 외 필드 passthrough).
resultDocuments 각 항목의 다이소 원본 키를 한국어 친화 키로 정규화한다.
"""
from __future__ import annotations

from typing import Any

from errors import ArgumentError
from api import SEARCH_PRODUCTS, DEFAULT_USER_AGENT, get_image_url
from http_util import http_get_json


def _extract_documents(data: Any) -> tuple[list[dict[str, Any]], int]:
    """검색 응답에서 (resultDocuments, totalSize)를 안전하게 추출한다.

    구조가 기대와 다르거나 결과가 없으면 ([], 0)을 반환한다(graceful).
    """
    if not isinstance(data, dict):
        return [], 0
    result_set = data.get("resultSet")
    if not isinstance(result_set, dict):
        return [], 0
    results = result_set.get("result")
    if not isinstance(results, list) or not results:
        return [], 0
    first = results[0]
    if not isinstance(first, dict):
        return [], 0
    docs = first.get("resultDocuments")
    if not isinstance(docs, list):
        return [], 0
    try:
        total = int(first.get("totalSize") or 0)
    except (TypeError, ValueError):
        total = 0
    # dict 항목만 통과 (방어).
    docs = [d for d in docs if isinstance(d, dict)]
    return docs, total


def _to_int_price(raw: Any) -> int:
    """PD_PRC(문자열) → int. 파싱 실패 시 0 (ref `parseInt(...) || 0`)."""
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return 0


def _normalize_product(doc: dict[str, Any]) -> dict[str, Any]:
    """resultDocuments 항목을 출력용 product 스키마로 정규화한다.

    매핑(task spec / output-schema.json):
      PD_NO→id, PDNM||EXH_PD_NM→name, int(PD_PRC)→price,
      get_image_url(ATCH_FILE_URL)→image_url, BRND_NM(빈문자열→None)→brand,
      SOLD_OUT_YN=='Y'→sold_out, NEW_PD_YN=='Y'→is_new, PKUP_OR_PSBL_YN=='Y'→pickup_available.
    """
    brand = doc.get("BRND_NM") or None  # 빈 문자열("")도 None으로
    return {
        "id": doc.get("PD_NO"),
        "name": doc.get("PDNM") or doc.get("EXH_PD_NM") or "",
        "price": _to_int_price(doc.get("PD_PRC")),
        "currency": "KRW",
        "image_url": get_image_url(doc.get("ATCH_FILE_URL")),
        "brand": brand,
        "sold_out": doc.get("SOLD_OUT_YN") == "Y",
        "is_new": doc.get("NEW_PD_YN") == "Y",
        "pickup_available": doc.get("PKUP_OR_PSBL_YN") == "Y",
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
    """키워드로 다이소 상품을 검색한다 (REQ-001).

    Args:
        query: 검색어. 빈 문자열/공백만 → ArgumentError(exit 2).
        page: 페이지 번호(1-base). FindStoreGoods `pageNum`.
        page_size: 페이지당 결과 수. FindStoreGoods `cntPerPage`.
        timeout / user_agent / throttle: http_util로 전달.

    Returns:
        {query, page, page_size, total_count, count, products:[...]}.
        결과 0건이면 count=0, products=[] (exit 3 처리는 CLI 책임).

    Raises:
        ArgumentError: query가 비었을 때.
        AntiBotBlockError / DaisoFetchError: http_util에서 전파.
    """
    if not query or not query.strip():
        raise ArgumentError("검색어를 입력해주세요.")

    params = {
        "searchTerm": query,
        "cntPerPage": page_size,
        "pageNum": page,
    }
    data = http_get_json(
        SEARCH_PRODUCTS,
        params,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    docs, total = _extract_documents(data)
    products = [_normalize_product(d) for d in docs]

    return {
        "query": query,
        "page": page,
        "page_size": page_size,
        "total_count": total,
        "count": len(products),
        "products": products,
    }


def _fetch_product_doc(
    search_term: str,
    *,
    exact_id: str | None,
    timeout: float,
    user_agent: str,
    throttle: float,
) -> dict[str, Any] | None:
    """searchTerm으로 질의 후 단일 상품 문서를 고른다.

    exact_id가 주어지면 PD_NO == exact_id 정확매칭만 반환한다(실패 시 None — ID
    조회가 다른 상품으로 폴백하지 않도록). exact_id가 None이면 첫 결과(이름 조회).
    """
    params = {
        "searchTerm": search_term,
        "cntPerPage": 10 if exact_id else 1,
        "pageNum": 1,
    }
    data = http_get_json(
        SEARCH_PRODUCTS,
        params,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    docs, _ = _extract_documents(data)
    if not docs:
        return None
    if exact_id is not None:
        # ID 조회는 정확매칭만 반환한다. 매칭 실패 시 첫 결과로 폴백하면 "1049516
        # 가격"을 물었는데 다른 상품 가격을 반환하는 오류가 된다(codex P1) → None.
        for doc in docs:
            if doc.get("PD_NO") == exact_id:
                return doc
        return None
    # 이름 조회(exact_id=None)만 첫 결과 폴백 허용.
    return docs[0]


def get_price(
    product_id: str | None = None,
    product_name: str | None = None,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """productId 또는 상품명으로 가격·상세를 조회한다 (REQ-002).

    productId → searchTerm=productId 질의 후 PD_NO 정확매칭(실패 시 EmptyResultError
    exit 3 — 다른 상품으로 폴백하지 않음). productName → 첫 결과. 둘 다 없으면
    ArgumentError(exit 2).

    Args:
        product_id: 상품 ID(PD_NO).
        product_name: 상품명 (product_id가 없을 때 사용).
        timeout / user_agent / throttle: http_util로 전달.

    Returns:
        {product_id, product_name, current_price, currency, image_url, brand, sold_out}.

    Raises:
        ArgumentError: product_id·product_name 둘 다 없을 때.
        EmptyResultError 대신 None→호출부(CLI)에서 exit 3 처리하지 않고,
            여기서는 상품 미발견 시 EmptyResultError를 던진다(CLI exit 3).
    """
    if not product_id and not product_name:
        raise ArgumentError("상품 ID 또는 상품명을 입력해주세요.")

    if product_id:
        doc = _fetch_product_doc(
            product_id,
            exact_id=product_id,
            timeout=timeout,
            user_agent=user_agent,
            throttle=throttle,
        )
    else:
        doc = _fetch_product_doc(
            product_name or "",
            exact_id=None,
            timeout=timeout,
            user_agent=user_agent,
            throttle=throttle,
        )

    if doc is None:
        # 상품 미발견 — CLI에서 exit 3로 잡도록 EmptyResultError.
        from errors import EmptyResultError

        target = product_id or product_name
        raise EmptyResultError(f"상품을 찾을 수 없습니다: {target}")

    brand = doc.get("BRND_NM") or None
    return {
        "product_id": doc.get("PD_NO"),
        "product_name": doc.get("PDNM") or doc.get("EXH_PD_NM") or "",
        "current_price": _to_int_price(doc.get("PD_PRC")),
        "currency": "KRW",
        "image_url": get_image_url(doc.get("ATCH_FILE_URL")),
        "brand": brand,
        "sold_out": doc.get("SOLD_OUT_YN") == "Y",
    }
