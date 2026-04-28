"""K-Startup 정부 지원사업 API 클라이언트.

지원 서비스:
    - 통합공고 지원사업 공고 정보 조회 (getAnnouncementInformation01)
    - 통합공고 사업 현황 조회 (getBusinessInformation01)

엔드포인트: https://nidapi.k-startup.go.kr/api/kisedKstartupService/v1
인증: serviceKey 쿼리 파라미터 (공공데이터포털 발급)
활용신청: https://www.data.go.kr/data/15125364/openapi.do

참고: https://www.k-startup.go.kr
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://nidapi.k-startup.go.kr/api/kisedKstartupService/v1"
_TIMEOUT = 15

_ENDPOINT_ANNOUNCEMENT = f"{_BASE_URL}/getAnnouncementInformation"
_ENDPOINT_BUSINESS = f"{_BASE_URL}/getBusinessInformation"


class FundingAPIError(Exception):
    """K-Startup 지원사업 API 호출 오류."""


def _request_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    """공통 JSON 요청 함수.

    Args:
        url: 요청 URL (엔드포인트 포함).
        params: 쿼리 파라미터 딕셔너리.

    Returns:
        파싱된 JSON 응답 딕셔너리.

    Raises:
        FundingAPIError: 네트워크 오류, JSON 파싱 실패.
    """
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}"

    logger.debug("지원사업 API 요청: %s", full_url)

    try:
        with urllib.request.urlopen(full_url, timeout=_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        raise FundingAPIError(f"네트워크 오류: {exc}") from exc

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FundingAPIError(f"JSON 파싱 실패: {exc}") from exc

    return data


def _normalize_response(data: dict[str, Any]) -> dict[str, Any]:
    """API 응답에서 total_count와 items를 정규화."""
    return {
        "total_count": data.get("totalCount", data.get("matchCount", 0)),
        "items": data.get("data", []),
    }


def search_announcements(
    api_key: str,
    keyword: str | None = None,
    active_only: bool = False,
    field: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    rows: int = 100,
) -> dict[str, Any]:
    """통합공고 지원사업 공고 정보 조회.

    Args:
        api_key: 공공데이터포털 API 키.
        keyword: 공고명 키워드 검색 (부분 일치).
        active_only: True면 모집 중인 공고만 조회 (rcrt_prgs_yn=Y).
        field: 지원 분야 필터 (예: "사업화", "R&D").
        from_date: 접수 시작일 하한 (YYYYMMDD).
        to_date: 접수 종료일 상한 (YYYYMMDD).
        page: 페이지 번호 (기본 1).
        rows: 페이지당 건수 (기본 100).

    Returns:
        {"total_count": N, "items": [...]}

    Raises:
        FundingAPIError: 네트워크 오류, API 응답 오류.
    """
    params: dict[str, str] = {
        "serviceKey": api_key,
        "returnType": "json",
        "page": str(page),
        "perPage": str(rows),
    }

    # 검색 조건 파라미터 추가
    if keyword:
        params["cond[biz_pbanc_nm::LIKE]"] = keyword
    if active_only:
        params["cond[rcrt_prgs_yn::EQ]"] = "Y"
    if field:
        params["cond[supt_biz_clsfc::LIKE]"] = field
    if from_date:
        params["cond[pbanc_rcpt_bgng_dt::GTE]"] = from_date
    if to_date:
        params["cond[pbanc_rcpt_end_dt::LTE]"] = to_date

    data = _request_json(_ENDPOINT_ANNOUNCEMENT, params)
    return _normalize_response(data)


def get_business_overview(
    api_key: str,
    keyword: str | None = None,
    year: str | None = None,
    page: int = 1,
    rows: int = 100,
) -> dict[str, Any]:
    """통합공고 사업 현황 조회.

    Args:
        api_key: 공공데이터포털 API 키.
        keyword: 사업명 키워드 검색 (cond[supt_biz_titl_nm::LIKE] 매핑).
        year: 사업 연도 (예: "2026"). cond[biz_yr::EQ] 매핑.
        page: 페이지 번호.
        rows: 페이지당 건수.

    Returns:
        {"total_count": N, "items": [...]}

    Raises:
        FundingAPIError: 네트워크 오류, API 응답 오류.
    """
    params: dict[str, str] = {
        "serviceKey": api_key,
        "returnType": "json",
        "page": str(page),
        "perPage": str(rows),
    }

    if keyword:
        params["cond[supt_biz_titl_nm::LIKE]"] = keyword
    if year:
        params["cond[biz_yr::EQ]"] = year

    data = _request_json(_ENDPOINT_BUSINESS, params)
    return _normalize_response(data)
