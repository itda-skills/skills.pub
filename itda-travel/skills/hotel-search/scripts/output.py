#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""output.py - JSON / Markdown 렌더 (소스 공통 offer 스키마).

정규 offer 스키마(사이트 무관 — booking/tripadvisor/agoda 파서가 이 형태로 매핑):
  {
    "source":            str,          # "booking" | "tripadvisor" | "agoda" | ...
    "hotel_name":        str,          # 사이트 표시명
    "url":               str | None,   # 상세/예약 딥링크(affiliate 미부착)
    "price":             int | None,   # 표시 총액(체류 전체) 정수
    "per_night":         int | None,   # 1박 환산가 정수
    "currency":          str,          # ISO 4217 (KRW/USD/...)
    "rating":            float | None, # 사이트 평점(원척도 유지)
    "rating_scale":      float | None, # 평점 만점(booking=10, tripadvisor=5 등)
    "review_count":      int | None,
    "room_type":         str | None,
    "free_cancellation": bool | None,
    "breakfast":         bool | None,
  }

render 결과(단일 소스) data 스키마:
  {
    "query": str, "checkin": str, "checkout": str, "nights": int,
    "adults": int, "currency": str, "source": str,
    "offers": [offer, ...],
    "_disclaimer": str,
  }
"""
from __future__ import annotations

import json


def to_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _won(v) -> str:
    """정수 가격 → 천단위 구분 문자열. None → '—'."""
    if v is None:
        return "—"
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return str(v)


def _rating(o: dict) -> str:
    r = o.get("rating")
    if r is None:
        return "—"
    scale = o.get("rating_scale")
    base = f"{r:g}"
    if scale:
        base += f"/{scale:g}"
    rc = o.get("review_count")
    if rc:
        base += f" ({rc:,})"
    return base


def offers_to_markdown(data: dict) -> str:
    """단일 소스 offer 목록을 비교표(마크다운)로 렌더한다."""
    src = data.get("source", "")
    lines = [f"# 호텔 가격 — {data.get('query', '')} ({src})", ""]

    ci, co = data.get("checkin"), data.get("checkout")
    nights = data.get("nights")
    meta = []
    if ci and co:
        meta.append(f"{ci} → {co}")
    if nights:
        meta.append(f"{nights}박")
    if data.get("adults"):
        meta.append(f"성인 {data['adults']}인")
    if data.get("currency"):
        meta.append(data["currency"])
    if meta:
        lines.append("· ".join(meta))
        lines.append("")

    offers = data.get("offers") or []
    if not offers:
        lines.append("_해당 조건에 매칭되는 호텔이 없습니다._")
        return "\n".join(lines)

    cur = data.get("currency", "")
    lines.append(f"| 호텔 | 1박 | 총액 | 평점 | 객실 | 무료취소 |")
    lines.append("|---|---:|---:|---|---|:---:|")
    for o in offers:
        name = o.get("hotel_name") or "—"
        url = o.get("url")
        name_cell = f"[{name}]({url})" if url else name
        pn = _won(o.get("per_night"))
        total = _won(o.get("price"))
        room = o.get("room_type") or "—"
        fc = o.get("free_cancellation")
        fc_cell = "✓" if fc else ("✗" if fc is False else "—")
        lines.append(f"| {name_cell} | {pn} | {total} | {_rating(o)} | {room} | {fc_cell} |")

    lines.append("")
    lines.append(f"_통화: {cur} · 조회 시점 참고값 · affiliate 미부착_")
    disc = data.get("_disclaimer")
    if disc:
        lines.append(f"_{disc}_")
    return "\n".join(lines)
