"""한국은행 ECOS OpenAPI 클라이언트.

제안서/사업계획서에 필요한 거시경제 지표 수집:
    - 100대 주요 경제지표 (KeyStatisticList)
    - 통계 데이터 조회 (StatisticSearch)
    - 통계표 목록 (StatisticTableList)
    - 세부항목 목록 (StatisticItemList)

엔드포인트: https://ecos.bok.or.kr/api/
인증: PATH 기반 (URL 경로에 인증키 포함)
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://ecos.bok.or.kr/api"
_TIMEOUT = 15

# 주기 코드
PERIOD_CODES = {
    "year": "A",
    "semi": "S",
    "quarter": "Q",
    "month": "M",
    "day": "D",
}

# 제안서에서 자주 참조하는 주요 통계표
KEY_STAT_CODES = {
    "cpi": ("021Y125", "소비자물가지수(2020=100)"),
    "gdp": ("111Y017", "실질 GDP 성장률"),
    "exchange": ("731Y003", "환율"),
    "interest": ("028Y001", "기준금리/콜금리"),
    "national_income": ("200Y001", "국민소득 통계"),
}


class ECOSAPIError(Exception):
    """ECOS API 호출 오류."""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


def _build_url(*segments: str) -> str:
    """PATH 기반 URL 생성.

    ECOS API는 쿼리 파라미터가 아닌 경로(path) 기반으로 파라미터를 전달.

    Args:
        segments: URL 경로 세그먼트.

    Returns:
        완성된 URL (trailing slash 포함).
    """
    return _BASE_URL + "/" + "/".join(str(s) for s in segments) + "/"


def _request(url: str) -> dict[str, Any]:
    """ECOS API 호출.

    Args:
        url: 전체 URL.

    Returns:
        파싱된 JSON 응답.

    Raises:
        ECOSAPIError: 네트워크 오류, 파싱 실패, API 오류.
    """
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        raise ECOSAPIError(f"네트워크 오류: {exc}") from exc

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ECOSAPIError(f"JSON 파싱 실패: {exc}") from exc

    # 에러 응답 확인
    if "RESULT" in data:
        code = data["RESULT"].get("CODE", "")
        msg = data["RESULT"].get("MESSAGE", "알 수 없는 오류")

        # 정보 100: 인증키 유효하지 않음
        if code == "INFO-100":
            raise ECOSAPIError(
                "인증키가 유효하지 않습니다. ECOS_API_KEY를 확인하세요.",
                error_code=code,
            )
        # INFO-200: 데이터 없음 (에러가 아닌 정상 응답)
        if code == "INFO-200":
            return {"_empty": True, "_message": msg}

        # ERROR 계열
        if code.startswith("ERROR"):
            # 주요 에러에 사용자 친화적 안내 추가
            hints = {
                "ERROR-101": " → 주기와 날짜 형식이 맞는지 확인하세요 (A:2024, Q:2024Q1, M:202401, D:20240101).",
                "ERROR-400": " → 검색 범위를 줄여서 다시 시도하세요.",
                "ERROR-602": " → 과도한 호출로 제한되었습니다. 잠시 후 재시도하세요.",
            }
            hint = hints.get(code, "")
            raise ECOSAPIError(f"ECOS API 오류 ({code}): {msg}{hint}", error_code=code)

    return data


# @MX:ANCHOR: [AUTO] ECOS 100대 주요 경제지표 조회 함수.
# @MX:REASON: fan_in >= 3 (collect_econ의 key/search 서브커맨드); 핵심 경제지표 진입점.
def get_key_statistics(
    api_key: str,
    start: int = 1,
    end: int = 200,
) -> list[dict[str, Any]]:
    """100대 주요 경제지표 조회.

    한국은행이 선정한 핵심 경제지표를 한번에 조회. 제안서에서 경제 환경 개요에 유용.

    Args:
        api_key: ECOS 인증키.
        start: 시작 건수 (기본 1).
        end: 종료 건수 (기본 200).

    Returns:
        주요 지표 목록. 각 항목:
        {CLASS_NAME, KEYSTAT_NAME, DATA_VALUE, CYCLE, UNIT_NAME}
    """
    url = _build_url("KeyStatisticList", api_key, "json", "kr", start, end)
    data = _request(url)

    if data.get("_empty"):
        return []

    return data.get("KeyStatisticList", {}).get("row", [])


def search_statistics(
    api_key: str,
    stat_code: str,
    period: str,
    start_date: str,
    end_date: str,
    item_code1: str = "",
    item_code2: str = "",
    item_code3: str = "",
    item_code4: str = "",
    start: int = 1,
    end: int = 1000,
) -> list[dict[str, Any]]:
    """통계 데이터 조회 (StatisticSearch).

    Args:
        api_key: ECOS 인증키.
        stat_code: 통계표코드 (예: "021Y125").
        period: 주기 ("A", "Q", "M", "D").
        start_date: 시작일 (주기에 맞는 형식).
        end_date: 종료일.
        item_code1~4: 항목코드 (선택).
        start: 시작 건수.
        end: 종료 건수 (최대 10000).

    Returns:
        통계 데이터 목록. 각 항목:
        {STAT_CODE, STAT_NAME, ITEM_CODE1, ITEM_NAME1, UNIT_NAME, TIME, DATA_VALUE}
    """
    # PATH 세그먼트 구성
    segments = [
        "StatisticSearch", api_key, "json", "kr",
        str(start), str(end),
        stat_code, period, start_date, end_date,
    ]

    # 항목코드 추가 (빈 문자열이면 생략하되, 중간 코드가 있으면 이전 것도 포함)
    codes = [item_code1, item_code2, item_code3, item_code4]
    # 마지막 비어있지 않은 코드까지만 포함
    last_idx = -1
    for i, code in enumerate(codes):
        if code:
            last_idx = i
    if last_idx >= 0:
        for i in range(last_idx + 1):
            segments.append(codes[i] or "")

    url = _build_url(*segments)
    data = _request(url)

    if data.get("_empty"):
        return []

    return data.get("StatisticSearch", {}).get("row", [])


def get_table_list(
    api_key: str,
    start: int = 1,
    end: int = 1000,
) -> list[dict[str, Any]]:
    """통계표 목록 조회.

    Args:
        api_key: ECOS 인증키.
        start: 시작 건수.
        end: 종료 건수.

    Returns:
        통계표 목록. 각 항목:
        {STAT_CODE, STAT_NAME, CYCLE, ORG_NAME}
    """
    url = _build_url("StatisticTableList", api_key, "json", "kr", start, end)
    data = _request(url)

    if data.get("_empty"):
        return []

    return data.get("StatisticTableList", {}).get("row", [])


def get_item_list(
    api_key: str,
    stat_code: str,
    start: int = 1,
    end: int = 500,
) -> list[dict[str, Any]]:
    """통계표 세부항목 목록 조회.

    Args:
        api_key: ECOS 인증키.
        stat_code: 통계표코드.
        start: 시작 건수.
        end: 종료 건수.

    Returns:
        항목 목록. 각 항목:
        {STAT_CODE, STAT_NAME, GRP_CODE, GRP_NAME, ITEM_CODE, ITEM_NAME, CYCLE}
    """
    url = _build_url("StatisticItemList", api_key, "json", "kr", start, end, stat_code)
    data = _request(url)

    if data.get("_empty"):
        return []

    return data.get("StatisticItemList", {}).get("row", [])


def search_word(
    api_key: str,
    word: str,
    start: int = 1,
    end: int = 20,
) -> list[dict[str, Any]]:
    """통계용어사전 검색.

    경제/통계 용어의 공식 정의를 조회. 제안서에서 용어 설명 인용에 유용.

    Args:
        api_key: ECOS 인증키.
        word: 검색할 용어 (예: "소비자동향지수", "GDP디플레이터").
        start: 시작 건수.
        end: 종료 건수.

    Returns:
        용어 목록. 각 항목: {WORD, CONTENT}
    """
    url = _build_url("StatisticWord", api_key, "json", "kr", start, end, word)
    data = _request(url)

    if data.get("_empty"):
        return []

    return data.get("StatisticWord", {}).get("row", [])


def parse_value(val_str: str) -> float | None:
    """DATA_VALUE 문자열을 숫자로 변환.

    Args:
        val_str: DATA_VALUE 필드 값.

    Returns:
        숫자 값, 또는 None.
    """
    if not val_str or val_str.strip() in ("-", "", "…", "x", "X", "*"):
        return None
    try:
        return float(val_str.replace(",", ""))
    except ValueError:
        return None


def summarize_data(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """통계 데이터를 제안서용 요약 형태로 정리.

    Args:
        rows: search_statistics()의 반환값.

    Returns:
        정리된 데이터: [{time, stat_name, item_name, value, unit}, ...]
    """
    results: list[dict[str, Any]] = []

    for row in rows:
        value = parse_value(row.get("DATA_VALUE", ""))
        if value is None:
            continue

        results.append({
            "time": row.get("TIME", ""),
            "stat_code": row.get("STAT_CODE", ""),
            "stat_name": row.get("STAT_NAME", ""),
            "item_name": row.get("ITEM_NAME1", ""),
            "item_name2": row.get("ITEM_NAME2", ""),
            "value": value,
            "unit": row.get("UNIT_NAME", ""),
        })

    return results
