from __future__ import annotations

import urllib.parse
from typing import Any

from law_api import _SEARCH_URL, _fetch_xml
from law_cache import cache_get, cache_key, cache_set

LSTRM_SEARCH_SUBDIR = "lstrm_search"
LSTRM_RLT_SUBDIR = "lstrm_rlt"
JO_RLT_LSTRM_SUBDIR = "jo_rlt_lstrm"
LSTRM_RLT_JO_SUBDIR = "lstrm_rlt_jo"


def _extract_mst_from_link(link: str) -> str:
    if not link:
        return ""
    parsed = urllib.parse.urlparse(link)
    params = urllib.parse.parse_qs(parsed.query)
    return params.get("MST", [""])[0]


def _extract_query_param(link: str, name: str) -> str:
    if not link:
        return ""
    parsed = urllib.parse.urlparse(link)
    params = urllib.parse.parse_qs(parsed.query)
    return params.get(name, [""])[0]


def _format_article_number(article_no: str, branch_no: str) -> str:
    if not article_no:
        return ""

    try:
        base = str(int(article_no))
    except ValueError:
        base = article_no.lstrip("0") or article_no

    branch = branch_no.lstrip("0")
    if branch:
        return f"{base}의{int(branch)}"
    return base


def _deduplicate_items(
    items: list[dict[str, Any]], key_fields: tuple[str, ...]
) -> list[dict[str, Any]]:
    unique_items: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for item in items:
        key = tuple(str(item.get(field, "")) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items


def search_legal_terms(
    query: str,
    oc: str = "test",
    display: int = 20,
    page: int = 1,
    homonym_yn: str | None = None,
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
            "homonym_yn": homonym_yn,
        }
    )
    if not no_cache:
        try:
            cached = cache_get(LSTRM_SEARCH_SUBDIR, key)
            if isinstance(cached, list):
                return cached
        except Exception:
            pass

    params = {
        "OC": oc,
        "target": "lstrmAI",
        "type": "XML",
        "query": query,
        "display": str(display),
        "page": str(page),
    }
    if homonym_yn:
        params["homonymYn"] = homonym_yn

    url = _SEARCH_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    results: list[dict[str, Any]] = []
    for term_el in root.findall("법령용어"):
        term_relation_link = term_el.findtext("용어간관계링크", "")
        results.append(
            {
                "term_id": term_el.attrib.get("id", ""),
                "term_name": term_el.findtext("법령용어명", ""),
                "homonym_yn": term_el.findtext("동음이의어존재여부", ""),
                "note": term_el.findtext("비고", ""),
                "term_relation_link": term_relation_link,
                "article_relation_link": term_el.findtext("조문간관계링크", ""),
                "mst": _extract_mst_from_link(term_relation_link),
            }
        )

    if not no_cache:
        try:
            cache_set(LSTRM_SEARCH_SUBDIR, key, results, ttl=3600)
        except Exception:
            pass

    return results


def get_legal_term_relations(
    mst: str | None = None,
    oc: str = "test",
    *,
    no_cache: bool = False,
) -> dict[str, Any]:
    from law_api import LawAPIError, _SERVICE_URL

    if not mst:
        raise LawAPIError("법령용어 관계 조회에는 --mst가 필요합니다.")

    key = cache_key({"mst": mst, "oc": oc})
    if not no_cache:
        try:
            cached = cache_get(LSTRM_RLT_SUBDIR, key)
            if isinstance(cached, dict):
                return cached
        except Exception:
            pass

    params = {
        "OC": oc,
        "target": "lstrmRlt",
        "type": "XML",
        "MST": mst,
    }
    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    term_el = root.find("법령용어")
    result: dict[str, Any] = {
        "term_id": "",
        "term_name": "",
        "note": "",
        "relation_count": 0,
        "relations": [],
    }

    if term_el is not None:
        result["term_id"] = term_el.attrib.get("id", "")
        result["term_name"] = term_el.findtext("법령용어명", "")
        result["note"] = term_el.findtext("비고", "")

        relations: list[dict[str, Any]] = []
        for relation_el in term_el.findall("연계용어"):
            term_relation_link = relation_el.findtext("용어간관계링크", "")
            relations.append(
                {
                    "related_id": relation_el.attrib.get("id", ""),
                    "everyday_term_name": relation_el.findtext("일상용어명", ""),
                    "relation_code": relation_el.findtext("용어관계코드", ""),
                    "relation_name": relation_el.findtext("용어관계", ""),
                    "everyday_term_link": relation_el.findtext("일상용어조회링크", ""),
                    "term_relation_link": term_relation_link,
                    "related_mst": _extract_mst_from_link(term_relation_link),
                }
            )

        relations = _deduplicate_items(relations, ("related_mst", "relation_code"))
        result["relations"] = relations
        result["relation_count"] = len(relations)

    if not no_cache:
        try:
            cache_set(LSTRM_RLT_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result


def get_legal_term_article_relations(
    mst: str | None = None,
    oc: str = "test",
    *,
    no_cache: bool = False,
) -> dict[str, Any]:
    from law_api import LawAPIError, _SERVICE_URL

    if not mst:
        raise LawAPIError("법령용어 조문 관계 조회에는 --mst가 필요합니다.")

    key = cache_key({"mst": mst, "oc": oc})
    if not no_cache:
        try:
            cached = cache_get(LSTRM_RLT_JO_SUBDIR, key)
            if isinstance(cached, dict):
                return cached
        except Exception:
            pass

    params = {
        "OC": oc,
        "target": "lstrmRltJo",
        "type": "XML",
        "MST": mst,
    }
    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    term_el = root.find("법령용어")
    result: dict[str, Any] = {
        "term_id": "",
        "term_name": "",
        "note": "",
        "term_relation_link": "",
        "article_count": 0,
        "linked_articles": [],
    }

    if term_el is not None:
        result["term_id"] = term_el.attrib.get("id", "")
        result["term_name"] = term_el.findtext("법령용어명", "")
        result["note"] = term_el.findtext("비고", "")
        result["term_relation_link"] = term_el.findtext("용어간관계링크", "")

        linked_articles: list[dict[str, Any]] = []
        for article_el in term_el.findall("연계법령"):
            article_term_link = article_el.findtext("조문연계용어링크", "")
            linked_articles.append(
                {
                    "relation_id": article_el.attrib.get("id", ""),
                    "law_name": article_el.findtext("법령명", ""),
                    "article_number": _format_article_number(
                        article_el.findtext("조번호", ""),
                        article_el.findtext("조가지번호", ""),
                    ),
                    "article_content": article_el.findtext("조문내용", ""),
                    "term_type_code": article_el.findtext("용어구분코드", ""),
                    "term_type_name": article_el.findtext("용어구분", ""),
                    "article_term_link": article_term_link,
                    "law_id": _extract_query_param(article_term_link, "ID"),
                    "jo": _extract_query_param(article_term_link, "JO"),
                }
            )

        linked_articles = _deduplicate_items(
            linked_articles, ("law_id", "jo", "term_type_code")
        )
        result["linked_articles"] = linked_articles
        result["article_count"] = len(linked_articles)

    if not no_cache:
        try:
            cache_set(LSTRM_RLT_JO_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result


def get_article_legal_term_relations(
    law_id: str | None = None,
    jo: str | None = None,
    oc: str = "test",
    *,
    no_cache: bool = False,
) -> dict[str, Any]:
    from law_api import LawAPIError, _SERVICE_URL

    if not law_id or not jo:
        raise LawAPIError("조문-법령용어 관계 조회에는 --id와 --jo가 필요합니다.")

    key = cache_key({"law_id": law_id, "jo": jo, "oc": oc})
    if not no_cache:
        try:
            cached = cache_get(JO_RLT_LSTRM_SUBDIR, key)
            if isinstance(cached, dict):
                return cached
        except Exception:
            pass

    params = {
        "OC": oc,
        "target": "joRltLstrm",
        "type": "XML",
        "ID": law_id,
        "JO": jo,
    }
    url = _SERVICE_URL + "?" + urllib.parse.urlencode(params)
    root = _fetch_xml(url)

    article_el = root.find("법령조문")
    result: dict[str, Any] = {
        "relation_id": "",
        "law_id": law_id,
        "jo": jo,
        "law_name": "",
        "article_number": "",
        "article_content": "",
        "term_count": 0,
        "linked_terms": [],
    }

    if article_el is not None:
        result["relation_id"] = article_el.attrib.get("id", "")
        result["law_name"] = article_el.findtext("법령명", "")
        result["article_number"] = _format_article_number(
            article_el.findtext("조번호", ""),
            article_el.findtext("조가지번호", ""),
        )
        result["article_content"] = article_el.findtext("조문내용", "")

        linked_terms: list[dict[str, Any]] = []
        for term_el in article_el.findall("연계용어"):
            term_relation_link = term_el.findtext("용어간관계링크", "")
            article_relation_link = term_el.findtext("용어연계조문링크", "")
            linked_terms.append(
                {
                    "related_id": term_el.attrib.get("id", ""),
                    "term_name": term_el.findtext("법령용어명", ""),
                    "note": term_el.findtext("비고", ""),
                    "term_type_code": term_el.findtext("용어구분코드", ""),
                    "term_type_name": term_el.findtext("용어구분", ""),
                    "term_relation_link": term_relation_link,
                    "article_relation_link": article_relation_link,
                    "mst": _extract_mst_from_link(term_relation_link),
                }
            )

        linked_terms = _deduplicate_items(linked_terms, ("mst", "term_type_code"))
        result["linked_terms"] = linked_terms
        result["term_count"] = len(linked_terms)

    if not no_cache:
        try:
            cache_set(JO_RLT_LSTRM_SUBDIR, key, result, ttl=86400)
        except Exception:
            pass

    return result
