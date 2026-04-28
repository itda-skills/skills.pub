"""itda-skills 데이터 경로 해석 유틸리티.

모든 스킬이 동일한 로직으로 환경(Claude Code / Cowork)에 따라
적절한 데이터 디렉토리를 결정한다.

경로 규칙:
  ITDA_DATA_ROOT 환경변수: {ITDA_DATA_ROOT}/{skill_name}/  (최우선)
  Claude Code:             {CWD}/.itda-skills/{skill_name}/
  Cowork + 마운트 O:       {CWD}/mnt/.itda-skills/{skill_name}/
  Cowork + 마운트 X:       {CWD}/.itda-skills/{skill_name}/

사용법:
  from itda_path import resolve_data_dir, resolve_cache_dir

  data = resolve_data_dir("law-korean")           # .itda-skills/law-korean/
  cache = resolve_cache_dir("law-korean")          # .itda-skills/law-korean/cache/
  profiles = resolve_data_dir("web-reader", "profiles")

테스트/CI에서 루트 경로 고정:
  ITDA_DATA_ROOT=/path/to/repo/.itda-skills python3 -m pytest ...
"""
from __future__ import annotations

import os
from pathlib import Path

_ITDA_DIR = ".itda-skills"
_MNT_DIR = "mnt"


def is_cowork() -> bool:
    """현재 Cowork 환경인지 여부를 반환한다."""
    return os.environ.get("CLAUDE_CODE_IS_COWORK") == "1"


def has_host_mount() -> bool:
    """Cowork에서 호스트 마운트(./mnt/)가 있는지 여부를 반환한다."""
    return Path(_MNT_DIR).is_dir()


def _base_dir() -> Path:
    """데이터 루트 디렉토리를 결정한다.

    ITDA_DATA_ROOT 환경변수가 설정된 경우 해당 경로를 절대경로로 반환한다.
    미설정 시 CWD 기준으로 환경을 감지하여 결정한다.
    """
    env_root = os.environ.get("ITDA_DATA_ROOT")
    if env_root:
        return Path(env_root).resolve()
    if is_cowork() and has_host_mount():
        return Path.cwd() / _MNT_DIR / _ITDA_DIR
    return Path.cwd() / _ITDA_DIR


def resolve_data_dir(skill_name: str, subdir: str = "") -> Path:
    """스킬의 데이터 디렉토리 경로를 결정하고 자동 생성한다.

    Args:
        skill_name: 스킬 이름 (예: "law-korean").
        subdir: 하위 디렉토리 (예: "cache"). 빈 문자열이면 스킬 루트.

    Returns:
        생성된 디렉토리의 절대 경로.
    """
    path = _base_dir() / skill_name
    if subdir:
        path = path / subdir

    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_cache_dir(skill_name: str) -> Path:
    """스킬의 캐시 디렉토리를 반환한다.

    캐시는 재생성 가능한 데이터이므로 Cowork 세션 종료 시 소멸해도 무방하다.
    그러나 호스트 마운트가 있으면 마운트 경로를 우선 사용하여
    세션 간 캐시를 공유한다.

    Args:
        skill_name: 스킬 이름 (예: "law-korean").

    Returns:
        생성된 캐시 디렉토리의 절대 경로.
    """
    return resolve_data_dir(skill_name, "cache")


def resolve_browsers_dir() -> Path:
    """Playwright 브라우저 바이너리 캐시 디렉토리를 반환한다.

    Cowork 환경에서 호스트 마운트가 있으면 영속 경로를 사용하여
    세션 간 바이너리를 공유한다 (재설치 방지).

    Returns:
        생성된 브라우저 캐시 디렉토리의 절대 경로.
    """
    path = _base_dir() / "browser" / "playwright"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_playwright_env() -> None:
    """Cowork 환경에서 Playwright 바이너리 영속성을 보장한다.

    PLAYWRIGHT_BROWSERS_PATH 환경변수를 설정하여
    Cowork + 호스트 마운트 시 세션 간 Chromium 바이너리를 공유한다.
    로컬 Claude Code에서는 기본 경로(~/.cache/ms-playwright/)를 사용하므로
    환경변수를 설정하지 않는다.

    Side effect:
        Cowork 환경에서 os.environ["PLAYWRIGHT_BROWSERS_PATH"]를 설정한다.
    """
    if not is_cowork():
        return
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(resolve_browsers_dir())
