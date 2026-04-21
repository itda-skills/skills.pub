from __future__ import annotations

import re
import urllib.parse
from typing import Any

from law_api import _SEARCH_URL, _SERVICE_URL, LawAPIError, _fetch_xml
from law_cache import cache_get, cache_key, cache_set

OLD_AND_NEW_SEARCH_SUBDIR = "old_and_new_search"
OLD_AND_NEW_DETAIL_SUBDIR = "old_and_new"


def _deduplicate_csv_text(value: str) -> str:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        return value

    unique_parts: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part in seen:
            continue
        seen.add(part)
        unique_parts.append(part)
    return ", ".join(unique_parts)


def search_old_and_new(
    query: str,
    oc: str = "test",
    display: int = 20,
    page: int = 1,
    *,
    no_cache: bool = False,
) -> list[dict[str, Any]]:
    display = max(1, min(100, display))

    key = cache_key(
        {
            "query": query,
            "oc": oc,
            "display": display,
            "page": page,
        }
    )
    if not no_cache:
        try:
            cached = cache_get(OLD_AND_NEW_SEARCH_SUBDIR, key)
            if isinstance(cached, list):
                return cached
        except Exception:
            pass

    params = {
        "OC": oc,
        "target": "oldAndNew",
        "type": "XML",
        "query": query,
        "display": str(display),
        "page": str(page),
    }
    url = _SEARCH_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    results: list[dict[str, Any]] = []
    for el in root.findall("oldAndNew"):
        results.append(
            {
                "comparison_name": el.findtext("신구법명", ""),
                "comparison_id": el.findtext("신구법ID", ""),
                "comparison_serial": el.findtext("신구법일련번호", ""),
                "promulgation_date": el.findtext("공포일자", ""),
                "promulgation_no": el.findtext("공포번호", ""),
                "revision_type": el.findtext("제개정구분명", ""),
                "ministry_name": _deduplicate_csv_text(el.findtext("소관부처명", "")),
                "law_type": el.findtext("법령구분명", ""),
                "effective_date": el.findtext("시행일자", ""),
            }
        )

    if not no_cache:
        try:
            cache_set(OLD_AND_NEW_SEARCH_SUBDIR, key, results, ttl=3600)
        except Exception:
            pass

    return results


def _clean_compare_article_text(value: str) -> str:
    value = value.replace("<P>", "").replace("</P>", "")
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def _parse_detail_info(info: Any, prefix: str) -> dict[str, Any]:
    if info is None:
        return {
            f"{prefix}_law_name": "",
            f"{prefix}_law_id": "",
            f"{prefix}_mst": "",
            f"{prefix}_effective_date": "",
            f"{prefix}_promulgation_date": "",
            f"{prefix}_promulgation_no": "",
            f"{prefix}_current": "",
            f"{prefix}_revision_type": "",
            f"{prefix}_law_type": "",
        }

    return {
        f"{prefix}_law_name": info.findtext("법령명", ""),
        f"{prefix}_law_id": info.findtext("법령ID", ""),
        f"{prefix}_mst": info.findtext("법령일련번호", ""),
        f"{prefix}_effective_date": info.findtext("시행일자", ""),
        f"{prefix}_promulgation_date": info.findtext("공포일자", ""),
        f"{prefix}_promulgation_no": info.findtext("공포번호", ""),
        f"{prefix}_current": info.findtext("현행여부", ""),
        f"{prefix}_revision_type": info.findtext("제개정구분명", ""),
        f"{prefix}_law_type": info.findtext("법종구분", ""),
    }


def _parse_detail_articles(root: Any, section_name: str) -> list[str]:
    section = root.find(section_name)
    if section is None:
        return []

    results: list[str] = []
    for article in section.findall("조문"):
        text = _clean_compare_article_text((article.text or "").strip())
        if text:
            results.append(text)
    return results


def get_old_and_new_detail(
    comparison_id: str | None = None,
    mst: str | None = None,
    oc: str = "test",
    *,
    no_cache: bool = False,
) -> dict[str, Any]:
    if not comparison_id and not mst:
        raise LawAPIError("신구법 상세 조회에는 --id 또는 --mst 중 하나가 필요합니다.")

    key = cache_key({"comparison_id": comparison_id, "mst": mst, "oc": oc})
    if not no_cache:
        try:
            cached = cache_get(OLD_AND_NEW_DETAIL_SUBDIR, key)
            if isinstance(cached, dict):
                return cached
        except Exception:
            pass

    params = {
        "OC": oc,
        "target": "oldAndNew",
        "type": "XML",
    }
    if comparison_id:
        params["ID"] = comparison_id
    if mst:
        params["MST"] = mst

    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    result = {
        **_parse_detail_info(root.find("구조문_기본정보"), "old"),
        **_parse_detail_info(root.find("신조문_기본정보"), "new"),
        "old_articles": _parse_detail_articles(root, "구조문목록"),
        "new_articles": _parse_detail_articles(root, "신조문목록"),
    }

    if not no_cache:
        try:
            cache_set(OLD_AND_NEW_DETAIL_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result
