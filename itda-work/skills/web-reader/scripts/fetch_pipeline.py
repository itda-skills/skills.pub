"""fetch_pipeline.py - 정적/동적 fetch orchestrator.

SPEC-WEBREADER-008 REQ-2, REQ-3, REQ-4 통합 orchestrator.

fetch_html / fetch_dynamic은 단일 책임 유지.
fetch_pipeline만 두 모듈을 사용하여 역방향 import 금지 원칙 준수.
"""
from __future__ import annotations

import os
import sys
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# scripts/ 디렉토리 절대 경로 (importlib 기반 로딩에 사용)
_scripts_dir = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

MIN_TEXT_LENGTH_DEFAULT = 500
MIN_MEANINGFUL_TAGS_DEFAULT = 3

_PLAYWRIGHT_BROWSERS_PATH_ENV = "PLAYWRIGHT_BROWSERS_PATH"
_DEFAULT_BROWSERS_PATH = str(Path.home() / ".cache" / "playwright")


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class QualityVerdict:
    """콘텐츠 품질 사전 판정 결과 (REQ-3)."""

    passed: bool
    text_length: int
    meaningful_tag_count: int
    quality_score: float
    reason: str


@dataclass
class FetchResult:
    """fetch_with_fallback() 반환 결과 (REQ-2.3)."""

    html: str
    final_url: str
    # fetch_method: "static" | "dynamic" | "degraded_static"
    fetch_method: str
    quality_score: float
    meaningful_tag_count: int
    fallback_reason: str
    # 기타 메타 (headers 등)
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# WI-3: 콘텐츠 품질 휴리스틱 (REQ-3)
# ---------------------------------------------------------------------------

def assess_static_quality(
    html: str,
    *,
    min_text_length: int = MIN_TEXT_LENGTH_DEFAULT,
    min_meaningful_tags: int = MIN_MEANINGFUL_TAGS_DEFAULT,
) -> QualityVerdict:
    """정적 fetch 결과의 본문 품질을 사전 판정한다.

    # @MX:NOTE: [AUTO] 정적 fetch 품질 사전 판정 — fetch 단계, scorer.py와 책임 분리.
    # REQ-3.1 산식: min(text_len/MIN_TEXT_LEN, tag_count/MIN_TAGS, 1.0).
    # 임계값 CLI/env override (REQ-3.3).

    Args:
        html: 정적 fetch로 받은 HTML 문자열.
        min_text_length: 텍스트 길이 임계값 (기본 500).
        min_meaningful_tags: 의미 있는 태그 최소 수 (기본 3).

    Returns:
        QualityVerdict (passed, text_length, meaningful_tag_count, quality_score, reason).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        # BeautifulSoup 없으면 품질 판정 불가 → 통과 처리 (downstream이 처리)
        return QualityVerdict(
            passed=True,
            text_length=0,
            meaningful_tag_count=0,
            quality_score=1.0,
            reason="bs4 unavailable, skipping quality check",
        )

    soup = BeautifulSoup(html, "html.parser")

    # body 텍스트 추출 (script/style 제외)
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    body = soup.find("body")
    body_text = (body or soup).get_text(separator=" ", strip=True) if soup else ""
    text_length = len(body_text)

    # meaningful_tag_count: <p>, <article>, <section>, <h1>~<h6>
    meaningful_tag_count = (
        len(soup.find_all("p"))
        + len(soup.find_all("article"))
        + len(soup.find_all("section"))
        + sum(len(soup.find_all(f"h{i}")) for i in range(1, 7))
    )

    # REQ-3.1 산식
    quality_score = min(
        text_length / max(min_text_length, 1),
        meaningful_tag_count / max(min_meaningful_tags, 1),
        1.0,
    )

    # REQ-3.2: quality_score < 1.0이면 임계값 미달 → 동적 폴백 트리거
    passed = quality_score >= 1.0

    if passed:
        reason = ""
    else:
        parts = []
        if text_length < min_text_length:
            parts.append(f"text_length={text_length} < {min_text_length}")
        if meaningful_tag_count < min_meaningful_tags:
            parts.append(f"meaningful_tags={meaningful_tag_count} < {min_meaningful_tags}")
        reason = "; ".join(parts) or "quality below threshold"

    return QualityVerdict(
        passed=passed,
        text_length=text_length,
        meaningful_tag_count=meaningful_tag_count,
        quality_score=quality_score,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# WI-4 보조: Playwright 설치 시도 (REQ-4)
# ---------------------------------------------------------------------------

def _attempt_playwright_install(*, stderr_out=None) -> tuple[bool, str]:
    """Playwright 설치를 3단계로 시도한다.

    # @MX:WARN: [AUTO] Playwright 설치 재시도 로직 — subprocess 호출 + 환경변수 변이.
    # @MX:REASON: Cowork sandbox에서 /usr/local/lib에 대한 Permission denied 사고(2026-04-27).
    # SPEC-WEBREADER-008 REQ-4.3 / CLAUDE.local.md "관리자 권한 정책" / "Python 패키지 설치 정책" 준수.
    # sudo / pip install (uv 외 직접) / 관리자 권한 / 시스템 경로 쓰기 절대 호출 금지.

    Args:
        stderr_out: 메시지를 출력할 파일 객체 (기본: sys.stderr).

    Returns:
        (success: bool, reason: str) 튜플.
    """
    import sys as _sys
    _out = stderr_out or _sys.stderr

    def _print(msg: str) -> None:
        print(msg, file=_out)

    browsers_path = str(Path.home() / ".cache" / "playwright")
    env_with_browsers = {**os.environ, _PLAYWRIGHT_BROWSERS_PATH_ENV: browsers_path}

    # 1차 시도: uv pip install --system playwright (CLAUDE.local.md 권장)
    _print("[web-reader] Playwright 설치 시도 1차: uv pip install --system playwright")
    try:
        result1 = subprocess.run(
            ["uv", "pip", "install", "--system", "playwright"],
            capture_output=True,
            text=True,
            env=env_with_browsers,
        )
        if result1.returncode == 0:
            _print("[web-reader] uv pip install --system playwright 성공. chromium 설치 중...")
            result_chromium = subprocess.run(
                ["playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                env=env_with_browsers,
            )
            if result_chromium.returncode == 0:
                _print("[web-reader] Playwright + chromium 설치 완료 (1차).")
                return True, ""
            else:
                _print(f"[web-reader] chromium binary 설치 실패: {result_chromium.stderr[:200]}")
                return False, "browser binary install failed"
        else:
            stderr_text = result1.stderr or ""
            # PyPI 도달 불가 → 즉시 graceful degrade (재시도 의미 없음)
            if any(kw in stderr_text.lower() for kw in (
                "connection", "network", "timeout", "unreachable", "resolve", "dns"
            )):
                _print("[web-reader] PyPI 도달 불가 — 즉시 graceful degrade.")
                return False, "pypi unreachable"
            # Permission denied 또는 기타 → 2차 시도
            _print(f"[web-reader] 1차 실패 (returncode={result1.returncode}). 2차 시도...")
    except FileNotFoundError:
        _print("[web-reader] uv 명령을 찾을 수 없음. 2차 시도...")

    # 2차 시도: uv venv 사용자 로컬 venv 폴백
    venv_path = Path.home() / ".cache" / "web-reader-venv"
    _print(f"[web-reader] Playwright 설치 시도 2차: uv venv {venv_path}")
    try:
        result_venv = subprocess.run(
            ["uv", "venv", str(venv_path)],
            capture_output=True,
            text=True,
        )
        if result_venv.returncode == 0:
            venv_python = str(venv_path / "bin" / "python")
            venv_env = {
                **os.environ,
                "VIRTUAL_ENV": str(venv_path),
                "PATH": str(venv_path / "bin") + os.pathsep + os.environ.get("PATH", ""),
                _PLAYWRIGHT_BROWSERS_PATH_ENV: browsers_path,
            }
            result_install = subprocess.run(
                ["uv", "pip", "install", "--python", venv_python, "playwright"],
                capture_output=True,
                text=True,
                env=venv_env,
            )
            if result_install.returncode == 0:
                result_chromium2 = subprocess.run(
                    [venv_python, "-m", "playwright", "install", "chromium"],
                    capture_output=True,
                    text=True,
                    env=venv_env,
                )
                if result_chromium2.returncode == 0:
                    _print("[web-reader] Playwright + chromium 설치 완료 (2차 venv).")
                    return True, ""
                else:
                    _print("[web-reader] 2차 chromium 설치 실패. 3차 시도...")
            else:
                _print("[web-reader] 2차 pip install 실패. 3차 시도...")
        else:
            _print("[web-reader] uv venv 생성 실패. 3차 시도...")
    except FileNotFoundError:
        _print("[web-reader] uv 명령을 찾을 수 없음 (2차). 3차 시도...")

    # 3차 시도: browser binary 설치 경로 대체 (non-writable ~/.cache 대응)
    _print("[web-reader] Playwright 설치 시도 3차: --browsers-path 대체 경로")
    try:
        try:
            # shared/itda_path.py 경로 사용 (CLAUDE.local.md 데이터 경로 정책)
            _shared_dir = os.path.join(_scripts_dir)
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location("itda_path", os.path.join(_shared_dir, "itda_path.py"))
            if _spec and _spec.loader:
                _itda_path = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_itda_path)  # type: ignore[union-attr]
                alt_browsers_path = str(_itda_path.resolve_data_dir("web-reader", "playwright-browsers"))
            else:
                raise ImportError("itda_path not found")
        except Exception:
            alt_browsers_path = os.path.join(os.getcwd(), ".itda-skills", "web-reader", "playwright-browsers")

        alt_env = {**os.environ, _PLAYWRIGHT_BROWSERS_PATH_ENV: alt_browsers_path}
        result3 = subprocess.run(
            ["playwright", "install", "chromium", "--browsers-path", alt_browsers_path],
            capture_output=True,
            text=True,
            env=alt_env,
        )
        if result3.returncode == 0:
            _print(f"[web-reader] Playwright chromium 설치 완료 (3차, {alt_browsers_path}).")
            return True, ""
        else:
            _print(f"[web-reader] 3차 browser binary 설치 실패: {result3.stderr[:200]}")
    except FileNotFoundError:
        _print("[web-reader] playwright 명령을 찾을 수 없음 (3차).")

    return False, "permission denied"


# ---------------------------------------------------------------------------
# WI-2: fetch_with_fallback() orchestrator (REQ-2)
# ---------------------------------------------------------------------------

# @MX:ANCHOR: [AUTO] fetch_with_fallback — fetch_html과 fetch_dynamic의 단일 진입점.
# @MX:REASON: fan_in이 extract_content.py + 향후 다른 모듈에서 증가 예정. REQ-2 invariant 보호.
# 변경 시 site_pattern → 정적 → 품질 평가 → 동적 → 비교 → graceful degrade 6단계 순서 보장.
def fetch_with_fallback(
    url: str,
    *,
    static_only: bool = False,
    dynamic_only: bool = False,
    min_text_length: int = MIN_TEXT_LENGTH_DEFAULT,
    min_meaningful_tags: int = MIN_MEANINGFUL_TAGS_DEFAULT,
    site_pattern: dict | None = None,
    stderr_out=None,
) -> FetchResult:
    """정적/동적 fetch orchestrator.

    REQ-2: 정적 fetch → 콘텐츠 품질 검증 → 부족 시 동적 폴백 → 비교 → 반환.

    Args:
        url: fetch할 URL.
        static_only: True이면 정적 fetch만. 품질 미달이어도 동적 시도 안 함.
        dynamic_only: True이면 동적 fetch만. 정적 시도 없이 바로 Playwright.
        min_text_length: 품질 판정 텍스트 길이 임계값.
        min_meaningful_tags: 품질 판정 의미 태그 수 임계값.
        site_pattern: match_site_pattern() 결과 dict. None이면 패턴 없음.
        stderr_out: 메시지 출력 대상 (기본: sys.stderr).

    Returns:
        FetchResult (html, final_url, fetch_method, quality_score, fallback_reason, ...).

    Raises:
        ContentExtractionError: 정적+동적+degrade 모두 빈 본문일 때.
    """
    import sys as _sys
    from exceptions import ContentExtractionError  # type: ignore[import]

    _out = stderr_out or _sys.stderr

    def _log(msg: str) -> None:
        print(msg, file=_out)

    # REQ-6.4: dynamic: True 패턴이면 정적 품질 휴리스틱 우회, 즉시 동적 시도
    force_dynamic = bool(site_pattern and site_pattern.get("dynamic"))

    static_result: FetchResult | None = None

    # ── 정적 fetch ──────────────────────────────────────────────────────────
    if not dynamic_only and not force_dynamic:
        static_result = _do_static_fetch(url, min_text_length, min_meaningful_tags)

        if static_only or static_result is None:
            if static_result is None:
                raise ContentExtractionError(
                    url=url,
                    html_size=0,
                    failed_field="body",
                    attempted_selectors=[],
                    original_exc=None,
                )
            return static_result

        # 품질 충분 → 정적 바로 반환 (동적 시도 불필요)
        if static_result.quality_score >= 1.0:
            return static_result

        # 품질 미달 → 동적 폴백 시도
        _log(
            f"[web-reader] 정적 fetch 품질 미달 (score={static_result.quality_score:.2f}). "
            "동적 fetch로 폴백 중..."
        )

    # ── 동적 fetch ──────────────────────────────────────────────────────────
    dynamic_result: FetchResult | None = None
    playwright_install_reason = ""

    try:
        dynamic_result = _do_dynamic_fetch(url, min_text_length, min_meaningful_tags)
    except _PlaywrightNotAvailable as e:
        playwright_install_reason = str(e)
        # Playwright 없음 → 설치 시도
        _log(f"[web-reader] Playwright 미설치 감지. 설치를 시도합니다...")
        install_ok, install_reason = _attempt_playwright_install(stderr_out=_out)
        if install_ok:
            try:
                dynamic_result = _do_dynamic_fetch(url, min_text_length, min_meaningful_tags)
            except Exception as e2:
                _log(f"[web-reader] 설치 후 동적 fetch 실패: {e2}")
                playwright_install_reason = f"dynamic fetch failed after install: {e2}"
        else:
            playwright_install_reason = install_reason

    except Exception as e:
        _log(f"[web-reader] 동적 fetch 오류: {e}")
        playwright_install_reason = f"dynamic fetch error: {e}"

    # ── 결과 비교 (REQ-2.2) ─────────────────────────────────────────────────
    if dynamic_result is not None:
        if static_result is not None:
            return _compare_and_select(static_result, dynamic_result)
        else:
            # dynamic_only 또는 force_dynamic 케이스
            return dynamic_result

    # ── Graceful degrade (REQ-4.2) ───────────────────────────────────────────
    if static_result is not None:
        degrade_reason = playwright_install_reason or "playwright unavailable"
        _log(
            f"[web-reader] Playwright 설치 실패 — 정적 결과로 graceful degrade. "
            f"사유: {degrade_reason}"
        )
        return FetchResult(
            html=static_result.html,
            final_url=static_result.final_url,
            fetch_method="degraded_static",
            quality_score=static_result.quality_score,
            meaningful_tag_count=static_result.meaningful_tag_count,
            fallback_reason=degrade_reason,
            extra=static_result.extra,
        )

    # 정적 + 동적 모두 실패 → ContentExtractionError
    raise ContentExtractionError(
        url=url,
        html_size=0,
        failed_field="body",
        attempted_selectors=[],
        original_exc=None,
    )


def _compare_and_select(static: FetchResult, dynamic: FetchResult) -> FetchResult:
    """REQ-2.2 비교 알고리즘: dynamic이 static보다 0.10 이상 우수해야 채택."""
    if dynamic.quality_score > static.quality_score + 0.10:
        # 의미 있는 개선 → dynamic 채택
        return FetchResult(
            html=dynamic.html,
            final_url=dynamic.final_url,
            fetch_method="dynamic",
            quality_score=dynamic.quality_score,
            meaningful_tag_count=dynamic.meaningful_tag_count,
            fallback_reason="static content insufficient",
            extra=dynamic.extra,
        )
    elif dynamic.quality_score == static.quality_score:
        # 동률: meaningful_tag_count 더 많은 쪽
        if dynamic.meaningful_tag_count > static.meaningful_tag_count:
            return FetchResult(
                html=dynamic.html,
                final_url=dynamic.final_url,
                fetch_method="dynamic",
                quality_score=dynamic.quality_score,
                meaningful_tag_count=dynamic.meaningful_tag_count,
                fallback_reason="tied quality, dynamic has more meaningful tags",
                extra=dynamic.extra,
            )
        else:
            # 최종 동률: cheaper static 채택
            return static
    else:
        # dynamic이 더 나쁘거나 미세 개선 → static 채택
        return static


class _PlaywrightNotAvailable(Exception):
    """Playwright import 불가 시 내부 시그널."""
    pass


def _do_static_fetch(
    url: str,
    min_text_length: int,
    min_meaningful_tags: int,
) -> FetchResult | None:
    """fetch_html 모듈로 정적 fetch를 수행하고 FetchResult를 반환한다."""
    import importlib.util as _ilu

    filepath = os.path.join(_scripts_dir, "fetch_html.py")
    spec = _ilu.spec_from_file_location("fetch_html", filepath)
    if spec is None or spec.loader is None:
        return None
    fh = _ilu.module_from_spec(spec)
    spec.loader.exec_module(fh)  # type: ignore[union-attr]

    fetch_result = fh.fetch_url(url)
    if not fetch_result.get("content") or fetch_result.get("error"):
        return None

    html = str(fetch_result["content"])
    final_url = str(fetch_result.get("url") or url)
    verdict = assess_static_quality(
        html,
        min_text_length=min_text_length,
        min_meaningful_tags=min_meaningful_tags,
    )

    return FetchResult(
        html=html,
        final_url=final_url,
        fetch_method="static",
        quality_score=verdict.quality_score,
        meaningful_tag_count=verdict.meaningful_tag_count,
        fallback_reason="",
        extra={"headers": fetch_result.get("headers", {})},
    )


def _do_dynamic_fetch(
    url: str,
    min_text_length: int,
    min_meaningful_tags: int,
) -> FetchResult:
    """fetch_dynamic 모듈로 동적 fetch를 수행하고 FetchResult를 반환한다."""
    import importlib.util as _ilu

    filepath = os.path.join(_scripts_dir, "fetch_dynamic.py")
    spec = _ilu.spec_from_file_location("fetch_dynamic", filepath)
    if spec is None or spec.loader is None:
        raise _PlaywrightNotAvailable("fetch_dynamic module not found")
    fd = _ilu.module_from_spec(spec)
    spec.loader.exec_module(fd)  # type: ignore[union-attr]

    if not fd.is_playwright_available():
        raise _PlaywrightNotAvailable("playwright not installed")

    # fetch_dynamic의 fetch_page 함수 호출
    fetch_func = getattr(fd, "fetch_page", None) or getattr(fd, "fetch_url", None)
    if fetch_func is None:
        raise _PlaywrightNotAvailable("fetch_dynamic has no fetch_page/fetch_url function")

    fetch_result = fetch_func(url)
    if not fetch_result or not fetch_result.get("content"):
        raise RuntimeError(f"dynamic fetch returned empty content for {url}")

    html = str(fetch_result["content"])
    final_url = str(fetch_result.get("url") or url)
    verdict = assess_static_quality(
        html,
        min_text_length=min_text_length,
        min_meaningful_tags=min_meaningful_tags,
    )

    return FetchResult(
        html=html,
        final_url=final_url,
        fetch_method="dynamic",
        quality_score=verdict.quality_score,
        meaningful_tag_count=verdict.meaningful_tag_count,
        fallback_reason="",
        extra={},
    )
