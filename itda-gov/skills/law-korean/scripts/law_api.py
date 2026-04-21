"""Shared API module for Korean national law (법제처 DRF Open API).

Provides:
    - parse_article_number(): Convert user article input to JO parameter
    - resolve_oc(): Determine OC (user ID) from CLI arg / env / .env / default
    - _fetch_xml(): HTTP GET + XML parse with retry
    - search_laws(): Search laws by name or keyword
    - get_law_detail(): Retrieve law content / specific article
    - resolve_law_id(): Resolve law name to law ID
    - smart_search(): Fuzzy search with abbreviation + fallback chain
"""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from env_loader import resolve_oc as resolve_oc  # noqa: PLC0414 — re-export
from law_abbreviations import resolve_abbreviation
from law_cache import SEARCH_SUBDIR, LAW_SUBDIR, cache_get, cache_key, cache_set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
_SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"
_REQUEST_TIMEOUT = 20  # 초 (기존 10 → 20)

# 재시도 설정
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # 초기 대기 시간 (초)
_RETRYABLE_CODES = {429, 503, 504}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LawAPIError(Exception):
    """Raised for law API errors: network failures, parse errors, not found."""




# ---------------------------------------------------------------------------
# Article number (JO parameter) encoding
# ---------------------------------------------------------------------------

# @MX:ANCHOR: [AUTO] Core JO encoding used by both get_law_detail and get_law CLI.
# @MX:REASON: fan_in >= 3; encoding logic must remain stable per FR-004.
def parse_article_number(user_input: str | int) -> str:
    """Convert a user-supplied article reference to the 6-char JO parameter.

    Rules (FR-004):
        Plain article:   60  -> '000060'  (str(n).zfill(6))
        Branch article:  76의2  -> '007602'  (article.zfill(4) + branch.zfill(2))

    Note: The SPEC table shows '제1조 -> 000010' which appears to be a
    documentation error.  The consistent formula gives '000001' for article 1.

    Args:
        user_input: Article reference such as 60, '60', '제60조', '76조의2',
                    '제76조의2', '76의2'.

    Returns:
        6-character zero-padded JO string.

    Raises:
        LawAPIError: If user_input cannot be parsed as a valid article number.
    """
    s = str(user_input).strip()

    # 제 접두사 제거
    s = re.sub(r"^제", "", s)
    # 조 접미사 제거 (조의N 또는 조 뒤)
    s = re.sub(r"조(?=의|$)", "", s)

    # 가지조문: 76의2, 14의3 형태
    branch_match = re.match(r"^(\d+)의(\d+)$", s)
    if branch_match:
        article_num = int(branch_match.group(1))
        branch_num = int(branch_match.group(2))
        return f"{article_num:04d}{branch_num:02d}"

    # 일반 조문: 60, 1 등
    plain_match = re.match(r"^(\d+)$", s)
    if plain_match:
        article_num = int(plain_match.group(1))
        return f"{article_num:06d}"

    raise LawAPIError(f"잘못된 조문 번호 형식입니다: '{user_input}'")



# ---------------------------------------------------------------------------
# HTTP + XML helpers
# ---------------------------------------------------------------------------

def _fetch_xml(url: str) -> ET.Element:
    """HTTP GET + XML 파싱. 503/504/429는 지수 백오프로 재시도.

    Args:
        url: 요청할 전체 URL.

    Returns:
        파싱된 XML 루트 Element.

    Raises:
        LawAPIError: 네트워크 오류, HTTP 오류, XML 파싱 오류 시.
    """
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=_REQUEST_TIMEOUT) as resp:
                data = resp.read()
            try:
                return ET.fromstring(data)
            except ET.ParseError as exc:
                raise LawAPIError(f"XML 파싱 오류가 발생했습니다: {exc}") from exc

        except urllib.error.HTTPError as exc:
            if exc.code not in _RETRYABLE_CODES:
                # 재시도 불필요한 HTTP 오류 (404 등)
                raise LawAPIError(f"HTTP 오류: {exc.code}") from exc
            last_exc = exc

        except urllib.error.URLError as exc:
            last_exc = LawAPIError(f"네트워크 오류가 발생했습니다: {exc}")

        except OSError as exc:
            last_exc = LawAPIError(f"연결 오류가 발생했습니다: {exc}")

        # 다음 시도 전 대기 (마지막 시도는 제외)
        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_BASE_DELAY * (2 ** (attempt - 1)))

    # 최대 재시도 소진
    if isinstance(last_exc, LawAPIError):
        raise last_exc
    raise LawAPIError(f"최대 재시도 횟수를 초과했습니다: {last_exc}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# @MX:ANCHOR: [AUTO] Primary search entry point. Called by search_law CLI and resolve_law_id.
# @MX:REASON: fan_in >= 2; interface must remain stable per FR-001.
def search_laws(
    query: str,
    oc: str = "test",
    search_body: bool = False,
    display: int = 10,
    page: int = 1,
    *,
    no_cache: bool = False,
) -> list[dict[str, Any]]:
    """Search Korean laws by name or body keyword.

    Args:
        query: Search term (law name or keyword).
        oc: User ID for the API (OC parameter).
        search_body: If True, search law body text (search=2); otherwise
                     search law name (search=1, default).
        display: Number of results to return (1-100).
        page: Page number for pagination.
        no_cache: 캐시를 사용하지 않고 항상 API를 호출한다.

    Returns:
        List of dicts with keys: law_name, law_type, ministry,
        enforcement_date, law_id.  Empty list when no results.

    Raises:
        LawAPIError: On network or parse errors.
    """
    display = max(1, min(100, display))
    params = {
        "OC": oc,
        "target": "law",
        "type": "XML",
        "query": query,
        "search": "2" if search_body else "1",
        "display": str(display),
        "page": str(page),
    }

    # 캐시 조회
    if not no_cache:
        key = cache_key({"query": query, "oc": oc, "search_body": search_body,
                         "display": display, "page": page})
        try:
            cached = cache_get(SEARCH_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass  # 캐시 실패 시 API 호출로 폴백

    url = _SEARCH_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    results: list[dict[str, Any]] = []
    for law_el in root.findall("law"):
        results.append({
            "law_name": law_el.findtext("법령명한글", ""),
            "law_type": law_el.findtext("법령구분명", ""),
            "ministry": law_el.findtext("소관부처명", ""),
            "enforcement_date": law_el.findtext("시행일자", ""),
            "law_id": law_el.findtext("법령ID", ""),
        })

    # 캐시 저장 (1시간 TTL)
    if not no_cache:
        try:
            cache_set(SEARCH_SUBDIR, key, results, ttl=3600)
        except Exception:
            pass

    return results


def _extract_article_content(unit: ET.Element) -> str:
    """Build full article content from 항/호 sub-elements.

    The API stores article body in <항> elements (paragraphs), each containing
    <항번호> and <항내용>, with optional <호> sub-items. The top-level
    <조문내용> contains only a brief header line; actual text is in <항>.

    Args:
        unit: A <조문단위> Element.

    Returns:
        Multi-line string with all paragraph and sub-item text, or the
        <조문내용> text if no <항> elements exist.
    """
    paragraphs: list[str] = []
    for hang in unit.findall("항"):
        content = (hang.findtext("항내용") or "").strip()
        if content:
            paragraphs.append(content)
        for ho in hang.findall("호"):
            ho_content = (ho.findtext("호내용") or "").strip()
            if ho_content:
                paragraphs.append("  " + ho_content)
            for mok in ho.findall("목"):
                mok_num = (mok.findtext("목번호") or "").strip()
                mok_content = (mok.findtext("목내용") or "").strip()
                if mok_num or mok_content:
                    paragraphs.append(f"    {mok_num} {mok_content}")

    if paragraphs:
        return "\n".join(paragraphs)

    # 항 요소가 없으면 조문내용 사용
    return (unit.findtext("조문내용") or "").strip()


def get_law_detail(
    law_id: str,
    article_no: str | None = None,
    oc: str = "test",
    *,
    no_cache: bool = False,
    structured: bool = False,
) -> dict[str, Any]:
    """Retrieve law content, optionally filtered to a specific article.

    Fetches the full law and filters client-side when article_no is given.
    The JO parameter is not used because the API omits <조문> content when
    JO is specified, returning only <기본정보>.

    Args:
        law_id: Law ID (숫자 or string).
        article_no: User-supplied article reference (e.g. '60', '제76조의2').
                    If provided, only articles with matching 조문번호 are returned.
        oc: User ID for the API.
        no_cache: 캐시를 사용하지 않고 항상 API를 호출한다.
        structured: True이면 항/호/목 구조 파싱 결과를 추가한다.

    Returns:
        Dict with keys:
            - law_name: str
            - articles: list of dicts with article_number, title, content

    Raises:
        LawAPIError: On network, parse errors, or invalid article_no.
    """
    # article_no 유효성 검사 (LawAPIError 발생 가능)
    target_num: str | None = None
    if article_no is not None:
        parse_article_number(article_no)  # 유효성 검사; 잘못된 입력이면 LawAPIError
        # XML <조문번호> 형식으로 정규화 (예: "60", "76의2")
        s = str(article_no).strip()
        s = re.sub(r"^제", "", s)
        s = re.sub(r"조(?=의|$)", "", s)
        target_num = s

    # 캐시 조회
    if not no_cache:
        key = cache_key({"law_id": str(law_id), "article_no": article_no, "oc": oc})
        try:
            cached = cache_get(LAW_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass

    params: dict[str, str] = {
        "OC": oc,
        "target": "law",
        "type": "XML",
        "ID": str(law_id),
    }
    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    # 법령명 추출
    law_name = ""
    basic_info = root.find("기본정보")
    if basic_info is not None:
        law_name = basic_info.findtext("법령명_한글", "")

    # 조문 목록 추출
    articles: list[dict[str, str]] = []
    jo_section = root.find("조문")
    if jo_section is not None:
        for unit in jo_section.findall("조문단위"):
            num = (unit.findtext("조문번호") or "").strip()
            # article_no 지정 시 클라이언트 사이드 필터링
            if target_num is not None and num != target_num:
                continue
            articles.append({
                "article_number": num,
                "title": (unit.findtext("조문제목") or "").strip(),
                "content": _extract_article_content(unit),
            })

    result = {"law_name": law_name, "articles": articles}

    # 캐시 저장 (24시간 TTL)
    if not no_cache:
        try:
            cache_set(LAW_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result


def resolve_law_id(law_name: str, oc: str = "test") -> str:
    """Resolve a law name to its law ID by searching.

    Performs a name search and returns the first result's ID.

    Args:
        law_name: Korean law name to look up.
        oc: User ID for the API.

    Returns:
        Law ID string of the first matching result.

    Raises:
        LawAPIError: If no laws are found with the given name.
    """
    results = search_laws(law_name, oc=oc, display=1)
    if not results:
        raise LawAPIError(f"법령을 찾을 수 없습니다: '{law_name}'")
    return results[0]["law_id"]


# ---------------------------------------------------------------------------
# Smart search (FR-015) — 약어 변환 + 폴백 체인
# ---------------------------------------------------------------------------

_LAW_SUFFIXES = ("법", "령", "규칙", "조례")


# @MX:ANCHOR: [AUTO] 스마트 검색 래퍼. search_law CLI의 기본 검색 진입점.
# @MX:REASON: fan_in >= 2; FR-015 폴백 체인 제어.
def smart_search(
    query: str,
    oc: str = "test",
    search_body: bool = False,
    display: int = 10,
    page: int = 1,
    strict: bool = False,
    no_cache: bool = False,
) -> list[dict[str, Any]]:
    """스마트 검색 — 약어 변환 + 폴백 검색 체인.

    검색 전략 (순서대로):
    1. 직접 검색
    2. 약어 변환 후 재검색
    3. 본문 검색 폴백
    4. 접미사 추가 폴백 (query + "법")

    strict=True이면 폴백 없이 정확 매칭만 수행한다.

    Args:
        query: 검색어 (약어 또는 법령명).
        oc: 법제처 OC (사용자 ID).
        search_body: True이면 본문 검색.
        display: 결과 수 (1-100).
        page: 페이지 번호.
        strict: True이면 폴백 없이 직접 검색만.
        no_cache: 캐시 우회 여부.

    Returns:
        법령 검색 결과 목록.
    """
    # 1단계: 직접 검색
    results = search_laws(query, oc, search_body, display, page, no_cache=no_cache)
    if results or strict:
        return results

    # 2단계: 약어 변환 후 재검색
    resolved = resolve_abbreviation(query)
    if resolved != query:
        results = search_laws(resolved, oc, False, display, page, no_cache=no_cache)
        if results:
            return results

    # 3단계: 본문 검색 폴백
    if not search_body:
        results = search_laws(query, oc, True, display, page, no_cache=no_cache)
        if results:
            return results

    # 4단계: 접미사 추가 폴백
    if not any(query.endswith(suffix) for suffix in _LAW_SUFFIXES):
        results = search_laws(query + "법", oc, False, display, page, no_cache=no_cache)
        if results:
            return results

    return []
