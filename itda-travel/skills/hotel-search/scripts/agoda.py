#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agoda.py - Agoda 호텔 가격 조회 (검색 결과).

Booking(booking.py)과 동형 2-스텝 구조: Claude 가 hyve web_browse `extract` 로 카드 raw 를
얻고, 이 모듈이 (a) 검색 path 를 만들고 build_agoda_path, (b) raw 를 정제 parse_agoda.

## 라이브 실측 결과 (#982, 2026-07-07 · references/booking-live-probe.md 동반)

- 검색결과는 SPA. 정본 raw = web_browse `extract`(item_selector=hotel-item) 구조화 JSON.
- **anti-bot** — Booking 과 동일하게 **mode=attach**(사용자 워밍업 Chrome)가 priced 결과의 정본.
- **확정 selector**(priced 카드):
    hotel_name         [data-selenium='hotel-name']              "St.John's Hotel"
    total_per_night    [data-selenium='total-price-per-night']   "Total per night ₩ 314,007" (세금포함)
    review(aria)       [data-mimir-element-data='dictator']      "…Average rating Excellent 8.5 out of 10 with 27,382 reviews…"
    free_cancel        [data-badge-id='fcl']                     "+ FREE CANCELLATION" (존재=무료취소)
  ⚠️ **가격 정본 = total-price-per-night(세금·수수료 포함)**. 헤드라인 display-price 는 세금 제외
     할인가라 사이트 간 비교의 정본이 아니다(data-accuracy). room_type·url 은 검색카드에 미표기 → None.

## 검색 URL

GET https://www.agoda.com/search
  textToSearch={질의}   checkIn/checkOut={YYYY-MM-DD}
  rooms / adults / children   priceCur={ISO}   los={박수}   locale=ko-kr
(dest 는 자동완성 선택으로 city/latlong 해소가 정본 — Booking 동형. cold 세션은 anti-bot 스트립 가능.)
"""
from __future__ import annotations

import re
from urllib.parse import urlencode

from errors import BlockedError, NoResultError

_BLOCK = ("Access Denied", "captcha", "unusual traffic", "Are you a robot", "px-captcha")

_AGODA_RATING_SCALE = 10.0

# "Total per night ₩ 314,007" → 314007 (첫 숫자 그룹).
_WON_RE = re.compile(r"[\d][\d,]*")
# aria: "… 8.5 out of 10 with 27,382 reviews" → (8.5, 27382). 등급어 무관("Very good" 등).
_AGODA_REVIEW_RE = re.compile(r"([\d.]+)\s+out of 10 with\s+([\d,]+)\s+reviews")


def build_agoda_path(
    query: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "KRW",
    lang: str = "ko",
) -> str:
    """Agoda 검색결과 경로를 빌드한다(www.agoda.com origin 기준 상대 경로).

    textToSearch 기반 검색 URL. 워밍업(attach) 세션에서 navigate 하거나 검색폼 인터랙션 출발점.
    """
    from datetime import date

    try:
        los = (date.fromisoformat(checkout) - date.fromisoformat(checkin)).days
    except ValueError:
        los = 1
    params = {
        "textToSearch": query,
        "checkIn": checkin,
        "checkOut": checkout,
        "rooms": rooms,
        "adults": adults,
        "children": 0,
        "priceCur": currency,
        "los": max(los, 1),
        "locale": f"{lang}-kr" if lang == "ko" else lang,
    }
    return "/search?" + urlencode(params)


def extract_agoda(fetch_result: dict):
    """web_browse extract 결과에서 hotel-item items 리스트를 뽑는다(차단/비정상 체크 포함)."""
    if isinstance(fetch_result, list):
        return fetch_result

    status = fetch_result.get("status")
    text = (fetch_result.get("text") or fetch_result.get("html") or "")[:2000]
    if status == 403 or any(s.lower() in text.lower() for s in _BLOCK):
        raise BlockedError(
            "Agoda 봇 차단(403/CAPTCHA) — web_browse mode=attach(사용자 워밍업 Chrome)로 재시도하세요"
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
        "Agoda 응답에 hotel-item items 가 없습니다 "
        "(web_browse extract(item_selector=[data-selenium='hotel-item']) 결과를 저장했는지 확인)"
    )


def _parse_won(text) -> int | None:
    """'Total per night ₩ 314,007' → 314007. 파싱 불가 → None."""
    if text is None:
        return None
    m = _WON_RE.search(str(text))
    if not m:
        return None
    digits = m.group(0).replace(",", "")
    return int(digits) if digits.isdigit() else None


def _parse_review(text) -> tuple[float | None, int | None]:
    """aria 텍스트에서 '… X out of 10 with Y reviews' → (X, Y). 없으면 (None, None)."""
    if not text:
        return None, None
    m = _AGODA_REVIEW_RE.search(str(text))
    if not m:
        return None, None
    return float(m.group(1)), int(m.group(2).replace(",", ""))


def _free_cancellation(free_cancel) -> bool | None:
    """free-cancellation 배지([data-badge-id='fcl']) 텍스트가 있으면 True, 없으면 None."""
    if free_cancel and "FREE CANCELLATION" in str(free_cancel).upper():
        return True
    return None


def parse_agoda(raw, *, query: str, nights: int, currency: str, urls: dict | None = None) -> list[dict]:
    """Agoda hotel-item items 를 output.py 공통 offer 스키마 리스트로 정제한다.

    raw = extract items([{hotel_name, total_per_night, review, free_cancel}, ...]).
    total_per_night = 세금·수수료 포함 1박가(정본) → per_night=그 값, price(체류 총액)=per_night×nights.
    미렌더/무가격 카드(hotel_name 또는 total_per_night 없음)는 건너뛴다.
    """
    if not isinstance(raw, list):
        raise NoResultError("Agoda raw 가 items 리스트가 아닙니다")

    url_map = urls or {}
    offers: list[dict] = []
    for card in raw:
        if not isinstance(card, dict):
            continue
        name = (card.get("hotel_name") or "").strip()
        per_night = _parse_won(card.get("total_per_night"))
        if not name or per_night is None:
            continue  # 미렌더/무가격(재고 없음) 카드
        total = per_night * nights if nights else per_night
        rating, review_count = _parse_review(card.get("review"))
        offers.append(
            {
                "source": "agoda",
                "hotel_name": name,
                "url": url_map.get(name) or card.get("url"),
                "price": total,
                "per_night": per_night,
                "currency": currency,
                "rating": rating,
                "rating_scale": _AGODA_RATING_SCALE if rating is not None else None,
                "review_count": review_count,
                "room_type": None,  # Agoda 검색카드는 객실타입 미표기(상세에서 결정)
                "free_cancellation": _free_cancellation(card.get("free_cancel")),
                "breakfast": None,
            }
        )

    if not offers:
        raise NoResultError(
            "Agoda 결과 카드 0건 — 호텔 매칭 없음/재고 없음, 또는 anti-bot(mode=attach 재시도)"
        )
    return offers
