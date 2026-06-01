"""display_location.py - 매장 내 진열 위치 조회 (REQ-005).

selIntPdStDispInfo POST(productId+storeCode), **AES 인증**. ref-daiso
`tools/getDisplayLocation.ts`(fetchDisplayLocation) 포팅.

데이터 함정(§2-D):
  - stairNo는 음수 문자열("-2", 지하층) → 문자열 그대로 보존(int 변환 금지).
  - zoneNo/storeErp도 문자열로 보존. storeErp 누락 시 storeCode로 대체.

이 기능은 순수 AES(degrade 불가) — AuthError는 그대로 전파해 CLI exit 6이 된다.
무인증 폴백 소스가 없으므로 인증 실패 시 의미 있는 결과를 만들 수 없기 때문이다.
"""
from __future__ import annotations

from typing import Any

import api
from auth import authed_post_json
from errors import ArgumentError


def _str_or(value: Any, default: str = "") -> str:
    """값을 문자열로 보존한다. None이면 default. 음수/숫자 문자열도 그대로."""
    if value is None:
        return default
    return str(value)


def get_display_location(
    product_id: str,
    store_code: str,
    *,
    timeout: float = 30.0,
    user_agent: str = api.DEFAULT_USER_AGENT,
    throttle: float = 0.0,
) -> dict[str, Any]:
    """productId + storeCode로 매장 내 진열 위치를 조회한다 (REQ-005, AES 인증).

    Args:
        product_id: 상품 ID(PD_NO). 빈 값 → ArgumentError(exit 2).
        store_code: 매장 코드(strCd). 빈 값 → ArgumentError(exit 2).
        timeout / user_agent / throttle: 네트워크 옵션(AES UA 일관성 위해 전달).

    Returns:
        {
          product_id, store_code, has_location,
          locations: [{zone_no, stair_no, store_erp}],
          auth: {method: "daiso-aes", performed: True},  # 결과 반환 = AES 인증 수행됨
          message?,   # success=False 또는 위치 없음일 때
        }

    Raises:
        ArgumentError: product_id 또는 store_code가 비었을 때.
        AuthError: cryptography 미설치 또는 인증 거부(403). degrade 불가 — 전파(exit 6).
        AntiBotBlockError / DaisoFetchError: 기타 오류 전파.
    """
    if not product_id or not product_id.strip():
        raise ArgumentError("상품 ID를 입력해주세요.")
    if not store_code or not store_code.strip():
        raise ArgumentError("매장 코드를 입력해주세요.")

    data = authed_post_json(
        api.DISPLAY_LOCATION,
        {"pdNo": product_id, "strCd": store_code},
        user_agent=user_agent,
        timeout=timeout,
        throttle=throttle,
    )

    # success=False/부재 → 위치 없음 + 응답 메시지 (L-1: ref `!data.success`, 부재=falsy).
    if not isinstance(data, dict) or not bool(data.get("success")):
        message = None
        if isinstance(data, dict):
            message = data.get("message")
        return {
            "product_id": product_id,
            "store_code": store_code,
            "has_location": False,
            "locations": [],
            "message": message,
            # 여기 도달했다는 건 AES 인증 호출이 200을 받았다는 뜻(서버가 위치 없음 응답).
            "auth": {"method": "daiso-aes", "performed": True},
        }

    rows = data.get("data")
    locations: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, dict):
                continue
            locations.append(
                {
                    "zone_no": _str_or(item.get("zoneNo")),
                    # stairNo는 음수 문자열("-2") 보존 — int 변환 금지.
                    "stair_no": _str_or(item.get("stairNo")),
                    "store_erp": _str_or(item.get("storeErp"), store_code),
                }
            )

    result: dict[str, Any] = {
        "product_id": product_id,
        "store_code": store_code,
        "has_location": len(locations) > 0,
        "locations": locations,
        # 진열위치는 순수 AES — 결과가 있다는 건 인증 조회를 통과했다는 뜻.
        "auth": {"method": "daiso-aes", "performed": True},
    }
    if not locations:
        result["message"] = "해당 매장에서 상품 진열 위치를 찾을 수 없습니다."
    return result
