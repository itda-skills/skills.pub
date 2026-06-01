"""daiso_keyword.py - 다이소 매장 검색 키워드 변형(H-1).

역/공백/서비스명이 섞인 검색어를 다이소 매장 검색용으로 보정한다.
ref-daiso `src/utils/daisoKeyword.ts`(buildDaisoStoreKeywordVariants)를 그대로 포팅한다.

원본 변형 규칙(순서·중복제거 보존):
  base         = 원문 trim
  compact      = 모든 공백 제거
  withoutNoise = compact에서 "다이소"/"근처"/"주변" 제거
  withoutStation = withoutNoise에서 끝의 "역" 1회 제거
  last         = withoutStation 끝의 "(중앙)(역)?" → "$1" (축약)

후보 5종을 trim 후 빈 문자열·중복을 제거해 순서를 보존한다.

예) "안산 중앙역 다이소"
    → ["안산 중앙역 다이소", "안산중앙역다이소", "안산중앙역", "안산중앙"]

stdlib `re`만 사용한다(외부 의존 금지).
"""
from __future__ import annotations

import re

#: 연속 공백(JS `\s+`).
_WHITESPACE_RE = re.compile(r"\s+")
#: 노이즈 토큰(서비스명·근처/주변). ref `/(다이소|근처|주변)/g`.
_NOISE_RE = re.compile(r"(다이소|근처|주변)")
#: 끝의 "역". ref `/역$/g`.
_TRAILING_STATION_RE = re.compile(r"역$")
#: 끝의 "(중앙)(역)?" → "$1". ref `/(중앙)(역)?$/g`.
_CENTRAL_RE = re.compile(r"(중앙)(역)?$")


def build_store_keyword_variants(keyword: str) -> list[str]:
    """검색어를 다이소 매장 검색용 변형 후보 리스트로 보정한다.

    ref-daiso `buildDaisoStoreKeywordVariants` 포팅. 빈/공백 입력은 빈 리스트.

    Args:
        keyword: 원문 검색어.

    Returns:
        변형 후보 리스트(순서 보존, 빈 문자열·중복 제거). 입력이 비면 [].
    """
    base = keyword.strip()
    if not base:
        return []

    compact = _WHITESPACE_RE.sub("", base)
    without_noise = _NOISE_RE.sub("", compact)
    without_station = _TRAILING_STATION_RE.sub("", without_noise)
    central = _CENTRAL_RE.sub(r"\1", without_station)

    candidates = [
        base,
        compact,
        without_noise,
        without_station,
        central,
    ]

    unique: list[str] = []
    for item in candidates:
        item = item.strip()
        if not item or item in unique:
            continue
        unique.append(item)
    return unique
