#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 부동산(new.land.naver.com) SPA 어댑터.

SPEC-WEB-NAVERLAND-001 REQ-NL-001~004 (어댑터 기본),
REQ-NL-010~013 (좌표 파싱·entry 자동화),
REQ-NL-022 (capture_pattern), REQ-NL-032 (robots.txt),
REQ-NL-040~044 (extract 정규화), REQ-NL-050~052 (Markdown 출력),
REQ-NL-060~062 (에러/회귀), REQ-NL-070~072 (PII 처리).

Python 3.10 문법 기준.
"""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.robotparser
from datetime import datetime, timezone
from typing import Any

from spa_adapters.base import Adapter, PageDef, AdapterEntryError, run_entry_steps

# ---------------------------------------------------------------------------
# 모듈 레벨 robots 캐시 — URL 별로 RobotFileParser 인스턴스를 캐싱한다.
# 동일 도메인에 대해 반복 fetch를 방지한다 (REQ-NL-032).
# @MX:NOTE: [AUTO] _robots_cache — robots.txt 요청 1회 제한을 위한 모듈 레벨 캐시.
#           테스트 격리 시 _robots_cache.clear()로 초기화 필요.
# ---------------------------------------------------------------------------
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

# 네이버 부동산 캡처 대상 API 패턴 (plan.md 확정값)
# @MX:NOTE: [AUTO] _CAPTURE_PATTERN — plan.md M3에서 확정된 라이브 캡처 정규식.
#           변경 시 capture 테스트 fixture와 반드시 동기화할 것.
_CAPTURE_PATTERN = (
    r"^https://new\.land\.naver\.com/api/"
    r"(complexes|articles|cortars|regions|developmentplan)"
)

# 네이버 부동산 robots.txt URL
_ROBOTS_URL = "https://new.land.naver.com/robots.txt"

# 한국 영토 범위 (경고 판단 기준)
_KOREA_LAT_MIN = 33.0
_KOREA_LAT_MAX = 38.7
_KOREA_LNG_MIN = 124.0
_KOREA_LNG_MAX = 132.0


# ---------------------------------------------------------------------------
# 공용 함수
# ---------------------------------------------------------------------------

# @MX:ANCHOR: [AUTO] parse_ms — ms 파라미터 파싱의 단일 진입점
# @MX:REASON: [AUTO] SPEC-WEB-NAVERLAND-001 REQ-NL-010; entry(), 테스트, 외부 호출 등
#             여러 경로에서 참조 예정 (fan_in >= 3). 형식 변경 시 모든 호출처 영향.
def parse_ms(value: str) -> tuple[float, float, int]:
    """ms 파라미터 문자열을 (lat, lng, zoom) 튜플로 파싱한다.

    인자:
        value: "lat,lng,zoom" 형식의 문자열 (예: "37.5665,126.9780,15")

    반환:
        (lat: float, lng: float, zoom: int) 튜플

    예외:
        AdapterEntryError(stage="parse_ms"): 형식 오류 또는 변환 실패 시

    주의:
        한국 영토 범위(lat 33.0~38.7, lng 124.0~132.0) 밖이면 stderr에 경고를 출력하지만
        abort하지 않는다 (REQ-NL-011).
    """
    # 콤마 분리
    parts = value.split(",")
    if len(parts) != 3:
        raise AdapterEntryError(
            stage="parse_ms",
            message=f"ms 파라미터 형식 오류: 콤마 구분 3개 필요, 입력값: {value!r}",
        )

    # float/int 변환
    try:
        lat = float(parts[0])
        lng = float(parts[1])
        zoom = int(parts[2])
    except (ValueError, TypeError) as exc:
        raise AdapterEntryError(
            stage="parse_ms",
            message=f"ms 파라미터 형식 오류: 숫자 변환 실패, 입력값: {value!r}",
        ) from exc

    # 한국 영토 범위 경고 (abort 아님)
    if not (
        _KOREA_LAT_MIN <= lat <= _KOREA_LAT_MAX
        and _KOREA_LNG_MIN <= lng <= _KOREA_LNG_MAX
    ):
        print(
            f"경고: 좌표({lat}, {lng})가 한국 영토 범위 밖입니다. "
            f"(lat {_KOREA_LAT_MIN}~{_KOREA_LAT_MAX}, "
            f"lng {_KOREA_LNG_MIN}~{_KOREA_LNG_MAX})",
            file=sys.stderr,
        )

    return lat, lng, zoom


def _fetch_robots(robots_url: str) -> urllib.robotparser.RobotFileParser:
    """robots.txt를 fetch하여 파서를 반환한다 (모듈 레벨 캐시 사용).

    fetch 실패 시 보수적으로 abort — robots 허용 여부를 알 수 없으면 진입하지 않는다.

    인자:
        robots_url: robots.txt URL

    반환:
        RobotFileParser 인스턴스

    예외:
        AdapterEntryError(stage="robots_fetch_failed"): fetch 실패 시
    """
    if robots_url in _robots_cache:
        return _robots_cache[robots_url]

    rfp = urllib.robotparser.RobotFileParser()
    rfp.set_url(robots_url)
    try:
        rfp.read()
    except Exception as exc:
        raise AdapterEntryError(
            stage="robots_fetch_failed",
            message=f"robots.txt fetch 실패 ({robots_url}): {exc}",
        ) from exc

    _robots_cache[robots_url] = rfp
    return rfp


# ---------------------------------------------------------------------------
# 어댑터 클래스
# ---------------------------------------------------------------------------

class NaverLandAdapter(Adapter):
    """네이버 부동산(new.land.naver.com) SPA 어댑터.

    지원 페이지:
        - complexes: 지도 영역 진입 (ms 파라미터 필요)
        - complex_detail: 단지 상세 진입 (complex_no 파라미터 필요)

    REQ-NL-001~004, REQ-NL-012~013, REQ-NL-022, REQ-NL-032.
    """

    # REQ-NL-001: 도메인 패턴
    domain_pattern = r"^(www\.)?new\.land\.naver\.com$"

    # REQ-NL-002: 프레임워크 식별자
    framework = "custom"

    # REQ-NL-003~004: 페이지 정의
    # @MX:NOTE: [AUTO] pages — complexes(지도 영역)와 complex_detail(단지 상세) 두 진입점 정의.
    #           entry_url은 entry()에서 포맷팅된 후 PageDef를 재사용하지 않으므로
    #           템플릿 문자열로 관리한다.
    pages = {
        "complexes": PageDef(
            entry_url="https://new.land.naver.com/complexes?ms={ms}",
            capture_pattern=_CAPTURE_PATTERN,
        ),
        "complex_detail": PageDef(
            entry_url="https://new.land.naver.com/complexes/{complex_no}",
            capture_pattern=_CAPTURE_PATTERN,
        ),
    }

    def _build_target_url(self, page_key: str, kwargs: dict[str, Any]) -> str:
        """page_key와 kwargs로부터 진입 URL을 생성한다.

        인자:
            page_key: 검증 완료된 페이지 키
            kwargs: entry()로 전달된 키워드 인자

        반환:
            포맷팅된 진입 URL 문자열

        예외:
            AdapterEntryError(stage="missing_arg"): 필수 인자 누락
            AdapterEntryError(stage="parse_ms"): ms 형식 오류
        """
        if page_key == "complexes":
            # ms 파라미터 처리 (문자열 또는 lat/lng/zoom 분리 형식)
            if "ms" in kwargs:
                ms_str = kwargs["ms"]
            elif "lat" in kwargs and "lng" in kwargs and "zoom" in kwargs:
                ms_str = f"{kwargs['lat']},{kwargs['lng']},{kwargs['zoom']}"
            else:
                raise AdapterEntryError(
                    stage="missing_arg",
                    message=(
                        "complexes 페이지 진입에 ms 파라미터가 필요합니다. "
                        "ms='lat,lng,zoom' 또는 lat, lng, zoom을 각각 전달하세요."
                    ),
                )
            # parse_ms를 통해 형식 검증 (예외는 parse_ms에서 raise)
            parse_ms(ms_str)
            return self.pages["complexes"].entry_url.format(ms=ms_str)

        # complex_detail
        if "complex_no" not in kwargs:
            raise AdapterEntryError(
                stage="missing_arg",
                message="complex_detail 페이지 진입에 complex_no 파라미터가 필요합니다.",
            )
        return self.pages["complex_detail"].entry_url.format(
            complex_no=kwargs["complex_no"]
        )

    def entry(self, driver: Any, page_key: str = "complexes", **kwargs: Any) -> None:
        """지정된 페이지로 진입한다.

        인자:
            driver: BrowserDriver 인스턴스
            page_key: 진입할 페이지 키 ("complexes" 또는 "complex_detail")
            **kwargs:
                - complexes 페이지: ms (str, "lat,lng,zoom" 형식) 또는
                  lat (float) + lng (float) + zoom (int)
                - complex_detail 페이지: complex_no (str)

        예외:
            AdapterEntryError(stage="unknown_page"): 알 수 없는 page_key
            AdapterEntryError(stage="missing_arg"): 필수 인자 누락
            AdapterEntryError(stage="parse_ms"): ms 형식 오류
            AdapterEntryError(stage="robots_blocked"): robots.txt 차단
            AdapterEntryError(stage="robots_fetch_failed"): robots.txt fetch 실패
        """
        # page_key 검증
        if page_key not in self.pages:
            raise AdapterEntryError(
                stage="unknown_page",
                message=f"알 수 없는 page_key: {page_key!r}. 지원: {list(self.pages.keys())}",
            )

        # 진입 URL 생성
        target_url = self._build_target_url(page_key, kwargs)

        # robots.txt 검사 (REQ-NL-032)
        rfp = _fetch_robots(_ROBOTS_URL)
        if not rfp.can_fetch("*", target_url):
            raise AdapterEntryError(
                stage="robots_blocked",
                message=f"robots.txt에 의해 접근이 차단되었습니다: {target_url}",
            )

        # 진입 URL로 이동 — PageDef를 재사용하되 entry_url만 교체
        page_def = self.pages[page_key]
        page_copy = PageDef(
            entry_url=target_url,
            steps=page_def.steps,
            capture_pattern=page_def.capture_pattern,
            field_mapping=page_def.field_mapping,
            list_field=page_def.list_field,
        )
        run_entry_steps(driver, page_copy)

    # @MX:ANCHOR: [AUTO] extract — naver_land 정규화 파이프라인의 단일 진입점
    # @MX:REASON: [AUTO] extract_content.py, 단위 테스트, 외부 호출 등 fan_in >= 3.
    #             스키마 변경 시 이 함수가 영향 범위의 중심이 된다 (REQ-NL-040~044).
    def extract(self, driver: Any, captures: list[dict]) -> dict:
        """캡처 데이터에서 정규화된 콘텐츠를 추출한다.

        REQ-NL-040~044, REQ-NL-060~062, REQ-NL-070~072, REQ-NL-081.

        인자:
            driver: BrowserDriver 인스턴스 (사용하지 않음 — 미래 확장 예비)
            captures: JSONL에서 로드된 list[dict]. 각 항목:
                {"url": str, "status": int, "content_type": str,
                 "body": dict|list, "timestamp": str}

        반환:
            정규화된 dict (스키마는 plan.md 참조).
            에러 발생 시도 dict를 반환하고 meta.warnings에 기록한다 (REQ-NL-044).
        """
        warnings: list[str] = []
        endpoint_counts: dict[str, int] = {}

        # anti-bot 감지: 4xx/5xx 비율 계산 (REQ-NL-034, REQ-NL-060)
        anti_bot_detected = _detect_anti_bot(captures, warnings)

        # 좌표·query 정보 추출 (REQ-NL-040)
        query = _extract_query(captures, warnings)

        # 각 캡처 항목을 엔드포인트 유형으로 분류
        complexes: list[dict] = []
        complex_details: list[dict] = []
        listings: list[dict] = []
        regions: list[dict] = []
        development_plans: dict[str, list] = {}

        for cap in captures:
            url: str = cap.get("url", "")
            status: int = cap.get("status", 0)
            body: Any = cap.get("body")

            # 에러 응답 skip (body 무의미)
            if status >= 400:
                continue

            # 엔드포인트 분류
            ep_key = _endpoint_key(url)
            if ep_key:
                endpoint_counts[ep_key] = endpoint_counts.get(ep_key, 0) + 1

            if "/api/complexes/single-markers/" in url:
                # 지도 마커 목록 (list)
                if isinstance(body, list):
                    _parse_markers(body, complexes, warnings)

            elif "/api/complexes/overview/" in url:
                # 단지 상세 (dict)
                if isinstance(body, dict):
                    detail = _parse_complex_detail(body)
                    if detail:
                        complex_details.append(detail)

            elif "/api/articles/complex/" in url:
                # 매물 목록 (dict with articleList)
                complex_id = _extract_complex_id_from_url(url, r"/articles/complex/(\w+)")
                if isinstance(body, dict):
                    article_list = body.get("articleList", [])
                    if isinstance(article_list, list):
                        _parse_articles(article_list, complex_id, listings, warnings)

            elif "/api/cortars" in url:
                # 행정구역 (dict)
                if isinstance(body, dict):
                    region = _parse_region(body)
                    if region:
                        regions.append(region)

            elif "/api/developmentplan/" in url:
                # 개발계획 (list)
                plan_type = _extract_plan_type(url)
                if plan_type and isinstance(body, list):
                    if plan_type not in development_plans:
                        development_plans[plan_type] = []
                    development_plans[plan_type].extend(body)

        return {
            "query": query,
            "complexes": complexes,
            "complex_details": complex_details,
            "listings": listings,
            "regions": regions,
            "development_plans": development_plans,
            "meta": {
                "collected_at": datetime.now(tz=timezone.utc).isoformat(),
                "robots_check": {"allowed": True, "user_agent": "*"},
                "anti_bot_detected": anti_bot_detected,
                "warnings": warnings,
                "endpoint_counts": endpoint_counts,
            },
        }


# ---------------------------------------------------------------------------
# 모듈 레벨 헬퍼 함수 — extract() 내부에서 사용
# ---------------------------------------------------------------------------

# anti-bot 감지 임계값: 4xx/5xx 응답 비율이 이 값을 초과하면 감지
_ANTI_BOT_RATIO_THRESHOLD = 0.5

# 스키마 변경 감지: 핵심 필드 누락률이 이 값을 초과하면 경고
_SCHEMA_MISSING_THRESHOLD = 0.5

# 단지 마커 핵심 필드 (스키마 변경 감지 대상)
_COMPLEX_CRITICAL_FIELDS = ("complexName", "latitude", "longitude")

# 매물 핵심 필드 (스키마 변경 감지 대상)
_ARTICLE_CRITICAL_FIELDS = ("articleNo", "tradeTypeCode")


def _detect_anti_bot(captures: list[dict], warnings: list[str]) -> bool:
    """4xx/5xx 응답 비율로 anti-bot 감지를 수행한다 (REQ-NL-034, REQ-NL-060).

    인자:
        captures: 전체 캡처 목록
        warnings: 경고 메시지를 추가할 list (in-place 수정)

    반환:
        anti-bot 감지 여부 (bool)
    """
    if not captures:
        return False

    error_count = sum(1 for c in captures if c.get("status", 0) >= 400)
    total = len(captures)
    ratio = error_count / total

    if ratio > _ANTI_BOT_RATIO_THRESHOLD:
        msg = (
            f"anti-bot 차단 의심: 응답 {total}건 중 {error_count}건이 4xx/5xx ({ratio:.0%}). "
            "--stealth 옵션을 사용하거나 잠시 후 재시도하세요."
        )
        warnings.append(msg)
        return True
    return False


def _extract_query(captures: list[dict], warnings: list[str]) -> dict:
    """캡처 URL에서 좌표·zoom 정보를 추출한다 (REQ-NL-040, REQ-NL-062).

    cortars URL의 centerLat/centerLon 파라미터 또는
    single-markers URL의 bbox 파라미터를 사용한다.

    인자:
        captures: 전체 캡처 목록
        warnings: 경고 메시지를 추가할 list

    반환:
        {"lat": float|None, "lng": float|None, "zoom": int|None, "url": str|None}
    """
    query: dict[str, Any] = {"lat": None, "lng": None, "zoom": None, "url": None}

    for cap in captures:
        url = cap.get("url", "")
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)

        # cortars URL: centerLat, centerLon, zoom
        if "/api/cortars" in url:
            try:
                lat_vals = qs.get("centerLat") or qs.get("centerlat")
                lng_vals = qs.get("centerLon") or qs.get("centerlon")
                zoom_vals = qs.get("zoom")
                if lat_vals and lng_vals:
                    lat = float(lat_vals[0])
                    lng = float(lng_vals[0])
                    zoom = int(zoom_vals[0]) if zoom_vals else None
                    query.update({"lat": lat, "lng": lng, "zoom": zoom, "url": url})

                    # 한국 범위 체크 (REQ-NL-062)
                    if not (
                        _KOREA_LAT_MIN <= lat <= _KOREA_LAT_MAX
                        and _KOREA_LNG_MIN <= lng <= _KOREA_LNG_MAX
                    ):
                        warnings.append(
                            f"좌표({lat}, {lng})가 한국 영토 범위 밖입니다. "
                            f"(lat {_KOREA_LAT_MIN}~{_KOREA_LAT_MAX}, "
                            f"lng {_KOREA_LNG_MIN}~{_KOREA_LNG_MAX})"
                        )
                    break
            except (ValueError, TypeError, IndexError):
                pass

    return query


def _endpoint_key(url: str) -> str | None:
    """URL에서 엔드포인트 분류 키를 추출한다 (meta.endpoint_counts용).

    인자:
        url: 캡처 URL

    반환:
        엔드포인트 키 문자열 또는 None
    """
    patterns = [
        (r"/api/complexes/single-markers/2\.0", "complexes/single-markers/2.0"),
        (r"/api/complexes/overview/", "complexes/overview"),
        (r"/api/articles/complex/", "articles/complex"),
        (r"/api/cortars", "cortars"),
        (r"/api/developmentplan/jigu/", "developmentplan/jigu"),
        (r"/api/developmentplan/rail/", "developmentplan/rail"),
        (r"/api/developmentplan/road/", "developmentplan/road"),
        (r"/api/developmentplan/station/", "developmentplan/station"),
        (r"/api/regions/", "regions"),
    ]
    for pattern, key in patterns:
        if re.search(pattern, url):
            return key
    return None


def _extract_complex_id_from_url(url: str, pattern: str) -> str | None:
    """URL에서 단지 ID를 추출한다.

    인자:
        url: 캡처 URL
        pattern: 단지 ID 추출용 정규식 (캡처 그룹 1이 ID)

    반환:
        단지 ID 문자열 또는 None
    """
    m = re.search(pattern, url)
    return m.group(1) if m else None


def _extract_plan_type(url: str) -> str | None:
    """developmentplan URL에서 계획 유형을 추출한다.

    인자:
        url: 캡처 URL

    반환:
        "jigu"|"rail"|"road"|"station" 또는 None
    """
    m = re.search(r"/api/developmentplan/(\w+)/", url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# PII 마스킹 헬퍼 (REQ-NL-072)
# ---------------------------------------------------------------------------

def _mask_article_pii(article: dict) -> dict:
    """매물 dict에서 PII 필드를 마스킹한 사본을 반환한다 (REQ-NL-072).

    plan.md PII 처리표 준수:
    - realtorName → "공인중개사사무소(MASK)"
    - realtorId   → "MASK_ID"
    - detailAddress → ""
    - cpName, cpid  → "출처(MASK)"
    - cpPcArticleUrl, cpMobileArticleUrl, cpPcArticleBridgeUrl → scheme://host/MASKED

    인자:
        article: 원본 매물 dict

    반환:
        PII 마스킹이 적용된 새 dict (원본 불변)
    """
    masked = dict(article)

    if "realtorName" in masked:
        masked["realtorName"] = "공인중개사사무소(MASK)"
    if "realtorId" in masked:
        masked["realtorId"] = "MASK_ID"
    if "detailAddress" in masked:
        masked["detailAddress"] = ""
    if "cpName" in masked:
        masked["cpName"] = "출처(MASK)"
    if "cpid" in masked:
        masked["cpid"] = "출처(MASK)"

    # URL 필드: 도메인만 유지 (scheme://host/MASKED)
    url_fields = ("cpPcArticleUrl", "cpMobileArticleUrl", "cpPcArticleBridgeUrl")
    for field in url_fields:
        if field in masked and masked[field]:
            masked[field] = _mask_url_to_domain(masked[field])

    return masked


def _mask_url_to_domain(url: str) -> str:
    """URL을 scheme://host/MASKED 형태로 단축한다.

    인자:
        url: 원본 URL 문자열

    반환:
        scheme://host/MASKED 형태 문자열. 파싱 실패 시 "/MASKED" 반환.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/MASKED"
    except Exception:
        pass
    return "/MASKED"


# ---------------------------------------------------------------------------
# 단지 마커 파싱
# ---------------------------------------------------------------------------

def _parse_markers(
    body: list,
    complexes: list[dict],
    warnings: list[str],
) -> None:
    """complexes/single-markers 응답에서 단지 목록을 정규화한다 (REQ-NL-041).

    스키마 변경 감지: 핵심 필드 누락률이 _SCHEMA_MISSING_THRESHOLD 초과 시 경고 (REQ-NL-061).

    인자:
        body: 마커 list (API 응답 body)
        complexes: 정규화된 단지를 추가할 list (in-place 수정)
        warnings: 경고 메시지를 추가할 list
    """
    if not body:
        return

    # COMPLEX 타입만 필터링
    complex_markers = [m for m in body if isinstance(m, dict) and m.get("markerType") == "COMPLEX"]
    if not complex_markers:
        # markerType 필드가 없을 수도 있음 → 전체 사용
        complex_markers = [m for m in body if isinstance(m, dict)]

    if not complex_markers:
        return

    # 스키마 변경 감지 (REQ-NL-061)
    missing_count = sum(
        1 for m in complex_markers
        if any(field not in m for field in _COMPLEX_CRITICAL_FIELDS)
    )
    missing_ratio = missing_count / len(complex_markers)
    if missing_ratio > _SCHEMA_MISSING_THRESHOLD:
        warnings.append(
            f"단지 마커 스키마 변경 의심: {len(complex_markers)}건 중 {missing_count}건에서 "
            f"핵심 필드({', '.join(_COMPLEX_CRITICAL_FIELDS)}) 누락 ({missing_ratio:.0%}). "
            "어댑터 필드 매핑을 업데이트하세요."
        )

    for marker in complex_markers:
        if not isinstance(marker, dict):
            continue

        # 핵심 필드 없는 항목은 skip (스키마 변경으로 파싱 불가)
        if not marker.get("complexName") and not marker.get("markerId"):
            continue

        try:
            lat_raw = marker.get("latitude")
            lng_raw = marker.get("longitude")
            complexes.append({
                "complex_id": str(marker.get("markerId", "")),
                "name": str(marker.get("complexName", "")),
                "lat": float(lat_raw) if lat_raw is not None else 0.0,
                "lng": float(lng_raw) if lng_raw is not None else 0.0,
                "real_estate_type_code": str(marker.get("realEstateTypeCode", "")),
                "real_estate_type_name": str(marker.get("realEstateTypeName", "")),
                "completion_year_month": marker.get("completionYearMonth"),
                "total_dong_count": _to_int_or_none(marker.get("totalDongCount")),
                "total_household_count": _to_int_or_none(marker.get("totalHouseholdCount")),
                "floor_area_ratio": _to_int_or_none(marker.get("floorAreaRatio")),
                "min_area": _to_float_or_none(marker.get("minArea")),
                "max_area": _to_float_or_none(marker.get("maxArea")),
                "deal_count": _to_int_or_none(marker.get("dealCount")),
                "lease_count": _to_int_or_none(marker.get("leaseCount")),
                "rent_count": _to_int_or_none(marker.get("rentCount")),
                "total_article_count": _to_int_or_none(marker.get("totalArticleCount")),
                "raw": dict(marker),
            })
        except (TypeError, ValueError):
            warnings.append(f"단지 마커 파싱 오류 (markerId={marker.get('markerId')}): skip")


def _parse_complex_detail(body: dict) -> dict | None:
    """complexes/overview/{id} 응답을 정규화한다.

    인자:
        body: 단지 상세 dict

    반환:
        정규화된 complex_detail dict 또는 None (파싱 실패 시)
    """
    try:
        lat_raw = body.get("latitude")
        lng_raw = body.get("longitude")
        return {
            "complex_id": str(body.get("complexNo", "")),
            "complex_name": str(body.get("complexName", "")),
            "complex_type": str(body.get("complexType", "")),
            "total_household_count": _to_int_or_none(body.get("totalHouseHoldCount")),
            "total_dong_count": _to_int_or_none(body.get("totalDongCount")),
            "use_approve_ymd": body.get("useApproveYmd"),
            "min_price": _to_int_or_none(body.get("minPrice")),
            "max_price": _to_int_or_none(body.get("maxPrice")),
            "min_lease_price": _to_int_or_none(body.get("minLeasePrice")),
            "max_lease_price": _to_int_or_none(body.get("maxLeasePrice")),
            "lat": float(lat_raw) if lat_raw is not None else 0.0,
            "lng": float(lng_raw) if lng_raw is not None else 0.0,
            "pyeongs": body.get("pyeongs", []),
            "dongs": body.get("dongs", []),
            "raw": dict(body),
        }
    except (TypeError, ValueError):
        return None


def _parse_articles(
    article_list: list,
    complex_id: str | None,
    listings: list[dict],
    warnings: list[str],
) -> None:
    """articles/complex/{id} 응답의 articleList를 정규화한다 (REQ-NL-042).

    PII 마스킹 포함 (REQ-NL-072).

    인자:
        article_list: 매물 dict list
        complex_id: URL에서 추출한 단지 ID (str | None)
        listings: 정규화된 매물을 추가할 list (in-place 수정)
        warnings: 경고 메시지를 추가할 list
    """
    if not article_list:
        return

    # 스키마 변경 감지 (REQ-NL-061)
    missing_count = sum(
        1 for a in article_list
        if isinstance(a, dict) and any(field not in a for field in _ARTICLE_CRITICAL_FIELDS)
    )
    if article_list and missing_count / len(article_list) > _SCHEMA_MISSING_THRESHOLD:
        warnings.append(
            f"매물 스키마 변경 의심: {len(article_list)}건 중 {missing_count}건에서 "
            f"핵심 필드({', '.join(_ARTICLE_CRITICAL_FIELDS)}) 누락. "
            "어댑터 필드 매핑을 업데이트하세요."
        )

    for article in article_list:
        if not isinstance(article, dict):
            continue

        # PII 마스킹 (REQ-NL-072)
        masked = _mask_article_pii(article)

        try:
            lat_raw = masked.get("latitude")
            lng_raw = masked.get("longitude")
            listings.append({
                "article_no": str(masked.get("articleNo", "")),
                "article_name": str(masked.get("articleName", "")),
                "complex_id": complex_id,
                "trade_type_code": str(masked.get("tradeTypeCode", "")),
                "trade_type_name": str(masked.get("tradeTypeName", "")),
                "real_estate_type_code": str(masked.get("realEstateTypeCode", "")),
                "real_estate_type_name": str(masked.get("realEstateTypeName", "")),
                "floor_info": str(masked.get("floorInfo", "")),
                "price": str(masked.get("dealOrWarrantPrc", "")),
                "area1": _to_float_or_none(masked.get("area1")),
                "area2": _to_float_or_none(masked.get("area2")),
                "direction": str(masked.get("direction", "")),
                "article_confirm_ymd": str(masked.get("articleConfirmYmd", "")),
                "feature_desc": str(masked.get("articleFeatureDesc", "")),
                "tags": list(masked.get("tagList", [])),
                "building_name": str(masked.get("buildingName", "")),
                "lat": float(lat_raw) if lat_raw is not None else None,
                "lng": float(lng_raw) if lng_raw is not None else None,
                "raw": masked,
            })
        except (TypeError, ValueError) as exc:
            warnings.append(f"매물 파싱 오류 (articleNo={article.get('articleNo')}): {exc}")


def _parse_region(body: dict) -> dict | None:
    """cortars 응답을 정규화한다.

    인자:
        body: 행정구역 dict

    반환:
        정규화된 region dict 또는 None (파싱 실패 시)
    """
    try:
        return {
            "cortar_no": str(body.get("cortarNo", "")),
            "cortar_name": str(body.get("cortarName", "")),
            "city_name": str(body.get("cityName", "")),
            "division_name": str(body.get("divisionName", "")),
            "sector_name": str(body.get("sectorName", "")),
            "center_lat": float(body.get("centerLat", 0.0)),
            "center_lng": float(body.get("centerLon", 0.0)),
            "vertex_lists": body.get("cortarVertexLists", []),
            "raw": dict(body),
        }
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 타입 변환 유틸
# ---------------------------------------------------------------------------

def _to_int_or_none(value: Any) -> int | None:
    """값을 int로 변환하거나 None을 반환한다."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float_or_none(value: Any) -> float | None:
    """값을 float으로 변환하거나 None을 반환한다."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# M5 — Markdown 출력 헬퍼 (REQ-NL-050~052)
# ---------------------------------------------------------------------------

def to_markdown(extracted: dict) -> str:
    """extract() 결과를 Markdown 문자열로 변환한다 (REQ-NL-050~052).

    extract_content.py의 _render_capture_as_markdown과는 별개로
    어댑터 내부에서 네이버 부동산 특화 Markdown을 생성한다.

    인자:
        extracted: extract()가 반환한 dict

    반환:
        UTF-8 Markdown 문자열
    """
    lines: list[str] = []
    meta = extracted.get("meta", {})
    query = extracted.get("query", {})
    complexes = extracted.get("complexes", [])
    listings = extracted.get("listings", [])
    regions = extracted.get("regions", [])
    warnings = meta.get("warnings", [])

    # ── 헤더 ──
    lines.append("# Naver Land 단지 조회 결과\n")

    # ── 조회 정보 ──
    lines.append("## 조회 정보")
    lat = query.get("lat")
    lng = query.get("lng")
    zoom = query.get("zoom")
    if lat is not None and lng is not None:
        zoom_str = f" (zoom {zoom})" if zoom is not None else ""
        lines.append(f"- 좌표: {lat}, {lng}{zoom_str}")
    lines.append(f"- 수집 시각: {meta.get('collected_at', 'N/A')}")
    robots_check = meta.get("robots_check", {})
    robots_allowed = robots_check.get("allowed", True)
    lines.append(f"- robots.txt: {'허용' if robots_allowed else '차단'}")
    if meta.get("anti_bot_detected"):
        lines.append("- **⚠ anti-bot 차단 감지됨**")
    lines.append("")

    # ── 단지 목록 ──
    lines.append(f"## 단지 목록 ({len(complexes)}개)\n")
    if complexes:
        lines.append("| 단지명 | 위도 | 경도 | 세대수 | 동수 | 전용면적 범위 | 매물 수 |")
        lines.append("|--------|------|------|--------|------|--------------|--------|")
        for c in complexes:
            name = c.get("name", "")
            lat_c = c.get("lat", "")
            lng_c = c.get("lng", "")
            hh = c.get("total_household_count", "")
            dong = c.get("total_dong_count", "")
            min_a = c.get("min_area")
            max_a = c.get("max_area")
            area_range = (
                f"{min_a}~{max_a}㎡" if min_a is not None and max_a is not None
                else "N/A"
            )
            total_art = c.get("total_article_count", "")
            lines.append(
                f"| {name} | {lat_c} | {lng_c} | {hh} | {dong} | {area_range} | {total_art} |"
            )
        lines.append("")

    # ── 단지 상세 ──
    complex_details = extracted.get("complex_details", [])
    if complex_details:
        lines.append("## 단지 상세\n")
        for d in complex_details:
            lines.append(f"### {d.get('complex_name', '알 수 없음')}")
            lines.append(f"- 단지번호: {d.get('complex_id', '')}")
            lines.append(f"- 유형: {d.get('complex_type', '')}")
            lines.append(f"- 세대수: {d.get('total_household_count', 'N/A')}")
            lines.append(f"- 동수: {d.get('total_dong_count', 'N/A')}")
            approve = d.get("use_approve_ymd")
            if approve:
                lines.append(f"- 사용승인일: {approve}")
            min_p = d.get("min_price")
            max_p = d.get("max_price")
            if min_p is not None and max_p is not None:
                lines.append(f"- 매매가격대: {min_p:,}~{max_p:,}만원")
            lines.append("")

    # ── 매물 ──
    if listings:
        lines.append(f"## 매물 ({len(listings)}건)\n")
        lines.append("| 거래유형 | 가격 | 면적(공급/전용) | 층 | 방향 | 확인일 |")
        lines.append("|----------|------|-----------------|-----|------|--------|")
        for listing in listings:
            trade = listing.get("trade_type_name", "")
            price = listing.get("price", "")
            area1 = listing.get("area1")
            area2 = listing.get("area2")
            area_str = (
                f"{area1}/{area2}㎡" if area1 is not None and area2 is not None
                else "N/A"
            )
            floor = listing.get("floor_info", "")
            direction = listing.get("direction", "")
            confirm_ymd = listing.get("article_confirm_ymd", "")
            lines.append(
                f"| {trade} | {price} | {area_str} | {floor} | {direction} | {confirm_ymd} |"
            )
        lines.append("")

    # ── 행정구역 ──
    if regions:
        lines.append("## 행정구역\n")
        for r in regions:
            city = r.get("city_name", "")
            division = r.get("division_name", "")
            sector = r.get("sector_name", "")
            cortar_name = r.get("cortar_name", "")
            lines.append(f"- {city} {division} {sector} ({cortar_name})")
        lines.append("")

    # ── 메타 ──
    lines.append("## 메타\n")
    if warnings:
        lines.append("### 경고")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    endpoint_counts = meta.get("endpoint_counts", {})
    if endpoint_counts:
        lines.append("### 응답 통계")
        for ep, cnt in endpoint_counts.items():
            lines.append(f"- {ep}: {cnt}건")

    return "\n".join(lines)
