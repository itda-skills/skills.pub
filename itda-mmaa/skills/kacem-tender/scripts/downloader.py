"""파일 다운로드 모듈.

User-Agent를 Chrome Desktop으로 고정하고 지수 백오프 재시도를 지원한다.
"""
from __future__ import annotations

import time
from pathlib import Path

import requests
import urllib3

# KACEM(446 포트)이 신뢰 체인 외 인증서를 제공하므로 SSL 검증을 비활성화한다.
# 운영 영향: KACEM 도메인 한정. 다른 호스트 호출은 본 스킬 범위 외.
# urllib3 InsecureRequestWarning 억제 — 매 호출마다 경고가 stderr를 어지럽히는 것을 방지.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SSL_VERIFY = False


# REQ-COLLECT-001: PC Chrome Desktop UA 고정
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_DEFAULT_HEADERS = {
    "User-Agent": CHROME_USER_AGENT,
    "Accept": "*/*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def make_headers(extra: dict | None = None) -> dict:
    """기본 헤더 + 추가 헤더를 합쳐 반환한다."""
    h = dict(_DEFAULT_HEADERS)
    if extra:
        h.update(extra)
    return h


def download_file(
    url: str,
    dest: Path,
    max_retries: int = 3,
    extra_headers: dict | None = None,
) -> Path:
    """URL에서 파일을 다운로드해 dest에 저장한다.

    실패 시 지수 백오프(1s/2s/4s)로 최대 max_retries회 재시도.
    0바이트 응답 및 max_retries 초과 시 예외 발생.

    # @MX:ANCHOR: [AUTO] 다운로드 진입점 — main에서 게시글별 호출
    # @MX:REASON: fan_in >= 3 (main, test_downloader, test_main)
    """
    headers = make_headers(extra_headers)
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30, verify=SSL_VERIFY)
            if resp.status_code >= 500:
                raise requests.HTTPError(f"서버 오류 {resp.status_code}")

            content = resp.content
            if len(content) == 0:
                raise ValueError("0바이트 응답 — 첨부 없음")

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            return dest

        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait)

    raise RuntimeError(f"다운로드 실패 (최대 재시도 초과): {url}") from last_exc
