#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_html.py - HTTP fetcher optimized for Korean websites.

Uses curl_cffi for HTTP/TLS impersonation. Supports encoding detection,
retry logic, custom headers/cookies, SSL bypass, and generic WAF escalation.

Usage:
    python3 fetch_html.py --url URL [options]
    py -3 fetch_html.py --url URL [options]  # Windows

Exit codes:
    0 - Success
    1 - Network or HTTP error
    2 - Invalid arguments
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os as _os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse, urljoin

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 or later is required.")

try:
    from curl_cffi import requests as cffi
except ImportError:
    sys.exit(
        "curl_cffi is required. Install with: pip install curl_cffi"
    )

# ---------------------------------------------------------------------------
# 로컬 모듈 importlib 로더
# ---------------------------------------------------------------------------

_scripts_dir = _os.path.dirname(_os.path.abspath(__file__))


def _load_local_module(module_name: str):  # type: ignore[return]
    """scripts/ 디렉토리에서 모듈을 importlib로 로드한다.

    sys.modules 캐시에 있는 모듈이 scripts/ 디렉토리 외부에서 온 경우
    (import hijacking 방어) 무시하고 파일 경로 기반으로 재로드한다.
    """
    filepath = _os.path.join(_scripts_dir, f"{module_name}.py")
    if module_name in sys.modules:
        cached = sys.modules[module_name]
        cached_file = getattr(cached, "__file__", None)
        # __file__이 scripts/ 디렉토리 내부이면 캐시 사용
        if cached_file is not None:
            try:
                if _os.path.abspath(cached_file).startswith(_scripts_dir + _os.sep):
                    return cached
            except (TypeError, ValueError):
                pass
        # 외부 모듈이거나 __file__ 없음 → 재로드
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# url_validator lazy load (순환 import 방지를 위해 함수 호출 시 로드)
def _get_url_validator():  # type: ignore[return]
    """url_validator 모듈을 반환한다."""
    return _load_local_module("url_validator")


def _get_challenge_validators():  # type: ignore[return]
    """challenge_validators 모듈을 반환한다."""
    return _load_local_module("challenge_validators")


def _get_waf_detector():  # type: ignore[return]
    """waf_detector 모듈을 반환한다."""
    return _load_local_module("waf_detector")


def _get_url_transforms():  # type: ignore[return]
    """url_transforms 모듈을 반환한다."""
    return _load_local_module("url_transforms")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAFARI_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

FIREFOX_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
    "Gecko/20100101 Firefox/133.0"
)

DEFAULT_IMPERSONATE = "safari"
DEFAULT_USER_AGENT = SAFARI_USER_AGENT
DEFAULT_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_DELAYS = [1, 3]  # seconds for each retry attempt
MAX_BODY_BYTES = 50 * 1024 * 1024  # 50MB
DEFAULT_MAX_GRID_ATTEMPTS = 12


@dataclass
class FetchAttempt:
    """Trace row for one curl_cffi attempt."""

    phase: str
    url: str
    url_transform: str
    impersonate: str
    referer: str
    status: int = 0
    body_size: int = 0
    verdict: str = ""
    reasons: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "executor": "curl_cffi",
            "url": self.url,
            "url_transform": self.url_transform,
            "impersonate": self.impersonate,
            "referer": self.referer,
            "status": self.status,
            "body_size": self.body_size,
            "verdict": self.verdict,
            "reasons": self.reasons,
            "elapsed_s": self.elapsed_s,
            "error": self.error,
        }


class _ValidationResponse:
    """Minimal response adapter for challenge validators."""

    def __init__(self, response: object, text: str, body_size: int) -> None:
        self._response = response
        self.text = text
        self.body_size = body_size
        self.status_code = int(getattr(response, "status_code", 0) or 0)
        self.headers = getattr(response, "headers", {})
        self.cookies = getattr(response, "cookies", {})
        self.url = getattr(response, "url", "")


# ---------------------------------------------------------------------------
# Encoding detection
# ---------------------------------------------------------------------------


def detect_encoding(
    content_bytes: bytes,
    http_charset: str | None = None,
) -> str:
    """Detect character encoding of HTML content.

    Detection chain:
        1. HTTP Content-Type charset (http_charset parameter)
        2. HTML <meta charset="..."> tag
        3. HTML <meta http-equiv="Content-Type" content="...charset=..."> tag
        4. Heuristic: try UTF-8, EUC-KR, CP949
        5. Fallback: UTF-8

    Args:
        content_bytes: Raw response body bytes.
        http_charset: Charset from HTTP Content-Type header, or None.

    Returns:
        Encoding name string (e.g. 'utf-8', 'euc-kr', 'cp949').
    """
    if http_charset:
        return http_charset.strip()

    # Inspect first 4KB for meta charset
    snippet = content_bytes[:4096]
    try:
        snippet_str = snippet.decode("latin-1", errors="replace")
    except Exception:
        snippet_str = ""

    # <meta charset="...">
    meta_charset = re.search(
        r'<meta[^>]+charset=["\']?([A-Za-z0-9_\-]+)',
        snippet_str,
        re.IGNORECASE,
    )
    if meta_charset:
        return meta_charset.group(1).strip()

    # <meta http-equiv="Content-Type" content="text/html; charset=...">
    http_equiv = re.search(
        r"charset=([A-Za-z0-9_\-]+)",
        snippet_str,
        re.IGNORECASE,
    )
    if http_equiv:
        return http_equiv.group(1).strip()

    # Heuristic: test a 4KB snippet to avoid decoding megabytes
    test_bytes = content_bytes[:4096]
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            test_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"


def decode_content(content_bytes: bytes, encoding: str) -> str:
    """Decode bytes to string using given encoding, with fallback.

    Args:
        content_bytes: Raw bytes to decode.
        encoding: Target encoding name.

    Returns:
        Decoded string. Uses 'replace' error handler on failure.
    """
    try:
        return content_bytes.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return content_bytes.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------


def _user_agent_for_impersonate(user_agent: str, impersonate: str) -> str:
    """Keep the default UA aligned with the TLS impersonation family."""
    if user_agent != DEFAULT_USER_AGENT:
        return user_agent
    imp = impersonate.lower()
    if "chrome" in imp or "edge" in imp:
        return CHROME_USER_AGENT
    if "firefox" in imp:
        return FIREFOX_USER_AGENT
    return SAFARI_USER_AGENT


def _self_root(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/"
    return ""


def _referer_for_strategy(url: str, strategy: str) -> str:
    if strategy == "self_root":
        return _self_root(url)
    if strategy == "google_search":
        return "https://www.google.com/"
    if strategy == "none":
        return ""
    return _self_root(url)


def _build_headers(
    url: str,
    *,
    user_agent: str,
    impersonate: str,
    extra_headers: dict[str, str] | None = None,
    referer_strategy: str = "self_root",
) -> dict[str, str]:
    """Build Korean-optimized headers for one attempt."""
    headers: dict[str, str] = {
        "User-Agent": _user_agent_for_impersonate(user_agent, impersonate),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    referer = _referer_for_strategy(url, referer_strategy)
    if referer:
        headers["Referer"] = referer

    if extra_headers:
        headers.update(extra_headers)

    return headers


def _make_session(impersonate: str, cookies: dict[str, str] | None = None) -> "cffi.Session":
    session = cffi.Session(impersonate=impersonate)
    if cookies:
        session.cookies.update(cookies)
    return session


def _read_response_bytes(response: object) -> tuple[bytes, int, str | None]:
    """Read a curl_cffi response body while enforcing the 50MB limit."""
    headers = getattr(response, "headers", {}) or {}
    content_length_str = headers.get("Content-Length", "0") or "0"
    try:
        content_length = int(content_length_str)
    except (TypeError, ValueError):
        content_length = 0

    if content_length > MAX_BODY_BYTES:
        return (
            b"",
            content_length,
            f"Response body too large: {content_length} bytes (max 50MB)",
        )

    chunks: list[bytes] = []
    total_size = 0
    try:
        for chunk in response.iter_content():  # type: ignore[attr-defined]
            if not isinstance(chunk, bytes):
                chunks = []
                total_size = 0
                break
            total_size += len(chunk)
            if total_size > MAX_BODY_BYTES:
                return (
                    b"",
                    total_size,
                    f"Response body too large: >{MAX_BODY_BYTES} bytes (max 50MB)",
                )
            chunks.append(chunk)
    except (AttributeError, AssertionError, TypeError):
        chunks = []
        total_size = 0

    if chunks or total_size > 0:
        return b"".join(chunks), total_size, None

    content_bytes = getattr(response, "content", b"")
    if not isinstance(content_bytes, bytes):
        content_bytes = b""
    if len(content_bytes) > MAX_BODY_BYTES:
        return (
            b"",
            len(content_bytes),
            f"Response body too large: {len(content_bytes)} bytes (max 50MB)",
        )
    return content_bytes, len(content_bytes), None


def _decode_response(
    response: object,
    content_bytes: bytes,
    encoding: str,
) -> tuple[str, str]:
    if encoding == "auto":
        http_charset: str | None = None
        content_type = (getattr(response, "headers", {}) or {}).get("Content-Type", "")
        charset_match = re.search(r"charset=([A-Za-z0-9_\-]+)", content_type)
        if charset_match:
            http_charset = charset_match.group(1)
        detected_encoding = detect_encoding(content_bytes, http_charset=http_charset)
    else:
        detected_encoding = encoding
    return decode_content(content_bytes, detected_encoding), detected_encoding


def _validate_response(
    response: object,
    decoded: str,
    body_size: int,
    *,
    success_selectors: list[str] | None = None,
    known_bad_sizes: list[int] | None = None,
):
    validators = _get_challenge_validators()
    adapter = _ValidationResponse(response, decoded, body_size)
    return validators.validate(
        adapter,
        success_selectors=success_selectors,
        known_bad_sizes=known_bad_sizes,
    )


def _result_from_response(
    response: object,
    content_bytes: bytes,
    decoded: str,
    detected_encoding: str,
    *,
    trace: list[FetchAttempt] | None = None,
    challenge: object | None = None,
    profile_used: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "content": decoded,
        "encoding": detected_encoding,
        "status_code": int(getattr(response, "status_code", 0) or 0),
        "url": str(getattr(response, "url", "")),
        "size": len(content_bytes),
    }
    if trace is not None:
        result["trace"] = [attempt.to_dict() for attempt in trace]
    if challenge is not None:
        result["challenge"] = challenge.to_dict()
    if profile_used:
        result["waf_profile"] = profile_used
    return result


def _error_result(
    *,
    url: str,
    status_code: int,
    error: str,
    size: int = 0,
    encoding: str = "utf-8",
    content: str = "",
    trace: list[FetchAttempt] | None = None,
    challenge: object | None = None,
    profile_used: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "content": content,
        "encoding": encoding,
        "status_code": status_code,
        "url": url,
        "size": size,
        "error": error,
    }
    if trace is not None:
        result["trace"] = [attempt.to_dict() for attempt in trace]
    if challenge is not None:
        result["challenge"] = challenge.to_dict()
    if profile_used:
        result["waf_profile"] = profile_used
    return result


def _is_escalation_candidate(status_code: int, verdict: str) -> bool:
    """Escalate WAF-like failures, but keep ordinary 404/400 behavior stable."""
    return verdict == "challenge" or status_code in {401, 403, 429}


# ---------------------------------------------------------------------------
# Cookie-aware redirect follower (REQ-1.3)
# ---------------------------------------------------------------------------


def _follow_redirects(
    session: "cffi.Session",
    method: str,
    url: str,
    cookies: dict[str, str] | None = None,
    allow_private: bool = False,
    max_redirects: int = 10,
    **kwargs: object,
) -> object:
    """Cross-domain 리다이렉트 시 쿠키를 원본 도메인에만 전송한다.

    HTTP 클라이언트의 기본 리다이렉트 처리는 쿠키를 모든 도메인에 전달할 수 있다.
    이 함수는 allow_redirects=False로 수동으로 리다이렉트를 추적하며,
    도메인이 변경되면 쿠키를 제거한다.

    Args:
        session: curl_cffi Session 인스턴스.
        method: HTTP 메서드 ('GET', 'POST', ...).
        url: 시작 URL.
        cookies: 초기 쿠키 dict. 원본 도메인에만 전송된다.
        allow_private: SSRF 검증 시 private IP 허용 여부.
        max_redirects: 최대 리다이렉트 횟수. 초과 시 마지막 응답 반환.
        **kwargs: session.request()에 전달할 추가 인수.

    Returns:
        최종 응답 객체.
    """
    original_host = urlparse(url).hostname
    current_cookies: dict[str, str] | None = cookies

    # 초기 요청 실행 (max_redirects=0 시에도 resp가 정의되도록)
    resp = session.get(
        url,
        allow_redirects=False,
        cookies=current_cookies,
        **kwargs,
    )

    for _ in range(max_redirects):
        status_code = int(getattr(resp, "status_code", 0) or 0)
        if not (300 <= status_code < 400 and resp.headers.get("Location")):
            break
        redirect_url = resp.headers.get("Location", "")
        if not redirect_url:
            break
        # 상대 Location 해석
        if not urlparse(redirect_url).scheme:
            redirect_url = urljoin(url, redirect_url)
        # redirect 대상 SSRF 검증
        uv = _get_url_validator()
        uv.validate_url(redirect_url, allow_private=allow_private)
        redirect_host = urlparse(redirect_url).hostname
        if redirect_host != original_host:
            # cross-domain: 쿠키 제거
            current_cookies = None
        url = redirect_url
        resp = session.get(
            url,
            allow_redirects=False,
            cookies=current_cookies,
            **kwargs,
        )

    return resp


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------


def fetch_url(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    extra_headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    no_verify: bool = False,
    encoding: str = "auto",
    allow_private: bool = False,
    impersonate: str = DEFAULT_IMPERSONATE,
    success_selectors: list[str] | None = None,
    max_attempts: int = DEFAULT_MAX_GRID_ATTEMPTS,
) -> dict[str, object]:
    """Fetch a URL with retry logic, TLS impersonation, and WAF escalation.

    Args:
        url: Target URL to fetch.
        timeout: Request timeout in seconds.
        user_agent: User-Agent string.
        extra_headers: Additional HTTP headers.
        cookies: Cookies to include in the request.
        no_verify: If True, skip SSL certificate verification.
        encoding: Encoding override ('auto' for detection).
        allow_private: If True, allow private/loopback IP addresses (SSRF bypass).
        impersonate: curl_cffi impersonation target for the first attempt.
        success_selectors: Optional CSS selectors used as positive success proof.
        max_attempts: Max grid attempts after the initial probe.

    Returns:
        Dict with keys: content, encoding, status_code, url, size.

    Raises:
        SystemExit(1): On unrecoverable network/HTTP error.
        SSRFError: On SSRF-unsafe URL (caller should handle).
    """
    # SSRF 방지 URL 검증
    uv = _get_url_validator()
    uv.validate_url(url, allow_private=allow_private)

    session = _make_session(impersonate, cookies)
    headers = _build_headers(
        url,
        user_agent=user_agent,
        impersonate=impersonate,
        extra_headers=extra_headers,
        referer_strategy="self_root",
    )
    last_error: Exception | None = None
    trace: list[FetchAttempt] = []

    for attempt in range(MAX_RETRIES + 1):
        started = time.time()
        probe = FetchAttempt(
            phase="probe" if attempt == 0 else "retry",
            url=url,
            url_transform="original",
            impersonate=impersonate,
            referer="self_root",
        )
        try:
            # 모든 경로에서 _follow_redirects()를 사용:
            # - redirect 대상 SSRF 검증 (REQ-1.2)
            # - cookies 제공 시 cross-domain cookie scoping (REQ-1.3)
            response = _follow_redirects(
                session,
                "GET",
                url,
                cookies=cookies if cookies else None,
                allow_private=allow_private,
                headers=headers,
                timeout=timeout,
                verify=not no_verify,
                stream=True,
            )

            status_code = response.status_code
            probe.status = int(status_code)
            probe.elapsed_s = round(time.time() - started, 3)

            # Retry on 5xx
            if 500 <= status_code < 600:
                last_error = Exception(f"HTTP {status_code}")
                probe.verdict = "blocked"
                probe.reasons = [f"status={status_code}"]
                trace.append(probe)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAYS[attempt])
                continue

            content_bytes, body_size, body_error = _read_response_bytes(response)
            probe.body_size = body_size
            if body_error:
                probe.verdict = "blocked"
                probe.reasons = ["body_too_large"]
                trace.append(probe)
                return _error_result(
                    url=str(getattr(response, "url", url)),
                    status_code=int(status_code),
                    error=body_error,
                    size=body_size,
                    trace=trace,
                )

            final_url = response.url
            decoded, detected_encoding = _decode_response(
                response,
                content_bytes,
                encoding,
            )
            validation = _validate_response(
                response,
                decoded,
                len(content_bytes),
                success_selectors=success_selectors,
            )
            probe.verdict = validation.verdict.value
            probe.reasons = validation.reasons
            probe.body_size = validation.body_size or len(content_bytes)
            trace.append(probe)

            if validation.ok:
                return _result_from_response(
                    response,
                    content_bytes,
                    decoded,
                    detected_encoding,
                    trace=trace,
                    challenge=validation,
                )

            if _is_escalation_candidate(int(status_code), validation.verdict.value):
                grid_result = _escalate_grid(
                    original_url=url,
                    user_agent=user_agent,
                    extra_headers=extra_headers,
                    cookies=cookies,
                    no_verify=no_verify,
                    encoding=encoding,
                    allow_private=allow_private,
                    timeout=timeout,
                    success_selectors=success_selectors,
                    base_impersonate=impersonate,
                    base_referer="self_root",
                    max_attempts=max_attempts,
                    first_response=response,
                    first_decoded=decoded,
                    first_body_size=len(content_bytes),
                    trace=trace,
                )
                return grid_result

            if 400 <= status_code < 500:
                return _error_result(
                    url=str(final_url),
                    status_code=int(status_code),
                    error=f"HTTP {status_code}",
                    size=len(content_bytes),
                    trace=trace,
                    challenge=validation,
                )

            return _error_result(
                url=str(final_url),
                status_code=int(status_code),
                error=f"Challenge detected: {validation.verdict.value}",
                size=len(content_bytes),
                encoding=detected_encoding,
                content=decoded,
                trace=trace,
                challenge=validation,
            )

        except (cffi.exceptions.ConnectionError, cffi.exceptions.Timeout) as exc:
            last_error = exc
            probe.elapsed_s = round(time.time() - started, 3)
            probe.verdict = "unknown"
            probe.error = f"{type(exc).__name__}: {str(exc)[:200]}"
            trace.append(probe)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAYS[attempt])
            continue
        except cffi.exceptions.ImpersonateError as exc:
            last_error = exc
            probe.elapsed_s = round(time.time() - started, 3)
            probe.verdict = "unknown"
            probe.error = f"unsupported_impersonate:{impersonate}"
            trace.append(probe)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAYS[attempt])
            continue
        except cffi.exceptions.RequestException as exc:
            last_error = exc
            probe.elapsed_s = round(time.time() - started, 3)
            probe.verdict = "unknown"
            probe.error = f"{type(exc).__name__}: {str(exc)[:200]}"
            trace.append(probe)
            break

    return _error_result(
        url=url,
        status_code=0,
        error=str(last_error),
        trace=trace,
    )


def _flatten_tls_candidates(profile: dict[str, object]) -> list[str]:
    groups = profile.get("tls_impersonate_candidates") or [["safari", "chrome"]]
    out: list[str] = []
    for group in groups:
        if isinstance(group, str):
            out.append(group)
        else:
            try:
                out.extend(str(item) for item in group)  # type: ignore[arg-type]
            except TypeError:
                continue
    avoid = set(str(item) for item in (profile.get("tls_impersonate_avoid") or []))
    deduped: list[str] = []
    for candidate in out:
        if candidate in avoid or candidate in deduped:
            continue
        deduped.append(candidate)
    return deduped or ["safari", "chrome"]


def _jitter_between_grid_attempts() -> None:
    min_ms = int(_os.environ.get("WEB_READER_GRID_JITTER_MS_MIN", "150"))
    max_ms = int(_os.environ.get("WEB_READER_GRID_JITTER_MS_MAX", "400"))
    if min_ms <= 0 and max_ms <= 0:
        return
    if max_ms < min_ms:
        max_ms = min_ms
    time.sleep(random.uniform(min_ms / 1000.0, max_ms / 1000.0))


def _run_grid_attempt(
    *,
    url: str,
    transform_name: str,
    impersonate: str,
    referer_strategy: str,
    user_agent: str,
    extra_headers: dict[str, str] | None,
    cookies: dict[str, str] | None,
    no_verify: bool,
    encoding: str,
    allow_private: bool,
    timeout: int,
    success_selectors: list[str] | None,
    known_bad_sizes: list[int] | None,
) -> tuple[FetchAttempt, dict[str, object] | None, object | None]:
    attempt = FetchAttempt(
        phase="grid",
        url=url,
        url_transform=transform_name,
        impersonate=impersonate,
        referer=referer_strategy,
    )
    started = time.time()
    uv = _get_url_validator()
    try:
        uv.validate_url(url, allow_private=allow_private)
        # Grid attempts are stateless single HTTP tries; no cookie-warming hop is applied.
        session = _make_session(impersonate, cookies)
        headers = _build_headers(
            url,
            user_agent=user_agent,
            impersonate=impersonate,
            extra_headers=extra_headers,
            referer_strategy=referer_strategy,
        )
        response = _follow_redirects(
            session,
            "GET",
            url,
            cookies=cookies if cookies else None,
            allow_private=allow_private,
            headers=headers,
            timeout=timeout,
            verify=not no_verify,
            stream=True,
        )
        attempt.status = int(getattr(response, "status_code", 0) or 0)
        content_bytes, body_size, body_error = _read_response_bytes(response)
        attempt.body_size = body_size
        if body_error:
            attempt.verdict = "blocked"
            attempt.reasons = ["body_too_large"]
            attempt.error = body_error
            return attempt, None, None

        decoded, detected_encoding = _decode_response(response, content_bytes, encoding)
        validation = _validate_response(
            response,
            decoded,
            len(content_bytes),
            success_selectors=success_selectors,
            known_bad_sizes=known_bad_sizes,
        )
        attempt.verdict = validation.verdict.value
        attempt.reasons = validation.reasons
        attempt.body_size = validation.body_size or len(content_bytes)
        if validation.ok:
            return (
                attempt,
                _result_from_response(
                    response,
                    content_bytes,
                    decoded,
                    detected_encoding,
                    challenge=validation,
                ),
                validation,
            )
        return (
            attempt,
            _error_result(
                url=str(getattr(response, "url", url)),
                status_code=attempt.status,
                error=f"Challenge detected: {validation.verdict.value}",
                size=len(content_bytes),
                encoding=detected_encoding,
                content=decoded,
                challenge=validation,
            ),
            validation,
        )
    except cffi.exceptions.ImpersonateError:
        attempt.verdict = "unknown"
        attempt.error = f"unsupported_impersonate:{impersonate}"
        return attempt, None, None
    except cffi.exceptions.RequestException as exc:
        attempt.verdict = "unknown"
        attempt.error = f"{type(exc).__name__}: {str(exc)[:200]}"
        return attempt, None, None
    except (uv.SSRFError, ValueError) as exc:  # type: ignore[name-defined]
        attempt.verdict = "unknown"
        attempt.error = f"{type(exc).__name__}: {str(exc)[:200]}"
        return attempt, None, None
    finally:
        attempt.elapsed_s = round(time.time() - started, 3)


def _escalate_grid(
    *,
    original_url: str,
    user_agent: str,
    extra_headers: dict[str, str] | None,
    cookies: dict[str, str] | None,
    no_verify: bool,
    encoding: str,
    allow_private: bool,
    timeout: int,
    success_selectors: list[str] | None,
    base_impersonate: str,
    base_referer: str,
    max_attempts: int,
    first_response: object,
    first_decoded: str,
    first_body_size: int,
    trace: list[FetchAttempt],
) -> dict[str, object]:
    waf_detector = _get_waf_detector()
    url_transforms = _get_url_transforms()
    profiles = waf_detector._load_profiles()
    first_adapter = _ValidationResponse(first_response, first_decoded, first_body_size)
    hits = waf_detector.detect(first_adapter, profiles=profiles)
    profile_used: str | None = None
    best_result: dict[str, object] | None = None
    best_validation: object | None = None
    attempts_used = 0

    load_error = waf_detector.last_load_error()
    if load_error:
        trace.append(
            FetchAttempt(
                phase="grid",
                url=original_url,
                url_transform="profile_loader",
                impersonate=base_impersonate,
                referer="",
                verdict="unknown",
                error=f"profiles_fallback: {load_error}",
            )
        )

    for hit in hits[:3]:
        if attempts_used >= max_attempts:
            break
        profile_id = str(hit.profile_id)
        profile_used = profile_id
        profile = waf_detector.load_profile(profile_id, profiles=profiles)
        tls_candidates = _flatten_tls_candidates(profile)
        referer_order = list(profile.get("referer_strategies") or ["self_root"])
        transform_order = list(profile.get("url_transform_order") or ["original"])
        known_bad_sizes = profile.get("known_bad_sizes") or None

        for transform_name, transformed_url in url_transforms.iter_transformed(
            original_url,
            transform_order,
        ):
            for tls in tls_candidates:
                for referer_strategy in referer_order:
                    if attempts_used >= max_attempts:
                        break
                    if (
                        transform_name == "original"
                        and tls == base_impersonate
                        and referer_strategy == base_referer
                    ):
                        continue
                    attempt, result, validation = _run_grid_attempt(
                        url=transformed_url,
                        transform_name=transform_name,
                        impersonate=tls,
                        referer_strategy=str(referer_strategy),
                        user_agent=user_agent,
                        extra_headers=extra_headers,
                        cookies=cookies,
                        no_verify=no_verify,
                        encoding=encoding,
                        allow_private=allow_private,
                        timeout=timeout,
                        success_selectors=success_selectors,
                        known_bad_sizes=known_bad_sizes,  # type: ignore[arg-type]
                    )
                    trace.append(attempt)
                    attempts_used += 1
                    if result is not None:
                        result["trace"] = [item.to_dict() for item in trace]
                        result["waf_profile"] = profile_id
                        best_result = result
                        best_validation = validation
                        if not result.get("error"):
                            return result
                    _jitter_between_grid_attempts()

    if best_result is not None:
        best_result["trace"] = [item.to_dict() for item in trace]
        best_result["waf_profile"] = profile_used or best_result.get("waf_profile", "")
        if best_result.get("error"):
            best_result["error"] = (
                f"{best_result['error']}; curl_cffi grid exhausted. "
                "JS challenge may require Lightpanda --dynamic-only or hyve MCP web_browse.render."
            )
        return best_result

    return _error_result(
        url=original_url,
        status_code=int(getattr(first_response, "status_code", 0) or 0),
        error=(
            "curl_cffi grid exhausted without a usable response. "
            "JS challenge may require Lightpanda --dynamic-only or hyve MCP web_browse.render."
        ),
        size=first_body_size,
        content=first_decoded,
        trace=trace,
        challenge=best_validation,
        profile_used=profile_used,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace | None:
    """Parse CLI arguments. Returns None and exits with code 2 if --url missing."""
    parser = argparse.ArgumentParser(
        description="Fetch a webpage with Korean-optimized headers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    parser.add_argument("--url", default=None, help="URL to fetch")
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--encoding",
        default="auto",
        help="Character encoding (default: auto-detect)",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent string (default: aligned with --impersonate)",
    )
    parser.add_argument(
        "--impersonate",
        default=DEFAULT_IMPERSONATE,
        help=f"curl_cffi TLS impersonation target (default: {DEFAULT_IMPERSONATE})",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_GRID_ATTEMPTS,
        help=f"Max WAF grid attempts after the first probe (default: {DEFAULT_MAX_GRID_ATTEMPTS})",
    )
    parser.add_argument(
        "--header",
        action="append",
        dest="headers",
        metavar="KEY: VALUE",
        help="Extra header in 'Key: Value' format (repeatable)",
    )
    parser.add_argument(
        "--cookie",
        action="append",
        dest="cookies",
        metavar="name=value",
        help="Cookie in 'name=value' format (repeatable)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        default=False,
        help="Disable SSL certificate verification",
    )
    parser.add_argument(
        "--allow-private",
        action="store_true",
        default=False,
        help="Allow private/loopback IP addresses (disables SSRF protection)",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        default=False,
        help="Print curl_cffi attempt trace JSON to stderr",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Returns:
        0 on success, 1 on network/HTTP error, 2 on invalid args.
    """
    args = _parse_args(argv)

    if args.url is None:
        print("Error: --url is required", file=sys.stderr)
        return 2

    # Parse extra headers
    extra_headers: dict[str, str] = {}
    if args.headers:
        for h in args.headers:
            if ": " in h:
                k, v = h.split(": ", 1)
                extra_headers[k.strip()] = v.strip()
            elif ":" in h:
                k, v = h.split(":", 1)
                extra_headers[k.strip()] = v.strip()

    # Parse cookies — each --cookie arg may contain multiple pairs separated by "; "
    cookies: dict[str, str] = {}
    if args.cookies:
        import re as _re
        for c in args.cookies:
            for pair in _re.split(r";\s*", c):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    cookies[k.strip()] = v.strip()

    try:
        result = fetch_url(
            args.url,
            timeout=args.timeout,
            user_agent=args.user_agent,
            extra_headers=extra_headers or None,
            cookies=cookies or None,
            no_verify=args.no_verify,
            encoding=args.encoding,
            allow_private=args.allow_private,
            impersonate=args.impersonate,
            max_attempts=args.max_attempts,
        )
    except Exception as exc:
        # SSRFError (ValueError 서브클래스)를 포함한 검증 오류
        uv = _get_url_validator()
        if isinstance(exc, uv.SSRFError) or isinstance(exc, ValueError):
            print(f"Error: SSRF 차단 — {exc}", file=sys.stderr)
            return 2
        raise

    status_code = int(result["status_code"])  # type: ignore[arg-type]
    final_url = str(result["url"])
    detected_encoding = str(result["encoding"])
    size = int(result["size"])  # type: ignore[arg-type]

    # Always write stats to stderr
    print(f"URL: {final_url}", file=sys.stderr)
    print(f"Status: {status_code}", file=sys.stderr)
    print(f"Encoding: {detected_encoding}", file=sys.stderr)
    print(f"Size: {size}", file=sys.stderr)
    if args.trace and "trace" in result:
        print("Trace:", file=sys.stderr)
        print(json.dumps(result["trace"], ensure_ascii=False, indent=2), file=sys.stderr)

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    if 400 <= status_code < 600:
        print(f"Error: HTTP {status_code}", file=sys.stderr)
        return 1

    content = str(result["content"])

    # NOTE: SPEC-WEBREADER-LIGHTEN-001 v3.0.0 — SPA 감지 / deep-link advisory 블록 제거.
    # SPA 의심 페이지는 hyve MCP web_browse.render (SPEC-WEB-MCP-002) 로 위임.
    # 본 fetch_html.py 는 정적 fetch 단일 책임만 유지.

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
