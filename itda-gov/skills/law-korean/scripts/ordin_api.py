"""자치법규 API 모듈 — 법제처 DRF Open API (target=ordin).

SPEC: SPEC-LAW-004 FR-024, FR-025
"""
from __future__ import annotations

import urllib.parse
from typing import Any

import sys

from law_api import _fetch_xml, LawAPIError, _SEARCH_URL, _SERVICE_URL
from law_cache import cache_get, cache_set, cache_key

# 캐시 서브디렉토리
ORDIN_SEARCH_SUBDIR = "ordin_search"
ORDIN_SUBDIR = "ordin"

# 지방자치단체 코드 매핑 (17개 시도)
LOCAL_GOV_CODES: dict[str, str] = {
    "서울특별시": "6110000",
    "부산광역시": "6260000",
    "대구광역시": "6270000",
    "인천광역시": "6280000",
    "광주광역시": "6290000",
    "대전광역시": "6300000",
    "울산광역시": "6310000",
    "세종특별자치시": "6360000",
    "경기도": "6410000",
    "강원특별자치도": "6420000",
    "충청북도": "6430000",
    "충청남도": "6440000",
    "전북특별자치도": "6450000",
    "전라남도": "6460000",
    "경상북도": "6470000",
    "경상남도": "6480000",
    "제주특별자치도": "6490000",
}


def _resolve_org_code(org: str | None) -> str | None:
    """한국어 지자체명을 API 코드로 변환한다. 이미 코드이면 그대로 반환."""
    if org is None:
        return None
    resolved = LOCAL_GOV_CODES.get(org)
    if resolved is not None:
        return resolved
    if not org.isdigit():
        known = ", ".join(LOCAL_GOV_CODES.keys())
        print(f"경고: 인식되지 않는 지자체명 '{org}'. 알려진 지자체: {known}", file=sys.stderr)
    return org


def search_ordinances(
    query: str,
    oc: str = "test",
    search_body: bool = False,
    org: str | None = None,
    display: int = 20,
    page: int = 1,
    *,
    no_cache: bool = False,
) -> list[dict[str, Any]]:
    """자치법규를 검색한다.

    Args:
        query: 검색어.
        oc: 법제처 OC (사용자 ID).
        search_body: True이면 본문 검색.
        org: 지자체명 (한국어) 또는 코드. None이면 전체.
        display: 결과 수 (기본 20).
        page: 페이지 번호.
        no_cache: True이면 캐시 우회.

    Returns:
        [{ordin_name, ordin_type, org_name, promulgate_date, ordin_id}, ...] 목록.

    Raises:
        LawAPIError: 네트워크 오류 또는 파싱 오류 시.
    """
    display = max(1, min(100, display))
    org_code = _resolve_org_code(org)

    # 캐시 키
    cache_params = {
        "query": query, "oc": oc, "search_body": search_body,
        "org": org_code, "display": display, "page": page,
    }
    key = cache_key(cache_params)

    if not no_cache:
        try:
            cached = cache_get(ORDIN_SEARCH_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass

    params: dict[str, str] = {
        "OC": oc,
        "target": "ordin",
        "type": "XML",
        "query": query,
        "search": "2" if search_body else "1",
        "display": str(display),
        "page": str(page),
    }
    if org_code:
        params["org"] = org_code

    url = _SEARCH_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    results: list[dict[str, Any]] = []
    for el in root.findall("ordin"):
        results.append({
            "ordin_name": el.findtext("자치법규명", ""),
            "ordin_type": el.findtext("자치법규종류", ""),
            "org_name": el.findtext("기관명", ""),
            "promulgate_date": el.findtext("공포일자", ""),
            "ordin_id": el.findtext("자치법규ID", ""),
        })

    if not no_cache:
        try:
            cache_set(ORDIN_SEARCH_SUBDIR, key, results, ttl=3600)
        except Exception:
            pass

    return results


def get_ordinance_detail(
    ordin_id: str,
    oc: str = "test",
    *,
    no_cache: bool = False,
) -> dict[str, Any]:
    """자치법규 상세 정보를 조회한다.

    Args:
        ordin_id: 자치법규ID.
        oc: 법제처 OC (사용자 ID).
        no_cache: True이면 캐시 우회.

    Returns:
        {ordin_name, ordin_type, org_name, promulgate_date, effective_date, content} 딕셔너리.

    Raises:
        LawAPIError: 네트워크 오류 또는 파싱 오류 시.
    """
    key = cache_key({"ordin_id": ordin_id, "oc": oc})
    if not no_cache:
        try:
            cached = cache_get(ORDIN_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass

    params: dict[str, str] = {
        "OC": oc,
        "target": "ordin",
        "type": "XML",
        "ID": ordin_id,
    }
    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    # 자치법규정보 하위 요소 파싱
    info = root.find("자치법규정보")
    if info is None:
        info = root

    result: dict[str, Any] = {
        "ordin_name": info.findtext("자치법규명", ""),
        "ordin_type": info.findtext("자치법규종류", ""),
        "org_name": info.findtext("기관명", ""),
        "promulgate_date": info.findtext("공포일자", ""),
        "effective_date": info.findtext("시행일자", ""),
        "content": info.findtext("조문내용", ""),
    }

    if not no_cache:
        try:
            cache_set(ORDIN_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result
