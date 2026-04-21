"""DART OpenAPI (전자공시시스템) 클라이언트.

경쟁사 분석에 필요한 핵심 API만 래핑:
    - 고유번호 조회 (corpCode.xml → ZIP → XML 파싱)
    - 기업개황 (/api/company.json)
    - 주요계정 재무제표 (/api/fnlttSinglAcnt.json)
    - 직원현황 (/api/empSttus.json)

엔드포인트: https://opendart.fss.or.kr/api/
인증: crtfc_key 쿼리 파라미터 (40자리)
"""
from __future__ import annotations

import io
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://opendart.fss.or.kr/api"
_TIMEOUT = 15

# 보고서 코드
REPRT_CODES = {
    "annual": "11011",      # 사업보고서
    "half": "11012",        # 반기보고서
    "q1": "11013",          # 1분기보고서
    "q3": "11014",          # 3분기보고서
}

# 제안서에서 자주 참조하는 핵심 계정명
KEY_ACCOUNTS = {
    "매출액", "수익(매출액)", "영업이익(손실)", "영업이익",
    "당기순이익(손실)", "당기순이익", "자산총계", "부채총계", "자본총계",
}


class DARTAPIError(Exception):
    """DART API 호출 오류."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


def _request_json(endpoint: str, params: dict[str, str]) -> dict[str, Any]:
    """DART API JSON 엔드포인트 호출.

    Args:
        endpoint: 엔드포인트 이름 (예: "company").
        params: 쿼리 파라미터 (crtfc_key 포함).

    Returns:
        파싱된 JSON 응답 딕셔너리.

    Raises:
        DARTAPIError: 네트워크 오류, 파싱 실패, API 오류 등.
    """
    query = urllib.parse.urlencode(params)
    url = f"{_BASE_URL}/{endpoint}.json?{query}"

    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        raise DARTAPIError(f"네트워크 오류: {exc}") from exc

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise DARTAPIError(f"JSON 파싱 실패: {exc}") from exc

    # 에러 코드 확인
    status = data.get("status", "")
    if status and status != "000":
        msg = data.get("message", "알 수 없는 오류")
        raise DARTAPIError(f"DART API 오류 ({status}): {msg}", error_code=status)

    return data


def _request_binary(url: str) -> bytes:
    """바이너리 데이터 다운로드.

    Args:
        url: 전체 URL.

    Returns:
        바이너리 데이터.

    Raises:
        DARTAPIError: 다운로드 실패.
    """
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()
    except urllib.error.URLError as exc:
        raise DARTAPIError(f"다운로드 실패: {exc}") from exc


# @MX:ANCHOR: [AUTO] corp_code 조회의 핵심 함수.
# @MX:REASON: fan_in >= 3 (collect_company의 모든 서브커맨드); 회사명→고유번호 변환 계약.
def find_corp_code(
    api_key: str,
    corp_name: str,
    cache_path: str | None = None,
) -> list[dict[str, str]]:
    """회사명으로 DART 고유번호(corp_code)를 검색.

    corpCode.xml ZIP 파일을 다운로드하여 파싱. cache_path가 지정되면
    다운로드한 XML을 캐싱하여 재사용.

    Args:
        api_key: DART API 인증키.
        corp_name: 검색할 회사명 (부분 일치).
        cache_path: 캐시 파일 경로 (None이면 캐시 안 함).

    Returns:
        매칭된 기업 목록:
        [{"corp_code": "00126380", "corp_name": "삼성전자", "stock_code": "005930"}, ...]

    Raises:
        DARTAPIError: ZIP 다운로드/파싱 실패.
    """
    from pathlib import Path

    xml_content = None

    # 캐시 확인
    if cache_path:
        cache_file = Path(cache_path)
        if cache_file.exists():
            logger.info("캐시에서 corpCode.xml 로드: %s", cache_path)
            xml_content = cache_file.read_bytes()

    # 캐시 없으면 다운로드
    if xml_content is None:
        url = f"{_BASE_URL}/corpCode.xml?crtfc_key={api_key}"
        zip_data = _request_binary(url)

        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                names = zf.namelist()
                if not names:
                    raise DARTAPIError("ZIP 파일이 비어있습니다.")
                xml_content = zf.read(names[0])
        except zipfile.BadZipFile as exc:
            raise DARTAPIError(f"ZIP 파싱 실패: {exc}") from exc

        # 캐시 저장
        if cache_path:
            cache_file = Path(cache_path)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(xml_content)
            logger.info("corpCode.xml 캐시 저장: %s", cache_path)

    # XML 파싱 및 검색
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise DARTAPIError(f"XML 파싱 실패: {exc}") from exc

    results: list[dict[str, str]] = []
    search_lower = corp_name.lower()
    search_parts = _split_mixed_query(corp_name)

    for item in root.iter("list"):
        name = item.findtext("corp_name", "")
        name_eng = item.findtext("corp_eng_name", "")
        if _match_corp(search_lower, search_parts, name, name_eng):
            results.append({
                "corp_code": item.findtext("corp_code", ""),
                "corp_name": name,
                "corp_name_eng": name_eng,
                "stock_code": item.findtext("stock_code", "").strip(),
                "modify_date": item.findtext("modify_date", ""),
            })

    return results


import re

# 한글 유니코드 범위
_RE_HANGUL = re.compile(r"[가-힣]+")
_RE_NON_HANGUL = re.compile(r"[a-zA-Z0-9]+")


def _split_mixed_query(query: str) -> list[str]:
    """한글+영문 혼합 검색어를 부분으로 분리.

    예: "삼성SDS" → ["삼성", "sds"]
        "LG CNS" → ["lg", "cns"]
        "삼성전자" → ["삼성전자"]

    Args:
        query: 검색어.

    Returns:
        분리된 소문자 토큰 목록. 단일 언어면 빈 리스트.
    """
    hangul_parts = _RE_HANGUL.findall(query)
    alpha_parts = _RE_NON_HANGUL.findall(query)

    # 한글과 영문이 모두 있을 때만 분리 (혼합 검색어)
    if hangul_parts and alpha_parts:
        return [p.lower() for p in hangul_parts + alpha_parts]
    return []


def _match_corp(
    search_lower: str,
    search_parts: list[str],
    name: str,
    name_eng: str,
) -> bool:
    """기업명 매칭 판정.

    매칭 전략:
    1. 단순 부분 매칭: 검색어가 한글명 또는 영문명에 포함
    2. 혼합 매칭: 한글 부분이 한글명에, 영문 부분이 영문명에 모두 포함

    Args:
        search_lower: 소문자 변환된 원본 검색어.
        search_parts: _split_mixed_query()의 결과.
        name: DART 한글 회사명.
        name_eng: DART 영문 회사명.

    Returns:
        매칭 여부.
    """
    name_lower = name.lower()
    eng_lower = name_eng.lower()

    # 전략 1: 단순 부분 매칭
    if search_lower in name_lower or search_lower in eng_lower:
        return True

    # 전략 2: 혼합 매칭 (한글+영문 분리)
    if search_parts:
        hangul_ok = all(
            p in name_lower for p in search_parts if _RE_HANGUL.fullmatch(p)
        )
        alpha_ok = all(
            p in eng_lower for p in search_parts if _RE_NON_HANGUL.fullmatch(p)
        )
        if hangul_ok and alpha_ok:
            return True

    return False


def get_company_info(api_key: str, corp_code: str) -> dict[str, Any]:
    """기업개황 조회.

    Args:
        api_key: DART API 인증키.
        corp_code: 8자리 고유번호.

    Returns:
        기업개황 딕셔너리 (corp_name, ceo_nm, induty_code, adres 등).
    """
    return _request_json("company", {
        "crtfc_key": api_key,
        "corp_code": corp_code,
    })


def get_financial_statements(
    api_key: str,
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
) -> list[dict[str, Any]]:
    """단일회사 주요계정 재무제표 조회.

    Args:
        api_key: DART API 인증키.
        corp_code: 8자리 고유번호.
        bsns_year: 사업연도 (예: "2024").
        reprt_code: 보고서 코드 (기본: "11011" 사업보고서).

    Returns:
        재무제표 계정 목록.
        각 항목: {account_nm, fs_div, sj_div, thstrm_amount, frmtrm_amount, ...}
    """
    data = _request_json("fnlttSinglAcnt", {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    })
    return data.get("list", [])


def get_employee_status(
    api_key: str,
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
) -> list[dict[str, Any]]:
    """직원현황 조회.

    Args:
        api_key: DART API 인증키.
        corp_code: 8자리 고유번호.
        bsns_year: 사업연도.
        reprt_code: 보고서 코드.

    Returns:
        직원현황 목록.
        각 항목: {fo_bbm, sexdstn, rgllbr_co, cnttk_co, sm, avrg_cnwk_sdytrn, ...}
    """
    data = _request_json("empSttus", {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    })
    return data.get("list", [])


def filter_key_financials(
    statements: list[dict[str, Any]],
    fs_div: str = "CFS",
) -> list[dict[str, str]]:
    """재무제표에서 제안서용 핵심 계정만 추출.

    Args:
        statements: get_financial_statements()의 반환값.
        fs_div: "CFS"(연결) 또는 "OFS"(개별). 기본 연결.

    Returns:
        핵심 계정 목록: [{account_nm, thstrm_amount, frmtrm_amount}, ...]
    """
    results: list[dict[str, str]] = []

    for item in statements:
        if item.get("fs_div") != fs_div:
            continue
        account = item.get("account_nm", "")
        if account in KEY_ACCOUNTS:
            results.append({
                "account_nm": account,
                "thstrm_amount": item.get("thstrm_amount", ""),
                "frmtrm_amount": item.get("frmtrm_amount", ""),
                "bsns_year": item.get("bsns_year", ""),
                "currency": item.get("currency", "KRW"),
            })

    return results
