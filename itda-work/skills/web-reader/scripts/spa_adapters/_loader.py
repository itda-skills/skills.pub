#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPA 어댑터 로더 — 매니페스트 화이트리스트 기반 안전 로딩.
SPEC-WEBREADER-006: AC-5 보안 검증 (매니페스트 미등록 어댑터 로드 거부).
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

# scripts/ 디렉토리를 sys.path에 자동 등록 (한 번만 실행)
# 어댑터 모듈 임포트 시 scripts/ 기준으로 탐색하기 위함
_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

# 기본 매니페스트 경로 (spa_adapters/manifest.json)
_DEFAULT_MANIFEST_PATH = Path(__file__).parent / "manifest.json"

# 매니페스트 각 어댑터 항목에 필수인 키 목록
_REQUIRED_ADAPTER_KEYS: tuple[str, ...] = (
    "name",
    "module",
    "domain_pattern",
    "framework",
    "default_page",
    "pages",
)

# 어댑터 모듈은 반드시 이 네임스페이스로 시작해야 함 (보안: 임의 모듈 로드 차단)
# @MX:NOTE: [AUTO] spa_adapters. 네임스페이스 제한은 AC-5 보안 요구사항.
#           이를 통해 어댑터가 os, subprocess 등 임의 모듈을 위장할 수 없도록 방지.
_ALLOWED_MODULE_PREFIX = "spa_adapters."

__all__ = [
    "AdapterNotFoundError",
    "AdapterManifestError",
    "load_manifest",
    "load_adapter",
    "list_available_adapters",
    "get_default_page",
]


class AdapterNotFoundError(Exception):
    """매니페스트에 등록되지 않은 어댑터를 요청했을 때 발생."""


class AdapterManifestError(Exception):
    """매니페스트 파일이 유효하지 않거나 읽기에 실패했을 때 발생."""


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    """
    어댑터 매니페스트 JSON을 읽고 기본 스키마를 검증한다.

    인자:
        path: 매니페스트 파일 경로. None이면 기본 경로 사용.

    반환:
        파싱된 매니페스트 dict

    예외:
        AdapterManifestError: 파일이 없거나, JSON 파싱 실패, 스키마 오류
    """
    manifest_path = path if path is not None else _DEFAULT_MANIFEST_PATH

    try:
        text = Path(manifest_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise AdapterManifestError(
            f"매니페스트 파일을 찾을 수 없습니다: {manifest_path}"
        )
    except OSError as exc:
        raise AdapterManifestError(
            f"매니페스트 파일 읽기 실패: {manifest_path} — {exc}"
        )

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterManifestError(
            f"매니페스트 JSON 파싱 실패: {manifest_path} — {exc}"
        )

    # 최상위 'adapters' 키 존재 여부 확인
    if "adapters" not in data:
        raise AdapterManifestError(
            "매니페스트에 'adapters' 키가 없습니다."
        )

    return data


def _validate_adapter_entry(entry: dict[str, Any]) -> None:
    """
    어댑터 항목의 필수 키 존재 여부를 검증한다.

    예외:
        AdapterManifestError: 필수 키 누락
    """
    for key in _REQUIRED_ADAPTER_KEYS:
        if key not in entry:
            raise AdapterManifestError(
                f"어댑터 항목에 필수 키 '{key}'가 없습니다: {entry}"
            )


# @MX:ANCHOR: [AUTO] load_adapter — 모든 어댑터 로딩의 단일 진입점
# @MX:REASON: [AUTO] SPEC-WEBREADER-006 AC-5; fetch_dynamic.py --adapter 옵션,
#             list_adapters.py, 테스트 코드 등 여러 곳에서 호출 예정 (fan_in >= 3).
#             매니페스트 화이트리스트 검증이 이 함수를 통해서만 수행되므로
#             bypass 없이 반드시 이 경로를 거쳐야 함.
def load_adapter(name: str, manifest: dict[str, Any] | None = None):
    """
    매니페스트에서 어댑터를 탐색하고 해당 모듈을 임포트하여 인스턴스를 반환한다.

    보안: manifest.json에 등록된 어댑터만 로드 가능 (AC-5).
    보안: module 값은 'spa_adapters.' 로 시작해야 함 (네임스페이스 보호).

    인자:
        name: 어댑터 이름 (manifest.json의 name 필드)
        manifest: 미리 로드된 매니페스트 dict. None이면 기본 파일 사용.

    반환:
        Adapter 인스턴스

    예외:
        AdapterNotFoundError: 매니페스트에 이름이 없을 때
        AdapterManifestError: 매니페스트 스키마 오류 또는 네임스페이스 위반
    """
    if manifest is None:
        manifest = load_manifest()

    # 최상위 구조 검증
    if "adapters" not in manifest:
        raise AdapterManifestError(
            "매니페스트에 'adapters' 키가 없습니다."
        )

    # 매니페스트에서 이름 검색
    entry = None
    for item in manifest["adapters"]:
        # 필수 키 검증 (루프 중 수행하여 잘못된 항목도 감지)
        _validate_adapter_entry(item)
        if item["name"] == name:
            entry = item
            break

    if entry is None:
        raise AdapterNotFoundError(
            f"어댑터 '{name}'이(가) 매니페스트에 등록되어 있지 않습니다."
        )

    # 모듈 네임스페이스 보호: spa_adapters. 로 시작해야 함
    module_path: str = entry["module"]
    if not module_path.startswith(_ALLOWED_MODULE_PREFIX):
        raise AdapterManifestError(
            f"어댑터 모듈 경로가 허용된 네임스페이스('{_ALLOWED_MODULE_PREFIX}')로 "
            f"시작하지 않습니다: '{module_path}'"
        )

    # 모듈 임포트 및 어댑터 클래스 탐색
    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        raise AdapterNotFoundError(
            f"어댑터 모듈 '{module_path}' 임포트 실패: {exc}"
        )

    # 모듈에서 Adapter 서브클래스 탐색 (이름 규칙: 클래스명에 'Adapter' 포함)
    from spa_adapters.base import Adapter

    adapter_class = None
    for attr_name in dir(mod):
        obj = getattr(mod, attr_name)
        try:
            if (
                isinstance(obj, type)
                and issubclass(obj, Adapter)
                and obj is not Adapter
            ):
                adapter_class = obj
                break
        except TypeError:
            continue

    if adapter_class is None:
        raise AdapterNotFoundError(
            f"모듈 '{module_path}'에서 Adapter 서브클래스를 찾을 수 없습니다."
        )

    return adapter_class()


def get_default_page(adapter_name: str, manifest: dict[str, Any] | None = None) -> str | None:
    """
    매니페스트에서 어댑터의 default_page 값을 반환한다.

    인자:
        adapter_name: 어댑터 이름 (manifest.json의 name 필드)
        manifest: 미리 로드된 매니페스트 dict. None이면 기본 파일 사용.

    반환:
        default_page 문자열, 또는 어댑터를 찾지 못하면 None.
    """
    if manifest is None:
        try:
            manifest = load_manifest()
        except AdapterManifestError:
            return None

    for item in manifest.get("adapters", []):
        if item.get("name") == adapter_name:
            return item.get("default_page")
    return None


def list_available_adapters(manifest: dict[str, Any] | None = None) -> list[dict]:
    """
    사용 가능한 어댑터 목록을 반환한다.

    인자:
        manifest: 미리 로드된 매니페스트 dict. None이면 기본 파일 사용.

    반환:
        어댑터 항목 dict의 리스트 (name, framework, default_page, pages 포함)
    """
    if manifest is None:
        manifest = load_manifest()

    adapters = manifest.get("adapters", [])
    return list(adapters)
