"""금융위원회 주식시세정보 API 클라이언트 (data.go.kr 15094808).

엔드포인트: https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo
인증: serviceKey (공공데이터포털 발급)

정본: itda-gov/skills/stock-quote/scripts/stock_quote_api.py
스킬 자기완결 정책상 복제. 변경 시 정본과 동기화 필요.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

# API 엔드포인트
_API_ENDPOINT = (
    "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService"
    "/getStockPriceInfo"
)

# 활용신청 안내 URL (HTTP 403 시 안내)
_APPLY_URL = "https://www.data.go.kr/data/15094808/openapi.do"

# 요청 타임아웃(초)
_REQUEST_TIMEOUT = 15


class StockAPIError(Exception):
    """주식시세정보 API 호출 중 발생하는 오류."""


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
    # serviceKey는 별도로 인코딩 (safe='' 으로 모든 특수문자 인코딩, g2b 정본 패턴)
    encoded_key = urllib.parse.quote(api_key, safe="")

    # 나머지 파라미터 인코딩
    other_params = urllib.parse.urlencode(params)

    if other_params:
        return f"{_API_ENDPOINT}?serviceKey={encoded_key}&{other_params}"
    return f"{_API_ENDPOINT}?serviceKey={encoded_key}"


def _normalize_items(items: list | dict | None) -> list:
    """items 필드 정규화 — dict-vs-list 응답 통일.

    API가 단건이면 dict, 복수이면 list로 반환하는 경우를 처리.

    Args:
        items: 응답 body.items.item 값.

    Returns:
        항상 list 형태로 반환.
    """
    if items is None:
        return []
    if isinstance(items, list):
        return items
    if isinstance(items, dict):
        return [items]
    return []


# @MX:ANCHOR: [AUTO] 주식시세정보 API 핵심 호출 함수.
# @MX:REASON: fan_in >= 3 (collect_stock_quote 서브커맨드 3개, stock_portfolio); API 계약의 진입점.
def get_stock_price(
    api_key: str,
    *,
    srtn_cd: str | None = None,
    itms_nm: str | None = None,
    like_itms_nm: str | None = None,
    like_srtn_cd: str | None = None,
    bas_dt: str | None = None,
    begin_bas_dt: str | None = None,
    end_bas_dt: str | None = None,
    page: int = 1,
    rows: int = 100,
) -> dict:
    """주식시세정보 getStockPriceInfo 호출.

    최소 필터 파라미터 중 하나 이상을 지정해야 한다.
    (srtn_cd, itms_nm, like_itms_nm, like_srtn_cd, bas_dt, begin_bas_dt, end_bas_dt)

    Args:
        api_key: 공공데이터포털 serviceKey.
        srtn_cd: 단축코드 (정확 일치).
        itms_nm: 종목명 (정확 일치).
        like_itms_nm: 종목명 부분 일치.
        like_srtn_cd: 단축코드 부분 일치.
        bas_dt: 기준일자 일치 (YYYYMMDD).
        begin_bas_dt: 기준일자 범위 시작 (YYYYMMDD).
        end_bas_dt: 기준일자 범위 끝 (YYYYMMDD, 미포함).
        page: 페이지 번호 (기본 1).
        rows: 페이지당 결과 수 (기본 100).

    Returns:
        다음 키를 포함하는 딕셔너리:
        - status: "ok"
        - items: 시세 item 목록
        - totalCount: 전체 결과 수
        - pageNo: 현재 페이지 번호
        - numOfRows: 페이지당 결과 수

    Raises:
        StockAPIError: HTTP 403, 네트워크 오류, API 오류, JSON 파싱 실패 등.
    """
    params: dict[str, str] = {
        "numOfRows": str(rows),
        "pageNo": str(page),
        "resultType": "json",
    }

    # 필터 파라미터 — 제공된 것만 추가
    if srtn_cd is not None:
        params["srtnCd"] = srtn_cd  # 정확 일치 (docstring과 일치하도록 수정)
    if itms_nm is not None:
        params["itmsNm"] = itms_nm
    if like_itms_nm is not None:
        params["likeItmsNm"] = like_itms_nm
    if like_srtn_cd is not None:
        params["likeSrtnCd"] = like_srtn_cd
    if bas_dt is not None:
        params["basDt"] = bas_dt
    if begin_bas_dt is not None:
        params["beginBasDt"] = begin_bas_dt
    if end_bas_dt is not None:
        params["endBasDt"] = end_bas_dt

    url = build_url(api_key, params)

    try:
        with urllib.request.urlopen(url, timeout=_REQUEST_TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise StockAPIError(
                f"권한 거부 (HTTP 403) — 활용신청이 필요합니다.\n"
                f"  data.go.kr 계정으로 15094808 데이터셋 활용신청(자동승인) 필요:\n"
                f"  {_APPLY_URL}"
            ) from exc
        raise StockAPIError(f"네트워크 오류: {exc}") from exc
    except urllib.error.URLError as exc:
        raise StockAPIError(f"네트워크 오류: {exc}") from exc

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise StockAPIError(f"JSON 파싱 실패: {exc}") from exc

    # 응답 구조 검증
    try:
        header = data["response"]["header"]
        body = data["response"]["body"]
    except (KeyError, TypeError) as exc:
        raise StockAPIError(f"예상치 못한 응답 구조: {exc}") from exc

    result_code = header.get("resultCode", "")
    if result_code != "00":
        result_msg = header.get("resultMsg", "")
        raise StockAPIError(
            f"API 오류 (resultCode={result_code}): {result_msg}"
        )

    # items 정규화 (단건=dict, 복수=list 처리)
    raw_items = (body.get("items") or {}).get("item")
    items = _normalize_items(raw_items)

    return {
        "status": "ok",
        "items": items,
        "totalCount": body.get("totalCount", 0),
        "pageNo": body.get("pageNo", page),
        "numOfRows": body.get("numOfRows", rows),
    }


def _is_numeric_code(ticker: str) -> bool:
    """6자리 숫자 종목코드인지 판단."""
    return ticker.isdigit() and len(ticker) == 6


def _dedupe_by_latest_bas_dt(items: list[dict]) -> list[dict]:
    """srtnCd 기준으로 최신 basDt만 남긴다.

    같은 단축코드에 복수 기준일 데이터가 올 때 현재가 조회에서 최신 기준만 사용.

    Args:
        items: 정규화된 item 목록.

    Returns:
        srtnCd 기준으로 dedupe된 목록 (최신 basDt 우선).
    """
    best: dict[str, dict] = {}
    for item in items:
        code = item.get("srtnCd", "")
        if not code:
            continue
        existing = best.get(code)
        if existing is None or item.get("basDt", "") > existing.get("basDt", ""):
            best[code] = item
    return list(best.values())


def resolve_ticker(api_key: str, ticker: str) -> dict:
    """종목 식별자를 단일 종목으로 해석.

    해석 전략:
    1. 6자리 숫자 → likeSrtnCd 조회
    2. 텍스트 → likeItmsNm 조회 후:
       a. 정확히 itmsNm == ticker인 결과가 있으면 → resolved
       b. 복수 결과이고 정확 일치 없음 → ambiguous (candidates 포함)
    3. 결과 0건 → error:not_found (추측 금지)
    4. 복수 basDt → 최신 basDt로 dedupe

    Args:
        api_key: 공공데이터포털 serviceKey.
        ticker: 종목코드(6자리 숫자) 또는 종목명.

    Returns:
        다음 중 하나:
        - {"status": "resolved", "srtnCd": ..., "itmsNm": ..., "basDt": ..., ...}
        - {"status": "ambiguous", "query": ticker, "candidates": [...]}
        - {"status": "error", "error_type": "not_found", "query": ticker}
    """
    if _is_numeric_code(ticker):
        # 숫자 코드 → likeSrtnCd
        resp = get_stock_price(api_key, like_srtn_cd=ticker, rows=10)
        items = _dedupe_by_latest_bas_dt(resp["items"])
    else:
        # 종목명 → likeItmsNm (부분 일치)
        resp = get_stock_price(api_key, like_itms_nm=ticker, rows=100)
        items = _dedupe_by_latest_bas_dt(resp["items"])

    # 0건 → not_found
    if not items:
        return {"status": "error", "error_type": "not_found", "query": ticker}

    # 정확 일치 우선 (itmsNm == ticker)
    exact = [item for item in items if item.get("itmsNm", "") == ticker]
    if len(exact) == 1:
        return {"status": "resolved", **exact[0]}
    if len(exact) > 1:
        # 정확 일치 복수 — ambiguous
        return {
            "status": "ambiguous",
            "query": ticker,
            "candidates": exact,
        }

    # 1건이면 resolved
    if len(items) == 1:
        return {"status": "resolved", **items[0]}

    # 복수 결과 → ambiguous
    return {
        "status": "ambiguous",
        "query": ticker,
        "candidates": items,
    }
