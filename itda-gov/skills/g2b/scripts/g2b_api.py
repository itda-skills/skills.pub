"""나라장터 공공데이터개방표준서비스 API 클라이언트.

공공데이터포털(https://www.data.go.kr) G2B 입찰공고 조회 API 래퍼.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

# API 엔드포인트
_API_ENDPOINT = (
    "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService"
    "/getDataSetOpnStdBidPblancInfo"
)

# 요청 타임아웃(초)
_REQUEST_TIMEOUT = 15


class G2BAPIError(Exception):
    """나라장터 API 호출 중 발생하는 오류."""


def format_date(date_str: str) -> str:
    """YYYY-MM-DD 형식 날짜를 YYYYMMDD로 변환.

    API에 전달하기 전 날짜 형식을 변환. begin_dt에는 0000, end_dt에는 2359를
    호출자가 직접 붙여서 사용.

    Args:
        date_str: YYYY-MM-DD 형식의 날짜 문자열.

    Returns:
        YYYYMMDD 형식의 날짜 문자열.

    Raises:
        ValueError: 날짜 형식이 올바르지 않거나 존재하지 않는 날짜인 경우.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            f"날짜 형식이 올바르지 않습니다: '{date_str}'. YYYY-MM-DD 형식으로 입력하세요."
        ) from exc
    return dt.strftime("%Y%m%d")


def validate_date_range(begin_dt: str, end_dt: str) -> None:
    """날짜 범위가 1개월을 초과하지 않는지 검증.

    Args:
        begin_dt: 시작일 (YYYYMMDD 형식).
        end_dt: 종료일 (YYYYMMDD 형식).

    Raises:
        G2BAPIError: 날짜 범위가 1개월을 초과하는 경우.
    """
    begin = datetime.strptime(begin_dt, "%Y%m%d")
    end = datetime.strptime(end_dt, "%Y%m%d")

    # 1개월 이내 여부 확인 (31일 기준으로 판단)
    delta = end - begin
    if delta.days > 31:
        raise G2BAPIError(
            f"날짜 범위가 1개월을 초과합니다 ({delta.days}일). "
            "최대 1개월 이내로 지정하세요."
        )


def build_url(api_key: str, params: dict) -> str:
    """API 요청 URL을 구성.

    serviceKey는 별도로 인코딩하여 이중 인코딩을 방지.
    다른 파라미터는 urllib.parse.urlencode로 인코딩.

    Args:
        api_key: 공공데이터포털 serviceKey (URL 디코딩 상태).
        params: serviceKey를 제외한 나머지 파라미터 딕셔너리.

    Returns:
        완성된 API 요청 URL 문자열.
    """
    # serviceKey는 별도로 인코딩 (safe='' 으로 모든 특수문자 인코딩)
    encoded_key = urllib.parse.quote(api_key, safe="")

    # 나머지 파라미터 인코딩
    other_params = urllib.parse.urlencode(params)

    if other_params:
        return f"{_API_ENDPOINT}?serviceKey={encoded_key}&{other_params}"
    return f"{_API_ENDPOINT}?serviceKey={encoded_key}"


# @MX:ANCHOR: [AUTO] G2B 입찰공고 조회의 핵심 API 호출 함수.
# @MX:REASON: fan_in >= 3 (collect_g2b 및 향후 확장); API 계약의 진입점.
def search_bids(
    api_key: str,
    begin_dt: str,
    end_dt: str,
    page: int = 1,
    rows: int = 10,
) -> dict:
    """나라장터 입찰공고를 조회.

    Args:
        api_key: 공공데이터포털 serviceKey.
        begin_dt: 조회 시작일 (YYYY-MM-DD 형식).
        end_dt: 조회 종료일 (YYYY-MM-DD 형식).
        page: 페이지 번호 (기본값 1).
        rows: 페이지당 결과 수 (기본값 10).

    Returns:
        다음 키를 포함하는 딕셔너리:
        - items: 입찰공고 목록
        - totalCount: 전체 결과 수
        - pageNo: 현재 페이지 번호
        - numOfRows: 페이지당 결과 수

    Raises:
        G2BAPIError: 날짜 범위 초과, 네트워크 오류, API 오류, JSON 파싱 실패 등.
        ValueError: 날짜 형식이 올바르지 않은 경우.
    """
    # rows 상한 적용 (API가 1000 이상이면 기본값 10으로 리셋)
    rows = max(1, min(999, rows))

    # 날짜 형식 변환 (YYYY-MM-DD → YYYYMMDD)
    begin_yyyymmdd = format_date(begin_dt)
    end_yyyymmdd = format_date(end_dt)

    # 날짜 범위 검증 (1개월 이내)
    validate_date_range(begin_yyyymmdd, end_yyyymmdd)

    # API 파라미터 구성 (시간 붙이기: begin=0000, end=2359)
    params = {
        "type": "json",
        "pageNo": str(page),
        "numOfRows": str(rows),
        "bidNtceBgnDt": begin_yyyymmdd + "0000",
        "bidNtceEndDt": end_yyyymmdd + "2359",
    }

    url = build_url(api_key, params)

    try:
        with urllib.request.urlopen(url, timeout=_REQUEST_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        raise G2BAPIError(f"네트워크 오류: {exc}") from exc

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise G2BAPIError(f"JSON 파싱 실패: {exc}") from exc

    # 응답 구조 검증
    try:
        header = data["response"]["header"]
        body = data["response"]["body"]
    except (KeyError, TypeError) as exc:
        raise G2BAPIError(f"예상치 못한 응답 구조: {exc}") from exc

    result_code = header.get("resultCode", "")
    if result_code != "00":
        result_msg = header.get("resultMsg", "")
        raise G2BAPIError(
            f"API 오류 (resultCode={result_code}): {result_msg}"
        )

    items = body.get("items") or []
    return {
        "items": items,
        "totalCount": body.get("totalCount", 0),
        "pageNo": body.get("pageNo", page),
        "numOfRows": body.get("numOfRows", rows),
    }
