#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""booking.py - Booking.com 호텔 가격 조회 (검색 결과).

2-스텝 구조(coupang 전례): Claude 가 hyve web_browse MCP 로 raw 를 얻고,
이 모듈이 (a) fetch 할 path 를 만들고 build_booking_path, (b) raw 를 정제 parse_booking.

## 라이브 실측 결과 (#982 task #3, 2026-07-07 · references/booking-live-probe.md)

- **검색 결과는 SSR DOM** — 리스팅 graphql XHR 없음(부수 호출만). spa-api-first 비적용,
  DOM 파싱이 정본. 정본 raw = web_browse `extract`(item_selector=property-card) 구조화 JSON.
- **anti-bot(AWS WAF)** — 워밍업 안 된 세션은 가격을 원천 withhold(카드가 "날짜 선택" 상태,
  가격 요소 0). **mode=attach**(사용자가 로그인/브라우징한 Chrome)로 붙어야 priced 결과가 온다.
- **확정 selector**(priced 카드):
    hotel_name  [data-testid='title']
    price       [data-testid='price-and-discounted-price']   "₩726,000" (체류 총액, sb_price_type=total)
    review      [data-testid='review-score']                 "9.2 9.2 최고 764개 이용 후기" (scale=10)
    unit        [data-testid='recommended-units']            객실타입 + "무료 취소" 포함 여부
  url(href)은 extract 미지원(항상 텍스트 반환) → MVP None(상세 딥링크는 향후 HTML 파싱 확장).

## 검색 URL 파라미터

GET https://www.booking.com/searchresults.ko.html
  ss={질의}                     호텔명(자동완성으로 dest_id/latlong 해소가 정본)
  checkin/checkout={YYYY-MM-DD}
  group_adults / no_rooms / group_children
  selected_currency={ISO}       lang={locale}

⚠️ cold(비워밍업) 세션은 위 파라미터가 스트립되어 빈 검색폼으로 되돌아온다(anti-bot).
   attach 워밍업 세션에서는 ss= 딥링크가 유지되거나, 검색폼 인터랙션(타이핑→자동완성 선택→
   날짜 캘린더 [data-date] 클릭→검색)이 안정 경로다. 상세는 SKILL.md 참고.
"""
from __future__ import annotations

import re
from urllib.parse import urlencode

from errors import BlockedError, NoResultError

# 차단 시그니처(HTML 본문) — 방어적. 정본 경로는 extract items.
_BLOCK = ("Access Denied", "captcha", "unusual traffic", "Are you a robot")

# Booking 평점 만점(고정).
_BOOKING_RATING_SCALE = 10.0

# 가격 문자열의 천단위 정수 추출("₩726,000" → 726000).
_WON_RE = re.compile(r"[\d][\d,]*")
# 평점 선두 숫자("9.2 9.2 최고 …" → 9.2, "10 10 강력 추천 …" → 10).
_SCORE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)")
# 후기수("764개 이용 후기" → 764).
_REVIEW_COUNT_RE = re.compile(r"([\d,]+)\s*개\s*이용\s*후기")
# 객실 타입 = unit 텍스트 선두 구절. 첫 구조/상세 마커에서 절단.
_ROOM_CUT_RE = re.compile(
    r"\s+(?:-|–|•|단독으로|무료\s*취소|초대형|대형|더블침대|싱글침대|킹침대|퀸침대|침대\s|\d+\s*베드)"
)

# HTML 보조 파싱(url 채움) — extract 가 href 미지원이라 검색결과 HTML 에서 카드별 상세 URL 추출.
_CARD_MARKER = 'data-testid="property-card"'
_HTML_TITLE_RE = re.compile(r'data-testid="title"[^>]*>([^<]+)<')
_HTML_TITLELINK_TAG_RE = re.compile(r'<a\b[^>]*data-testid="title-link"[^>]*>')
_HTML_HREF_RE = re.compile(r'href="([^"]+)"')


def build_booking_path(
    query: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "KRW",
    lang: str = "ko",
) -> str:
    """Booking 검색결과 경로를 빌드한다(www.booking.com origin 기준 상대 경로).

    ss= 기반 검색 URL. 워밍업(attach) 세션에서 navigate 하거나, 검색폼 인터랙션의
    출발 URL 로 쓴다. dest_id/latlong 은 자동완성 선택으로 해소되므로 여기 넣지 않는다.
    """
    params = {
        "ss": query,
        "checkin": checkin,
        "checkout": checkout,
        "group_adults": adults,
        "no_rooms": rooms,
        "group_children": 0,
        "selected_currency": currency,
        "lang": lang,
    }
    return "/searchresults.ko.html?" + urlencode(params)


def extract_booking(fetch_result: dict):
    """web_browse 결과(dict)에서 property-card items 리스트를 뽑는다(차단/비정상 체크 포함).

    정본 raw = web_browse `extract`(item_selector=property-card) 응답:
        {"count": N, "items": [{hotel_name, price, review_score, unit}, ...]}
    방어적으로 {json:[...]} / {json:{items:[...]}} / 최상위 리스트도 허용한다.
    403/CAPTCHA 시그니처(agent 가 html/text 를 저장한 경우)는 BlockedError 로 표면화한다.
    """
    if isinstance(fetch_result, list):
        return fetch_result

    status = fetch_result.get("status")
    text = (fetch_result.get("text") or fetch_result.get("html") or "")[:2000]
    if status == 403 or any(s.lower() in text.lower() for s in _BLOCK):
        raise BlockedError(
            "Booking 봇 차단(403/CAPTCHA) — web_browse mode=attach(사용자 워밍업 Chrome)로 재시도하세요"
        )

    items = fetch_result.get("items")
    if items is None:
        j = fetch_result.get("json")
        if isinstance(j, list):
            items = j
        elif isinstance(j, dict) and isinstance(j.get("items"), list):
            items = j["items"]
    if isinstance(items, list):
        return items

    raise NoResultError(
        "Booking 응답에 property-card items 가 없습니다 "
        "(web_browse extract(item_selector=[data-testid='property-card']) 결과를 저장했는지 확인)"
    )


def _parse_won(text) -> int | None:
    """'₩726,000' / '95,848' → 726000 / 95848. 파싱 불가 → None."""
    if text is None:
        return None
    m = _WON_RE.search(str(text).replace(" ", " "))
    if not m:
        return None
    digits = m.group(0).replace(",", "")
    return int(digits) if digits.isdigit() else None


def _parse_review(text) -> tuple[float | None, int | None]:
    """'9.2 9.2 최고 764개 이용 후기' → (9.2, 764). None/무후기 → (None, None)."""
    if not text:
        return None, None
    ms = _SCORE_RE.search(text)
    rating = float(ms.group(1)) if ms else None
    mc = _REVIEW_COUNT_RE.search(text)
    count = int(mc.group(1).replace(",", "")) if mc else None
    return rating, count


def _room_type(unit) -> str | None:
    """recommended-units 텍스트 선두 구절을 객실타입 표시값으로 추출(best-effort 표시 힌트)."""
    if not unit:
        return None
    rt = _ROOM_CUT_RE.split(unit, maxsplit=1)[0].strip()
    return rt or None


def _free_cancellation(unit) -> bool | None:
    """unit 텍스트에 '무료 취소' 표기가 있으면 True. 없으면 None(불명 — False 로 단정하지 않음)."""
    if not unit:
        return None
    return True if "무료 취소" in unit else None


def _canonical_url(href) -> str | None:
    """affiliate 쿼리(?aid/label/…)를 제거한 상세 경로만 남긴다(affiliate 미부착 정책)."""
    if not href:
        return None
    path = str(href).split("?", 1)[0].strip()
    return path or None


def parse_name_url_map(html) -> dict[str, str]:
    """검색결과 HTML 에서 카드별 (호텔명 → canonical 상세 URL) 매핑을 만든다.

    web_browse `extract` 는 href 를 못 주므로(텍스트만), 상세 딥링크가 필요하면 에이전트가
    `snapshot mode=html` 로 저장한 HTML 을 이 헬퍼로 파싱해 url 을 채운다(이름 기준 매칭 —
    카드 순서 취약성 회피). 매칭 실패/HTML 부재는 빈 dict(= url None 유지).
    """
    if not html or not isinstance(html, str):
        return {}
    out: dict[str, str] = {}
    for seg in html.split(_CARD_MARKER)[1:]:
        mt = _HTML_TITLE_RE.search(seg)
        if not mt:
            continue
        name = mt.group(1).strip()
        if not name or name in out:
            continue
        ma = _HTML_TITLELINK_TAG_RE.search(seg)
        if not ma:
            continue
        mh = _HTML_HREF_RE.search(ma.group(0))
        url = _canonical_url(mh.group(1)) if mh else None
        if url:
            out[name] = url
    return out


def parse_booking(
    raw, *, query: str, nights: int, currency: str, urls: dict | None = None
) -> list[dict]:
    """Booking property-card items 를 output.py 공통 offer 스키마 리스트로 정제한다.

    raw = extract items 리스트([{hotel_name, price, review_score, unit}, ...]).
    price 는 체류 총액(sb_price_type=total) → per_night = round(total/nights).
    urls = parse_name_url_map(html) 결과(호텔명→상세 URL). 주면 offer.url 을 채운다(없으면 None).
    검색은 위치 인근 다수 호텔을 반환(거리순) — 첫 결과가 통상 질의 호텔.
    호텔 매칭(어느 카드가 질의 호텔인가)은 에이전트가 이름/주소로 확인한다(SKILL.md).
    """
    if not isinstance(raw, list):
        raise NoResultError("Booking raw 가 items 리스트가 아닙니다")

    url_map = urls or {}
    offers: list[dict] = []
    for card in raw:
        if not isinstance(card, dict):
            continue
        name = (card.get("hotel_name") or "").strip()
        if not name:
            continue
        total = _parse_won(card.get("price"))
        per_night = round(total / nights) if (total is not None and nights) else None
        rating, review_count = _parse_review(card.get("review_score"))
        unit = card.get("unit")
        offers.append(
            {
                "source": "booking",
                "hotel_name": name,
                "url": url_map.get(name) or card.get("url"),  # HTML 매핑 우선, 없으면 None
                "price": total,
                "per_night": per_night,
                "currency": currency,
                "rating": rating,
                "rating_scale": _BOOKING_RATING_SCALE if rating is not None else None,
                "review_count": review_count,
                "room_type": _room_type(unit),
                "free_cancellation": _free_cancellation(unit),
                "breakfast": None,  # recommended-units 에 조식 정보 없음(MVP None)
            }
        )

    if not offers:
        raise NoResultError(
            "Booking 결과 카드 0건 — 호텔 매칭 없음/재고 없음, 또는 anti-bot(mode=attach 재시도)"
        )
    return offers
