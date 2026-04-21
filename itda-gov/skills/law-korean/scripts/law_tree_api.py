"""법령 체계도 API 모듈 — 법제처 DRF Open API (target=lsStmd).

SPEC: SPEC-LAW-004 FR-026
"""
from __future__ import annotations

import urllib.parse
from typing import Any

from law_api import _fetch_xml, LawAPIError, _SERVICE_URL
from law_cache import cache_get, cache_set, cache_key

# 캐시 서브디렉토리
LAW_TREE_SUBDIR = "law_tree"


def get_law_tree(
    law_id: str | None = None,
    mst: str | None = None,
    oc: str = "test",
    *,
    no_cache: bool = False,
) -> dict[str, Any]:
    """법령 체계도(상위/하위 법령 관계)를 조회한다.

    law_id 또는 mst 중 하나 이상을 반드시 전달해야 한다.

    Args:
        law_id: 법령 ID.
        mst: 법령 MST 번호.
        oc: 법제처 OC (사용자 ID).
        no_cache: True이면 캐시 우회.

    Returns:
        {law_name, law_id, children: [{law_name, law_type, law_id, children: []}, ...]} 딕셔너리.

    Raises:
        LawAPIError: law_id와 mst가 모두 None이거나 네트워크 오류 시.
    """
    if law_id is None and mst is None:
        raise LawAPIError("law_id 또는 mst 중 하나를 반드시 지정해야 합니다.")

    # 캐시 키
    key = cache_key({"law_id": law_id, "mst": mst, "oc": oc})
    if not no_cache:
        try:
            cached = cache_get(LAW_TREE_SUBDIR, key)
            if cached is not None:
                return cached
        except Exception:
            pass

    params: dict[str, str] = {
        "OC": oc,
        "target": "lsStmd",
        "type": "XML",
    }
    if law_id is not None:
        params["ID"] = law_id
    if mst is not None:
        params["MST"] = mst

    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    # 상위법령정보 파싱
    parent_info = root.find("상위법령정보")
    root_name = ""
    root_id = law_id or mst or ""
    if parent_info is not None:
        root_name = parent_info.findtext("법령명", "")
        root_id = parent_info.findtext("법령ID", root_id)

    # 하위법령정보 파싱
    children: list[dict[str, Any]] = []
    for child_el in root.findall("하위법령정보"):
        children.append({
            "law_name": child_el.findtext("법령명", ""),
            "law_type": child_el.findtext("법령종류", ""),
            "law_id": child_el.findtext("법령ID", ""),
            "children": [],  # 단일 레벨 응답이므로 빈 목록
        })

    result: dict[str, Any] = {
        "law_name": root_name,
        "law_id": root_id,
        "children": children,
    }

    if not no_cache:
        try:
            cache_set(LAW_TREE_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result
