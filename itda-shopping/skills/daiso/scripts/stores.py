"""stores.py - 매장 검색 (REQ-003, 무인증).

소스 2종을 단일 정규화 스키마로 통합한다(OQ-2):
  1순위 selStr (fapi `selStr`, POST, 키워드+좌표, 거리정렬) — camelCase 키.
  폴백  레거시 HTML (`shop_search`, GET, 지역/텍스트) — data-info JSON의 snake_case 키.

소스 선택:
  - 지역(sido/gugun/dong) 지정 또는 keyword 없음 → 레거시 HTML.
  - keyword 있고 지역 없음 → selStr 1순위, 결과 0이면 레거시 HTML 폴백.

정규화 매장 스키마(단일):
  {store_code, name, address, phone, lat, lng, distance_km, open_time, close_time,
   options:{parking, sim_card, pickup, tax_free, elevator, ramp, cashless}}

좌표 가드: strLttd==0 and strLitd==0 인 매장은 제외(쓰레기 km).

HTML 파서는 ref `findStores.ts:parseStoresFromHtml`의 정규식 로직을 stdlib `re`로 포팅한다
(BeautifulSoup 등 외부 의존 금지).
"""
from __future__ import annotations

import json
import re
from typing import Any

from api import (
    DEFAULT_USER_AGENT,
    LEGACY_SHOP_SEARCH,
    STORE_SEARCH,
    format_time,
)
from daiso_keyword import build_store_keyword_variants
from http_util import http_get_text, http_post_json

#: 서울시청 기본 좌표 (EXC-6: 외부 지오코딩 없음).
DEFAULT_LAT = 37.5665
DEFAULT_LNG = 126.978


# ---------------------------------------------------------------------------
# 옵션 정규화 헬퍼
# ---------------------------------------------------------------------------


def _yn(value: Any) -> bool:
    """다이소 Y/N 플래그를 bool로. 'Y'만 True, 그 외(빈 문자열·None·'N')는 False."""
    return value == "Y"


def _empty_options() -> dict[str, bool]:
    """모든 옵션 키가 False인 기본 옵션 dict."""
    return {
        "parking": False,
        "sim_card": False,
        "pickup": False,
        "tax_free": False,
        "elevator": False,
        "ramp": False,
        "cashless": False,
    }


# ---------------------------------------------------------------------------
# selStr (1순위) — camelCase 정규화
# ---------------------------------------------------------------------------


def _coerce_coord(value: Any) -> float | None:
    """좌표 값을 float로. 변환 불가 시 None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_distance(value: Any) -> float | None:
    """km 문자열을 float로. 변환 불가 시 None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_selstr_store(s: dict[str, Any]) -> dict[str, Any] | None:
    """selStr data 항목을 정규화 스키마로 변환한다.

    (0,0) 좌표(쓰레기 km) 매장은 None을 반환해 호출부에서 제외한다.
    """
    lat = _coerce_coord(s.get("strLttd"))
    lng = _coerce_coord(s.get("strLitd"))
    # (0,0) 좌표 가드 — 둘 다 0이면 제외.
    if lat == 0 and lng == 0:
        return None

    return {
        "store_code": s.get("strCd"),
        "name": s.get("strNm") or "",
        "address": s.get("strAddr") or "",
        "phone": s.get("strTno") or None,
        "lat": lat,
        "lng": lng,
        "distance_km": _coerce_distance(s.get("km")),
        "open_time": format_time(s.get("opngTime")),
        "close_time": format_time(s.get("clsngTime")),
        "options": {
            "parking": _yn(s.get("parkYn")),
            "sim_card": _yn(s.get("usimYn")),
            "pickup": _yn(s.get("pkupYn")),
            "tax_free": _yn(s.get("taxfYn")),
            "elevator": _yn(s.get("elvtYn")),
            "ramp": _yn(s.get("entrRampYn")),
            "cashless": _yn(s.get("nocashYn")),
        },
    }


def _fetch_selstr_stores(
    keyword: str,
    lat: float,
    lng: float,
    *,
    timeout: float,
    user_agent: str,
    throttle: float,
) -> list[dict[str, Any]]:
    """selStr 호출 후 정규화된 매장 리스트를 반환한다((0,0) 제외)."""
    payload = {
        "inclusiveStrCd": "",
        "keyword": keyword,
        "curLttd": lat,
        "curLitd": lng,
    }
    data = http_post_json(
        STORE_SEARCH,
        payload,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    stores: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        norm = _normalize_selstr_store(row)
        if norm is not None:
            stores.append(norm)
    return stores


# ---------------------------------------------------------------------------
# 레거시 HTML (폴백) — snake_case data-info 정규화
# ---------------------------------------------------------------------------

#: bx-store div 시작 태그.
_DIV_START_RE = re.compile(r'<div[^>]*class="bx-store"[^>]*>', re.IGNORECASE)
_DATA_START_RE = re.compile(r'data-start="(\d+)"')
_DATA_END_RE = re.compile(r'data-end="(\d+)"')
_DATA_LAT_RE = re.compile(r'data-lat="([^"]+)"')
_DATA_LNG_RE = re.compile(r'data-lng="([^"]+)"')
_DATA_INFO_RE = re.compile(r"data-info='([^']*)'")
_NAME_RE = re.compile(r'<h4[^>]*class="place"[^>]*>([^<]+)</h4>', re.IGNORECASE)
_PHONE_RE = re.compile(r'<em[^>]*class="phone"[^>]*>([^<]*)</em>', re.IGNORECASE)
_ADDR_RE = re.compile(r'<p[^>]*class="addr"[^>]*>([^<]+)</p>', re.IGNORECASE)


def _parse_info_json(info_raw: str) -> dict[str, str]:
    """data-info 속성 문자열을 JSON dict로 파싱한다.

    HTML 엔티티(&quot; → ", &amp; → &)를 복원한 뒤 json.loads. 실패 시 {}.
    """
    info_str = info_raw.replace("&quot;", '"').replace("&amp;", "&")
    try:
        parsed = json.loads(info_str)
        if isinstance(parsed, dict):
            return {str(k): ("" if v is None else str(v)) for k, v in parsed.items()}
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


def parse_stores_from_html(html: str) -> list[dict[str, Any]]:
    """레거시 매장검색 HTML에서 매장 리스트를 정규화 스키마로 파싱한다.

    ref `findStores.ts:parseStoresFromHtml` 포팅:
      - bx-store div를 순회하며 data-start/end/lat/lng/info 속성과
        h4.place / em.phone / p.addr 텍스트를 추출.
      - 필수 속성(start·end·lat·lng) 또는 매장명이 없으면 해당 블록 skip.
      - data-info JSON의 snake_case 키를 옵션 스키마로 매핑.
      - 레거시는 store_code(strCd) 미제공 → None.

    좌표 (0,0) 매장은 정규화 단계에서 제외한다(selStr와 동일 정책).
    """
    stores: list[dict[str, Any]] = []

    matches = list(_DIV_START_RE.finditer(html))
    for idx, div_match in enumerate(matches):
        start_idx = div_match.start()
        div_tag = div_match.group(0)

        # 다음 bx-store div 시작 전까지를 한 블록으로(없으면 +2000자 윈도우).
        if idx + 1 < len(matches):
            block_end = matches[idx + 1].start()
        else:
            block_end = start_idx + 2000
        block = html[start_idx:block_end]

        start_m = _DATA_START_RE.search(div_tag)
        end_m = _DATA_END_RE.search(div_tag)
        lat_m = _DATA_LAT_RE.search(div_tag)
        lng_m = _DATA_LNG_RE.search(div_tag)
        info_m = _DATA_INFO_RE.search(div_tag)

        # 필수 데이터 속성 누락 시 skip (ref와 동일).
        if not (start_m and end_m and lat_m and lng_m):
            continue

        name_m = _NAME_RE.search(block)
        if not name_m:
            continue
        phone_m = _PHONE_RE.search(block)
        addr_m = _ADDR_RE.search(block)

        info = _parse_info_json(info_m.group(1)) if info_m else {}

        lat = _coerce_coord(lat_m.group(1))
        lng = _coerce_coord(lng_m.group(1))
        if lat == 0 and lng == 0:
            continue  # (0,0) 좌표 가드

        phone = ""
        if phone_m:
            phone = phone_m.group(1).replace("T.", "").strip()

        stores.append(
            {
                "store_code": None,  # 레거시 HTML은 strCd 미제공
                "name": name_m.group(1).strip(),
                "address": addr_m.group(1).strip() if addr_m else "",
                "phone": phone or None,
                "lat": lat,
                "lng": lng,
                "distance_km": None,  # 레거시는 거리 미제공
                "open_time": format_time(start_m.group(1)),
                "close_time": format_time(end_m.group(1)),
                "options": {
                    "parking": _yn(info.get("shp_pak")),
                    "sim_card": _yn(info.get("usim_yn")),
                    "pickup": _yn(info.get("online_yn")),
                    "tax_free": _yn(info.get("tax_free")),
                    "elevator": _yn(info.get("elvtor")),
                    "ramp": _yn(info.get("entrramp")),
                    "cashless": _yn(info.get("ptcard")),
                },
            }
        )

    return stores


def _fetch_legacy_stores(
    name_address: str,
    sido: str,
    gugun: str,
    dong: str,
    *,
    timeout: float,
    user_agent: str,
    throttle: float,
) -> list[dict[str, Any]]:
    """레거시 shop_search HTML을 가져와 파싱한다."""
    params = {
        "name_address": name_address,
        "sido": sido,
        "gugun": gugun,
        "dong": dong,
    }
    html = http_get_text(
        LEGACY_SHOP_SEARCH,
        params,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    return parse_stores_from_html(html)


# ---------------------------------------------------------------------------
# 공개 진입점
# ---------------------------------------------------------------------------


def find_stores(
    keyword: str | None = None,
    sido: str | None = None,
    gugun: str | None = None,
    dong: str | None = None,
    lat: float = DEFAULT_LAT,
    lng: float = DEFAULT_LNG,
    limit: int = 50,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """키워드/지역/좌표로 매장을 검색한다 (REQ-003, HF-1).

    소스 선택(OQ-2 + HF-1):
      - 지역(sido/gugun/dong) 지정 → 레거시 HTML(변형 없이 원문).
      - keyword 있고 지역 없음 → 키워드 변형 후보(H-1)를 순차 시도. 각 변형마다
        selStr 1순위 → 결과 0이면 레거시 HTML 폴백을 시도하고, 첫 비어있지 않은
        결과를 채택한다(ref `fetchStores`/`fetchStoreInventory` 패턴).
      - keyword·지역 모두 없음 → 좌표-only selStr POST(`keyword=""`, lat/lng 기준
        거리정렬). HF-1 신규 분기 — `inventory <id>`를 keyword 없이 호출할 때 좌표
        주변 매장을 얻기 위함. `_fetch_selstr_stores`·(0,0) 가드를 그대로 재사용한다.
    `source`에 실제 채택된 소스("selStr" | "legacy_html")를 표기한다.

    인자 가드는 호출부(CLI `_handle_stores`)가 담당한다(HF-2). find_stores는 좌표-only
    분기를 가지므로 keyword/지역이 없어도 raise하지 않는다.

    키워드 변형(H-1): "안산 중앙역 다이소" 원문이 0건이어도 "안산중앙역"·"안산중앙"
    등 축약 후보로 매장을 찾는다. 변형은 이 함수 한 곳에서만 적용한다(inventory는
    find_stores를 호출하므로 자동 상속 — 중복 변형 금지).

    Args:
        keyword: 매장명/주소 키워드.
        sido / gugun / dong: 지역 필터(레거시 HTML 전용).
        lat / lng: selStr 기준 좌표(기본 서울시청).
        limit: 반환 최대 매장 수.
        timeout / user_agent / throttle: http_util로 전달.

    Returns:
        {search_params, source, total_count, count, stores:[정규화...]}.

    Raises:
        AntiBotBlockError / DaisoFetchError: http_util에서 전파.
    """
    has_region = bool(sido or gugun or dong)
    search_params = {
        "keyword": keyword,
        "sido": sido,
        "gugun": gugun,
        "dong": dong,
        "lat": lat,
        "lng": lng,
    }

    source: str
    stores: list[dict[str, Any]]

    if has_region:
        # 레거시 HTML 경로 (지역 검색은 변형 없이 원문 그대로).
        source = "legacy_html"
        stores = _fetch_legacy_stores(
            keyword or "",
            sido or "",
            gugun or "",
            dong or "",
            timeout=timeout,
            user_agent=user_agent,
            throttle=throttle,
        )
    elif keyword and keyword.strip():
        # 키워드 변형 후보(H-1)를 순차 시도한다. ref는 selStr·레거시가 각자 변형을
        # 순회하므로(fetchStoreInventory=selStr / fetchStores=legacy), 여기서도
        # 1단계로 selStr를 전 변형에 시도해 첫 비어있지 않은 결과를 채택하고,
        # 모두 0건이면 2단계로 레거시 HTML을 전 변형에 시도한다.
        variants = build_store_keyword_variants(keyword) or [keyword]
        source = "selStr"
        stores = []
        # 1단계: selStr 1순위 — 변형 순차 시도.
        for variant in variants:
            stores = _fetch_selstr_stores(
                variant,
                lat,
                lng,
                timeout=timeout,
                user_agent=user_agent,
                throttle=throttle,
            )
            if stores:
                break
        # 2단계: selStr가 전 변형에서 0건 → 레거시 HTML 폴백(변형 순차 시도).
        if not stores:
            source = "legacy_html"
            for variant in variants:
                stores = _fetch_legacy_stores(
                    variant,
                    "",
                    "",
                    "",
                    timeout=timeout,
                    user_agent=user_agent,
                    throttle=throttle,
                )
                if stores:
                    break
    else:
        # keyword·지역 모두 없음 → 좌표-only selStr POST(HF-1 신규 분기).
        # keyword="" 로 좌표(lat/lng) 주변 매장을 거리정렬로 받는다. 변형/레거시
        # 폴백 없이 단일 호출 — `_fetch_selstr_stores`·(0,0) 가드 무수정 재사용.
        source = "selStr"
        stores = _fetch_selstr_stores(
            "",
            lat,
            lng,
            timeout=timeout,
            user_agent=user_agent,
            throttle=throttle,
        )

    total = len(stores)
    limited = stores[: max(limit, 0)]
    return {
        "search_params": search_params,
        "source": source,
        "total_count": total,
        "count": len(limited),
        "stores": limited,
    }
