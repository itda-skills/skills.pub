#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPA 어댑터 베이스 클래스 및 공용 데이터클래스.
SPEC-WEBREADER-006: FR-ADAPT-01 어댑터 인터페이스 정의.
Python 3.10 문법 기준.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

# @MX:ANCHOR: [AUTO] Adapter — 모든 SPA 어댑터의 공통 베이스 클래스
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ADAPT-01; hometax, wetax, gov_kr 등
#             모든 어댑터가 상속하므로 fan_in >= 3 확정. 인터페이스 시그니처 변경 시
#             전체 어댑터 재검토 필요.

# @MX:ANCHOR: [AUTO] AdapterEntryError — 모든 어댑터의 공통 예외 클래스
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 FR-ADAPT-03; hometax/wetax/gov_kr/fetch_dynamic
#             등 모든 어댑터 및 CLI 분기에서 참조 (fan_in >= 3).
#             이 클래스를 변경하면 전체 어댑터에 영향.

# GitHub issue URL — entry 실패 시 사용자 안내용 (FR-ADAPT-03)
GITHUB_ISSUE_URL = (
    "https://github.com/allieuslee/itda-skills/issues/new"
    "?title=adapter+entry+failure"
)

__all__ = ["ClickStep", "PageDef", "Step", "Adapter", "AdapterEntryError", "run_entry_steps"]


class AdapterEntryError(Exception):
    """어댑터 entry() 단계 실패 시 발생하는 구조화된 예외.

    속성:
        stage: 실패 단계 이름 ("goto", "click", "wait" 등)
        selector: 실패한 CSS 셀렉터 (없으면 None)
        final_url: 실패 시점의 현재 URL (없으면 None)
        cause: 원인 예외 객체 (없으면 None)
        github_issue_url: 사용자에게 안내할 GitHub issue URL
    """

    def __init__(
        self,
        stage: str,
        *,
        selector: str | None = None,
        final_url: str | None = None,
        cause: BaseException | None = None,
        message: str | None = None,
    ) -> None:
        self.stage = stage
        self.selector = selector
        self.final_url = final_url
        self.cause = cause
        self.github_issue_url = GITHUB_ISSUE_URL
        self._custom_message = message
        super().__init__(str(self))

    def __str__(self) -> str:
        # 사용자 지정 메시지가 있으면 우선 사용
        if self._custom_message is not None:
            return (
                f"{self._custom_message}\n\n"
                f"이 문제가 반복되면 아래 링크에서 신고해 주세요:\n{self.github_issue_url}"
            )

        msg = f"어댑터 진입 실패 — 단계: {self.stage!r}"
        if self.selector is not None:
            msg += f", 셀렉터: {self.selector!r}"
        if self.final_url is not None:
            msg += f"\n현재 URL: {self.final_url}"
        if self.cause is not None:
            msg += f"\n원인: {self.cause}"
        msg += (
            f"\n\n이 문제가 반복되면 아래 링크에서 신고해 주세요:\n{self.github_issue_url}"
        )
        return msg


@dataclass
class ClickStep:
    """
    클릭 액션 정의 — 셀렉터 클릭 후 지정된 밀리초 대기.

    속성:
        selector: CSS 셀렉터 문자열
        wait_after_ms: 클릭 후 대기 시간 (ms). 기본값 0.
    """
    selector: str
    wait_after_ms: int = 0


# Sprint 1에서는 ClickStep만 정의. 추후 확장 가능한 union 타입.
# @MX:NOTE: [AUTO] Step 타입은 향후 ScrollStep, InputStep 등 추가 예정 (Sprint 2+)
Step = Union[ClickStep]


@dataclass
class PageDef:
    """
    어댑터의 단일 화면(page) 정의.

    속성:
        entry_url: 진입 URL (메인 페이지 URL)
        steps: 메인 진입 후 수행할 클릭 시퀀스
        capture_pattern: 캡처할 네트워크 응답 URL 정규식 (선택)
        field_mapping: JSON 응답 필드명 → 정규화 필드명 매핑 (선택)
        list_field: JSON 응답에서 목록 데이터를 담는 최상위 키 (선택)
    """
    entry_url: str
    steps: list[Step] = field(default_factory=list)
    capture_pattern: str | None = None
    field_mapping: dict[str, str] = field(default_factory=dict)
    list_field: str | None = None


def _safe_current_url(driver: Any) -> str | None:
    """드라이버에서 현재 URL을 안전하게 읽는다.

    BrowserDriver는 current_url() 메서드, Playwright Page는 .url 속성을 사용한다.
    어느 쪽도 없거나 예외가 발생하면 None을 반환한다.
    """
    try:
        if hasattr(driver, "current_url"):
            method = getattr(driver, "current_url")
            if callable(method):
                return method()
        # Playwright Page 직접 사용 시 .url 속성 fallback
        if hasattr(driver, "url"):
            attr = getattr(driver, "url")
            return attr() if callable(attr) else attr
        return None
    except Exception:
        return None


def run_entry_steps(driver: Any, page: "PageDef", *, sleep_fn: Any = None) -> None:
    """어댑터 entry() 공통 구현 — goto + ClickStep 시퀀스 실행.

    모든 어댑터의 entry() 핵심 로직을 공통화한 헬퍼 함수.
    개별 어댑터에서 직접 호출하여 코드 중복을 줄인다.

    인자:
        driver: BrowserDriver 인스턴스
        page: PageDef (entry_url, steps 포함)
        sleep_fn: 테스트 override용 sleep 함수 (기본 time.sleep)

    예외:
        AdapterEntryError: goto 또는 click 단계 실패 시
    """
    import time as _time

    _sleep = sleep_fn if sleep_fn is not None else _time.sleep

    # 1단계: 메인 페이지 진입
    try:
        driver.goto(page.entry_url, wait_until="networkidle")
    except Exception as exc:
        raise AdapterEntryError(
            stage="goto",
            final_url=_safe_current_url(driver),
            cause=exc,
        ) from exc

    # 2단계: 각 ClickStep 순서대로 실행
    for step in page.steps:
        try:
            driver.click(step.selector)
        except Exception as exc:
            raise AdapterEntryError(
                stage="click",
                selector=step.selector,
                final_url=_safe_current_url(driver),
                cause=exc,
            ) from exc

        # 클릭 후 대기
        if step.wait_after_ms > 0:
            wait_sec = step.wait_after_ms / 1000.0
            try:
                driver.evaluate(
                    f"() => new Promise(r => setTimeout(r, {step.wait_after_ms}))"
                )
            except Exception:
                _sleep(wait_sec)


class Adapter:
    """
    SPA 어댑터 베이스 클래스.

    서브클래스는 domain_pattern, framework, pages 클래스 속성을 정의하고
    entry(), extract() 메서드를 구현해야 한다.

    클래스 속성:
        domain_pattern: 어댑터가 담당하는 도메인 정규식
        framework: SPA 프레임워크 식별자 ("websquare5" | "nexacro" | "custom")
        pages: 화면명 → PageDef 매핑

    # @MX:WARN: [AUTO] pages를 클래스 변수로 선언할 경우 서브클래스 간 공유 위험
    # @MX:REASON: [AUTO] Python 클래스 변수는 인스턴스 간 공유됨. 각 서브클래스에서
    #             반드시 pages를 재정의(override)할 것. base.Adapter.pages = {}는
    #             변경하지 않도록 주의.
    """

    domain_pattern: str = ""
    framework: str = ""
    pages: dict[str, PageDef] = {}

    def __init_subclass__(cls, **kwargs: object) -> None:
        """서브클래스가 자체 pages를 정의하지 않으면 빈 dict로 초기화한다.

        클래스 변수 pages의 공유를 방지한다 (ISS-BASEPAGES-010).
        """
        super().__init_subclass__(**kwargs)
        # 서브클래스가 자체적으로 pages를 선언하지 않은 경우 독립 dict 할당
        if "pages" not in cls.__dict__:
            cls.pages = {}

    def entry(self, driver, page_key: str) -> None:
        """
        메인 진입 → 메뉴 클릭 → 목표 화면 도달까지 수행.

        서브클래스에서 반드시 구현해야 한다.

        인자:
            driver: BrowserDriver 인스턴스
            page_key: 어댑터 pages dict의 키 (화면명)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.entry()가 구현되지 않았습니다."
        )

    def extract(self, driver, captures: list[dict]) -> dict:
        """
        페이지/캡처 데이터에서 정규화된 콘텐츠를 추출한다.

        서브클래스에서 반드시 구현해야 한다.

        인자:
            driver: BrowserDriver 인스턴스
            captures: 캡처된 네트워크 응답 목록 (각 항목은 dict)

        반환:
            정규화된 콘텐츠 dict
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.extract()가 구현되지 않았습니다."
        )
