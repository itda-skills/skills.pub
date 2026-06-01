"""auth.py - 다이소 AES 경량 인증 (REQ-006).

매장별 재고(`selStrPkupStck`)와 진열위치(`selIntPdStDispInfo`)는 다이소가
난독화한 토큰 헤더를 요구한다(로그인/계정 우회가 아니라 공개 토큰 난독화 — NFR-2).

ref-daiso `services/daiso/client.ts`(createDaisoAuthContext / createDaisoAuthHeader)
알고리즘을 그대로 포팅한다(§2-C, 무수정 동작 확인):

  1. GET `/auth/request` → 본문=JWT token, 헤더 `X-DM-UID`=uid.
     ⚠️ 토큰은 **30초 만료** + 요청자 **IP·User-Agent 바인딩**이므로
     (a) 캐싱 금지 — 인증 호출 직전 발급(OQ-3),
     (b) `/auth/request`와 후속 인증 호출의 User-Agent 동일 강제(§2-B),
     (c) WebFetch 금지 — urllib 자체 GET으로 X-DM-UID 헤더를 직접 읽는다.
  2. token을 AES-128-CBC(PKCS7)로 암호화. key=UTF8("PRE_AUTH_ENC_KEY")(16B), 무작위 IV(16B).
  3. authValue = base64(iv) ∥ base64(ciphertext)  (구분자 없는 연결).
  4. 헤더 3종 + Content-Type:
       Authorization: Bearer <authValue>
       X-DM-UID: <uid>
       Cookie: DM_UID=<uid>
       Content-Type: application/json

graceful degrade(REQ-007): `cryptography` 미설치 시 AES 기능은 AuthError로
명확히 안내하고, 무인증 코어는 영향받지 않는다(이 모듈을 import만 해도
무인증 기능이 깨지면 안 되므로 try/except로 감싼다).
"""
from __future__ import annotations

import base64
import os
import urllib.error
import urllib.request
from typing import Any

import api
import http_util
from http_util import http_post_json
from errors import AntiBotBlockError, AuthError, DaisoFetchError

# cryptography는 선택 의존(NFR-1). 미설치여도 모듈 import는 성공해야 한다 —
# 무인증 코어(products/stores)가 이 모듈을 우회하더라도 전체가 깨지면 안 되기 때문.
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding

    _HAS_CRYPTO = True
except ImportError:  # pragma: no cover - 설치 환경에선 도달하지 않음
    _HAS_CRYPTO = False

#: AES-128 키. UTF-8 16바이트 정확(=AES-128). ref `client.ts:DAISO_AUTH_KEY`.
_AUTH_KEY = b"PRE_AUTH_ENC_KEY"
assert len(_AUTH_KEY) == 16, "AES-128 키는 정확히 16바이트여야 합니다"

#: AES 블록 크기(bit). PKCS7 패딩 단위.
_BLOCK_BITS = 128


def crypto_available() -> bool:
    """`cryptography`가 import 가능한지 여부.

    False면 AES 인증 기능(매장별 재고·진열위치)을 쓸 수 없다(REQ-007 degrade).
    """
    return _HAS_CRYPTO


def request_token(
    *,
    user_agent: str = api.DEFAULT_USER_AGENT,
    timeout: float = 30.0,
    throttle: float = 0.0,
) -> tuple[str, str]:
    """`/auth/request`에서 (token, dm_uid)를 발급받는다.

    응답 본문 헤더 `X-DM-UID`를 읽어야 하므로 http_util(본문만 반환)이 아니라
    urllib을 직접 사용한다. User-Agent는 인자 그대로 전송한다(§2-B: 후속
    인증 호출과 동일 UA 필수 — 토큰이 요청자 UA에 바인딩됨).

    M-2: urllib을 직접 쓰더라도 http_util.apply_throttle로 module-level throttle
    시계를 공유해 GET 직전 최소 간격을 보장한다(봇 차단 예방).

    Args:
        user_agent: User-Agent 헤더. 후속 인증 호출과 반드시 동일해야 한다.
        timeout: 타임아웃(초).
        throttle: 직전 호출과의 최소 간격(초). GET 직전 적용.

    Returns:
        (token, dm_uid). token은 strip된 JWT 문자열, dm_uid는 X-DM-UID 헤더값.

    Raises:
        AuthError: token이 비었거나 X-DM-UID 헤더가 없거나 네트워크 오류일 때.
    """
    # M-2: GET 직전 throttle 적용(http_util과 동일 시계 공유).
    http_util.apply_throttle(throttle)
    req = urllib.request.Request(
        api.AUTH_REQUEST,
        method="GET",
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # L-4: 무제한 read 방지 — http_util.read_capped로 상한 적용.
            raw = http_util.read_capped(resp, api.AUTH_REQUEST)
            # X-DM-UID 헤더(대소문자 무관). HTTPMessage.get은 case-insensitive.
            dm_uid = (resp.headers.get("X-DM-UID") or "").strip()
    except urllib.error.HTTPError as exc:  # 4xx/5xx
        # /auth/request는 공개 익명 엔드포인트라 403/429는 인증실패가 아니라 봇차단(exit 4).
        if exc.code in (403, 429):
            raise AntiBotBlockError(
                f"인증 토큰 발급이 차단된 듯합니다 (HTTP {exc.code}): {api.AUTH_REQUEST}",
                status_code=exc.code,
            ) from exc
        raise AuthError(
            f"인증 토큰 발급 실패 (HTTP {exc.code} {exc.reason}): {api.AUTH_REQUEST}"
        ) from exc
    except DaisoFetchError as exc:  # L-4: 과대 응답
        raise AuthError(f"인증 토큰 발급 응답이 비정상적으로 큽니다: {exc}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise AuthError(
            f"인증 토큰 발급 중 네트워크 오류 ({reason}): {api.AUTH_REQUEST}"
        ) from exc

    token = raw.decode("utf-8", errors="replace").strip()
    if not token:
        raise AuthError("인증 토큰이 비어 있습니다.")
    if not dm_uid:
        raise AuthError("인증 응답에 X-DM-UID 헤더가 없습니다.")
    return token, dm_uid


def encrypt_token(token: str, *, iv: bytes | None = None) -> str:
    """token을 AES-128-CBC(PKCS7)로 암호화하고 `base64(iv)∥base64(ct)`를 반환한다.

    iv를 주지 않으면 매 호출 `os.urandom(16)`으로 무작위 생성한다(프로덕션 경로).
    테스트는 고정 iv를 넘겨 결정론적 라운드트립을 검증한다.

    Args:
        token: 암호화할 JWT 문자열.
        iv: 16바이트 초기화 벡터. None이면 무작위.

    Returns:
        base64(iv)와 base64(ciphertext)를 구분자 없이 이어붙인 authValue 문자열.
        base64(iv)는 항상 앞 24글자(16바이트 → base64 24글자)이다.

    Raises:
        AuthError: `cryptography` 미설치 시.
        ValueError: iv 길이가 16이 아닐 때.
    """
    if not _HAS_CRYPTO:
        raise AuthError(
            "매장별 재고/진열위치는 cryptography가 필요합니다. "
            "uv pip install --system cryptography"
        )
    if iv is None:
        iv = os.urandom(16)
    if len(iv) != 16:
        raise ValueError("IV는 정확히 16바이트여야 합니다.")

    padder = padding.PKCS7(_BLOCK_BITS).padder()
    padded = padder.update(token.encode("utf-8")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(_AUTH_KEY), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    return base64.b64encode(iv).decode("ascii") + base64.b64encode(ciphertext).decode(
        "ascii"
    )


def build_auth_headers(
    *,
    user_agent: str = api.DEFAULT_USER_AGENT,
    timeout: float = 30.0,
    throttle: float = 0.0,
) -> dict[str, str]:
    """AES 인증 헤더 3종(+Content-Type)을 만든다.

    토큰은 호출 직전 발급한다(캐싱 금지 — 30초 만료, OQ-3). request_token과
    동일 user_agent를 쓴다(§2-B IP/UA 바인딩).

    Args:
        user_agent: `/auth/request`와 후속 인증 호출에 공통 적용할 UA.
        timeout: 타임아웃(초).
        throttle: `/auth/request` GET 직전 적용할 최소 간격(초, M-2).

    Returns:
        {"Authorization": "Bearer <authValue>", "X-DM-UID": <uid>,
         "Cookie": "DM_UID=<uid>", "Content-Type": "application/json"}.

    Raises:
        AuthError: `cryptography` 미설치, 토큰 발급/암호화 실패 시.
    """
    if not _HAS_CRYPTO:
        raise AuthError(
            "매장별 재고/진열위치는 cryptography가 필요합니다. "
            "uv pip install --system cryptography"
        )

    token, dm_uid = request_token(
        user_agent=user_agent, timeout=timeout, throttle=throttle
    )
    auth_value = encrypt_token(token)
    return {
        "Authorization": f"Bearer {auth_value}",
        "X-DM-UID": dm_uid,
        "Cookie": f"DM_UID={dm_uid}",
        "Content-Type": "application/json",
    }


def authed_post_json(
    url: str,
    payload: Any,
    *,
    user_agent: str = api.DEFAULT_USER_AGENT,
    timeout: float = 30.0,
    throttle: float = 0.0,
) -> Any:
    """AES 인증 헤더를 붙여 POST JSON을 호출한다.

    build_auth_headers(같은 user_agent)로 헤더를 만들고 http_post_json에
    extra_headers로 주입한다. 이 인증 엔드포인트의 403은 봇 차단이 아니라
    Unauthorized(인증 실패)이므로(프로브 5a/6a 확인), http_util이 올리는
    AntiBotBlockError(exit 4)를 AuthError(exit 6)로 변환한다.

    Args:
        url: 인증 엔드포인트 URL(STORE_INVENTORY / DISPLAY_LOCATION).
        payload: POST 본문(dict 또는 list).
        user_agent: build_auth_headers와 http_post_json에 공통 적용.
        timeout: 타임아웃(초).
        throttle: 직전 호출과의 최소 간격(초). GET(/auth/request)·POST 두 외부호출
            모두에 적용된다(M-2).

    Returns:
        파싱된 JSON 응답.

    Raises:
        AuthError: 인증 헤더 생성 실패 또는 403(Unauthorized).
        DaisoFetchError: 기타 네트워크/파싱 오류.
    """
    # M-2: 토큰 발급 GET에도 throttle 적용(build_auth_headers→request_token 경유).
    headers = build_auth_headers(
        user_agent=user_agent, timeout=timeout, throttle=throttle
    )
    try:
        return http_post_json(
            url,
            payload,
            user_agent=user_agent,
            extra_headers=headers,
            timeout=timeout,
            throttle=throttle,
        )
    except AntiBotBlockError as exc:
        # 이 엔드포인트의 403만 인증 거부(Unauthorized, 프로브 5a/6a 확인) → AuthError.
        # 429 등 rate-limit은 봇차단이므로 exit 4로 그대로 전파한다(degrade로 삼키지 않음).
        if exc.status_code == 403:
            raise AuthError(
                "인증 거부(403). 토큰 만료/UA·IP 불일치 가능"
            ) from exc
        raise
