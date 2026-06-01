"""api.py - 다이소 엔드포인트 상수 및 공용 헬퍼.

`references/api-endpoints.md` 정본을 그대로 옮긴 엔드포인트 URL 상수와,
ref-daiso `services/daiso/api.ts`의 `getImageUrl`/`formatTime`을 파이썬으로 포팅한
헬퍼를 정의한다. 이 모듈은 무인증 코어(products·stores·output)와
AES 인증 기능(auth·inventory·display_location)이 공유하므로,
DEFAULT_USER_AGENT도 여기 한 곳에 둔다(/auth/request와 후속 인증 호출의 UA 일관성).

stdlib만 사용한다(urllib.parse).
"""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

# ---------------------------------------------------------------------------
# 엔드포인트 상수 (references/api-endpoints.md 정본)
# ---------------------------------------------------------------------------

#: 상품검색 (가격/상세 포함). GET, 무인증.
SEARCH_PRODUCTS = "https://prdm.daisomall.co.kr/ssn/search/FindStoreGoods"

#: 온라인재고. POST JSON {"pdNo": ...}, 무인증. (mapi 호스트 — fapi 이전 안 됨)
ONLINE_STOCK = "https://mapi.daisomall.co.kr/ms/msg/selOnlStck"

#: 주변매장 (위치 기반, 거리정렬). POST JSON, 무인증. selStr.
STORE_SEARCH = "https://fapi.daisomall.co.kr/ms/msg/selStr"

#: 매장별재고 (정확 수량). POST JSON 배열, AES 인증. selStrPkupStck.
STORE_INVENTORY = "https://fapi.daisomall.co.kr/pd/pdh/selStrPkupStck"

#: 진열위치 (zone/계단/storeErp). POST JSON, AES 인증. selIntPdStDispInfo.
DISPLAY_LOCATION = "https://fapi.daisomall.co.kr/pdo/selIntPdStDispInfo"

#: 인증토큰 발급. GET → 본문=token, 헤더 X-DM-UID=uid. AES 인증 호출 직전 발급.
AUTH_REQUEST = "https://fapi.daisomall.co.kr/auth/request"

#: 레거시 매장검색 (HTML). GET, 무인증. name_address/sido/gugun/dong.
LEGACY_SHOP_SEARCH = "https://www.daiso.co.kr/cs/ajax/shop_search"

#: 레거시 시/도별 구/군 목록. GET. (지역 드릴다운 보조용)
LEGACY_SIDO_SEARCH = "https://www.daiso.co.kr/cs/ajax/sido_search"

#: 레거시 구/군별 동 목록. GET. (지역 드릴다운 보조용)
LEGACY_GUGUN_SEARCH = "https://www.daiso.co.kr/cs/ajax/gugun_search"

#: 상품 이미지 CDN 베이스 URL. 상대경로 prefix 부착에 사용.
IMAGE_BASE_URL = "https://cdn.daisomall.co.kr"

#: 이미지 호스트 치환 (img → cdn).
_IMAGE_SRC_HOST = "img.daisomall.co.kr"
_IMAGE_DST_HOST = "cdn.daisomall.co.kr"

#: 프로브에서 검증된 기본 User-Agent.
#: /auth/request 토큰은 요청자 UA가 payload에 바인딩되므로, 인증 호출과
#: 토큰 발급 호출의 UA를 반드시 동일하게 유지해야 한다(§2-B). 그래서 공유 상수.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def get_image_url(path: str | None) -> str | None:
    """상품 이미지 경로를 표시용 CDN URL로 정규화한다.

    ref-daiso `api.ts:getImageUrl` 포팅.
      - falsy(빈 문자열/None) → None.
      - 절대 URL(http/https) → 호스트가 `img.daisomall.co.kr`이면 `cdn.daisomall.co.kr`로 치환,
        그 외 호스트는 원본 그대로.
      - 상대 경로 → `https://cdn.daisomall.co.kr` prefix 부착.

    Args:
        path: API 응답의 `ATCH_FILE_URL`(상대 또는 절대). None 가능.

    Returns:
        정규화된 전체 이미지 URL, 또는 입력이 비었으면 None.
    """
    if not path:
        return None

    if path.startswith("http://") or path.startswith("https://"):
        parts = urlsplit(path)
        if parts.hostname == _IMAGE_SRC_HOST:
            # netloc(host[:port])에서 host만 치환. 포트/인증정보 보존.
            new_netloc = parts.netloc.replace(_IMAGE_SRC_HOST, _IMAGE_DST_HOST, 1)
            parts = parts._replace(netloc=new_netloc)
        return urlunsplit(parts)

    return f"{IMAGE_BASE_URL}{path}"


def format_time(time: str | None) -> str | None:
    """4자리 시간 문자열(예: "0900")을 "09:00" 형식으로 변환한다.

    ref-daiso `api.ts:formatTime` 포팅. 4자리가 아니면 원본 그대로 반환한다
    (selStr는 이미 "10:00" 형식이라 무변경, 레거시 HTML은 "1000" → "10:00").

    Args:
        time: 시간 문자열. None/빈 문자열은 그대로 반환.

    Returns:
        포맷팅된 시간 문자열(4자리일 때만 콜론 삽입), 아니면 입력 그대로.
    """
    if time and len(time) == 4 and time.isdigit():
        return f"{time[:2]}:{time[2:]}"
    return time
