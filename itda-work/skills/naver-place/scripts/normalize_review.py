#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""normalize_review.py - 리뷰 데이터 정규화 및 날짜 파싱.

네이버 플레이스 리뷰의 다양한 날짜 형식을 파싱하고
리뷰 데이터를 통합 스키마로 변환한다.

Date formats:
    "25.12.29.월" → "2025-12-29" (YY.M.D.요일)
    "1.30.금" → "2026-01-30" (M.D.요일, 현재 연도)
    "12.29.월" → "2025-12-29" (M.D.요일, 미래면 전년)

Unified review schema:
    reviewId, authorNickname, body, created, visited, originType,
    media[], votedKeywords[], visitCategories[]
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

# 날짜 정규식: YY.M.D.요일 또는 M.D.요일
_DATE_RE_FULL = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{1,2})\.(?:월|화|수|목|금|토|일)")
_DATE_RE_SHORT = re.compile(r"(\d{1,2})\.(\d{1,2})\.(?:월|화|수|목|금|토|일)")


def parse_review_date(date_str: str, reference: date) -> str:
    """리뷰 날짜 문자열을 YYYY-MM-DD 형식으로 파싱한다.

    Args:
        date_str: "25.12.29.월" 또는 "1.30.금" 형식의 날짜 문자열.
        reference: 기준 날짜 (현재 날짜 또는 수집일).

    Returns:
        "YYYY-MM-DD" 형식의 날짜 문자열.
    """
    # Try full format first: YY.M.D.요일
    match = _DATE_RE_FULL.search(date_str)
    if match:
        year_part, month_part, day_part = match.groups()[0:3]
        year = int(year_part)
        month = int(month_part)
        day = int(day_part)

        # 연도가 2자리인 경우 (YY.M.D)
        if year < 100:
            if year <= 50:
                year += 2000
            else:
                year += 1900

        # 날짜 유효성 검사 및 미래 날짜 처리
        return _finalize_date(year, month, day, reference)

    # Try short format: M.D.요일
    match = _DATE_RE_SHORT.search(date_str)
    if match:
        month_part, day_part = match.groups()[0:2]
        year = reference.year  # reference 연도 사용
        month = int(month_part)
        day = int(day_part)

        return _finalize_date(year, month, day, reference)

    return ""


def _finalize_date(year: int, month: int, day: int, reference: date) -> str:
    """날짜를 유효성 검사하고 미래 날짜를 조정한 후 ISO 포맷으로 반환한다."""
    try:
        parsed = date(year, month, day)
    except ValueError:
        return ""

    # 미래 날짜면 전년으로 처리 (12.29.월이 1월에 수집된 경우)
    if parsed > reference:
        year -= 1
        try:
            parsed = date(year, month, day)
        except ValueError:
            return ""

    return parsed.isoformat()


def normalize_review(raw: dict[str, Any], reference_date: date) -> dict[str, Any]:
    """리뷰 데이터를 통합 스키마로 정규화한다.

    Args:
        raw: 원본 리뷰 데이터 (HTML 파싱 또는 GraphQL).
        reference_date: 날짜 파싱을 위한 기준 날짜.

    Returns:
        통합 스키마의 review dict.
    """
    # 필드 매핑 (다양한 소스 필드명 지원)
    raw_id = raw.get("id") or raw.get("reviewId", "")
    _author_raw = raw.get("author") or raw.get("authorNickname") or raw.get("nickname", "")
    author = (_author_raw if isinstance(_author_raw, str) else "").strip()
    body = raw.get("body") or raw.get("content") or raw.get("reviewComment", "") or raw.get("text", "")

    raw_created = raw.get("created") or raw.get("createdAt") or ""
    raw_visited = raw.get("visited") or raw.get("visitedAt") or ""

    # 날짜 정규화
    if raw_created:
        created = parse_review_date(raw_created, reference_date)
    else:
        created = ""

    if raw_visited:
        visited = parse_review_date(raw_visited, reference_date)
    else:
        visited = ""

    # 미디어 (images[], photos[], media[])
    media = []
    for img in raw.get("images") or raw.get("photos") or raw.get("media") or []:
        if isinstance(img, str):
            media.append(img)
        elif isinstance(img, dict) and "url" in img:
            media.append(img["url"])

    # 키워드 (keywords[], votedKeywords[])
    keywords = raw.get("votedKeywords") or raw.get("keywords") or []

    # 방문 유형 (visitType[], visitCategories[])
    visit_cats = raw.get("visitCategories") or raw.get("visitType") or []
    if isinstance(visit_cats, str):
        visit_cats = [visit_cats]

    return {
        "reviewId": raw_id,
        "authorNickname": author,
        "body": body,
        "created": created,
        "visited": visited,
        "originType": raw.get("originType") or raw.get("deviceType") or "",
        "media": media,
        "votedKeywords": keywords,
        "visitCategories": visit_cats,
    }
