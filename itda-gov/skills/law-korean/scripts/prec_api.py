"""판례(판결) API 모듈 — 법제처 DRF Open API (target=prec).

SPEC: SPEC-LAW-004 FR-020, FR-021
"""
from __future__ import annotations

import urllib.parse
from typing import Any

import sys

from law_api import _fetch_xml, LawAPIError, _SEARCH_URL, _SERVICE_URL
from law_cache import cache_get, cache_set, cache_key

# 캐시 서브디렉토리
PREC_SEARCH_SUBDIR = "prec_search"
PREC_SUBDIR = "prec"

# 법원 코드 매핑
COURT_CODES: dict[str, str] = {
    "대법원": "400201",
    "헌법재판소": "400202",
    "각급법원": "400203",
}


def _resolve_court_code(court: str | None) -> str | None:
    """한국어 법원명을 API 코드로 변환한다. 이미 코드이면 그대로 반환."""
    if court is None:
        return None
    resolved = COURT_CODES.get(court)
    if resolved is not None:
        return resolved
    if not court.isdigit():
        known = ", ".join(COURT_CODES.keys())
        print(f"경고: 인식되지 않는 법원명 '{court}'. 알려진 법원: {known}", file=sys.stderr)
    return court


def search_precedents(
    query: str,
    oc: str = "test",
    search_body: bool = False,
    court: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    case_no: str | None = None,
    display: int = 20,
    page: int = 1,
    *,
    no_cache: bool = False,
) -> list[dict[str, Any]]:
    """판례를 검색한다.

    Args:
        query: 검색어 (판례명 또는 키워드).
        oc: 법제처 OC (사용자 ID).
        search_body: True이면 판례 본문 검색.
        court: 법원명 (한국어) 또는 API 코드. None이면 전체.
        date_from: 선고일자 시작 (YYYYMMDD).
        date_to: 선고일자 종료 (YYYYMMDD).
        case_no: 사건번호 필터.
        display: 결과 수 (기본 20).
        page: 페이지 번호.
        no_cache: True이면 캐시 우회.

    Returns:
        [{case_name, case_no, court_name, decision_date, prec_id}, ...] 목록.

    Raises:
        LawAPIError: 네트워크 오류 또는 파싱 오류 시.
    """
    display = max(1, min(100, display))
    court_code = _resolve_court_code(court)

    # 캐시 키 계산
    cache_params = {
        "query": query, "oc": oc, "search_body": search_body,
        "court": court_code, "date_from": date_from, "date_to": date_to,
        "case_no": case_no, "display": display, "page": page,
    }
    key = cache_key(cache_params)

    # 캐시 조회
    if not no_cache:
        try:
            cached = cache_get(PREC_SEARCH_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass

    # URL 파라미터 구성
    params: dict[str, str] = {
        "OC": oc,
        "target": "prec",
        "type": "XML",
        "query": query,
        "search": "2" if search_body else "1",
        "display": str(display),
        "page": str(page),
    }
    if court_code:
        params["court"] = court_code
    if date_from:
        params["startDt"] = date_from
    if date_to:
        params["endDt"] = date_to
    if case_no:
        params["caseNo"] = case_no

    url = _SEARCH_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    results: list[dict[str, Any]] = []
    for prec_el in root.findall("prec"):
        results.append({
            "case_name": prec_el.findtext("판례명", ""),
            "case_no": prec_el.findtext("사건번호", ""),
            "court_name": prec_el.findtext("법원명", ""),
            "decision_date": prec_el.findtext("선고일자", ""),
            "prec_id": prec_el.findtext("판례일련번호", ""),
        })

    # 캐시 저장 (1시간 TTL)
    if not no_cache:
        try:
            cache_set(PREC_SEARCH_SUBDIR, key, results, ttl=3600)
        except Exception:
            pass

    return results


def get_precedent_detail(
    prec_id: str,
    oc: str = "test",
    *,
    no_cache: bool = False,
) -> dict[str, Any]:
    """판례 상세 정보를 조회한다.

    Args:
        prec_id: 판례일련번호.
        oc: 법제처 OC (사용자 ID).
        no_cache: True이면 캐시 우회.

    Returns:
        {case_name, case_no, court_name, decision_date, summary,
         reasoning, ref_articles, ref_cases, full_text} 딕셔너리.

    Raises:
        LawAPIError: 네트워크 오류 또는 파싱 오류 시.
    """
    # 캐시 조회
    key = cache_key({"prec_id": prec_id, "oc": oc})
    if not no_cache:
        try:
            cached = cache_get(PREC_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass

    params: dict[str, str] = {
        "OC": oc,
        "target": "prec",
        "type": "XML",
        "ID": prec_id,
    }
    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    # 판례정보 하위 요소 파싱
    info = root.find("판례정보")
    if info is None:
        info = root

    result: dict[str, Any] = {
        "case_name": info.findtext("사건명", ""),
        "case_no": info.findtext("사건번호", ""),
        "court_name": info.findtext("법원명", ""),
        "decision_date": info.findtext("선고일자", ""),
        "summary": info.findtext("판시사항", ""),
        "reasoning": info.findtext("판결요지", ""),
        "ref_articles": info.findtext("참조조문", ""),
        "ref_cases": info.findtext("참조판례", ""),
        "full_text": info.findtext("판례내용", ""),
    }

    # 캐시 저장 (24시간 TTL)
    if not no_cache:
        try:
            cache_set(PREC_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result
