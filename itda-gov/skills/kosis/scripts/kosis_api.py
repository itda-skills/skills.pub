"""KOSIS 국가통계포털 OpenAPI 클라이언트.

제안서/사업계획서에 필요한 통계 데이터 수집:
    - 통합검색 (키워드 → 통계표 목록)
    - 통계자료 조회 (orgId + tblId → 실제 데이터)

엔드포인트: https://kosis.kr/openapi/
인증: apiKey 쿼리 파라미터
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_TIMEOUT = 15

# 엔드포인트
_SEARCH_URL = "https://kosis.kr/openapi/statisticsSearch.do"
_DATA_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
_LIST_URL = "https://kosis.kr/openapi/statisticsList.do"

# 활용신청 페이지 — 인증키 관련 오류 시 사용자에게 자동 부착
_KOSIS_APPLY_URL = "https://kosis.kr/openapi/"

_KOSIS_SETUP_GUIDE = (
    "\n[설정 안내] KOSIS_API_KEY를 확인하세요:\n"
    f"  1. {_KOSIS_APPLY_URL} 접속 → 회원가입 → Open API → 활용신청\n"
    "  2. 활용신청 즉시 자동 승인 (대기 없음). 마이페이지에서 인증키 확인\n"
    "  3. 환경변수 설정:\n"
    "     claude config set env.KOSIS_API_KEY \"발급받은_키\"\n"
    "  4. 첫 호출 실패 시 점검 절차:\n"
    "     - Base64 키 끝 '=' 패딩 누락 여부 확인 (전체 복사 필수)\n"
    "     - 만료된 인증키는 마이페이지에서 기간 연장 가능\n"
    "     - 잠시(수 분) 후 재시도 — 신규 발급 직후 일시적 미반영 가능\n"
)

# 정본 에러 코드 매핑 (출처: KOSIS OpenAPI 매뉴얼 v1.0 §1.4.2)
# references/kosis-매뉴얼/01-인증키-에러메시지.md 참조
_ERROR_CODE_HINTS: dict[str, dict[str, Any]] = {
    "10": {"desc": "인증키 누락", "category": "setup", "needs_apply_url": True},
    "11": {"desc": "인증키 기간만료", "category": "setup", "needs_apply_url": True},
    "20": {"desc": "필수요청변수 누락", "category": "setup", "needs_apply_url": False},
    "21": {"desc": "잘못된 요청변수", "category": "setup", "needs_apply_url": False},
    "30": {"desc": "조회결과 없음", "category": "data", "needs_apply_url": False},
    "31": {"desc": "조회결과 초과", "category": "data", "needs_apply_url": False},
    "40": {"desc": "호출가능건수 제한", "category": "transient", "needs_apply_url": False},
    "41": {"desc": "호출가능 ROW수 제한", "category": "transient", "needs_apply_url": False},
    "42": {"desc": "사용자별 이용 제한", "category": "setup", "needs_apply_url": True},
    "50": {"desc": "서버오류", "category": "transient", "needs_apply_url": False},
}

# 수록주기 코드
PERIOD_CODES = {
    "year": "Y",
    "half": "H",
    "quarter": "Q",
    "month": "M",
    "day": "D",
}


def _classify_kosis_error(error_code: str) -> tuple[str, str]:
    """KOSIS API 오류 코드를 사용자 메시지와 카테고리로 분류.

    정본 에러 코드 표(_ERROR_CODE_HINTS)에서 한글 설명을 가져오고,
    인증키 관련(10/11/42)은 활용신청 URL을 자동 부착한다.

    Args:
        error_code: KOSIS API err 코드.

    Returns:
        (사용자 메시지, 카테고리) 튜플.
        카테고리: "setup" | "transient" | "data" | "general"
    """
    hint = _ERROR_CODE_HINTS.get(error_code)
    if hint is None:
        return (
            f"KOSIS API 오류 (오류 코드: {error_code}) — 요청 파라미터 또는 서버 상태를 확인하세요.",
            "general",
        )

    if error_code in ("10", "11", "42"):
        return (
            f"KOSIS_API_KEY 확인 필요 (오류 코드: {error_code}, {hint['desc']}){_KOSIS_SETUP_GUIDE}",
            hint["category"],
        )
    if error_code in ("40", "41"):
        return (
            f"{hint['desc']} (오류 코드: {error_code}) — 호출 빈도를 줄이거나 KOSIS 관리자에게 문의하세요.",
            hint["category"],
        )
    if error_code == "50":
        return (
            f"{hint['desc']} (오류 코드: {error_code}) — 잠시 후 재시도하세요.",
            hint["category"],
        )
    if error_code in ("30", "31"):
        return (
            f"조회 결과 이슈 (오류 코드: {error_code}, {hint['desc']})",
            hint["category"],
        )
    # 20, 21, 기타: setup
    return (
        f"KOSIS API 오류 (오류 코드: {error_code}, {hint['desc']}) — 요청 파라미터를 확인하세요.",
        hint["category"],
    )


class KOSISAPIError(Exception):
    """KOSIS API 호출 오류."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


def _request(url: str, params: dict[str, str]) -> list[dict[str, Any]] | dict[str, Any]:
    """KOSIS API 호출.

    Args:
        url: 엔드포인트 URL.
        params: 쿼리 파라미터.

    Returns:
        파싱된 JSON 응답 (리스트 또는 딕셔너리).

    Raises:
        KOSISAPIError: 네트워크 오류, 파싱 실패, API 오류.
    """
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    full_url = f"{url}?{query}"

    try:
        with urllib.request.urlopen(full_url, timeout=_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        # @MX:NOTE: HTTP 403은 게이트웨이 단계 권한 거부 — 활용신청 안내 부착.
        if exc.code == 403:
            raise KOSISAPIError(
                f"권한 거부 (HTTP 403) — 활용신청이 필요할 수 있습니다."
                f"{_KOSIS_SETUP_GUIDE}",
                error_code="HTTP_403",
            ) from exc
        raise KOSISAPIError(f"네트워크 오류: {exc}") from exc
    except urllib.error.URLError as exc:
        raise KOSISAPIError(f"네트워크 오류: {exc}") from exc

    text = raw.decode("utf-8")

    # KOSIS 에러 응답은 비표준 JSON (키에 따옴표 없음):
    #   {err:"10",errMsg:"인증KEY값이 누락되었습니다."}
    # 표준 JSON으로 변환 후 파싱
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = _fix_unquoted_json(text)

    # 에러 응답 확인 — 정본 한글 hint + 활용신청 URL 자동 부착
    if isinstance(data, dict) and "err" in data:
        err_code = str(data.get("err", ""))
        err_msg = data.get("errMsg", "알 수 없는 오류")
        hint_msg, _category = _classify_kosis_error(err_code)
        raise KOSISAPIError(
            f"KOSIS API 오류 ({err_code}): {err_msg} | {hint_msg}",
            error_code=err_code,
        )

    return data


def _fix_unquoted_json(text: str) -> dict[str, Any] | list[dict[str, Any]]:
    """KOSIS 비표준 JSON을 파싱.

    KOSIS 응답은 키에 따옴표가 없는 JavaScript 객체 표기법:
        [{ORG_ID:"101",TBL_NM:"인구(시도)"}]
    값 내부에 콜론이 포함될 수 있어 단순 regex 치환은 불안전.
    문자열 밖의 키만 정확히 따옴표로 감싸는 상태 머신 방식으로 변환.

    Args:
        text: 비표준 JSON 문자열.

    Returns:
        파싱된 딕셔너리 또는 리스트.

    Raises:
        KOSISAPIError: 변환 후에도 파싱 실패.
    """
    result: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # 문자열 리터럴: 그대로 복사
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            result.append(text[i:j])
            i = j
            continue

        # { 또는 , 뒤의 키 (따옴표 없는 식별자):  key: → "key":
        if ch in '{,' :
            result.append(ch)
            i += 1
            # 공백 건너뛰기
            while i < n and text[i] in ' \t\n\r':
                result.append(text[i])
                i += 1
            # 따옴표 없는 키 탐지: [A-Za-z_][A-Za-z0-9_]* 뒤에 : 이 오는 패턴
            if i < n and text[i] != '"' and text[i] != '{' and text[i] != '[':
                key_start = i
                while i < n and (text[i].isalnum() or text[i] == '_'):
                    i += 1
                if i < n and text[i] == ':':
                    # 키에 따옴표 추가
                    result.append('"')
                    result.append(text[key_start:i])
                    result.append('"')
                else:
                    result.append(text[key_start:i])
            continue

        result.append(ch)
        i += 1

    fixed = "".join(result)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as exc:
        raise KOSISAPIError(f"JSON 파싱 실패: {exc}") from exc


# @MX:ANCHOR: [AUTO] KOSIS 통합검색의 핵심 함수.
# @MX:REASON: fan_in >= 3 (collect_stats의 search/data 서브커맨드); 통계표 탐색 진입점.
def search_statistics(
    api_key: str,
    keyword: str,
    start_count: int = 1,
    result_count: int = 10,
) -> list[dict[str, Any]]:
    """키워드로 통계표를 검색.

    Args:
        api_key: KOSIS 인증키.
        keyword: 검색 키워드 (예: "인구", "GDP", "시장 규모").
        start_count: 페이지 번호 (기본 1).
        result_count: 페이지당 결과 수 (기본 10).

    Returns:
        통계표 목록. 각 항목:
        {ORG_ID, ORG_NM, TBL_ID, TBL_NM, STAT_ID, STAT_NM, ...}
    """
    params = {
        "method": "getList",
        "apiKey": api_key,
        "searchNm": keyword,
        "sort": "RANK",
        "startCount": str(start_count),
        "resultCount": str(result_count),
        "format": "json",
    }

    data = _request(_SEARCH_URL, params)
    if isinstance(data, list):
        return data
    return []


def get_statistics_data(
    api_key: str,
    org_id: str,
    tbl_id: str,
    itm_id: str = "ALL",
    obj_l1: str = "ALL",
    obj_l2: str = "",
    prd_se: str = "Y",
    start_prd_de: str = "",
    end_prd_de: str = "",
    new_est_prd_cnt: int | None = None,
) -> list[dict[str, Any]]:
    """통계자료 조회 (파라미터 방식).

    Args:
        api_key: KOSIS 인증키.
        org_id: 기관 코드 (예: "101" = 통계청).
        tbl_id: 통계표 ID (예: "DT_1B04005N").
        itm_id: 항목 ID ("ALL" 또는 "T2+T3" 등).
        obj_l1: 1차 분류값 ("ALL" 또는 특정 코드).
        obj_l2: 2차 분류값.
        prd_se: 수록주기 ("Y"=연, "M"=월, "Q"=분기).
        start_prd_de: 시작 시점 (예: "2020").
        end_prd_de: 종료 시점 (예: "2024").
        new_est_prd_cnt: 최근 N개 시점 (start/end 대신 사용).

    Returns:
        통계 데이터 목록. 각 항목:
        {TBL_NM, C1, C1_NM, ITM_ID, ITM_NM, UNIT_NM, PRD_DE, DT, ...}
    """
    params: dict[str, str] = {
        "method": "getList",
        "apiKey": api_key,
        "orgId": org_id,
        "tblId": tbl_id,
        "itmId": itm_id,
        "objL1": obj_l1,
        "prdSe": prd_se,
        "format": "json",
        "jsonVD": "Y",
    }

    # objL2~L8: 값이 있을 때만 포함 (빈 문자열 전송 시 KOSIS가 거부)
    if obj_l2:
        params["objL2"] = obj_l2

    if new_est_prd_cnt is not None:
        params["newEstPrdCnt"] = str(new_est_prd_cnt)
    else:
        if start_prd_de:
            params["startPrdDe"] = start_prd_de
        if end_prd_de:
            params["endPrdDe"] = end_prd_de

    data = _request(_DATA_URL, params)
    if isinstance(data, list):
        return data
    return []


def parse_value(dt_str: str) -> float | None:
    """KOSIS DT 필드 값을 숫자로 변환.

    KOSIS는 모든 값을 문자열로 반환하므로 변환이 필요.

    Args:
        dt_str: DT 필드 값 (예: "51740000", "-", "").

    Returns:
        숫자 값, 또는 None (데이터 없음).
    """
    if not dt_str or dt_str.strip() in ("-", "…", "x", "X", ""):
        return None
    try:
        return float(dt_str.replace(",", ""))
    except ValueError:
        return None


def summarize_data(
    data: list[dict[str, Any]],
    value_field: str = "DT",
) -> list[dict[str, Any]]:
    """통계 데이터를 제안서용 요약 형태로 정리.

    Args:
        data: get_statistics_data()의 반환값.
        value_field: 값 필드명 (기본: "DT").

    Returns:
        정리된 데이터:
        [{period, item_name, category, value, unit}, ...]
    """
    results: list[dict[str, Any]] = []

    for row in data:
        value = parse_value(row.get(value_field, ""))
        if value is None:
            continue

        results.append({
            "period": row.get("PRD_DE", ""),
            "item_name": row.get("ITM_NM", ""),
            "item_name_eng": row.get("ITM_NM_ENG", ""),
            "category": row.get("C1_NM", ""),
            "category_eng": row.get("C1_NM_ENG", ""),
            "value": value,
            "unit": row.get("UNIT_NM", ""),
            "table_name": row.get("TBL_NM", ""),
            "org_id": row.get("ORG_ID", ""),
            "tbl_id": row.get("TBL_ID", ""),
        })

    return results
