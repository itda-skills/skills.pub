"""파일 기반 LRU 캐시 — itda_path.resolve_cache_dir("law-korean")에 저장.

구현: SPEC-LAW-003 FR-010
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from itda_path import resolve_cache_dir

# 캐시 서브디렉토리 이름
SEARCH_SUBDIR = "search"
LAW_SUBDIR = "law"

# 디렉토리당 최대 캐시 항목 수
MAX_ENTRIES_PER_DIR = 100

# 캐시 디렉토리 경로 (지연 초기화)
# @MX:NOTE: [AUTO] SHA-256 기반 캐시 키 생성. 파라미터 순서 무관 (sort_keys=True).
_CACHE_DIR: Path | None = None


def _get_cache_dir() -> Path:
    """캐시 디렉토리 경로를 반환한다 (지연 초기화)."""
    global _CACHE_DIR
    if _CACHE_DIR is None:
        _CACHE_DIR = resolve_cache_dir("law-korean")
    return _CACHE_DIR


def cache_key(params: dict) -> str:
    """파라미터 dict → SHA-256 해시 키 생성.

    Args:
        params: 캐시 키를 생성할 파라미터 딕셔너리.

    Returns:
        64자 SHA-256 16진수 해시 문자열.
    """
    serialized = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()


def _cache_file(subdir: str, key: str) -> Path:
    """캐시 파일의 절대 경로를 반환한다."""
    return _get_cache_dir() / subdir / f"{key}.json"


def cache_get(subdir: str, key: str) -> dict[str, Any] | None:
    """캐시 조회. 만료됐거나 없으면 None을 반환한다.

    Args:
        subdir: 캐시 서브디렉토리 (예: "search", "law").
        key: 캐시 키 (64자 해시).

    Returns:
        캐시된 데이터 dict. 없거나 만료되면 None.
    """
    path = _cache_file(subdir, key)
    try:
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        if time.time() > entry["timestamp"] + entry["ttl"]:
            return None
        return entry["data"]
    except Exception:
        return None


def cache_set(subdir: str, key: str, data: Any, ttl: int = 86400) -> None:
    """캐시 저장. MAX_ENTRIES_PER_DIR 초과 시 가장 오래된 파일 삭제.

    실패해도 예외를 발생시키지 않는다 (옵티미스틱 캐싱).

    Args:
        subdir: 캐시 서브디렉토리 (예: "search", "law").
        key: 캐시 키 (64자 해시).
        data: 저장할 데이터.
        ttl: 캐시 유효 시간(초). 기본 86400초(1일).
    """
    try:
        subdir_path = _get_cache_dir() / subdir
        subdir_path.mkdir(parents=True, exist_ok=True)

        # 용량 초과 시 가장 오래된 파일 삭제
        files = sorted(subdir_path.glob("*.json"), key=lambda p: p.stat().st_mtime)
        while len(files) >= MAX_ENTRIES_PER_DIR:
            files[0].unlink(missing_ok=True)
            files = files[1:]

        # 캐시 파일 원자적 저장 (temp → os.replace)
        path = subdir_path / f"{key}.json"
        tmp_path = subdir_path / f"{key}.json.tmp"
        entry = {"timestamp": time.time(), "ttl": ttl, "data": data}
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
        os.replace(str(tmp_path), str(path))
    except Exception:
        # 캐시 저장 실패는 무시 (옵티미스틱)
        pass


def cache_clear(subdir: str | None = None) -> int:
    """캐시 삭제. 삭제된 파일 수를 반환한다.

    Args:
        subdir: 삭제할 서브디렉토리. None이면 전체 삭제.

    Returns:
        삭제된 파일 수.
    """
    cache_dir = _get_cache_dir()
    count = 0
    if subdir is not None:
        target = cache_dir / subdir
        if target.exists():
            for f in target.glob("*.json"):
                f.unlink(missing_ok=True)
                count += 1
    else:
        if cache_dir.exists():
            for sub in cache_dir.iterdir():
                if sub.is_dir():
                    for f in sub.glob("*.json"):
                        f.unlink(missing_ok=True)
                        count += 1
    return count
