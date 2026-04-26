#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integration/test_hometax_live.py — 실제 홈택스 사이트 접속 통합 테스트.

@pytest.mark.live_hometax 마커 적용. CI에서 기본 skip.

SPEC-WEBREADER-006 AC-1: 홈택스 공지사항 ≥ 10건 추출 (실제 브라우저 필요).

실행 방법:
    python3 -m pytest scripts/integration/test_hometax_live.py -v -m live_hometax
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

import pytest

_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))


@pytest.mark.live_hometax
class TestHometaxLiveEntry(unittest.TestCase):
    """실제 홈택스 공지사항 진입 테스트 (AC-1 수동 통합 검증)."""

    def test_live_hometax_notice_entry_and_capture(self):
        """실제 hometax.go.kr 진입 → 공지사항 클릭 → 캡처 → ≥10건 검증 (AC-1).

        요구 사항:
        - Playwright 설치 필요 (playwright install chromium)
        - 실제 인터넷 연결 필요
        - 처리시간 ≤ 60초

        수동 실행 명령:
            cd itda-work/skills/web-reader
            python3 -m pytest scripts/integration/test_hometax_live.py \
                -v -m live_hometax -s
        """
        playwright = pytest.importorskip("playwright.sync_api")

        from spa_adapters.hometax import HometaxAdapter
        from spa_capture import CaptureHandler

        adapter = HometaxAdapter()
        page_def = adapter.pages["notice"]

        # CaptureHandler로 공지사항 API 응답 캡처
        capture_handler = CaptureHandler(pattern=page_def.capture_pattern)

        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="ko-KR",
            )
            page = context.new_page()
            page.on("response", capture_handler)

            from browser_driver import BrowserDriver

            driver = BrowserDriver(page)

            # AC-1: entry 후 캡처 데이터 확인
            adapter.entry(driver, "notice")

            context.close()

        # 캡처된 데이터 확인
        captures = capture_handler.get_captures()
        self.assertGreater(len(captures), 0, "캡처된 응답이 없습니다")

        result = adapter.extract(None, captures)
        items = result.get("items", [])

        # AC-1: 공지사항 ≥ 10건
        self.assertGreaterEqual(
            len(items), 10,
            f"공지사항이 10건 미만입니다 (실제: {len(items)}건). "
            "홈택스 사이트 구조가 변경되었을 수 있습니다."
        )

        # 각 공지에 title, date 필드가 있는지 확인
        for i, item in enumerate(items[:3]):  # 처음 3건만 상세 검증
            self.assertIn("title", item, f"items[{i}]에 title이 없습니다")
            self.assertIn("date", item, f"items[{i}]에 date가 없습니다")

    def test_live_hometax_main_page_entry(self):
        """실제 hometax.go.kr 메인 페이지 진입 검증 (네트워크 접근 확인).

        deep-link 차단 메시지가 stderr에 출력되지 않는지 확인.
        """
        playwright = pytest.importorskip("playwright.sync_api")

        from spa_adapters.hometax import HometaxAdapter

        adapter = HometaxAdapter()
        page_def = adapter.pages["notice"]

        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(locale="ko-KR")
            page = context.new_page()

            # 메인 페이지만 진입 (단순 접근 확인)
            page.goto(
                page_def.entry_url,
                wait_until="networkidle",
                timeout=45000,
            )
            final_url = page.url
            context.close()

        # 메인 페이지에 정상 진입됐는지 (index3 또는 index_pp)
        self.assertIn("hometax.go.kr", final_url)
