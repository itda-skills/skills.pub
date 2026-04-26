#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPA 프레임워크 자동 감지 모듈.
FR-DETECT-01: HTML 응답 시그니처로 WebSquare5 / Nexacro 감지.
"""
from __future__ import annotations

# @MX:ANCHOR: [AUTO] detect_spa_framework — 모든 SPA 감지 로직의 단일 진입점
# @MX:REASON: [AUTO] SPEC-WEBREADER-006의 FR-DETECT-01 구현; fetch_html, fetch_dynamic 등
#             여러 모듈에서 호출 예정 (fan_in >= 3 예상)

# WebSquare5 감지에 필요한 시그니처 목록 (3종 중 2개 이상 일치)
_WEBSQUARE5_SIGNATURES: list[str] = [
    "WebSquareExternal",
    "_websquare_/javascriptLoader.js",
    "WebSquare._bDocumentReady",
]

# Nexacro 감지 시그니처 목록 (1개 이상 일치)
_NEXACRO_SIGNATURES: list[str] = [
    "nexacro",
    "XPLATFORM",
    "nexacro.LSCRD_main",
]

__all__ = ["detect_spa_framework", "detect_deep_link_block"]


def detect_spa_framework(html: str | None) -> str | None:
    """
    HTML 문자열에서 SPA 프레임워크를 감지한다.

    반환값:
        "websquare5"  — WebSquare5 시그니처 2개 이상 일치
        "nexacro"     — Nexacro 시그니처 1개 이상 일치
        None          — 감지되지 않음 (일반 HTML, React/Vue 등)

    우선순위: WebSquare5 먼저 검사 후 Nexacro 검사.
    대소문자 구분: 시그니처 그대로 일치 (case-sensitive).
    """
    # None 또는 빈 문자열은 즉시 None 반환
    if not html:
        return None

    # WebSquare5 감지: 3종 시그니처 중 2개 이상 포함 여부
    ws_matches = sum(1 for sig in _WEBSQUARE5_SIGNATURES if sig in html)
    if ws_matches >= 2:
        return "websquare5"

    # Nexacro 감지: 1개 이상 포함 여부
    for sig in _NEXACRO_SIGNATURES:
        if sig in html:
            return "nexacro"

    return None


# @MX:ANCHOR: [AUTO] detect_deep_link_block — deep-link 차단 감지 단일 진입점
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ENTRY-03; fetch_dynamic.py --url 경로,
#             테스트, 향후 어댑터 진단 등에서 참조 예정 (fan_in >= 3).
def detect_deep_link_block(input_url: str, final_url: str) -> bool:
    """
    입력 URL과 페이지 로드 후 최종 URL을 비교해 deep-link 차단 여부를 판단한다.

    차단 판단 기준:
    1. 도메인(host)이 다른 경우 → True (타 사이트로 redirect)
    2. www 추가/제거 또는 http→https 변경만 있는 경우 → False (정상 리다이렉트)
    3. path는 같지만 핵심 query param(menuCd, w2xPath, screen 등)이 변경된 경우 → True
    4. deep-link 관련 query param이 사라진 경우 → True
    5. 동일 URL → False

    인자:
        input_url: 사용자가 입력한 원래 URL
        final_url: 페이지 로드 후 최종 URL (page.url)

    반환:
        True이면 deep-link 차단 감지됨
        False이면 정상 (차단 없음)
    """
    from urllib.parse import urlparse, parse_qs

    if input_url == final_url:
        return False

    try:
        in_parsed = urlparse(input_url)
        fin_parsed = urlparse(final_url)
    except Exception:
        # URL 파싱 실패 시 안전하게 False 반환
        return False

    def _normalize_host(host: str) -> str:
        """www. 접두사를 제거하고 소문자로 변환한다."""
        return host.lower().removeprefix("www.")

    in_host = _normalize_host(in_parsed.netloc)
    fin_host = _normalize_host(fin_parsed.netloc)

    # 도메인 변경 → 차단
    if in_host != fin_host:
        return True

    # 같은 도메인 내에서의 path/query 비교
    in_path = in_parsed.path.rstrip("/")
    fin_path = fin_parsed.path.rstrip("/")

    in_query = parse_qs(in_parsed.query, keep_blank_values=True)
    fin_query = parse_qs(fin_parsed.query, keep_blank_values=True)

    # query가 동일하면 단순 리다이렉트 (trailing slash, http→https 등)
    if in_query == fin_query and in_path == fin_path:
        return False

    # 입력 URL에 deep-link 관련 파라미터가 없으면 비교 불필요
    _DEEPLINK_PARAMS = frozenset(["menucd", "w2xpath", "screen", "pageid", "menuid"])
    in_params_lower = {k.lower() for k in in_query.keys()}
    has_deeplink_param = bool(in_params_lower & _DEEPLINK_PARAMS)

    if not has_deeplink_param:
        # deep-link 파라미터가 없는 경우 path 변경으로만 판단
        if in_path != fin_path:
            return True
        return False

    # deep-link 파라미터가 있는 경우:
    # 1. 해당 파라미터 값이 변경된 경우 → 차단
    # 2. 해당 파라미터가 사라진 경우 → 차단
    for param_lower in _DEEPLINK_PARAMS:
        # 원본에 있는 파라미터를 case-insensitive로 탐색
        in_val = None
        for k, v in in_query.items():
            if k.lower() == param_lower:
                in_val = v
                break

        if in_val is None:
            continue

        # 최종 URL에서 같은 파라미터 탐색
        fin_val = None
        for k, v in fin_query.items():
            if k.lower() == param_lower:
                fin_val = v
                break

        # 파라미터가 사라지거나 값이 변경되면 차단
        if fin_val is None or in_val != fin_val:
            return True

    return False
