#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""browser_manager.py - Playwright 브라우저 라이프사이클 관리.

headless Chromium을 실행하고 세션을 재사용한다.
stealth 패치를 적용하고 shared profile을 사용한다.

사용법:
    from browser_manager import launch_browser, get_shared_profile_path

    context = launch_browser(headless=True)
    page = context.new_page()
    # ... 작업 ...
    navigate_to_blank(page)  # 메모리 해제
    # context는 닫지 않음 (세션 재사용)
"""
from __future__ import annotations

import logging
from pathlib import Path

# Playwright 바이너리 영속성 보장 (모듈 import 시 즉시 호출)
from itda_path import ensure_playwright_env

ensure_playwright_env()

from playwright.sync_api import BrowserContext  # type: ignore[import]
from stealth import apply_stealth  # noqa: F401 (shared module symlink)


# 전역 context 인스턴스 (세션 재사용)
_context: BrowserContext | None = None
_pw = None


def get_shared_profile_path(profile_name: str = "default") -> Path:
    """공유 프로필 경로를 반환한다.

    Args:
        profile_name: 프로필 이름 (기본값: "default").

    Returns:
        프로필 디렉토리의 절대 경로.
    """
    from itda_path import resolve_data_dir
    return resolve_data_dir("browser", "profiles") / profile_name


# @MX:ANCHOR: [AUTO] Shared browser session factory — called by search_places, instant_search, collect_reviews (fan_in=3)
# @MX:REASON: Single persistent context for session reuse; each caller depends on this as the sole Playwright entry point
def launch_browser(
    headless: bool = True,
    profile_name: str = "default",
) -> BrowserContext:
    """Playwright 브라우저 context를 실행하고 반환한다.

    이미 실행 중인 context가 있으면 재사용한다.

    Args:
        headless: True이면 headless 모드.
        profile_name: 사용할 프로필 이름.

    Returns:
        BrowserContext 객체.
    """
    global _context

    if _context is not None:
        # 기존 세션 재사용
        return _context

    # 새 브라우저 실행 (persistent context)
    pw_dir = get_shared_profile_path(profile_name)
    pw_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    global _pw
    _pw = sync_playwright().start()
    _context = _pw.chromium.launch_persistent_context(
        user_data_dir=str(pw_dir),
        headless=headless,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
    )

    # stealth 패치 적용
    apply_stealth(_context)

    return _context


# @MX:ANCHOR: [AUTO] Page memory release contract — called by search_places, instant_search, collect_reviews (fan_in=3)
# @MX:REASON: Shared cleanup contract; all callers must call this before page.close() to free DOM memory
def navigate_to_blank(page) -> None:
    """페이지를 about:blank로 이동하여 메모리를 해제한다.

    Args:
        page: Playwright Page 객체.
    """
    page.goto("about:blank")


def close_browser() -> None:
    """브라우저를 닫는다."""
    global _context, _pw

    if _context is not None:
        try:
            _context.close()
        except Exception as e:
            logging.debug("Failed to close browser context: %s", e)
        _context = None

    if _pw is not None:
        try:
            _pw.stop()
        except Exception as e:
            logging.debug("Failed to stop Playwright: %s", e)
        _pw = None
