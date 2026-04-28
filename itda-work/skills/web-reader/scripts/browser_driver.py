#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
browser_driver.py - Playwright Page를 감싼 재사용 가능한 동기 드라이버.

SPEC: SPEC-WEBREADER-MULTISTEP-001 (v1.1)
"""
from __future__ import annotations

import importlib.util
import os as _os
import re
import sys
import types

_scripts_dir = _os.path.dirname(_os.path.abspath(__file__))


class BrowserDriverError(Exception):
    """드라이버 단계 실패 시 발생하는 구조화된 예외.

    Attributes:
        stage: 실패가 발생한 드라이버 메서드 이름 (goto, fill, click 등).
        selector: 관련 CSS selector (없으면 None).
        cause: 원인 예외 객체 (없으면 None).
    """

    def __init__(
        self,
        stage: str,
        *,
        selector: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.stage = stage
        self.selector = selector
        self.cause = cause
        super().__init__(str(self))

    def __str__(self) -> str:
        msg = f"브라우저 드라이버 오류 — 단계: {self.stage!r}"
        if self.selector is not None:
            msg += f", selector: {self.selector!r}"
        if self.cause is not None:
            msg += f", 원인: {self.cause}"
        return msg


def _load_local_module(module_name: str) -> types.ModuleType:
    """scripts/ 디렉토리에서 모듈을 importlib로 로드한다.

    fetch_dynamic.py의 _load_local_module과 동일한 패턴으로 구현.
    stdlib 섀도잉 방지 및 shared/ fallback을 포함한다.
    """
    filepath = _os.path.join(_scripts_dir, f"{module_name}.py")
    if not _os.path.isfile(filepath):
        _shared_dir = _os.path.normpath(
            _os.path.join(
                _scripts_dir, _os.pardir, _os.pardir, _os.pardir, _os.pardir, "shared"
            )
        )
        _shared_path = _os.path.join(_shared_dir, f"{module_name}.py")
        if _os.path.isfile(_shared_path):
            filepath = _shared_path

    if module_name in sys.modules:
        cached = sys.modules[module_name]
        cached_file = getattr(cached, "__file__", None)
        if cached_file is not None:
            try:
                abs_cached = _os.path.abspath(cached_file)
                if abs_cached.startswith(_scripts_dir + _os.sep):
                    return cached
                _shared_dir_abs = _os.path.normpath(
                    _os.path.join(
                        _scripts_dir, _os.pardir, _os.pardir, _os.pardir, _os.pardir, "shared"
                    )
                )
                if abs_cached.startswith(_os.path.abspath(_shared_dir_abs) + _os.sep):
                    return cached
            except (TypeError, ValueError):
                pass

    spec = importlib.util.spec_from_file_location(module_name, filepath)
    assert spec is not None and spec.loader is not None, f"Cannot load {filepath}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _get_url_validator() -> types.ModuleType:
    """url_validator 모듈을 반환한다."""
    return _load_local_module("url_validator")


# @MX:ANCHOR: [AUTO] BrowserDriver — primary hook-script API, fan_in >= 3 (fetch_dynamic.py, hook scripts, tests)
# @MX:REASON: Public boundary for all multi-step browser automation; changing the method signatures or error contract breaks all hook scripts.
# @MX:SPEC: SPEC-WEBREADER-MULTISTEP-001 v1.1 FR-DR
class BrowserDriver:
    """sync_playwright Page를 얇게 감싼 재사용 가능한 동기 드라이버.

    모든 메서드는 동기(sync) 방식으로 내부에서 Playwright Page를 위임 호출한다.
    SSRF 보안 검증이 goto()에 내장되어 있다.
    """

    def __init__(self, page: object, *, allow_private: bool = False) -> None:
        """드라이버를 초기화한다.

        Args:
            page: Playwright sync_playwright Page 객체.
            allow_private: True이면 private/loopback IP 허용. 기본 False.
        """
        self._page = page
        self._allow_private = allow_private

    def current_url(self) -> str:
        """현재 페이지 URL을 반환한다.

        Returns:
            현재 페이지 URL 문자열.
        """
        return self._page.url  # type: ignore[union-attr]

    def goto(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 30000,
    ) -> None:
        """지정된 URL로 이동한다.

        SSRF 방지 URL 검증을 수행한 후 Playwright page.goto()를 호출한다.

        Args:
            url: 이동할 URL.
            wait_until: Playwright wait_until 전략. 기본 "domcontentloaded".
            timeout_ms: 타임아웃 (밀리초). 기본 30000.

        Raises:
            SSRFError: SSRF-unsafe URL (allow_private=False인데 private IP).
            BrowserDriverError: Playwright 예외 발생 시 (stage="goto").
        """
        uv = _get_url_validator()
        uv.validate_url(url, allow_private=self._allow_private)

        try:
            self._page.goto(url, wait_until=wait_until, timeout=timeout_ms)  # type: ignore[union-attr]
        except Exception as exc:
            raise BrowserDriverError(stage="goto", selector=None, cause=exc) from exc

    def fill(
        self,
        selector: str,
        value: str,
        *,
        timeout_ms: int = 10000,
    ) -> None:
        """지정된 selector의 입력 필드에 값을 입력한다.

        Args:
            selector: CSS selector.
            value: 입력할 문자열.
            timeout_ms: 타임아웃 (밀리초). 기본 10000.

        Raises:
            BrowserDriverError: Playwright 예외 발생 시 (stage="fill").
        """
        try:
            self._page.fill(selector, value, timeout=timeout_ms)  # type: ignore[union-attr]
        except Exception as exc:
            raise BrowserDriverError(stage="fill", selector=selector, cause=exc) from exc

    def click(
        self,
        selector: str,
        *,
        timeout_ms: int = 10000,
    ) -> None:
        """지정된 selector를 클릭한다.

        Args:
            selector: CSS selector.
            timeout_ms: 타임아웃 (밀리초). 기본 10000.

        Raises:
            BrowserDriverError: Playwright 예외 발생 시 (stage="click").
        """
        try:
            self._page.click(selector, timeout=timeout_ms)  # type: ignore[union-attr]
        except Exception as exc:
            raise BrowserDriverError(stage="click", selector=selector, cause=exc) from exc

    def press(
        self,
        selector: str,
        key: str,
        *,
        timeout_ms: int = 10000,
    ) -> None:
        """지정된 selector에서 키를 누른다.

        Args:
            selector: CSS selector.
            key: 누를 키 이름 (예: "Enter", "Tab").
            timeout_ms: 타임아웃 (밀리초). 기본 10000.

        Raises:
            BrowserDriverError: Playwright 예외 발생 시 (stage="press").
        """
        try:
            self._page.press(selector, key, timeout=timeout_ms)  # type: ignore[union-attr]
        except Exception as exc:
            raise BrowserDriverError(stage="press", selector=selector, cause=exc) from exc

    def select_option(
        self,
        selector: str,
        value: object,
        *,
        timeout_ms: int = 10000,
    ) -> None:
        """지정된 selector의 <select> 요소에서 옵션을 선택한다.

        Args:
            selector: CSS selector.
            value: 선택할 옵션 값.
            timeout_ms: 타임아웃 (밀리초). 기본 10000.

        Raises:
            BrowserDriverError: Playwright 예외 발생 시 (stage="select_option").
        """
        try:
            self._page.select_option(selector, value, timeout=timeout_ms)  # type: ignore[union-attr]
        except Exception as exc:
            raise BrowserDriverError(
                stage="select_option", selector=selector, cause=exc
            ) from exc

    def wait_for_url(
        self,
        pattern: str | re.Pattern,  # type: ignore[type-arg]
        *,
        timeout_ms: int = 30000,
    ) -> None:
        """URL이 지정된 패턴과 일치할 때까지 대기한다.

        Args:
            pattern: URL 패턴 (문자열 또는 정규식).
            timeout_ms: 타임아웃 (밀리초). 기본 30000.

        Raises:
            BrowserDriverError: Playwright 예외 발생 시 (stage="wait_for_url").
        """
        try:
            self._page.wait_for_url(pattern, timeout=timeout_ms)  # type: ignore[union-attr]
        except Exception as exc:
            raise BrowserDriverError(
                stage="wait_for_url", selector=None, cause=exc
            ) from exc

    def wait_for_load_state(
        self,
        state: str = "networkidle",
        *,
        timeout_ms: int = 30000,
    ) -> None:
        """페이지의 로드 상태가 지정된 상태가 될 때까지 대기한다.

        Args:
            state: 대기할 로드 상태. 기본 "networkidle".
            timeout_ms: 타임아웃 (밀리초). 기본 30000.

        Raises:
            BrowserDriverError: Playwright 예외 발생 시 (stage="wait_for_load_state").
        """
        try:
            self._page.wait_for_load_state(state, timeout=timeout_ms)  # type: ignore[union-attr]
        except Exception as exc:
            raise BrowserDriverError(
                stage="wait_for_load_state", selector=None, cause=exc
            ) from exc

    def evaluate(self, js: str, arg: object = None) -> object:
        """JavaScript 표현식을 실행하고 결과를 반환한다.

        Args:
            js: 실행할 JavaScript 표현식.
            arg: JavaScript에 전달할 인자 (없으면 None).

        Returns:
            JavaScript 실행 결과.
        """
        if arg is not None:
            return self._page.evaluate(js, arg)  # type: ignore[union-attr]
        return self._page.evaluate(js)  # type: ignore[union-attr]

    def extract_html(self, *, selector: str | None = None, all_matches: bool = False) -> str:
        """현재 페이지 또는 특정 selector의 HTML을 반환한다.

        Args:
            selector: CSS selector. None이면 전체 페이지 HTML 반환.
            all_matches: True이면 querySelectorAll로 모든 매칭 요소의 outerHTML을
                         개행으로 결합하여 반환한다. False(기본)이면 querySelector로
                         첫 번째 매칭 요소만 반환한다 (하위 호환 유지).

        Returns:
            HTML 문자열.

        Raises:
            BrowserDriverError: selector가 지정됐지만 찾을 수 없을 때
                                 (stage="extract_html").
        """
        if selector is None:
            return self._page.content()  # type: ignore[union-attr]

        if all_matches:
            # ISS-SEMANTIC-ASYMMETRY: extract_content.py의 soup.select()와 동일하게
            # 모든 매칭 요소 outerHTML을 결합한다.
            result = self._page.evaluate(  # type: ignore[union-attr]
                """selector => {
                    const els = document.querySelectorAll(selector);
                    if (els.length === 0) return null;
                    return Array.from(els).map(el => el.outerHTML).join('\\n');
                }""",
                selector,
            )
        else:
            result = self._page.evaluate(  # type: ignore[union-attr]
                "selector => { const el = document.querySelector(selector); "
                "return el ? el.outerHTML : null; }",
                selector,
            )
        if result is None:
            raise BrowserDriverError(
                stage="extract_html", selector=selector, cause=None
            )
        return str(result)
