"""web_reader_client.py - fetch_html.py subprocess 래퍼.

REQ-BLOGREADER-006: 모든 HTTP 페치는 이 모듈을 통해 fetch_html.py subprocess로 처리한다.
직접 HTTP 라이브러리(requests, httpx, urllib.request 등) import 금지.

fetch_html.py CLI 인터페이스:
  --url URL
  --user-agent UA
  --header "Key: Value"  (반복 가능)
  --timeout N
  (주의: --max-retries 없음 — 전달하지 않을 것)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from errors import AntiBotBlockError, BlogNotFoundError, BlogReaderError

# @MX:ANCHOR: [AUTO] fetch_html — HTTP 페치 단일 진입점 (fan_in >= 3 예상)
# @MX:REASON: 모든 HTTP 호출이 이 함수를 통과해야 한다 (REQ-006.2)

# REQ-006.4: 기본 모바일 Safari UA
DEFAULT_MOBILE_SAFARI_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)

# fetch_html.py 경로 탐색
# 1. 환경변수 ITDA_BLOG_READER_FETCH_HTML (테스트 override)
# 2. 현재 스킬 기준 상대 경로: ../../web-reader/scripts/fetch_html.py
_THIS_DIR = Path(__file__).parent.resolve()
_DEFAULT_FETCH_HTML_PATH = (
    _THIS_DIR.parent.parent / "web-reader" / "scripts" / "fetch_html.py"
)


def _get_fetch_html_path() -> Path:
    """fetch_html.py 경로를 결정한다.

    환경변수 ITDA_BLOG_READER_FETCH_HTML이 설정되어 있으면 그 경로를 사용하고,
    없으면 web-reader 스킬의 기본 위치를 사용한다.
    """
    env_path = os.environ.get("ITDA_BLOG_READER_FETCH_HTML")
    if env_path:
        return Path(env_path)
    return _DEFAULT_FETCH_HTML_PATH


# anti-bot 차단 감지 마커 (REQ-009.2)
_ANTI_BOT_MARKERS = (
    "403",
    "429",
    "captcha",
    "too many requests",
    "forbidden",
    "bot detected",
    "access denied",
)

# ISS-0571abc3 / ISS-b6f00417:
# HTTP 200 본문 스캔 전용 마커. 네이버 표준 차단 문구만 보수적으로 선정.
# '403'/'429' 같은 모호한 일반 substring은 포함하지 않는다.
# ISS-b6f00417 근본 수정: 직전 세션이 _ANTI_BOT_MARKERS ∪ _ANTI_BOT_BODY_MARKERS 합집합을
# 200 본문 스캔에 사용하도록 과교정했으나, 일반 기술 블로그 글이 '403'/'429'/'captcha' 단어를
# 포함하면 오탐 AntiBotBlockError(exit 4)가 발생한다.
# 올바른 수정: 200 본문 스캔은 _ANTI_BOT_BODY_MARKERS 단독으로만 진행.
_ANTI_BOT_BODY_MARKERS = (
    "비정상적인 접근",
    "자동입력 방지",
    "보안 문자를 입력",
    "로봇이 아님을 확인",
    # 명백한 영문 차단 페이지 전용 마커만 보강 (ISS-0571abc3 원 우려 대응)
    # ISS-b6f00417 완전 수정: "automated access" 같은 일반 기술 표현은 제거.
    # 기준: 정상 블로그 본문("automated access to APIs", "automated access logging")에
    # 등장 가능한 2~3단어 substring은 모두 제거. 완전한 차단 전용 문구만 유지.
    "please complete the captcha",
    "verify you are human",
)

# 비공개/삭제 감지 마커 (REQ-009.4)
_NOT_FOUND_MARKERS = (
    "404",
    "not found",
    "비공개",
    "삭제된",
    "존재하지 않는",
)


def _detect_error_type(stdout: str, stderr: str) -> type[BlogReaderError]:
    """응답 본문에서 오류 유형을 감지한다.

    Returns:
        AntiBotBlockError, BlogNotFoundError, BlogReaderError 중 하나.
    """
    combined = (stdout + " " + stderr).lower()

    # anti-bot 마커 우선 확인
    for marker in _ANTI_BOT_MARKERS:
        if marker in combined:
            return AntiBotBlockError

    # 비공개/삭제 마커 확인
    for marker in _NOT_FOUND_MARKERS:
        if marker in combined:
            return BlogNotFoundError

    return BlogReaderError


def fetch_html(
    url: str,
    *,
    user_agent: str = DEFAULT_MOBILE_SAFARI_UA,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> str:
    """fetch_html.py subprocess를 호출해서 HTML을 가져온다.

    Args:
        url: 가져올 URL.
        user_agent: User-Agent 헤더 (기본: 모바일 Safari).
        headers: 추가 헤더 딕셔너리 (예: {"Referer": "..."}).
        timeout: 요청 타임아웃 (초).

    Returns:
        fetch_html.py stdout (HTML 또는 JSON 문자열).

    Raises:
        AntiBotBlockError: HTTP 403/429 또는 캡차 감지 시.
        BlogNotFoundError: HTTP 404 또는 비공개/삭제 페이지 감지 시.
        BlogReaderError: 기타 오류 시.
    """
    fetch_path = _get_fetch_html_path()

    cmd = [
        sys.executable,
        str(fetch_path),
        "--url", url,
        "--user-agent", user_agent,
        "--timeout", str(timeout),
    ]

    # 추가 헤더 처리
    if headers:
        for key, value in headers.items():
            cmd.extend(["--header", f"{key}: {value}"])

    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout + 5,  # subprocess 자체 타임아웃은 약간 더 길게
        )
    except subprocess.TimeoutExpired as exc:
        raise BlogReaderError(
            f"fetch_html.py 타임아웃 ({timeout}초 초과): {url}"
        ) from exc
    except FileNotFoundError as exc:
        raise BlogReaderError(
            f"fetch_html.py를 찾을 수 없습니다: {fetch_path}"
        ) from exc

    if result.returncode != 0:
        error_cls = _detect_error_type(result.stdout, result.stderr)
        if error_cls is AntiBotBlockError:
            raise AntiBotBlockError(
                f"anti-bot 차단 감지 — 우회 시도하지 않음: {url}\n"
                f"응답: {result.stdout[:200]}"
            )
        elif error_cls is BlogNotFoundError:
            raise BlogNotFoundError(
                f"블로그 또는 포스트를 찾을 수 없습니다 (비공개/삭제 가능): {url}\n"
                f"응답: {result.stdout[:200]}"
            )
        else:
            raise BlogReaderError(
                f"fetch_html.py 실패 (returncode={result.returncode}): {url}\n"
                f"stdout: {result.stdout[:200]}\n"
                f"stderr: {result.stderr[:200]}"
            )

    # ISS-b6f00417 근본 수정: HTTP 200 본문 스캔은 _ANTI_BOT_BODY_MARKERS 단독으로만 진행.
    # _ANTI_BOT_MARKERS('403','429','captcha' 등)는 기술 블로그 본문에서 자주 등장하는
    # 일반 단어라 200 본문 스캔에 합치면 오탐이 발생한다.
    # _ANTI_BOT_BODY_MARKERS에는 명백한 차단 페이지 전용 마커만 포함되어 있으므로 안전하다.
    # status-line/비200 경로의 _ANTI_BOT_MARKERS 사용(위 _detect_error_type)은 그대로 유지.
    stdout_lower = result.stdout.lower()
    for marker in _ANTI_BOT_BODY_MARKERS:
        if marker.lower() in stdout_lower:
            raise AntiBotBlockError(
                f"HTTP 200이지만 anti-bot/캡차 페이지 감지 ({marker!r}): {url}\n"
                f"응답 앞부분: {result.stdout[:200]}"
            )

    return result.stdout
