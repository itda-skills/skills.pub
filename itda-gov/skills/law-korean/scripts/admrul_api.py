"""행정규칙 API 모듈 — 법제처 DRF Open API (target=admrul).

SPEC: SPEC-LAW-004 FR-022, FR-023
"""
from __future__ import annotations

import urllib.parse
from typing import Any

import sys

from law_api import _fetch_xml, LawAPIError, _SEARCH_URL, _SERVICE_URL
from law_cache import cache_get, cache_set, cache_key

# 캐시 서브디렉토리
ADMRUL_SEARCH_SUBDIR = "admrul_search"
ADMRUL_SUBDIR = "admrul"

# 행정규칙 종류 코드 매핑
KIND_CODES: dict[str, str] = {
    "훈령": "1",
    "예규": "2",
    "고시": "3",
    "공고": "4",
    "지침": "5",
    "기타": "6",
}


def _resolve_kind_code(kind: str | None) -> str | None:
    """한국어 행정규칙 종류를 API 코드로 변환한다. 이미 코드이면 그대로 반환."""
    if kind is None:
        return None
    resolved = KIND_CODES.get(kind)
    if resolved is not None:
        return resolved
    if not kind.isdigit():
        known = ", ".join(KIND_CODES.keys())
        print(f"경고: 인식되지 않는 행정규칙 종류 '{kind}'. 알려진 종류: {known}", file=sys.stderr)
    return kind


def search_admin_rules(
    query: str,
    oc: str = "test",
    search_body: bool = False,
    ministry: str | None = None,
    kind: str | None = None,
    display: int = 20,
    page: int = 1,
    *,
    no_cache: bool = False,
) -> list[dict[str, Any]]:
    """행정규칙을 검색한다.

    Args:
        query: 검색어.
        oc: 법제처 OC (사용자 ID).
        search_body: True이면 본문 검색.
        ministry: 소관부처 코드. None이면 전체.
        kind: 행정규칙 종류 (한국어 또는 코드).
        display: 결과 수 (기본 20).
        page: 페이지 번호.
        no_cache: True이면 캐시 우회.

    Returns:
        [{rule_name, rule_type, ministry_name, issue_date, rule_id}, ...] 목록.

    Raises:
        LawAPIError: 네트워크 오류 또는 파싱 오류 시.
    """
    display = max(1, min(100, display))
    kind_code = _resolve_kind_code(kind)

    # 캐시 키
    cache_params = {
        "query": query, "oc": oc, "search_body": search_body,
        "ministry": ministry, "kind": kind_code,
        "display": display, "page": page,
    }
    key = cache_key(cache_params)

    if not no_cache:
        try:
            cached = cache_get(ADMRUL_SEARCH_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass

    params: dict[str, str] = {
        "OC": oc,
        "target": "admrul",
        "type": "XML",
        "query": query,
        "search": "2" if search_body else "1",
        "display": str(display),
        "page": str(page),
    }
    if ministry:
        params["ministry"] = ministry
    if kind_code:
        params["kindcd"] = kind_code

    url = _SEARCH_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    results: list[dict[str, Any]] = []
    for el in root.findall("admrul"):
        results.append({
            "rule_name": el.findtext("행정규칙명", ""),
            "rule_type": el.findtext("행정규칙종류", ""),
            "ministry_name": el.findtext("소관부처명", ""),
            "issue_date": el.findtext("발령일자", ""),
            "rule_id": el.findtext("행정규칙ID", ""),
        })

    if not no_cache:
        try:
            cache_set(ADMRUL_SEARCH_SUBDIR, key, results, ttl=3600)
        except Exception:
            pass

    return results


def get_admin_rule_detail(
    rule_id: str,
    oc: str = "test",
    *,
    no_cache: bool = False,
) -> dict[str, Any]:
    """행정규칙 상세 정보를 조회한다.

    Args:
        rule_id: 행정규칙ID.
        oc: 법제처 OC (사용자 ID).
        no_cache: True이면 캐시 우회.

    Returns:
        {rule_name, rule_type, ministry_name, issue_date, issue_no,
         effective_date, content} 딕셔너리.

    Raises:
        LawAPIError: 네트워크 오류 또는 파싱 오류 시.
    """
    key = cache_key({"rule_id": rule_id, "oc": oc})
    if not no_cache:
        try:
            cached = cache_get(ADMRUL_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass

    params: dict[str, str] = {
        "OC": oc,
        "target": "admrul",
        "type": "XML",
        "ID": rule_id,
    }
    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    # 행정규칙정보 하위 요소 파싱
    info = root.find("행정규칙정보")
    if info is None:
        info = root

    result: dict[str, Any] = {
        "rule_name": info.findtext("행정규칙명", ""),
        "rule_type": info.findtext("행정규칙종류", ""),
        "ministry_name": info.findtext("소관부처명", ""),
        "issue_date": info.findtext("발령일자", ""),
        "issue_no": info.findtext("발령번호", ""),
        "effective_date": info.findtext("시행일자", ""),
        "content": info.findtext("조문내용", ""),
    }

    if not no_cache:
        try:
            cache_set(ADMRUL_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result
