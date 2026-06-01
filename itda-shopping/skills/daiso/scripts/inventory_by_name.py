"""inventory_by_name.py - 상품명 기반 재고 통합 조회 (SPEC-SHOPPING-DAISO-002).

상품명 + 대강의 위치만 아는 사용자를 위해 상품 검색 → 후보 스코어링 →
(**고신뢰 시에만**) 재고 통합 조회를 한 번에 수행한다. "물티슈 강남에 재고
있어?"가 기존 2스텝(`products`→id→`inventory`)에서 1스텝으로 합쳐진다.

ref-daiso `tools/findInventoryByName.ts` 포팅 — 단 D-2/D-8/D-9/D-10/D-12 정정 반영:
  - D-2/D-8: **조건부 자동선택(exact-only)**. 범주어("마스크"·"물티슈")는 exact가
    없으므로 needs_selection으로 후보만 제시(재고 미조회). ref는 무조건 top1을
    선택해 범주어 오답 사고 위험 → 보수적으로 차단.
  - D-9/D-10: keyword만 준 경로는 좌표 해석 후 **좌표-only 재조회**(find_stores 2회)로
    거리 정합. lat/lng와 keyword 동시 시 keyword를 버리지 않고 사용.
  - D-12: 3상태(고신뢰/모호/위치미해결) **키 superset 통일**(미해당 필드 null 고정).

오케스트레이션 전용 모듈(D-11): products(무인증 검색)·inventory(AES) 단일책임을
보존하고, 제3책임(검색→스코어→위치해석→재고)을 여기로 분리한다. 재고 primitive는
`inventory.fetch_online_stock`·`inventory.build_store_inventory`를 cross-module로
호출하고, `get_price` 재호출은 하지 않는다(top1 후보를 selected_product로 재사용).
"""
from __future__ import annotations

import unicodedata
from typing import Any

import api
import inventory as inventory_mod
import products as products_mod
import stores as stores_mod
from errors import EmptyResultError

#: 서울시청 기본 좌표 (EXC: 외부 지오코딩 없음). stores 모듈과 동일.
DEFAULT_LAT = stores_mod.DEFAULT_LAT
DEFAULT_LNG = stores_mod.DEFAULT_LNG

#: 후속 도구 안내(고정 문안).
_NEXT_STEPS = {
    "product_search": "daiso products <검색어>",
    "inventory": "daiso inventory <상품ID> [--keyword 위치]",
    "display_location": "daiso display-location <상품ID> <매장코드>",
    "note": "진열 위치가 필요하면 store_inventory.stores[].store_code로 display-location을 호출하세요.",
}


def normalize(s: str) -> str:
    """상품명 비교용 정규화 (§6).

    NFKC 정규화 + 소문자화 후, 유니코드 카테고리가 P(구두점) 또는 Z(공백/구분자)로
    시작하는 문자를 모두 제거한다. ref `toLowerCase().replace(/\\s+/g,"")`보다 강한
    정규화 — 공백뿐 아니라 하이픈·괄호 등 구두점도 제거해 "물티슈(70매)"와
    "물티슈 70매"를 같게 본다.

    Args:
        s: 원문 문자열(상품명 또는 검색어).

    Returns:
        정규화 문자열. None/비문자열은 빈 문자열로 방어.
    """
    if not s:
        return ""
    t = unicodedata.normalize("NFKC", str(s)).lower()
    return "".join(
        ch for ch in t if not unicodedata.category(ch).startswith(("P", "Z"))
    )


def _score(cand: dict[str, Any], idx: int, nq: str) -> float:
    """상품 후보 점수 (§6).

    정확100 + 가용20(not sold_out) + prefix10 + contains5 - idx*0.001.
    idx 감점은 동점 시 검색 순위를 보존하기 위한 미세 tie-breaker다.

    Args:
        cand: 상품 후보 dict(products.search_products products[] 항목).
        idx: 검색 결과 내 순서(0-base).
        nq: 정규화된 질의(normalize(query)).

    Returns:
        점수(float).
    """
    nn = normalize(cand.get("name") or "")
    score = 0.0
    if nn == nq:
        score += 100.0
    if not cand.get("sold_out"):
        score += 20.0
    if nq and nn.startswith(nq):
        score += 10.0
    if nq and nq in nn:
        score += 5.0
    score -= idx * 0.001
    return score


def _gate(cands: list[dict[str, Any]], nq: str) -> dict[str, Any]:
    """exact-only 자동선택 게이트 (D-8/§6).

    후보를 점수순 정렬해 top1/top2를 본다.
      - exact   = normalize(top1.name) == nq
      - gap_ok  = 후보가 1개거나, top1.score - top2.score > 10
      - confident = exact and gap_ok
    confident가 아니면 needs_selection(후보만 반환, 재고 미조회). 범주어는 exact가
    없어 needs_selection으로 빠지고, 같은 이름 다른 옵션이 2개면 gap_ok=False로 모호.

    Args:
        cands: 상품 후보 리스트(비어있지 않음 — 호출부가 0건을 먼저 처리).
        nq: 정규화된 질의.

    Returns:
        {sorted, top1, top2, exact, gap_ok, confident}.
    """
    scored = sorted(
        ((c, _score(c, i, nq)) for i, c in enumerate(cands)),
        key=lambda pair: pair[1],
        reverse=True,
    )
    top1, s1 = scored[0]
    top2: dict[str, Any] | None = scored[1][0] if len(scored) > 1 else None
    s2 = scored[1][1] if len(scored) > 1 else None

    exact = normalize(top1.get("name") or "") == nq
    gap_ok = (len(scored) == 1) or (s2 is not None and (s1 - s2) > 10)
    confident = exact and gap_ok
    return {
        "sorted": [c for c, _ in scored],
        "scores": {id(c): sc for c, sc in scored},
        "top1": top1,
        "top1_score": s1,
        "top2": top2,
        "exact": exact,
        "gap_ok": gap_ok,
        "confident": confident,
    }


def _candidate_view(
    cand: dict[str, Any], score: float
) -> dict[str, Any]:
    """후보 경량 뷰 (§8/§11 — id/name/price/score/sold_out만).

    전체 product dict가 아니라 토큰 절감용 경량 필드만 노출한다.
    """
    return {
        "id": cand.get("id"),
        "name": cand.get("name"),
        "price": cand.get("price"),
        "score": round(score, 3),
        "sold_out": bool(cand.get("sold_out")),
    }


def _resolve_location_and_stores(
    store_query: str,
    lat: float | None,
    lng: float | None,
    *,
    page_size: int,
    timeout: float,
    user_agent: str,
    throttle: float,
) -> dict[str, Any]:
    """위치를 해석하고 재고용 주변 매장(store_search)을 확보한다 (§5, D-10/refine).

    | 입력 | center(source) | store_search · 거리 기준 | find_stores |
    |---|---|---|---|
    | lat&lng (+keyword 선택) | (lat,lng) input | find_stores(keyword=store_query or "", lat, lng) · 지정좌표 | 1 |
    | keyword만 | find_stores(store_query)[0] 좌표 store_query (0건→needs_location) | 동일 키워드 결과 그대로 · 거리=검색 기본좌표(근사) | 1 |
    | 없음 | 서울시청 default | find_stores("", 서울) 좌표-only · 서울기준 | 1 |

    refine 발견: keyword-only는 좌표-only 재조회(2콜)를 폐기하고 키워드 결과를 그대로
    쓴다(다이소 빈-keyword selStr ~1개만 반환 → 커버리지 보존). 그 결과 거리값은 검색
    기본 좌표 기준이라 원거리 키워드("부산")에선 근사치다 → location.distance_basis로 명시.

    좌표 침묵 폴백 금지(D-5): nonempty store_query가 0건이면 서울 재고를 답하지 않고
    needs_location 신호를 반환한다(store_search=None).

    Returns:
        {location|None, store_search|None, needs_location: bool}.
        location에는 distance_basis(거리값 기준 설명)를 함께 싣는다.
    """
    # 경로 1: lat & lng 명시 → 그 좌표 기준. keyword가 있으면 함께 넘긴다(D-10).
    if lat is not None and lng is not None:
        store_search = stores_mod.find_stores(
            keyword=(store_query or ""),
            lat=lat,
            lng=lng,
            limit=page_size,
            timeout=timeout,
            user_agent=user_agent,
            throttle=throttle,
        )
        location = {
            "lat": lat,
            "lng": lng,
            "source": "input",
            "store_name": None,
            "store_address": None,
            "distance_basis": "지정 좌표",  # 거리값이 사용자 지정 좌표 기준 — 정확
        }
        return {"location": location, "store_search": store_search, "needs_location": False}

    # 경로 2: keyword만 → 키워드 selStr 결과를 그대로 재고 대상으로 쓴다(find_stores 1회).
    #   ★refine 라이브 발견: 다이소 좌표-only selStr(빈 keyword)는 ~1개만 반환해, 과거
    #   D-9의 "center 해석 후 좌표-only 재조회"는 커버리지를 20→1로 죽였다(평이 inventory는
    #   키워드로 20개 조회). 키워드 결과(매칭 매장 전체)를 그대로 써 평이 inventory와
    #   동일 커버리지를 보장한다. 거리값(distance_km)은 검색 API 기준(기본 좌표)이며
    #   center=stores[0]은 위치 표시용이다(codex R2 거리정밀도 < 커버리지 trade-off).
    if store_query and store_query.strip():
        store_search = stores_mod.find_stores(
            keyword=store_query,
            lat=DEFAULT_LAT,
            lng=DEFAULT_LNG,
            limit=page_size,
            timeout=timeout,
            user_agent=user_agent,
            throttle=throttle,
        )
        stores = store_search.get("stores") or []
        if not stores:
            # D-5: nonempty 위치 키워드가 0건 → 서울 폴백 금지, 위치 미해결.
            return {"location": None, "store_search": None, "needs_location": True}
        first = stores[0]
        location = {
            "lat": first.get("lat"),
            "lng": first.get("lng"),
            "source": "store_query",
            "store_name": first.get("name"),
            "store_address": first.get("address"),
            # 거리값은 검색 기본 좌표(서울) 기준이라 원거리 키워드에선 근사치다(좌표 미지정 시).
            "distance_basis": "검색 기준(기본 좌표) — 거리 근사",
        }
        return {"location": location, "store_search": store_search, "needs_location": False}

    # 경로 3: 위치 정보 없음 → 서울시청 좌표-only(default).
    store_search = stores_mod.find_stores(
        keyword="",
        lat=DEFAULT_LAT,
        lng=DEFAULT_LNG,
        limit=page_size,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    location = {
        "lat": DEFAULT_LAT,
        "lng": DEFAULT_LNG,
        "source": "default",
        "store_name": None,
        "store_address": None,
        "distance_basis": "서울시청 기본 좌표",  # 위치 미지정 — 서울 기준
    }
    return {"location": location, "store_search": store_search, "needs_location": False}


def _empty_summary(headline: str) -> dict[str, Any]:
    """summary superset 골격 (모든 플래그 기본값)."""
    return {
        "headline": headline,
        "confident": False,
        "needs_selection": False,
        "needs_location": False,
        "sold_out_warning": None,
    }


def _base_result(
    query: str,
    store_query: str,
    candidate_limit: int,
    candidate_views: list[dict[str, Any]],
    product_total_count: int,
) -> dict[str, Any]:
    """3상태 공통 superset 골격 (D-12 — 미해당 필드 null 고정)."""
    return {
        "command": "inventory-by-name",
        "query": query,
        "store_query": store_query,
        "location": None,
        "summary": _empty_summary(""),
        "selected_product": None,
        "product_candidates": candidate_views,
        "product_total_count": product_total_count,
        "candidate_limit": candidate_limit,
        "online_stock": None,
        "store_inventory": None,
        "next_steps": dict(_NEXT_STEPS),
    }


def _apply_page_size(store_inventory: dict[str, Any], page_size: int) -> dict[str, Any]:
    """store_inventory.stores를 page_size로 잘라 shown·stores_truncated를 세팅한다 (§8/§11).

    build_store_inventory는 이미 find_stores limit으로 잘린 결과를 받지만, 출력
    토큰 절감을 위해 표시 행을 page_size로 한 번 더 제한하고 잘림 여부를 알린다.
    total_nearby_stores는 primitive가 이미 실어둔 값을 보존한다.
    """
    stores = store_inventory.get("stores") or []
    shown_stores = stores[: max(page_size, 0)]
    # find_stores(limit=page_size)가 이미 stores를 잘라 오므로 len(stores)는 page_size와
    # 같아 truncation 판단 기준이 될 수 없다. 주변 전체 매장 수(total_nearby_stores,
    # = selStr total_count)를 기준으로 "표시분보다 더 있는가"를 판단한다.
    total_nearby = store_inventory.get("total_nearby_stores", len(stores))
    out = dict(store_inventory)
    out["stores"] = shown_stores
    out["shown"] = len(shown_stores)
    out["stores_truncated"] = total_nearby > len(shown_stores)
    out.setdefault("total_nearby_stores", total_nearby)
    return out


def find_inventory_by_name(
    query: str,
    *,
    store_query: str = "",
    lat: float | None = None,
    lng: float | None = None,
    product_limit: int = 5,
    page_size: int = 10,
    timeout: float = 30.0,
    user_agent: str = api.DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """상품명으로 상품을 찾고 (고신뢰 시) 재고를 통합 조회한다 (§5).

    단계:
      1. products.search_products(query, page=1, page_size=product_limit) — total_count 확보.
         후보 0건 → EmptyResultError(CLI exit 3).
      2. exact-only 게이트(_gate). NOT confident → needs_selection 상태(재고 미조회).
      3. 위치+매장 해석(_resolve_location_and_stores). nonempty store_query 0건 →
         needs_location 상태(재고 미조회, 서울 폴백 금지).
      4. 고신뢰 + 위치해결 → inventory.fetch_online_stock + inventory.build_store_inventory.
         selected_product는 top1 후보 재사용(get_price 0).

    Args:
        query: 상품 검색어. 빈 값 가드는 CLI 책임(여기서도 0건이면 EmptyResult).
        store_query: 위치 키워드(역명/동네/매장명). 없으면 서울 폴백(default).
        lat / lng: 좌표 직접 지정. 둘 다 또는 둘 다 없음(CLI가 XOR을 exit 2로 막음).
        product_limit: 상품 후보 수(1..20, CLI 검증).
        page_size: 재고 매장 표시 수(1..50, CLI 검증).
        timeout / user_agent / throttle: 네트워크 옵션.

    Returns:
        §8 3상태 superset dict(command=="inventory-by-name").

    Raises:
        EmptyResultError: 상품 후보 0건(CLI exit 3).
        AntiBotBlockError / DaisoFetchError / AuthError: 하위 호출에서 전파(AuthError는
            build_store_inventory 내부에서 graceful degrade되어 전파되지 않음).
    """
    # 1. 검색.
    search = products_mod.search_products(
        query,
        page=1,
        page_size=product_limit,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    cands = search.get("products") or []
    product_total_count = int(search.get("total_count") or 0)

    if not cands:
        # 후보 0건 → exit 3. (superset을 못 채우므로 CLI에서 잡아 stderr+exit3.)
        raise EmptyResultError(f'"{query}" 상품 후보를 찾지 못했습니다.')

    # 2. 스코어링 + 게이트.
    gate = _gate(cands, normalize(query))
    score_map = gate["scores"]
    candidate_views = [
        _candidate_view(c, score_map.get(id(c), 0.0)) for c in gate["sorted"]
    ]

    result = _base_result(
        query=query,
        store_query=store_query,
        candidate_limit=product_limit,
        candidate_views=candidate_views,
        product_total_count=product_total_count,
    )

    top1 = gate["top1"]

    # 2b. 모호(NOT confident) → needs_selection. 재고 미조회.
    if not gate["confident"]:
        result["summary"] = {
            "headline": (
                f'"{query}" 검색 결과 {len(cands)}개 후보 중 자동 선택할 수 없습니다. '
                "아래 후보에서 상품을 골라 inventory <상품ID>로 재고를 조회하세요."
            ),
            "confident": False,
            "needs_selection": True,
            "needs_location": False,
            "sold_out_warning": None,
        }
        return result

    # 3. 위치 + 매장 해석.
    resolved = _resolve_location_and_stores(
        store_query,
        lat,
        lng,
        page_size=page_size,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )

    # 3b. 위치 미해결(nonempty store_query 0건) → needs_location. 재고 미조회.
    if resolved["needs_location"]:
        result["selected_product"] = _candidate_view(top1, gate["top1_score"])
        result["summary"] = {
            "headline": (
                f'"{top1.get("name")}" 상품을 선택했지만, 위치 "{store_query}"에 해당하는 '
                "매장을 찾지 못했습니다. 다른 위치 키워드나 좌표(--lat/--lng)를 지정하세요."
            ),
            "confident": True,
            "needs_selection": False,
            "needs_location": True,
            "sold_out_warning": None,
        }
        return result

    # 4. 고신뢰 + 위치해결 → 재고 통합 조회.
    product_id = top1.get("id")
    online_stock = inventory_mod.fetch_online_stock(
        product_id,
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    store_inventory = inventory_mod.build_store_inventory(
        product_id,
        store_search=resolved["store_search"],
        timeout=timeout,
        user_agent=user_agent,
        throttle=throttle,
    )
    store_inventory = _apply_page_size(store_inventory, page_size)

    sold_out_warning: str | None = None
    if top1.get("sold_out"):
        # D-8: exact 매치이지만 품절 → 조회하되 강경고.
        sold_out_warning = (
            f'⚠️ 선택 상품 "{top1.get("name")}"은(는) 품절 상태입니다. '
            "매장 재고가 있어도 온라인 구매가 불가할 수 있습니다."
        )

    in_stock = store_inventory.get("in_stock_count", 0)
    total_stores = store_inventory.get("total_stores", 0)
    # 공백만인 store_query("   ")는 truthy라 그대로 노출되므로 strip 후 판정(MINOR-2).
    scope = (store_query or "").strip() or "기준 위치 주변"
    result["location"] = resolved["location"]
    result["selected_product"] = _candidate_view(top1, gate["top1_score"])
    result["online_stock"] = online_stock
    result["store_inventory"] = store_inventory
    result["summary"] = {
        "headline": (
            f'"{query}" → "{top1.get("name")}" 기준 재고: {scope} 매장 {total_stores}곳 중 '
            f"{in_stock}곳 보유, 온라인 재고 {online_stock}개."
        ),
        "confident": True,
        "needs_selection": False,
        "needs_location": False,
        "sold_out_warning": sold_out_warning,
    }
    return result
