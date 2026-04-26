#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_dynamic.py - Playwright 기반 JS 렌더링 페이지 fetcher.

Playwright Chromium headless 브라우저를 사용해 JavaScript 렌더링 페이지를 가져온다.
Playwright 미설치 시 graceful하게 처리한다.

사용법:
    python3 fetch_dynamic.py --url URL [options]
    py -3 fetch_dynamic.py --url URL [options]  # Windows

종료 코드:
    0 - 성공
    1 - 네비게이션 에러 또는 타임아웃
    2 - 인자 오류 또는 Playwright 미설치
    3 - 프로필 lock 충돌 (다른 프로세스 사용 중)
    4 - --interactive 사용 시 TTY 없음
"""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os as _os
import re
import sys
import types
import traceback

# scripts 디렉토리 경로 (importlib 기반 로딩에 사용)
_scripts_dir = _os.path.dirname(_os.path.abspath(__file__))

import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Playwright TimeoutError — optional import; used for hook error handling.
# May not be importable if playwright is not installed.
try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # type: ignore[import]
except ImportError:
    PlaywrightTimeoutError = None  # type: ignore[assignment,misc]

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 이상이 필요합니다.")

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# Playwright 가용성 확인
# ---------------------------------------------------------------------------


def is_playwright_available() -> bool:
    """playwright 패키지 import 가능 여부를 반환한다.

    Returns:
        True이면 playwright import 가능, False이면 미설치.
    """
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Playwright wrapper (테스트에서 mock 가능)
# ---------------------------------------------------------------------------


def sync_playwright():  # type: ignore[return]
    """sync_playwright context manager를 반환한다. 테스트에서 mock 가능."""
    # Playwright 바이너리 영속성 보장 (Cowork 환경)
    from itda_path import ensure_playwright_env
    ensure_playwright_env()
    from playwright.sync_api import sync_playwright as _sp  # type: ignore[import]
    return _sp()


# ---------------------------------------------------------------------------
# Lazy import 헬퍼 (테스트에서 mock 가능)
# ---------------------------------------------------------------------------


def _load_local_module(module_name: str) -> types.ModuleType:
    """scripts/ 디렉토리에서 모듈을 importlib로 로드한다.

    stdlib 모듈 섀도잉을 방지하기 위해 sys.path 조작 없이
    파일 경로 기반으로 직접 로드한다.

    sys.modules 캐시에 있는 모듈이 scripts/ 디렉토리 외부에서 온 경우
    (import hijacking 방어) 무시하고 파일 경로 기반으로 재로드한다.

    빌드 시 shared/*.py가 scripts/에 주입되지만, 개발 환경에서는
    shared/ 디렉토리를 fallback으로 탐색한다.

    Args:
        module_name: 로드할 모듈의 파일명 (확장자 제외).

    Returns:
        로드된 모듈 객체.
    """
    filepath = _os.path.join(_scripts_dir, f"{module_name}.py")
    # 개발 환경 fallback: scripts/에 없으면 shared/ 탐색
    if not _os.path.isfile(filepath):
        _shared_dir = _os.path.normpath(
            _os.path.join(_scripts_dir, _os.pardir, _os.pardir, _os.pardir,
                          _os.pardir, "shared")
        )
        _shared_path = _os.path.join(_shared_dir, f"{module_name}.py")
        if _os.path.isfile(_shared_path):
            filepath = _shared_path
    if module_name in sys.modules:
        cached = sys.modules[module_name]
        cached_file = getattr(cached, "__file__", None)
        # __file__이 scripts/ 디렉토리 또는 shared/ 디렉토리 내부이면 캐시 사용
        if cached_file is not None:
            try:
                abs_cached = _os.path.abspath(cached_file)
                if abs_cached.startswith(_scripts_dir + _os.sep):
                    return cached
                # shared/ fallback 경로도 신뢰
                _shared_dir_abs = _os.path.normpath(
                    _os.path.join(_scripts_dir, _os.pardir, _os.pardir,
                                  _os.pardir, _os.pardir, "shared")
                )
                if abs_cached.startswith(_os.path.abspath(_shared_dir_abs) + _os.sep):
                    return cached
            except (TypeError, ValueError):
                pass
        # 외부 모듈이거나 __file__ 없음 → 재로드
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    assert spec is not None and spec.loader is not None, f"Cannot load {filepath}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _import_stealth() -> types.ModuleType:
    """stealth 모듈을 importlib 기반으로 lazy load한다."""
    return _load_local_module("stealth")


def _import_profile_manager() -> types.ModuleType:
    """profile_manager 모듈을 importlib 기반으로 lazy load한다."""
    return _load_local_module("profile_manager")


def _get_url_validator() -> types.ModuleType:
    """url_validator 모듈을 반환한다."""
    return _load_local_module("url_validator")


# ---------------------------------------------------------------------------
# 핵심 fetch (기존 ephemeral 방식)
# ---------------------------------------------------------------------------


def fetch_with_js(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    settle_time: float = 3.0,
    wait_until: str = "domcontentloaded",
    headless: bool = True,
    viewport: dict[str, int] | None = None,
    allow_private: bool = False,
    capture_handler: Any = None,
) -> dict[str, object]:
    """headless Chromium으로 URL을 fetch한다.

    Args:
        url: 가져올 대상 URL.
        timeout: 네비게이션 타임아웃 (초). 기본 30.
        user_agent: User-Agent 문자열. 기본 Chrome Desktop.
        settle_time: DOM 로드 후 네트워크 안정화 대기 시간 (초).
                     기본 3.0 (React/Next.js hydration 대기).
        wait_until: page.goto의 wait_until 전략.
                    기본 'domcontentloaded'.
        headless: True이면 headless 모드. 기본 True.
        viewport: 뷰포트 크기 dict (width, height). None이면 기본값 사용.
        allow_private: True이면 private/loopback IP 허용. 기본 False.
        capture_handler: page.on("response") 핸들러. None이면 미등록 (ISS-CAPTURE-023).

    Returns:
        content, url, size 키를 가진 dict.

    Raises:
        Exception: 네비게이션 실패 또는 타임아웃 시.
        SSRFError: SSRF-unsafe URL.
    """
    # SSRF 방지 URL 검증
    uv = _get_url_validator()
    uv.validate_url(url, allow_private=allow_private)

    timeout_ms = timeout * 1000
    settle_ms = int(settle_time * 1000)

    ctx_kwargs: dict[str, object] = {
        "user_agent": user_agent,
        "locale": "ko-KR",
        "extra_http_headers": {
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }
    if viewport:
        ctx_kwargs["viewport"] = viewport

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()
        # --capture-api 핸들러 등록 (ISS-CAPTURE-023: standalone --url + --capture-api 지원)
        if capture_handler is not None:
            page.on("response", capture_handler)
        # wait_until 전략: 기본 domcontentloaded로 long-polling hang 방지
        page.goto(url, timeout=timeout_ms, wait_until=wait_until)
        try:
            page.wait_for_load_state("networkidle", timeout=settle_ms)
        except Exception:
            pass  # 로드된 내용으로 진행
        html = page.content()
        final_url = page.url
        context.close()

    return {
        "content": html,
        "url": final_url,
        "size": len(html.encode("utf-8")),
    }


# ---------------------------------------------------------------------------
# 인터랙티브 모드 헬퍼
# ---------------------------------------------------------------------------


def _wait_for_user_input() -> None:
    """인터랙티브 모드에서 사용자 Enter 입력을 기다린다."""
    print("브라우저에서 작업을 완료한 뒤 Enter를 누르세요...", file=sys.stderr)
    try:
        sys.stdin.readline()
    except EOFError:
        pass


# ---------------------------------------------------------------------------
# 프로필 기반 fetch (persistent context)
# ---------------------------------------------------------------------------


def _fetch_with_profile(
    url: str,
    profile_dir: Path,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    settle_time: float = 3.0,
    wait_until: str = "domcontentloaded",
    use_stealth: bool = True,
    headless: bool = True,
    interactive: bool = False,
    viewport: dict[str, int] | None = None,
    allow_private: bool = False,
) -> dict[str, object]:
    """persistent context로 URL을 fetch한다.

    Args:
        url: 가져올 대상 URL.
        profile_dir: Playwright user_data_dir로 사용할 프로필 디렉토리.
        timeout: 네비게이션 타임아웃 (초).
        user_agent: User-Agent 문자열.
        settle_time: DOM 로드 후 안정화 대기 시간 (초).
        wait_until: page.goto의 wait_until 전략.
        use_stealth: True이면 stealth 패치 적용.
        headless: True이면 headless 모드.
        interactive: True이면 stdin.readline()으로 사용자 Enter 대기.
        viewport: 뷰포트 크기 dict (width, height).
        allow_private: True이면 private/loopback IP 허용. 기본 False.

    Returns:
        content, url, size 키를 가진 dict.
    """
    # SSRF 방지 URL 검증
    uv = _get_url_validator()
    uv.validate_url(url, allow_private=allow_private)

    timeout_ms = timeout * 1000
    settle_ms = int(settle_time * 1000)

    launch_kwargs: dict[str, object] = {
        "headless": headless,
        "user_agent": user_agent,
        "locale": "ko-KR",
        "extra_http_headers": {
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }
    if viewport:
        launch_kwargs["viewport"] = viewport

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            **launch_kwargs,
        )

        if use_stealth:
            stealth_mod = _import_stealth()
            stealth_mod.apply_stealth(context)

        page = context.new_page()
        page.goto(url, timeout=timeout_ms, wait_until=wait_until)
        try:
            page.wait_for_load_state("networkidle", timeout=settle_ms)
        except Exception:
            pass

        if interactive:
            _wait_for_user_input()

        html = page.content()
        final_url = page.url
        context.close()

    return {
        "content": html,
        "url": final_url,
        "size": len(html.encode("utf-8")),
    }


# ---------------------------------------------------------------------------
# ephemeral + stealth/interactive 지원 fetch
# ---------------------------------------------------------------------------


def _fetch_ephemeral_with_options(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    settle_time: float = 3.0,
    wait_until: str = "domcontentloaded",
    use_stealth: bool = False,
    headless: bool = True,
    interactive: bool = False,
    viewport: dict[str, int] | None = None,
    allow_private: bool = False,
    capture_handler: Any = None,
) -> dict[str, object]:
    """stealth/interactive 옵션을 지원하는 ephemeral context fetch.

    Args:
        url: 가져올 대상 URL.
        timeout: 네비게이션 타임아웃 (초).
        user_agent: User-Agent 문자열.
        settle_time: DOM 로드 후 안정화 대기 시간 (초).
        wait_until: page.goto의 wait_until 전략.
        use_stealth: True이면 stealth 패치 적용.
        headless: True이면 headless 모드.
        interactive: True이면 stdin.readline()으로 Enter 대기.
        viewport: 뷰포트 크기 dict.
        allow_private: True이면 private/loopback IP 허용. 기본 False.

    Returns:
        content, url, size 키를 가진 dict.
    """
    # SSRF 방지 URL 검증
    uv = _get_url_validator()
    uv.validate_url(url, allow_private=allow_private)

    timeout_ms = timeout * 1000
    settle_ms = int(settle_time * 1000)

    ctx_kwargs: dict[str, object] = {
        "user_agent": user_agent,
        "locale": "ko-KR",
        "extra_http_headers": {
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }
    if viewport:
        ctx_kwargs["viewport"] = viewport

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(**ctx_kwargs)

        if use_stealth:
            stealth_mod = _import_stealth()
            stealth_mod.apply_stealth(context)

        page = context.new_page()
        # --capture-api 핸들러 등록 (ISS-CAPTURE-023: standalone --url + --capture-api 지원)
        if capture_handler is not None:
            page.on("response", capture_handler)
        page.goto(url, timeout=timeout_ms, wait_until=wait_until)
        try:
            page.wait_for_load_state("networkidle", timeout=settle_ms)
        except Exception:
            pass

        if interactive:
            _wait_for_user_input()

        html = page.content()
        final_url = page.url
        context.close()

    return {
        "content": html,
        "url": final_url,
        "size": len(html.encode("utf-8")),
    }


# ---------------------------------------------------------------------------
# CLI 인수 파싱
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI 인수를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="Playwright Chromium으로 JS 렌더링 웹페이지를 가져온다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", default=None, help="가져올 URL")
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="출력 파일 경로 (기본: stdout)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"네비게이션 타임아웃 (초, 기본: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent 문자열 (기본: Chrome Desktop)",
    )
    parser.add_argument(
        "--settle-time",
        type=float,
        default=3.0,
        dest="settle_time",
        help="DOM 로드 후 네트워크 안정화 대기 시간 (초, 기본: 3.0)",
    )
    parser.add_argument(
        "--wait-until",
        default="domcontentloaded",
        dest="wait_until",
        choices=["load", "domcontentloaded", "networkidle", "commit"],
        help="Playwright wait_until 전략 (기본: domcontentloaded)",
    )
    # SPEC-WEBREADER-004 신규 옵션
    parser.add_argument(
        "--profile",
        default=None,
        metavar="NAME",
        help="브라우저 프로필 이름 (영속 컨텍스트 사용, 자동 stealth 활성화)",
    )
    parser.add_argument(
        "--stealth",
        action="store_true",
        default=False,
        help="안티봇 스텔스 패치 적용",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        default=False,
        help="브라우저 창 표시 (디버깅용, 기본: headless)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=False,
        help="수동 조작 모드 (TTY 필요, --headed 자동 활성화)",
    )
    parser.add_argument(
        "--viewport",
        default="1920x1080",
        metavar="WxH",
        help="브라우저 뷰포트 크기 (기본: 1920x1080)",
    )
    parser.add_argument(
        "--allow-private",
        action="store_true",
        default=False,
        help="private/loopback IP 허용 (SSRF 보호 비활성화)",
    )
    # SPEC-WEBREADER-MULTISTEP-001: hook-script 지원
    # @MX:NOTE: [AUTO] --adapter와 --hook-script는 상호배타.
    #           --adapter는 Sprint 3에서 hometax 등 내장 어댑터를 사용하고,
    #           --hook-script는 외부 .py 파일을 사용하는 기존 방식.
    #           두 경로는 서로 다른 페이지 진입 전략이므로 동시 사용 불가.
    exclusive_group = parser.add_mutually_exclusive_group()
    exclusive_group.add_argument(
        "--hook-script",
        default=None,
        metavar="PATH",
        help="hook-script 경로 (.py). run(page, args) 동기 함수를 실행한다.",
    )
    # SPEC-WEBREADER-006: adapter 지원 옵션
    exclusive_group.add_argument(
        "--adapter",
        default=None,
        metavar="NAME",
        help="SPA 어댑터 이름 (--hook-script와 상호배타). 예: hometax",
    )
    parser.add_argument(
        "--hook-arg",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="hook-script에 전달할 인자 (KEY=VALUE 형식, 복수 지정 가능)",
    )
    parser.add_argument(
        "--adapter-page",
        default=None,
        metavar="KEY",
        dest="adapter_page",
        help="어댑터에서 사용할 페이지 키 (기본: 어댑터 매니페스트 default_page)",
    )
    parser.add_argument(
        "--capture-api",
        default=None,
        metavar="PATTERN",
        dest="capture_api",
        help="API 응답 캡처 정규식 패턴 (FR-CAPTURE-01). 예: 'api/v1'",
    )
    parser.add_argument(
        "--list-adapters",
        action="store_true",
        default=False,
        dest="list_adapters",
        help="사용 가능한 SPA 어댑터 목록 출력 후 종료",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# hook-script 지원 (SPEC-WEBREADER-MULTISTEP-001)
# ---------------------------------------------------------------------------


def _parse_hook_args(hook_arg_list: list[str]) -> dict[str, str]:
    """--hook-arg KEY=VALUE 목록을 dict로 파싱한다.

    Args:
        hook_arg_list: ["KEY=VALUE", ...] 형태의 문자열 목록.

    Returns:
        파싱된 dict.

    Raises:
        SystemExit(2): KEY가 [A-Za-z_][A-Za-z0-9_]* 패턴이 아니거나 = 가 없는 경우.
    """
    _KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    result: dict[str, str] = {}
    for entry in hook_arg_list:
        if "=" not in entry:
            print(
                f"Error: --hook-arg 형식 오류 — 'KEY=VALUE' 형식이어야 합니다: {entry!r}",
                file=sys.stderr,
            )
            sys.exit(2)
        key, _, value = entry.partition("=")
        if not _KEY_PATTERN.match(key):
            print(
                f"Error: --hook-arg 키 형식 오류 — "
                f"[A-Za-z_][A-Za-z0-9_]* 패턴이어야 합니다: {key!r}",
                file=sys.stderr,
            )
            sys.exit(2)
        result[key] = value
    return result


def _load_hook_script(path: Path) -> types.ModuleType:
    """hook-script 파일을 검증하고 동적으로 로드한다.

    Args:
        path: hook-script 경로.

    Returns:
        로드된 모듈 객체.

    Raises:
        SystemExit(2): 파일이 없거나, .py가 아니거나, run 심볼이 없거나,
                       run이 coroutine 함수인 경우.
    """
    if not path.exists():
        print(
            f"Error: hook-script 파일을 찾을 수 없습니다: {path}",
            file=sys.stderr,
        )
        sys.exit(2)

    if path.suffix.lower() != ".py":
        print(
            f"Error: hook-script는 .py 확장자가 필요합니다: {path.suffix!r}",
            file=sys.stderr,
        )
        sys.exit(2)

    # Use a unique module name based on file path hash to avoid collisions
    hash_prefix = hashlib.sha1(str(path).encode()).hexdigest()[:8]
    module_name = f"_hook_{hash_prefix}"

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        print(
            f"Error: hook-script 로드 실패: {path}",
            file=sys.stderr,
        )
        sys.exit(2)

    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    if not hasattr(mod, "run"):
        print(
            f"Error: hook-script에 'run' 심볼이 없습니다: {path}",
            file=sys.stderr,
        )
        sys.exit(2)

    if not callable(mod.run):
        print(
            f"Error: hook-script의 'run'이 callable이 아닙니다: {type(mod.run)}",
            file=sys.stderr,
        )
        sys.exit(2)

    if inspect.iscoroutinefunction(mod.run):
        print(
            f"Error: hook-script의 'run'이 coroutine 함수입니다. "
            f"sync 함수만 허용됩니다 (async def는 사용 불가).",
            file=sys.stderr,
        )
        sys.exit(2)

    return mod


# ---------------------------------------------------------------------------
# list-adapters 위임 헬퍼 (테스트에서 mock 가능)
# ---------------------------------------------------------------------------


def _list_adapters_main() -> int:
    """list_adapters.main()을 argv=[] 로 위임 호출한다.

    테스트에서 patch.object(fetch_dynamic, "_list_adapters_main", ...) 형태로 mock 가능.
    argv=[]를 전달하여 fetch_dynamic의 sys.argv가 list_adapters에 넘어가지 않도록 한다.

    Returns:
        list_adapters.main() 반환값 (exit code).
    """
    list_adapters_mod = _load_local_module("list_adapters")
    return list_adapters_mod.main([])  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점.

    Returns:
        0=성공, 1=네비게이션 에러, 2=인자 오류/미설치, 3=lock 충돌, 4=TTY 없음.
    """
    args = _parse_args(argv)

    # --list-adapters: 어댑터 목록 출력 후 종료 (다른 인자 무시)
    if args.list_adapters:
        return _list_adapters_main()

    if args.url is None and args.adapter is None:
        print("Error: --url이 필요합니다", file=sys.stderr)
        return 2

    if not is_playwright_available():
        print(
            "Error: playwright가 설치되지 않았습니다. "
            "uv pip install --system playwright && playwright install chromium",
            file=sys.stderr,
        )
        return 2

    # --interactive는 --headed를 자동 활성화
    if args.interactive:
        args.headed = True

    # --interactive TTY 검사
    if args.interactive and not sys.stdin.isatty():
        print("Error: --interactive는 stdin에 TTY가 필요합니다", file=sys.stderr)
        return 4

    # viewport 파싱
    try:
        vp_parts = args.viewport.split("x", 1)
        viewport = {"width": int(vp_parts[0]), "height": int(vp_parts[1])}
    except (ValueError, AttributeError, IndexError):
        print(
            f"Error: --viewport는 WxH 형식이어야 합니다 (예: 1920x1080), 입력값: {args.viewport!r}",
            file=sys.stderr,
        )
        return 2

    headless = not args.headed
    use_stealth = args.stealth  # --profile 없이 --stealth만 사용 시

    profile_label = args.profile if args.profile else "ephemeral"
    # 프로필 사용 시 stealth 자동 활성화
    if args.profile is not None:
        use_stealth = True

    stealth_label = "active" if use_stealth else "disabled"

    # --capture-api 핸들러 생성 — 어댑터/hook-script 분기 공통 (ISS-CAPTURE-023)
    # 패턴 검증을 분기 진입 전에 수행하여 standalone --url + --capture-api도 동작하게 함.
    capture_handler = None
    if args.capture_api is not None:
        try:
            from spa_capture import CaptureHandler
            capture_handler = CaptureHandler(pattern=args.capture_api)
        except Exception as exc:
            print(f"Error: --capture-api 패턴 오류 — {exc}", file=sys.stderr)
            return 2

    # --hook-script 분기 처리
    if args.hook_script is not None:
        # Validate and load hook-script
        hook_module = _load_hook_script(Path(args.hook_script))
        hook_args_dict = _parse_hook_args(args.hook_arg)

        profile_dir_for_hook: str | None = None
        lock_cm_hook = None
        ProfileLockError_hook = None

        if args.profile is not None:
            pm = _import_profile_manager()
            try:
                pm.validate_profile_name(args.profile)
            except SystemExit:
                return 2
            profile_root = pm.get_profile_root()
            profile_dir = profile_root / args.profile
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_dir_for_hook = str(profile_dir)
            ProfileLockError_hook = pm.ProfileLockError
            lock_cm_hook = pm.ProfileLock(profile_dir, args.profile)

        from browser_driver import BrowserDriver, BrowserDriverError

        ctx_kwargs: dict[str, object] = {
            "user_agent": args.user_agent,
            "locale": "ko-KR",
            "extra_http_headers": {
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            "viewport": viewport,
        }

        def _run_hook_inline() -> int:
            with sync_playwright() as pw:
                if profile_dir_for_hook is not None:
                    launch_kwargs: dict[str, object] = {
                        "headless": headless,
                        **ctx_kwargs,
                    }
                    context = pw.chromium.launch_persistent_context(
                        user_data_dir=profile_dir_for_hook,
                        **launch_kwargs,
                    )
                else:
                    browser = pw.chromium.launch(headless=headless)
                    context = browser.new_context(**ctx_kwargs)

                if use_stealth:
                    stealth_mod = _import_stealth()
                    stealth_mod.apply_stealth(context)

                page = context.new_page()
                # --capture-api 핸들러를 hook-script 분기에도 연결 (ISS-CAPTURE-023)
                if capture_handler is not None:
                    page.on("response", capture_handler)
                driver = BrowserDriver(page, allow_private=args.allow_private)

                try:
                    return_value = hook_module.run(driver, hook_args_dict)
                except KeyboardInterrupt:
                    context.close()
                    return 130
                except BrowserDriverError as bde:
                    context.close()
                    print(
                        f"Error: 훅 실행 실패 — 단계: {bde.stage!r}, "
                        f"selector: {bde.selector!r}, 원인: {bde.cause}",
                        file=sys.stderr,
                    )
                    return 1
                except Exception as exc:
                    context.close()
                    if PlaywrightTimeoutError is not None and isinstance(
                        exc, PlaywrightTimeoutError
                    ):
                        print(
                            f"Error: 훅 실행 타임아웃 — 단계: playwright_timeout, 원인: {exc}",
                            file=sys.stderr,
                        )
                        return 1
                    print(f"Error: 훅 실행 오류 — {exc}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                    return 1

                if return_value is None:
                    # Output final page HTML
                    html = driver.extract_html()
                    context.close()
                    sys.stdout.write(html)
                else:
                    context.close()
                    try:
                        output_str = json.dumps(return_value, ensure_ascii=False)
                    except (TypeError, ValueError) as json_err:
                        print(
                            f"Error: hook 반환값을 JSON으로 직렬화할 수 없습니다: {json_err}",
                            file=sys.stderr,
                        )
                        return 1
                    sys.stdout.write(output_str + "\n")

            return 0

        if lock_cm_hook is not None:
            try:
                with lock_cm_hook:
                    return _run_hook_inline()
            except Exception as e:
                if ProfileLockError_hook is not None and isinstance(e, ProfileLockError_hook):
                    pid = getattr(e, "pid", "?")
                    print(
                        f"Error: 프로필 '{args.profile}'이 PID {pid}에 의해 사용 중입니다.",
                        file=sys.stderr,
                    )
                    return 3
                print(f"Error: {e}", file=sys.stderr)
                return 1
        else:
            return _run_hook_inline()

    # --adapter 분기 처리 (Sprint 3: 실제 어댑터 entry() 호출 구현)
    if args.adapter is not None:
        # ISS-LATEIMPORT-021: 분기 내 산재된 late import를 분기 시작부에 집중
        try:
            from spa_adapters._loader import (
                load_adapter,
                get_default_page,
                AdapterNotFoundError,
                AdapterManifestError,
            )
            from spa_adapters.base import AdapterEntryError
            from browser_driver import BrowserDriver
        except ImportError as _import_exc:
            print(
                f"[web-reader] 어댑터 실행에 필요한 모듈을 로드할 수 없습니다: {_import_exc}",
                file=sys.stderr,
            )
            return 2

        try:
            adapter = load_adapter(args.adapter)
        except AdapterNotFoundError as exc:
            print(f"Error: 어댑터 로드 실패 — {exc}", file=sys.stderr)
            return 2
        except AdapterManifestError as exc:
            print(f"Error: 어댑터 매니페스트 오류 — {exc}", file=sys.stderr)
            return 2

        # page_key 결정: --adapter-page > manifest default_page > 첫 번째 pages 키
        page_key = args.adapter_page
        if page_key is None:
            page_key = get_default_page(args.adapter)
            if page_key is None:
                pages = getattr(adapter, "pages", {})
                page_key = next(iter(pages), None)

        # 도메인 불일치 경고 (FR-ENTRY-02 안내만, 차단 없음)
        if args.url is not None:
            import re as _re
            from urllib.parse import urlparse as _urlparse
            _netloc = _urlparse(args.url).netloc.lower()
            _host_no_www = _netloc.removeprefix("www.")
            _domain_pat = getattr(adapter, "domain_pattern", "")
            if _domain_pat and isinstance(_domain_pat, str):
                _matched = (
                    _re.match(_domain_pat, _netloc)
                    or _re.match(_domain_pat, _host_no_www)
                )
                if not _matched:
                    print(
                        f"[web-reader] 경고: 입력 URL 도메인 '{_netloc}'이(가) "
                        f"어댑터 '{args.adapter}'의 도메인 패턴과 일치하지 않습니다. "
                        "어댑터가 예상대로 동작하지 않을 수 있습니다.",
                        file=sys.stderr,
                    )

        # entry_url 결정 (--url 미지정 시 어댑터 PageDef의 entry_url 사용)
        if args.url is not None:
            effective_url = args.url
        else:
            try:
                pages = getattr(adapter, "pages", {})
                if page_key and page_key in pages:
                    page_def = pages[page_key]
                    # PageDef 데이터클래스: .entry_url 속성
                    effective_url = getattr(page_def, "entry_url", None) or ""
                else:
                    effective_url = ""
            except Exception:
                effective_url = ""

            if not effective_url:
                print(
                    f"Error: 어댑터 '{args.adapter}'에서 entry_url을 찾을 수 없습니다. "
                    "--url을 명시적으로 지정하세요.",
                    file=sys.stderr,
                )
                return 2

        # capture_handler는 분기 공통으로 상단에서 이미 생성됨 (ISS-CAPTURE-023)

        # Sprint 3: 어댑터 entry() 호출 (FR-ENTRY-01)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=args.user_agent,
                    locale="ko-KR",
                    extra_http_headers={
                        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    },
                )
                page = context.new_page()

                if capture_handler is not None:
                    page.on("response", capture_handler)

                # BrowserDriver로 감싸서 어댑터 entry() 위임
                driver = BrowserDriver(page, allow_private=args.allow_private)

                if page_key is not None:
                    # 실제 어댑터 entry() 실행 (FR-ENTRY-01)
                    adapter.entry(driver, page_key)
                else:
                    # page_key 없음: 일반 goto fallback
                    page.goto(
                        effective_url,
                        timeout=args.timeout * 1000,
                        wait_until="domcontentloaded",
                    )
                    try:
                        page.wait_for_load_state(
                            "networkidle",
                            timeout=int(args.settle_time * 1000),
                        )
                    except Exception:
                        pass

                html = page.content()
                final_url = page.url
                context.close()

            result: dict[str, object] = {
                "content": html,
                "url": final_url,
                "size": len(html.encode("utf-8")),
            }

        except Exception as exc:
            # NotImplementedError: 미완성 어댑터 (wetax, gov_kr 등) — exit 5
            if isinstance(exc, NotImplementedError):
                print(
                    f"Error: 어댑터 '{args.adapter}' 미구현 — {exc}",
                    file=sys.stderr,
                )
                return 5
            # AdapterEntryError 포함 모든 예외: FR-ADAPT-03 — exit 5
            if isinstance(exc, AdapterEntryError):
                print(str(exc), file=sys.stderr)
                return 5
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        final_url = str(result["url"])
        size = int(result["size"])  # type: ignore[arg-type]
        content = str(result["content"])

        print(f"Profile: ephemeral", file=sys.stderr)
        print(f"Adapter: {args.adapter}", file=sys.stderr)
        print(f"URL: {final_url}", file=sys.stderr)
        print(f"Size: {size}", file=sys.stderr)
        if capture_handler is not None:
            print(f"CaptureFile: {capture_handler.output_path}", file=sys.stderr)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(content)
            except (OSError, IOError, PermissionError) as e:
                print(f"Error: 출력 파일 쓰기 실패: {e}", file=sys.stderr)
                return 1
        else:
            sys.stdout.write(content)

        return 0

    if args.profile is not None:
        # ---------- persistent context 경로 ----------
        pm = _import_profile_manager()

        try:
            pm.validate_profile_name(args.profile)
        except SystemExit:
            return 2

        profile_root = pm.get_profile_root()
        profile_dir = profile_root / args.profile
        profile_dir.mkdir(parents=True, exist_ok=True)

        ProfileLockError = pm.ProfileLockError
        lock_cm = pm.ProfileLock(profile_dir, args.profile)

        try:
            with lock_cm:
                result = _fetch_with_profile(
                    url=args.url,
                    profile_dir=profile_dir,
                    timeout=args.timeout,
                    user_agent=args.user_agent,
                    settle_time=args.settle_time,
                    wait_until=args.wait_until,
                    use_stealth=use_stealth,
                    headless=headless,
                    interactive=args.interactive,
                    viewport=viewport,
                    allow_private=args.allow_private,
                )

                meta = pm.read_profile_meta(profile_dir)
                if not meta:
                    meta = pm.create_default_meta(args.profile)
                meta["last_used_at"] = datetime.now(tz=timezone.utc).isoformat()
                domain = urlparse(str(result["url"])).netloc
                domains = meta.get("domains_visited", [])
                if domain and domain not in domains:
                    domains.append(domain)
                meta["domains_visited"] = domains
                pm.write_profile_meta(profile_dir, meta)

        except Exception as e:
            if isinstance(e, ProfileLockError):
                pid = getattr(e, "pid", "?")
                print(
                    f"Error: 프로필 '{args.profile}'이 PID {pid}에 의해 사용 중입니다. "
                    f"--force 옵션으로 강제 삭제할 수 있습니다.",
                    file=sys.stderr,
                )
                return 3
            # SSRF 에러 처리
            uv = _get_url_validator()
            if isinstance(e, uv.SSRFError) or isinstance(e, ValueError):
                print(f"Error: SSRF 차단 — {e}", file=sys.stderr)
                return 2
            print(f"Error: {e}", file=sys.stderr)
            return 1

    else:
        # ---------- 기존 ephemeral 경로 (하위 호환) ----------
        try:
            if use_stealth or args.interactive:
                # stealth + interactive: persistent context 없이 ephemeral로 실행
                result = _fetch_ephemeral_with_options(
                    url=args.url,
                    timeout=args.timeout,
                    user_agent=args.user_agent,
                    settle_time=args.settle_time,
                    wait_until=args.wait_until,
                    use_stealth=use_stealth,
                    headless=headless,
                    interactive=args.interactive,
                    viewport=viewport,
                    allow_private=args.allow_private,
                    capture_handler=capture_handler,
                )
            else:
                result = fetch_with_js(
                    args.url,
                    timeout=args.timeout,
                    user_agent=args.user_agent,
                    settle_time=args.settle_time,
                    wait_until=args.wait_until,
                    headless=headless,
                    viewport=viewport,
                    allow_private=args.allow_private,
                    capture_handler=capture_handler,
                )

        except Exception as exc:
            # SSRF 에러 처리
            uv = _get_url_validator()
            if isinstance(exc, uv.SSRFError) or isinstance(exc, ValueError):
                print(f"Error: SSRF 차단 — {exc}", file=sys.stderr)
                return 2
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    final_url = str(result["url"])
    size = int(result["size"])  # type: ignore[arg-type]

    # FR-DETECT-02 / FR-ENTRY-02 / FR-ENTRY-03: SPA 감지 + deep-link 차단 안내
    # --url 만 지정된 일반 경로에서만 실행 (--adapter, --hook-script 경로에서는 실행 안 함)
    _spa_advisory_url = args.url  # args.url이 None이면 이미 위에서 처리됨
    if _spa_advisory_url is not None:
        _content = str(result.get("content", ""))
        try:
            from spa_detector import detect_spa_framework, detect_deep_link_block
            _framework = detect_spa_framework(_content)
            if _framework is not None:
                # FR-DETECT-02: SPA 감지 메시지
                print(
                    f"[web-reader] {_framework.capitalize() if _framework != 'websquare5' else 'WebSquare5'} SPA가 감지되었습니다. "
                    "직접 URL 추출이 불완전할 수 있습니다. --adapter 옵션 또는 hook-script 사용을 권장합니다.",
                    file=sys.stderr,
                )
                # FR-ENTRY-03: deep-link 차단 감지
                _is_blocked = detect_deep_link_block(_spa_advisory_url, final_url)
                if _is_blocked:
                    print(
                        f"[web-reader] deep-link 차단을 감지했습니다 "
                        f"(입력 URL → {final_url}). "
                        "사이트 어댑터 또는 hook-script로 정상 진입 경로를 정의해 주세요.",
                        file=sys.stderr,
                    )
                    # FR-ENTRY-02: 매니페스트 매칭 시 어댑터 추천
                    try:
                        from urllib.parse import urlparse as _urlparse
                        import re as _re
                        from spa_adapters._loader import load_manifest
                        _manifest = load_manifest()
                        _input_host = _urlparse(_spa_advisory_url).netloc.lower()
                        for _adapter_entry in _manifest.get("adapters", []):
                            # available=false인 placeholder 어댑터는 추천하지 않음 (ISS-AVAIL-022)
                            if not _adapter_entry.get("available", True):
                                continue
                            _pattern = _adapter_entry.get("domain_pattern", "")
                            _name = _adapter_entry.get("name", "")
                            if _pattern and _name:
                                # www. 제거 후 비교
                                _host_no_www = _input_host.removeprefix("www.")
                                if _re.match(_pattern, _host_no_www) or _re.match(_pattern, _input_host):
                                    print(
                                        f"[web-reader] 이 도메인에는 사전 정의된 어댑터 '{_name}'이(가) 있습니다. "
                                        f"--adapter {_name} 사용을 고려하세요.",
                                        file=sys.stderr,
                                    )
                                    break
                    except Exception:
                        pass  # 매니페스트 로딩 실패는 무시 (안내 메시지 전용 로직)
        except Exception:
            pass  # SPA 감지 실패는 무시 (기존 동작 보장)

    # stderr 리포트 (Profile: 및 Stealth: 라인 포함)
    print(f"Profile: {profile_label}", file=sys.stderr)
    print(f"Stealth: {stealth_label}", file=sys.stderr)
    print(f"URL: {final_url}", file=sys.stderr)
    print(f"Size: {size}", file=sys.stderr)

    content = str(result["content"])

    if args.output:
        # REQ-3.6: 파일 쓰기 에러를 적절히 처리한다
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(content)
        except (OSError, IOError, PermissionError) as e:
            print(f"Error: 출력 파일 쓰기 실패: {e}", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
