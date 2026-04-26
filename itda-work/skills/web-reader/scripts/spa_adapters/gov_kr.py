#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gov_kr 어댑터 — 정부24 보도자료 (1차 지원).

정부24는 자체 SPA 프레임워크 사용 (WebSquare/Nexacro 아님).
deep-link 차단 우회 전략:
  메인 페이지(gov.kr/) 진입 → 메뉴 클릭 → 캡처 응답 수집

# @MX:WARN: [AUTO] GovKrAdapter — 실측 미진행 어댑터. 현장 검증 후 사용 권장.
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ADAPT-01; 정부24는 research.md에 미수록.
#             셀렉터 및 capture_pattern이 TODO 상태. 사이트 직접 검증 후 수정 필요.
"""
from __future__ import annotations

from typing import Any

from spa_adapters.base import Adapter, ClickStep, PageDef, GITHUB_ISSUE_URL

# @MX:ANCHOR: [AUTO] GovKrAdapter — 정부24 커스텀 SPA 어댑터
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ADAPT-01; fetch_dynamic.py --adapter gov_kr,
#             list_adapters.py, 테스트에서 모두 참조 (fan_in >= 3).


class GovKrAdapter(Adapter):
    """정부24 자체 SPA 어댑터.

    1차 지원: 보도자료(press) 화면.
    framework = "custom" (정부24는 WebSquare/Nexacro 외 자체 SPA 사용).

    # @MX:WARN: [AUTO] 셀렉터가 TODO 상태 — 현장 검증 전 사용 주의
    # @MX:REASON: [AUTO] 정부24 실측 미진행. 아래 셀렉터는 placeholder이며
    #             실제 사이트 접속 후 DevTools로 확인 후 교체해야 함.
    """

    domain_pattern: str = r"^(www\.)?gov\.kr$"
    framework: str = "custom"

    pages: dict[str, PageDef] = {
        "press": PageDef(
            entry_url="https://www.gov.kr/",
            steps=[
                # TODO: research 필요 — 정부24 보도자료 메뉴 셀렉터 미확인
                # DevTools로 정부24 보도자료 메뉴 앵커 확인 후 교체할 것
                ClickStep(selector="#TODO_GOVKR_PRESS_SELECTOR", wait_after_ms=5000),
            ],
            # TODO: research 필요 — 정부24 보도자료 API endpoint 미확인
            capture_pattern=r"TODO_GOVKR_PRESS_API_PATTERN",
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
            NotImplementedError: 정부24 어댑터는 셀렉터 실측 전 미완성.
            AdapterEntryError: 미정의 page_key 시
        """
        # 미완성 어댑터 — 실측 전 사용 불가 (ISS-PLACEHOLDER-005)
        raise NotImplementedError(
            f"정부24 어댑터는 셀렉터 실측 전입니다. "
            f"SPEC-WEBREADER-006 1차 범위 외. "
            f"현장 검증 후 셀렉터를 교체해 주세요. 신고: {GITHUB_ISSUE_URL}"
        )

    def extract(self, driver: Any, captures: list[dict[str, Any]]) -> dict[str, Any]:
        """캡처 데이터에서 field_mapping 기반으로 정규화된 아이템을 추출한다.

        인자:
            driver: BrowserDriver 인스턴스 (현재 미사용)
            captures: 캡처된 네트워크 응답 목록

        예외:
            NotImplementedError: 정부24 어댑터는 셀렉터 실측 전 미완성.
        """
        # 미완성 어댑터 — 실측 전 사용 불가 (ISS-PLACEHOLDER-005)
        raise NotImplementedError(
            f"정부24 어댑터는 셀렉터 실측 전입니다. "
            f"SPEC-WEBREADER-006 1차 범위 외. "
            f"현장 검증 후 셀렉터를 교체해 주세요. 신고: {GITHUB_ISSUE_URL}"
        )
