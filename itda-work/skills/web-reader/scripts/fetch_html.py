#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_html.py - HTTP fetcher optimized for Korean websites.

Uses the requests library for HTTP. Supports encoding detection,
retry logic, custom headers/cookies, and SSL bypass.

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
import os as _os
import re
import sys
import time
from urllib.parse import urlparse, urljoin

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 or later is required.")

try:
    import requests
except ImportError:
    sys.exit(
        "requests is required. Install with: pip install requests"
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_DELAYS = [1, 3]  # seconds for each retry attempt


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
# Cookie-aware redirect follower (REQ-1.3)
# ---------------------------------------------------------------------------


def _follow_redirects(
    session: "requests.Session",
    method: str,
    url: str,
    cookies: dict[str, str] | None = None,
    allow_private: bool = False,
    max_redirects: int = 10,
    **kwargs: object,
) -> "requests.Response":
    """Cross-domain 리다이렉트 시 쿠키를 원본 도메인에만 전송한다.

    requests의 기본 리다이렉트 처리는 쿠키를 모든 도메인에 전달한다.
    이 함수는 allow_redirects=False로 수동으로 리다이렉트를 추적하며,
    도메인이 변경되면 쿠키를 제거한다.

    Args:
        session: requests.Session 인스턴스.
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
        if not getattr(resp, "is_redirect", False):
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
) -> dict[str, object]:
    """Fetch a URL with retry logic and Korean-optimized headers.

    Args:
        url: Target URL to fetch.
        timeout: Request timeout in seconds.
        user_agent: User-Agent string.
        extra_headers: Additional HTTP headers.
        cookies: Cookies to include in the request.
        no_verify: If True, skip SSL certificate verification.
        encoding: Encoding override ('auto' for detection).
        allow_private: If True, allow private/loopback IP addresses (SSRF bypass).

    Returns:
        Dict with keys: content, encoding, status_code, url, size.

    Raises:
        SystemExit(1): On unrecoverable network/HTTP error.
        SSRFError: On SSRF-unsafe URL (caller should handle).
    """
    # SSRF 방지 URL 검증
    uv = _get_url_validator()
    uv.validate_url(url, allow_private=allow_private)

    session = requests.Session()

    # Build Korean-optimized base headers
    headers: dict[str, str] = {
        "User-Agent": user_agent,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Auto-derive Referer from URL domain
    try:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass

    # Apply extra headers
    if extra_headers:
        headers.update(extra_headers)

    # Set cookies on session
    if cookies:
        session.cookies.update(cookies)

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
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
            )

            status_code = response.status_code

            # REQ-2.9: Response body 50MB 크기 제한
            MAX_BODY_BYTES = 50 * 1024 * 1024  # 50MB
            content_length_str = response.headers.get("Content-Length", "0") or "0"
            try:
                content_length = int(content_length_str)
            except ValueError:
                content_length = 0
            if content_length > MAX_BODY_BYTES:
                return {
                    "content": "",
                    "encoding": "utf-8",
                    "status_code": status_code,
                    "url": response.url,
                    "size": content_length,
                    "error": f"Response body too large: {content_length} bytes (max 50MB)",
                }

            # Retry on 5xx
            if 500 <= status_code < 600:
                last_error = Exception(f"HTTP {status_code}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAYS[attempt])
                continue

            # 4xx is a hard error
            if 400 <= status_code < 500:
                return {
                    "content": "",
                    "encoding": "utf-8",
                    "status_code": status_code,
                    "url": response.url,
                    "size": 0,
                    "error": f"HTTP {status_code}",
                }

            # chunked transfer 대응: Content-Length가 없어도 50MB 제한 적용
            # Content-Length 헤더가 없거나 0인 경우 iter_content로 스트리밍 체크
            if content_length == 0:
                # Content-Length 없음 → iter_content로 스트리밍 읽기
                chunks: list[bytes] = []
                total_size = 0
                try:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not isinstance(chunk, bytes):
                            break  # mock 등에서 bytes가 아닌 경우 중단
                        total_size += len(chunk)
                        if total_size > MAX_BODY_BYTES:
                            return {
                                "content": "",
                                "encoding": "utf-8",
                                "status_code": status_code,
                                "url": response.url,
                                "size": total_size,
                                "error": f"Response body too large: >{MAX_BODY_BYTES} bytes (max 50MB)",
                            }
                        chunks.append(chunk)
                except (AttributeError, TypeError):
                    chunks = []
                if chunks:
                    content_bytes = b"".join(chunks)
                else:
                    # iter_content 실패 또는 빈 결과 → fallback to .content
                    content_bytes = response.content
                    if isinstance(content_bytes, bytes) and len(content_bytes) > MAX_BODY_BYTES:
                        return {
                            "content": "",
                            "encoding": "utf-8",
                            "status_code": status_code,
                            "url": response.url,
                            "size": len(content_bytes),
                            "error": f"Response body too large: {len(content_bytes)} bytes (max 50MB)",
                        }
            else:
                content_bytes = response.content
            final_url = response.url

            # Detect encoding
            if encoding == "auto":
                http_charset: str | None = None
                content_type = response.headers.get("Content-Type", "")
                charset_match = re.search(
                    r"charset=([A-Za-z0-9_\-]+)", content_type
                )
                if charset_match:
                    http_charset = charset_match.group(1)
                detected_encoding = detect_encoding(
                    content_bytes, http_charset=http_charset
                )
            else:
                detected_encoding = encoding

            decoded = decode_content(content_bytes, detected_encoding)

            return {
                "content": decoded,
                "encoding": detected_encoding,
                "status_code": status_code,
                "url": final_url,
                "size": len(content_bytes),
            }

        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAYS[attempt])
            continue
        except requests.RequestException as exc:
            last_error = exc
            break

    return {
        "content": "",
        "encoding": "utf-8",
        "status_code": 0,
        "url": url,
        "size": 0,
        "error": str(last_error),
    }


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
        help="User-Agent string (default: Chrome Desktop)",
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

    if "error" in result and status_code == 0:
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
