#!/usr/bin/env python3
"""Openverse(CC·퍼블릭도메인 이미지) 검색·다운로드 — 라이선스-프리 이미지 소스.

Openverse 는 Creative Commons/WordPress 가 운영하는 공식 오픈-라이선스 미디어 API 다.
키 불요·표준 라이브러리(urllib)만 사용하며, 라이선스/출처/저작자 메타를 네이티브로 준다.
스크래핑이 아니다(레포 web-search 스킬이 배제하는 SERP 스크래핑 부류와 다름).

pixel_art.py 의 `search` 오퍼레이션이 이 모듈을 호출해 후보 이미지를 내려받고, 에이전트가
미리보기·확인한 뒤 pixelate 로 넘긴다.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from pixelate import PixelArtError  # 통일된 에러 봉투 재사용

API = "https://api.openverse.org/v1/images/"
_UA = "hyve-pixel-art/0.2 (+https://github.com/itda-skills/hyve; license-free image search)"
_TIMEOUT = 25
# 저작자 표시(attribution)가 필요 없는 퍼블릭도메인 등가 라이선스.
_PUBLIC_DOMAIN = {"cc0", "pdm"}
_EXT = {"jpg": ".jpg", "jpeg": ".jpg", "png": ".png", "webp": ".webp", "gif": ".gif", "bmp": ".bmp"}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise PixelArtError("SEARCH_FAILED",
                            f"Openverse 검색에 실패했습니다: {e}",
                            {"suggestion": "잠시 후 재시도하거나 질의어를 바꾸세요. 검색이 계속 실패하면 imagegen 으로 생성하세요."}) from e


def _download(url: str, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)


def _ext_for(result: dict) -> str:
    ft = (result.get("filetype") or "").lower()
    if ft in _EXT:
        return _EXT[ft]
    path = urllib.parse.urlparse(result.get("url") or "").path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in _EXT.values() or ext in _EXT else ".jpg"


def search(query: str, count: int, license_type: str, min_width: int) -> list[dict]:
    """Openverse 이미지 검색(메타만). 결과가 없으면 NO_RESULTS."""
    if not query or not query.strip():
        raise PixelArtError("INVALID_PARAM", "'query' 가 비어 있습니다.", {"param": "query"})
    params = {
        "q": query.strip(),
        "page_size": max(count * 3, count),  # min_width 필터 여유분
        "license_type": license_type,
        "mature": "false",
    }
    data = _get_json(API + "?" + urllib.parse.urlencode(params))
    results = data.get("results") or []
    if min_width > 0:
        results = [r for r in results if (r.get("width") or 0) >= min_width]
    if not results:
        raise PixelArtError("NO_RESULTS",
                            f"'{query}' 에 대한 라이선스-프리 이미지를 찾지 못했습니다.",
                            {"suggestion": "질의어를 더 일반적으로 바꾸거나 --min-width 를 낮추세요. 그래도 없으면 imagegen 으로 생성하세요.",
                             "total": data.get("result_count", 0)})
    return results


def search_and_download(query: str, output_dir: str, count: int = 4,
                        license_type: str = "commercial,modification",
                        min_width: int = 256) -> list[dict]:
    """검색 후 상위 count 개 후보를 내려받아 로컬 경로·라이선스 메타를 반환한다."""
    results = search(query, count, license_type, min_width)
    os.makedirs(output_dir, exist_ok=True)
    out: list[dict] = []
    errors: list[str] = []
    for i, r in enumerate(results):
        if len(out) >= count:
            break
        url = r.get("url")
        if not url:
            continue
        dest = os.path.join(output_dir, f"candidate-{len(out) + 1}{_ext_for(r)}")
        try:
            _download(url, dest)
        except Exception as e:  # noqa: BLE001 — 개별 실패는 스킵, 전량 실패만 에러
            errors.append(f"{url}: {e}")
            continue
        lic = (r.get("license") or "").lower()
        out.append({
            "path": dest,
            "title": r.get("title") or "",
            "license": lic,
            "license_version": r.get("license_version") or "",
            "license_url": r.get("license_url") or "",
            "requires_attribution": lic not in _PUBLIC_DOMAIN,
            "attribution": (r.get("attribution") or "").strip(),
            "creator": r.get("creator") or "",
            "source": r.get("source") or "",
            "source_url": r.get("foreign_landing_url") or r.get("url") or "",
            "width": r.get("width"),
            "height": r.get("height"),
        })
    if not out:
        raise PixelArtError("DOWNLOAD_FAILED",
                            "후보 이미지를 내려받지 못했습니다.",
                            {"errors": errors[:5]})
    return out
