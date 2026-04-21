#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""normalize_place.py - 장소 데이터 정규화.

allSearch와 graphql의 다른 스키마를 통합 스키마로 변환한다.

Unified schema:
    id, name, category[], address, roadAddress, phone, lat, lng,
    reviewCount, imageUrl, menuInfo, distance, page, source
"""
from __future__ import annotations

from typing import Any


def normalize_all_search_place(raw: dict[str, Any], page: int = 1) -> dict[str, Any]:
    """allSearch 스키마를 통합 스키마로 정규화한다.

    Args:
        raw: allSearch 응답의 place 객체.
        page: 결과가 속한 페이지 번호.

    Returns:
        통합 스키마의 place dict.
    """
    return {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "category": raw.get("category") or [],
        "address": raw.get("address", ""),
        "roadAddress": raw.get("roadAddress", ""),
        "phone": raw.get("phone", ""),
        "lat": _parse_float(raw.get("y", "0")),
        "lng": _parse_float(raw.get("x", "0")),
        "reviewCount": raw.get("reviewCount", 0),
        "imageUrl": raw.get("imageUrl", ""),
        "menuInfo": raw.get("menuInfo", ""),
        "distance": raw.get("distance", ""),
        "page": page,
        "source": "allSearch",
    }


def normalize_graphql_place(raw: dict[str, Any], page: int = 1) -> dict[str, Any]:
    """graphql 스키마를 통합 스키마로 정규화한다.

    Args:
        raw: graphql 응답의 place 객체 (nested structure).
        page: 결과가 속한 페이지 번호.

    Returns:
        통합 스키마의 place dict.
    """
    # categories는 객체 배열이므로 name만 추출
    categories = raw.get("categories") or []
    category_list = [c.get("name", "") for c in categories if c.get("name")]

    return {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "category": category_list,
        "address": raw.get("address", ""),
        "roadAddress": raw.get("roadAddress", ""),
        "phone": raw.get("phone", ""),
        "lat": _parse_float(raw.get("y", "0")),
        "lng": _parse_float(raw.get("x", "0")),
        "reviewCount": raw.get("reviewCount", 0),
        "imageUrl": raw.get("thumbnail", ""),  # graphql은 thumbnail 필드
        "menuInfo": "",
        "distance": "",
        "page": page,
        "source": "graphql",
    }


def _parse_float(value: str | int | float | None) -> float:
    """문자열/숫자를 float로 변환한다. 실패 시 0.0 반환."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
