#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hometax 어댑터 — 국세청 홈택스 공지사항 (research.md 실측 데이터 기반).

WebSquare5 SPA의 deep-link 차단 우회 전략:
  메인 페이지(hometax.go.kr/) 진입 → 공지사항 메뉴 클릭 → 캡처 응답 수집

# @MX:ANCHOR: [AUTO] HometaxAdapter — WebSquare5 첫 어댑터 구현 (레퍼런스 패턴)
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ADAPT-01; 후속 어댑터(wetax, gov_kr)의
#             패턴 레퍼런스. entry/extract 시그니처 변경 시 전체 어댑터에 영향.
"""
from __future__ import annotations

from typing import Any

from spa_adapters.base import Adapter, AdapterEntryError, ClickStep, PageDef, run_entry_steps  # noqa: F401

# @MX:NOTE: [AUTO] 홈택스 공지사항 셀렉터 (research.md Phase D 실측)
# @MX:REASON: [AUTO] #mf_txppWframe_grpAnnc1은 실측으로 확인된 공지사항 메뉴 앵커.
#             사이트 개편 시 이 셀렉터가 변경될 수 있음. 변경 시 이 파일을 수정할 것.


# @MX:WARN: [AUTO] entry()의 click 타임아웃 및 사이트 개편 리스크
# @MX:REASON: [AUTO] 홈택스 WebSquare5는 메뉴 클릭 후 8초 이상 대기가 필요.
#             타임아웃이 너무 짧으면 셀렉터 미발견 오류. 사이트 개편 시 셀렉터 변경 필요.
class HometaxAdapter(Adapter):
    """국세청 홈택스 WebSquare5 SPA 어댑터.

    공지사항(notice) 화면에 대한 entry → 캡처 → 추출 흐름을 구현한다.
    """

    domain_pattern: str = r"^(www\.)?hometax\.go\.kr$"
    framework: str = "websquare5"

    # @MX:NOTE: [AUTO] pages['notice'].capture_pattern = wqAction.do.*ATXPPBAA001R01
    #           (research.md Phase E 실측 endpoint)
    pages: dict[str, PageDef] = {
        "notice": PageDef(
            entry_url="https://hometax.go.kr/",
            steps=[
                # research.md Phase D: #mf_txppWframe_grpAnnc1 클릭 후 8초 대기
                ClickStep(selector="#mf_txppWframe_grpAnnc1", wait_after_ms=8000),
            ],
            capture_pattern=r"wqAction\.do.*ATXPPBAA001R01",
            field_mapping={
                "title": "tbbsTtl",
                "body": "tbbsCntn",
                "date": "bltnStrtDt",
                "author": "wrtrNm",
                "views": "tbbsInqrCnt",
                "id": "tbbsSn",
                "video_url": "moviUrl",
            },
            list_field="anncMttrInqrList",
        ),
    }

    # @MX:ANCHOR: [AUTO] HometaxAdapter.entry — entry 흐름 단일 진입점
    # @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ENTRY-01; fetch_dynamic.py --adapter,
    #             통합 테스트, 재사용 어댑터 패턴이 모두 이 메서드를 호출 (fan_in >= 3).
    def entry(self, driver: Any, page_key: str) -> None:
        """메인 진입 → 메뉴 클릭 → 목표 화면 도달까지 수행한다.

        인자:
            driver: BrowserDriver 인스턴스
            page_key: pages dict의 키 (화면명)

        예외:
            KeyError: 미정의 page_key
            AdapterEntryError: 진입 단계(goto/click) 실패 시. 한국어 진단 메시지
                               와 GitHub issue URL을 포함한다.
        """
        # page_key 검증 — 미정의 시 KeyError 발생 (명확한 오류)
        page = self.pages[page_key]

        # 공통 헬퍼로 goto + step 시퀀스 실행
        run_entry_steps(driver, page)

    # @MX:ANCHOR: [AUTO] HometaxAdapter.extract — 캡처 데이터 정규화 단일 진입점
    # @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-CAPTURE-04; extract_content.py
    #             --from-capture와 직접 API 호출 모두 이 메서드를 거침 (fan_in >= 3).
    def extract(self, driver: Any, captures: list[dict[str, Any]]) -> dict[str, Any]:
        """캡처 데이터에서 field_mapping 기반으로 정규화된 아이템을 추출한다.

        인자:
            driver: BrowserDriver 인스턴스 (현재 미사용, 향후 확장용)
            captures: 캡처된 네트워크 응답 목록. 각 항목은
                      {"url":..., "status":..., "body": {...}} 형태.

        반환:
            {"items": [...], "page_key": "notice"}
            items의 각 dict는 field_mapping 역방향 키(title, date, 등)로 구성됨.
        """
        page = self.pages.get("notice")
        if page is None:
            return {"items": [], "page_key": "notice"}

        field_mapping = page.field_mapping  # src key → normalized key (역방향 적용)
        list_field = page.list_field or ""

        # field_mapping 역방향 생성: 원본 API 키 → 정규화 키
        reverse_map = {v: k for k, v in field_mapping.items()}

        all_items: list[dict[str, Any]] = []

        for capture in captures:
            body = capture.get("body")
            if not isinstance(body, dict):
                continue

            raw_list = body.get(list_field, [])
            if not isinstance(raw_list, list):
                continue

            for raw_item in raw_list:
                if not isinstance(raw_item, dict):
                    continue
                # 역방향 매핑 적용
                normalized: dict[str, Any] = {}
                for api_key, value in raw_item.items():
                    norm_key = reverse_map.get(api_key, api_key)
                    normalized[norm_key] = value
                all_items.append(normalized)

        return {"items": all_items, "page_key": "notice"}
