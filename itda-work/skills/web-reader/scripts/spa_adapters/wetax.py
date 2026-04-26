#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wetax 어댑터 — 위택스(지방세 포털) 공지사항·자료실 (1차 지원).

WebSquare5 SPA의 deep-link 차단 우회 전략:
  메인 페이지(wetax.go.kr/) 진입 → 메뉴 클릭 → 캡처 응답 수집

# @MX:WARN: [AUTO] WetaxAdapter — 실측 미진행 어댑터. 현장 검증 후 사용 권장.
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ADAPT-01; 위택스는 research.md에 미수록.
#             셀렉터 및 capture_pattern이 TODO 상태. 사이트 직접 검증 후 수정 필요.
"""
from __future__ import annotations

from typing import Any

from spa_adapters.base import Adapter, ClickStep, PageDef, GITHUB_ISSUE_URL

# @MX:ANCHOR: [AUTO] WetaxAdapter — 위택스 WebSquare5 어댑터
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ADAPT-01; fetch_dynamic.py --adapter wetax,
#             list_adapters.py, 테스트에서 모두 참조 (fan_in >= 3).


class WetaxAdapter(Adapter):
    """위택스(지방세 포털) WebSquare5 SPA 어댑터.

    1차 지원: 공지사항(notice), 자료실(data) 화면.

    # @MX:WARN: [AUTO] 셀렉터가 TODO 상태 — 현장 검증 전 사용 주의
    # @MX:REASON: [AUTO] 위택스 실측 미진행. 아래 셀렉터는 placeholder이며
    #             실제 사이트 접속 후 DevTools로 확인 후 교체해야 함.
    """

    domain_pattern: str = r"^(www\.)?wetax\.go\.kr$"
    framework: str = "websquare5"

    pages: dict[str, PageDef] = {
        "notice": PageDef(
            entry_url="https://www.wetax.go.kr/",
            steps=[
                # TODO: research 필요 — 위택스 공지사항 메뉴 셀렉터 미확인
                # DevTools로 위택스 공지사항 메뉴 앵커 확인 후 교체할 것
                ClickStep(selector="#TODO_WETAX_NOTICE_SELECTOR", wait_after_ms=5000),
            ],
            # TODO: research 필요 — 위택스 공지사항 API endpoint 미확인
            capture_pattern=r"TODO_WETAX_NOTICE_API_PATTERN",
            field_mapping={},
            list_field=None,
        ),
        "data": PageDef(
            entry_url="https://www.wetax.go.kr/",
            steps=[
                # TODO: research 필요 — 위택스 자료실 메뉴 셀렉터 미확인
                ClickStep(selector="#TODO_WETAX_DATA_SELECTOR", wait_after_ms=5000),
            ],
            # TODO: research 필요 — 위택스 자료실 API endpoint 미확인
            capture_pattern=r"TODO_WETAX_DATA_API_PATTERN",
            field_mapping={},
            list_field=None,
        ),
    }

    def entry(self, driver: Any, page_key: str) -> None:
        """메인 진입 → 메뉴 클릭 → 목표 화면 도달까지 수행한다.

        인자:
            driver: BrowserDriver 인스턴스
            page_key: pages dict의 키 (화면명)

        예외:
            NotImplementedError: 위택스 어댑터는 셀렉터 실측 전 미완성.
            AdapterEntryError: 미정의 page_key 시
        """
        # 미완성 어댑터 — 실측 전 사용 불가 (ISS-PLACEHOLDER-005)
        raise NotImplementedError(
            f"위택스 어댑터는 셀렉터 실측 전입니다. "
            f"SPEC-WEBREADER-006 1차 범위 외. "
            f"현장 검증 후 셀렉터를 교체해 주세요. 신고: {GITHUB_ISSUE_URL}"
        )

    def extract(self, driver: Any, captures: list[dict[str, Any]]) -> dict[str, Any]:
        """캡처 데이터에서 field_mapping 기반으로 정규화된 아이템을 추출한다.

        인자:
            driver: BrowserDriver 인스턴스 (현재 미사용)
            captures: 캡처된 네트워크 응답 목록

        예외:
            NotImplementedError: 위택스 어댑터는 셀렉터 실측 전 미완성.
        """
        # 미완성 어댑터 — 실측 전 사용 불가 (ISS-PLACEHOLDER-005)
        raise NotImplementedError(
            f"위택스 어댑터는 셀렉터 실측 전입니다. "
            f"SPEC-WEBREADER-006 1차 범위 외. "
            f"현장 검증 후 셀렉터를 교체해 주세요. 신고: {GITHUB_ISSUE_URL}"
        )
