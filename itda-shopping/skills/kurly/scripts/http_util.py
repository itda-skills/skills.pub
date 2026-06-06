"""http_util.py - urllib.request 기반 공용 HTTP 래퍼 (stdlib만).

모든 외부 호출은 여기를 거친다. 마켓컬리는 비로그인 공개 표면이라 GET만 쓴다
(daiso의 POST/AES 인증 경로는 없음).

설계 원칙:
  - GET-json(검색/count) / GET-text(goods HTML) 2종.
  - 403/429 감지 시 errors.AntiBotBlockError(exit 4) — 봇 차단 우회 안 함.
  - 기타 HTTP/네트워크 오류는 errors.KurlyFetchError(exit 1).
  - 일시 오류(타임아웃·일시적 네트워크 오류·5xx) 1회 재시도.
  - throttle: 호출 간 최소 지연(module-level 마지막 호출 시각 기준). time.monotonic 사용.
  - 예외는 raise로 전파.

L-5(수용): `_last_call_ts`는 모듈 전역이라 멀티스레드에서 안전하지 않다. 본 스킬은
단일스레드 CLI 스코프에서만 동작하므로 수용한다.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from errors import AntiBotBlockError, KurlyFetchError
from api import DEFAULT_USER_AGENT

#: anti-bot으로 간주하는 HTTP 상태코드.
_ANTIBOT_STATUS = frozenset({403, 429})

#: 재시도 대상 5xx 상태코드.
_RETRYABLE_STATUS = frozenset({500, 502, 503, 504})

#: 응답 본문 최대 바이트. 초과 시 KurlyFetchError로 거부 — 무제한 read 방지.
#: 컬리 검색 응답은 ~150KB, goods HTML은 ~125KB 수준이라 10MiB면 충분히 넉넉하다.
MAX_RESPONSE_BYTES = 10 * 1024 * 1024

#: throttle 계산용 — 가장 최근 HTTP 호출 시각(time.monotonic 기준). 프로세스 전역.
_last_call_ts: float = 0.0


def _apply_throttle(throttle: float) -> None:
    """직전 호출과의 간격이 throttle 미만이면 그 차이만큼 sleep한다."""
    global _last_call_ts
    if throttle > 0:
        elapsed = time.monotonic() - _last_call_ts
        wait = throttle - elapsed
        if wait > 0:
            time.sleep(wait)
    _last_call_ts = time.monotonic()


def _build_request(
    url: str,
    *,
    method: str,
    user_agent: str,
    accept: str,
) -> urllib.request.Request:
    """공통 헤더가 붙은 urllib Request를 만든다.

    Referer를 kurly.com으로 둔다 — 웹앱이 쓰는 공개 표면이므로 동일 출처에서
    온 것처럼 보내는 것이 자연스럽다(봇 차단 우회가 아니라 정상 요청 형태).
    """
    headers: dict[str, str] = {
        "User-Agent": user_agent,
        "Accept": accept,
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": "https://www.kurly.com/",
    }
    return urllib.request.Request(url, method=method, headers=headers)


def read_capped(resp: Any, url: str) -> bytes:
    """응답 본문을 MAX_RESPONSE_BYTES 상한까지 읽는다.

    상한+1 바이트를 읽어 초과를 감지한다 — 초과 시 KurlyFetchError로 거부해
    무제한 read를 방지한다.

    Args:
        resp: urlopen 응답 객체(read 메서드 보유).
        url: 오류 메시지용 URL.

    Returns:
        본문 바이트(상한 이하).

    Raises:
        KurlyFetchError: 본문이 MAX_RESPONSE_BYTES를 초과할 때.
    """
    raw = resp.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise KurlyFetchError(
            f"응답이 너무 큽니다 (>{MAX_RESPONSE_BYTES} bytes). 거부합니다: {url}"
        )
    return raw


def _execute(req: urllib.request.Request, *, timeout: float) -> bytes:
    """Request를 실행하고 응답 본문 바이트를 반환한다.

    일시 오류(타임아웃·URLError·5xx)는 1회 재시도한다.
    403/429 → AntiBotBlockError, 그 외 실패 → KurlyFetchError.
    본문은 MAX_RESPONSE_BYTES 상한까지만 읽는다.
    """
    last_exc: Exception | None = None
    for attempt in range(2):  # 최초 1회 + 재시도 1회
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return read_capped(resp, req.full_url)
        except urllib.error.HTTPError as exc:
            if exc.code in _ANTIBOT_STATUS:
                raise AntiBotBlockError(
                    f"봇 차단으로 보이는 응답입니다 (HTTP {exc.code}). "
                    f"우회하지 않고 종료합니다: {req.full_url}",
                    status_code=exc.code,
                ) from exc
            if exc.code in _RETRYABLE_STATUS and attempt == 0:
                last_exc = exc
                time.sleep(0.25)
                continue
            raise KurlyFetchError(
                f"HTTP 오류 {exc.code} ({exc.reason}): {req.full_url}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt == 0:
                time.sleep(0.25)
                continue
            reason = getattr(exc, "reason", exc)
            raise KurlyFetchError(
                f"네트워크 오류로 요청에 실패했습니다 ({reason}): {req.full_url}"
            ) from exc
    # 루프를 빠져나오는 경로(이론상 도달하지 않음 — 재시도 후 raise됨).
    raise KurlyFetchError(  # pragma: no cover
        f"요청에 실패했습니다: {req.full_url} ({last_exc})"
    )


def _parse_json(raw: bytes, url: str) -> Any:
    """응답 바이트를 JSON으로 파싱한다. 실패 시 KurlyFetchError."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise KurlyFetchError(
            f"JSON 파싱에 실패했습니다 ({exc.msg}): {url}"
        ) from exc


def _with_params(url: str, params: dict[str, Any] | None) -> str:
    """쿼리 파라미터를 URL에 인코딩해 붙인다. None 값은 빈 문자열로 보낸다."""
    if not params:
        return url
    encoded = urllib.parse.urlencode(
        {k: ("" if v is None else str(v)) for k, v in params.items()}
    )
    sep = "&" if ("?" in url) else "?"
    return f"{url}{sep}{encoded}"


def http_get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> Any:
    """GET 요청 후 JSON(dict 또는 list)을 반환한다.

    Args:
        url: 요청 URL.
        params: 쿼리 파라미터(dict). None 가능.
        timeout: 타임아웃(초).
        user_agent: User-Agent 헤더.
        throttle: 직전 호출과의 최소 간격(초).

    Returns:
        파싱된 JSON(dict | list).

    Raises:
        AntiBotBlockError: 403/429 (exit 4).
        KurlyFetchError: 기타 네트워크/파싱 오류 (exit 1).
    """
    _apply_throttle(throttle)
    full_url = _with_params(url, params)
    req = _build_request(
        full_url,
        method="GET",
        user_agent=user_agent,
        accept="application/json, text/plain, */*",
    )
    raw = _execute(req, timeout=timeout)
    return _parse_json(raw, full_url)


def http_get_text(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> str:
    """GET 요청 후 본문 텍스트(str)를 반환한다 (goods 상세 HTML 등).

    응답 인코딩은 UTF-8로 디코드하되, 디코드 실패 문자는 대체(errors='replace')한다.

    Args:
        url: 요청 URL.
        params: 쿼리 파라미터(dict). None 가능.
        timeout: 타임아웃(초).
        user_agent: User-Agent 헤더.
        throttle: 직전 호출과의 최소 간격(초).

    Returns:
        응답 본문 문자열.

    Raises:
        AntiBotBlockError: 403/429 (exit 4).
        KurlyFetchError: 기타 네트워크 오류 (exit 1).
    """
    _apply_throttle(throttle)
    full_url = _with_params(url, params)
    req = _build_request(
        full_url,
        method="GET",
        user_agent=user_agent,
        accept="text/html,application/xhtml+xml",
    )
    raw = _execute(req, timeout=timeout)
    return raw.decode("utf-8", errors="replace")
