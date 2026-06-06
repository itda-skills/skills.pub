"""api.py - 마켓컬리 엔드포인트 상수 및 헬퍼 (비로그인 공개 표면).

`references/api-endpoints.md` 정본의 URL 상수와 라이브 프로브로 검증된 UA를 둔다.
마켓컬리 웹앱이 실제로 사용하는 **비로그인 검색/상세 표면**만 사용한다 — 공식
개발자 Open API가 아니라 웹이 쓰는 공개 표면이므로 스키마가 바뀌면 깨질 수 있다.

stdlib만 사용한다.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 엔드포인트 상수 (references/api-endpoints.md 정본)
# ---------------------------------------------------------------------------

#: 통합검색 v4. GET, 무인증.
#: 응답 data.listSections[0].data.items[]에 상품, data.meta에 총계(pagination.total)와
#: 추천대체 신호(isSemanticRetryResult)가 함께 온다 → products는 이 1회 호출로 총계까지 얻는다.
SEARCH_V4 = "https://api.kurly.com/search/v4/sites/market/normal-search"

#: 검색 결과 수 v3 (가벼운 count). GET, 무인증.
#: products는 search v4의 meta.pagination.total로 총계를 얻으므로 호출하지 않는다.
#: "검색 전 후보 수만 빠르게" 필요할 때 쓸 수 있도록 상수만 보존한다(참고용).
SEARCH_COUNT_V3 = "https://api.kurly.com/search/v3/sites/market/normal-search/count"

#: 상품 상세 페이지 (HTML __NEXT_DATA__). GET, 무인증.
#: props.pageProps.product에 상세(배송타입 deliveryTypeInfos 등 검색결과엔 없는 필드)가 있다.
GOODS_BASE = "https://www.kurly.com/goods/"

#: 라이브 프로브로 검증된 기본 User-Agent (비로그인 + 평범한 UA로 WAF 없이 200).
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def goods_url(product_no: object) -> str:
    """상품 번호(no)로 컬리 상세 페이지 URL을 만든다.

    Args:
        product_no: 상품 번호(int 또는 str).

    Returns:
        `https://www.kurly.com/goods/<no>` 형식의 상세 페이지 URL.
    """
    return f"{GOODS_BASE}{product_no}"
