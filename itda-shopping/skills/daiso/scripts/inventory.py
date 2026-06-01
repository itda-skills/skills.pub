"""inventory.py - 상품 재고 조회 (REQ-004).

3개 소스를 병합한다:
  (a) 온라인 재고 — `selOnlStck` POST, 무인증. data.stck(number).
  (b) 주변 매장 목록 — stores.find_stores(selStr, 무인증). store_code(strCd) 보유 매장만.
  (c) 매장별 정확 수량 — `selStrPkupStck` POST 배열, **AES 인증**. data[].{strCd, stck(string)}.

ref-daiso `tools/checkInventory.ts`(fetchOnlineStock + fetchStoreInventory + checkInventory)
포팅. 데이터 함정(§2-D):
  - 온라인 stck는 number(0), 매장 stck는 string("0") → 둘 다 int 강제.
  - (0,0) 좌표 매장은 stores.find_stores가 이미 제외(정규화 단계).
  - store_code 없는 매장(레거시 HTML 폴백)은 매장별 수량 조회 불가 → 대상에서 제외.

graceful degrade(REQ-007): (c) 매장별 수량 조회가 AuthError(cryptography 미설치 또는
인증 거부)면 각 매장 quantity=None + `auth.performed=False` + 사유로 응답하고,
(a) 온라인 재고와 (b) 주변 매장 목록은 정상 반환한다. **전체 실패 금지.**

투명성(UX): 매장별 수량은 다이소 AES 인증 조회를 거치므로, store_inventory.auth에
인증 수행 여부(performed)·방식(method)을 **항상** 실어 사용자에게 알린다.
"""
from __future__ import annotations

from typing import Any

import api
import stores as stores_mod
from auth import authed_post_json
from errors import ArgumentError, AuthError


def _coerce_stock(value: Any) -> int:
    """재고 값을 int로 강제한다.

    온라인재고 number(0) / 매장재고 string("0") 양쪽을 흡수한다.
    ref `parseInt(...) || 0` 의미 — 파싱 실패 시 0.
    """
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def fetch_online_stock(
    product_id: str,
    *,
    timeout: float,
    user_agent: str,
    throttle: float,
) -> int:
    """온라인 재고를 조회한다(무인증). 실패/비정상 응답 시 0.

    공개 함수 — `inventory-by-name`(inventory_by_name.py)이 cross-module로 호출한다.
    """
    from http_util import http_post_json

    data = http_post_json(
        api.ONLINE_STOCK,
        {"pdNo": product_id},
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    # L-1: success 부재/falsy → 실패로 본다(ref `!data.success`, 부재=falsy=0).
    if not isinstance(data, dict) or not bool(data.get("success")):
        return 0
    inner = data.get("data")
    if not isinstance(inner, dict):
        return 0
    return _coerce_stock(inner.get("stck"))


def _fetch_store_quantities(
    product_id: str,
    store_codes: list[str],
    *,
    timeout: float,
    user_agent: str,
    throttle: float,
) -> dict[str, int]:
    """매장별 정확 수량을 배치 조회한다(AES 인증).

    selStrPkupStck에 [{pdNo, strCd}, ...] 배열을 POST하고 strCd→수량 맵을 만든다.
    매장 stck는 문자열("0")이므로 int로 강제한다.

    Raises:
        AuthError: cryptography 미설치 또는 인증 거부(403). 호출부가 degrade 처리.
    """
    payload = [{"pdNo": product_id, "strCd": sc} for sc in store_codes]
    data = authed_post_json(
        api.STORE_INVENTORY,
        payload,
        user_agent=user_agent,
        timeout=timeout,
        throttle=throttle,
    )
    quantities: dict[str, int] = {}
    # L-1: success 부재/falsy면 수량 데이터 없음으로 본다(빈 맵 → 각 매장 0 처리).
    if not isinstance(data, dict) or not bool(data.get("success")):
        return quantities
    rows = data.get("data")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("strCd") is not None:
                quantities[str(row["strCd"])] = _coerce_stock(row.get("stck"))
    return quantities


def build_store_inventory(
    product_id: str,
    *,
    store_search: dict[str, Any],
    timeout: float = 30.0,
    user_agent: str = api.DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """이미 조회된 주변 매장 목록(store_search)에 매장별 정확 수량을 부착한다 (D-7).

    `check_inventory`의 store_inventory 조립 로직을 추출한 primitive다. 매장 후보
    추출(store_code 보유) → AES 수량 배치조회 → degrade/auth 블록 → in/out 카운트 →
    total_nearby 까지 한 곳에서 만든다. `inventory-by-name`(inventory_by_name.py)이
    cross-module로 호출하므로 **공개 함수**(underscore 안 씀)다.

    `find_stores` 호출은 이 함수가 하지 않는다 — 호출부가 미리 한 번 호출해 결과
    (store_search)를 넘긴다. 그래야 by-name 경로처럼 좌표 해석을 위해 find_stores를
    먼저 부른 결과를 재고용으로 재사용할 수 있고, find_stores 중복 호출을 막는다.

    Args:
        product_id: 상품 ID(PD_NO). AES selStrPkupStck의 pdNo.
        store_search: stores.find_stores(...) 반환 dict
            ({search_params, source, total_count, count, stores:[...]}).
        timeout / user_agent / throttle: AES 네트워크 옵션.

    Returns:
        {
          total_stores, total_nearby_stores, in_stock_count, out_of_stock_count,
          auth: {method:"daiso-aes", performed: bool, note?|reason?},
          stores: [{...정규화 store..., quantity: int|None}],
        }

    Raises:
        AntiBotBlockError / DaisoFetchError: AES 무인증 외 호출에서 전파.
        (AuthError는 내부에서 graceful degrade 처리 — 전파하지 않는다.)
    """
    # store_code(strCd) 있는 매장만 매장별 수량 조회 대상(레거시 HTML 폴백은 strCd 없음).
    candidate_stores = [
        s for s in store_search.get("stores", []) if s.get("store_code")
    ]
    store_codes = [str(s["store_code"]) for s in candidate_stores]

    # (c) 매장별 정확 수량 (AES 인증). 실패 시 degrade.
    auth_unavailable = False
    degrade_message: str | None = None
    quantities: dict[str, int] = {}
    if store_codes:
        try:
            quantities = _fetch_store_quantities(
                product_id,
                store_codes,
                timeout=timeout,
                user_agent=user_agent,
                throttle=throttle,
            )
        except AuthError as exc:
            # graceful degrade — (a)(b)는 살리고 매장별 수량만 None.
            auth_unavailable = True
            degrade_message = (
                "매장별 정확 수량은 AES 인증이 필요합니다. "
                f"건너뜁니다 ({exc}). cryptography 설치 또는 토큰/UA 확인. "
                "온라인 재고와 주변 매장 목록은 정상 제공됩니다."
            )

    # 각 매장에 quantity 부착(degrade면 None).
    result_stores: list[dict[str, Any]] = []
    in_stock = 0
    out_of_stock = 0
    for s in candidate_stores:
        if auth_unavailable:
            qty: int | None = None
        else:
            qty = quantities.get(str(s["store_code"]), 0)
            if qty > 0:
                in_stock += 1
            else:
                out_of_stock += 1
        enriched = dict(s)
        enriched["quantity"] = qty
        result_stores.append(enriched)

    # M-1: total_stores는 표시 행(=store_code 보유 candidate)과 일관되게 맞춘다.
    #   stores/in_stock_count/out_of_stock_count가 candidate 기준이므로
    #   total_stores도 len(candidate_stores)로 둔다(legacy 무코드 매장 포함 시 불일치 제거).
    #   전체 주변 매장 수(레거시 무코드 포함)는 total_nearby_stores로 분리 노출한다.
    total_nearby = store_search.get("total_count", len(candidate_stores))
    store_inventory: dict[str, Any] = {
        "total_stores": len(candidate_stores),
        "total_nearby_stores": total_nearby,
        "in_stock_count": in_stock,
        "out_of_stock_count": out_of_stock,
        "stores": result_stores,
    }
    # AES 인증 수행 여부를 항상 명시한다(투명성 — 사용자 요청).
    #   performed=True  → 매장별 수량이 다이소 인증(AES) 조회 결과임을 알림.
    #   performed=False → 그 사유(degrade 또는 조회 대상 매장 없음)를 전달.
    if not store_codes:
        store_inventory["auth"] = {
            "method": "daiso-aes",
            "performed": False,
            "reason": "주변 조회 대상 매장이 없어 인증 조회를 수행하지 않았습니다.",
        }
    elif auth_unavailable:
        store_inventory["auth"] = {
            "method": "daiso-aes",
            "performed": False,
            "reason": degrade_message,
        }
    else:
        store_inventory["auth"] = {
            "method": "daiso-aes",
            "performed": True,
            "note": "매장별 정확 수량은 다이소 인증(AES) 조회 결과입니다.",
        }
    return store_inventory


def check_inventory(
    product_id: str,
    keyword: str = "",
    lat: float = stores_mod.DEFAULT_LAT,
    lng: float = stores_mod.DEFAULT_LNG,
    page_size: int = 30,
    *,
    timeout: float = 30.0,
    user_agent: str = api.DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """productId의 재고를 3소스 병합으로 조회한다 (REQ-004).

    (a) 온라인 재고 + (b) 주변 매장(find_stores) + (선택) 상품 요약을 조회한 뒤,
    매장별 수량 조립은 `build_store_inventory` primitive에 위임한다(D-7 — 단일 소스).
    출력은 primitive 도입 전과 **byte-identical**이다(149+ tests 회귀 게이트).

    Args:
        product_id: 상품 ID(PD_NO). 빈 값 → ArgumentError(exit 2).
        keyword: 매장 검색어(매장명/주소). 없으면 좌표 주변 매장.
        lat / lng: 매장 검색 기준 좌표(기본 서울시청).
        page_size: 매장별 수량을 조회할 최대 매장 수.
        timeout / user_agent / throttle: 네트워크 옵션. AES UA 일관성 위해 전달.

    Returns:
        {
          product_id, product?, online_stock,
          location: {lat, lng},
          store_inventory: {
            total_stores, total_nearby_stores, in_stock_count, out_of_stock_count,
            auth: {method: "daiso-aes", performed: bool, note?|reason?},
            stores: [{...정규화 store..., quantity: int|None}],
          }
        }

    Raises:
        ArgumentError: product_id가 비었을 때.
        AntiBotBlockError / DaisoFetchError: (a)(b) 무인증 호출에서 전파.
    """
    if not product_id or not product_id.strip():
        raise ArgumentError("상품 ID를 입력해주세요.")

    # (a) 온라인 재고 (무인증).
    online_stock = fetch_online_stock(
        product_id, timeout=timeout, user_agent=user_agent, throttle=throttle
    )

    # (b) 주변 매장 목록 (무인증, selStr 1순위).
    store_search = stores_mod.find_stores(
        keyword=keyword or None,
        lat=lat,
        lng=lng,
        limit=page_size,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )

    # (c) 매장별 정확 수량 조립 — primitive 위임(D-7). find_stores는 위에서 1회만 호출.
    store_inventory = build_store_inventory(
        product_id,
        store_search=store_search,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )

    # (선택) 상품 요약 — 실패해도 진행(REQ-004 부가정보).
    product_summary: dict[str, Any] | None = None
    try:
        import products as products_mod

        price = products_mod.get_price(
            product_id=product_id,
            timeout=timeout,
            user_agent=user_agent,
            throttle=throttle,
        )
        product_summary = {
            "name": price.get("product_name"),
            "price": price.get("current_price"),
            "brand": price.get("brand"),
            "image_url": price.get("image_url"),
            "sold_out": price.get("sold_out"),
        }
    except Exception:  # noqa: BLE001 - 부가정보 실패는 무시(전체 진행)
        product_summary = None

    result: dict[str, Any] = {
        "product_id": product_id,
        "online_stock": online_stock,
        "location": {"lat": lat, "lng": lng},
        "store_inventory": store_inventory,
    }
    if product_summary is not None:
        result["product"] = product_summary
    return result
