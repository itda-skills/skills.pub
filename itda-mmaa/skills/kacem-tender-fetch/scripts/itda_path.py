"""itda-skills 데이터 경로 해석 유틸리티.

모든 환경(macOS · Linux · Windows 로컬, Cowork 샌드박스)에서
동일한 후보 경로 열거(candidate-path enumeration) 알고리즘으로
적절한 데이터 디렉토리를 결정한다.

환경 분기 로직을 완전히 제거하고
단일 _candidate_roots() 함수로 통합했다 (SPEC-DATAPATH-002).

경로 우선순위:
  1. ITDA_DATA_ROOT 환경변수 (테스트·CI 오버라이드)
  2. /proc/mounts에서 추출한 rw 마운트 포인트 (Linux 한정)
  3. $HOME/mnt/ 하위 비시스템 디렉토리 (Cowork 호스트 마운트)
  4. $HOME (semi-persistent fallback)
  5. Path.cwd() (macOS/Windows 로컬 fallback)

데이터 경로 패턴:
  <root>/.itda-skills/<skill_name>/[subdir]

사용법:
  from itda_path import resolve_data_dir, resolve_cache_dir

  data = resolve_data_dir("law-korean")           # <root>/.itda-skills/law-korean/
  cache = resolve_cache_dir("law-korean")          # <root>/.itda-skills/law-korean/cache/
  profiles = resolve_data_dir("web-reader", "profiles")

테스트/CI에서 루트 경로 고정:
  ITDA_DATA_ROOT=/path/to/dir python3 -m pytest ...
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ITDA_DIR = ".itda-skills"

# $HOME/mnt/ 에서 제외할 시스템 디렉토리 이름
_MNT_EXCLUDE_NAMES = {"outputs", "uploads"}

# /proc/mounts 에서 제외할 마운트 포인트 prefix
_SYSTEM_PREFIXES = (
    "/proc", "/sys", "/dev", "/run", "/tmp", "/var", "/snap", "/boot",
)
# 정확히 일치 제외
_EXACT_EXCLUDE = {"/", "/sessions"}


def _list_rw_mounts() -> list[Path]:
    """/proc/mounts 에서 rw 마운트 포인트 목록을 추출한다.

    Linux가 아니거나 /proc/mounts가 없으면 빈 리스트를 반환한다.
    경로 깊이 내림차순으로 정렬하여 더 구체적인 경로가 우선된다.

    Returns:
        rw 마운트 포인트 Path 리스트 (깊이 내림차순).
    """
    if sys.platform != "linux":
        return []

    proc_mounts = Path("/proc/mounts")
    if not proc_mounts.exists():
        return []

    results: list[Path] = []
    try:
        with open(proc_mounts, encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 4:
                    continue
                # 두 번째 컬럼이 마운트 포인트
                mount_point_raw = parts[1]
                # 네 번째 컬럼의 옵션에 "rw"가 포함돼야 함
                options = parts[3].split(",")
                if "rw" not in options:
                    continue

                # \040 → 공백 디코드
                mount_point_str = mount_point_raw.replace("\\040", " ")
                mount_path = Path(mount_point_str)

                # 정확히 일치 제외
                if str(mount_path) in _EXACT_EXCLUDE:
                    continue

                # 시스템 prefix 제외
                path_str = str(mount_path)
                if any(
                    path_str == prefix or path_str.startswith(prefix + "/")
                    for prefix in _SYSTEM_PREFIXES
                ):
                    continue

                results.append(mount_path)
    except OSError:
        return []

    # 경로 깊이 내림차순 정렬 (깊은 경로 우선)
    results.sort(key=lambda p: len(p.parts), reverse=True)
    return results


def _candidate_roots() -> list[Path]:
    """데이터 루트 후보 경로 목록을 우선순위 순으로 반환한다.

    후보 우선순위 (높음 → 낮음):
        1. ITDA_DATA_ROOT 환경변수
        2. /proc/mounts rw 마운트 포인트 (Linux 한정)
        3. $HOME/mnt/ 하위 비시스템 디렉토리
        4. $HOME
        5. Path.cwd()

    Returns:
        중복 제거된 Path 리스트 (resolve() 기준).
    """
    candidates: list[Path] = []

    # 1. ITDA_DATA_ROOT 환경변수 최우선
    env_root = os.environ.get("ITDA_DATA_ROOT")
    if env_root:
        candidates.append(Path(env_root))

    # 2. /proc/mounts rw 마운트 포인트 (Linux 한정)
    candidates.extend(_list_rw_mounts())

    # 3. $HOME/mnt/ 하위 비시스템 디렉토리
    try:
        home = Path.home()
    except RuntimeError:
        home = None

    if home is not None:
        mnt_dir = home / "mnt"
        if mnt_dir.is_dir():
            subdirs = sorted(
                (d for d in mnt_dir.iterdir()
                 if d.is_dir()
                 and not d.name.startswith(".")
                 and d.name not in _MNT_EXCLUDE_NAMES),
                key=lambda d: d.name,
            )
            candidates.extend(subdirs)

    # 4. $HOME
    if home is not None:
        candidates.append(home)

    # 5. Path.cwd()
    candidates.append(Path.cwd())

    # resolve() 기준 중복 제거 (순서 보존)
    seen: set[str] = set()
    unique: list[Path] = []
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            # 심볼릭 링크 깨짐 등 resolve 실패 시 스킵
            continue
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            unique.append(resolved)

    return unique


def find_cached(rel: str) -> Path | None:
    """후보 경로에서 기존 캐시 디렉토리를 찾는다.

    <root>/.itda-skills/<rel> 경로를 각 후보에 대해 검사하여
    존재하고 비어있지 않은 첫 번째 경로를 반환한다.

    Args:
        rel: 캐시 상대 경로 (예: "browser/playwright").

    Returns:
        비어있지 않은 캐시 Path, 없으면 None.
    """
    for root in _candidate_roots():
        candidate = root / _ITDA_DIR / rel
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate
    return None


def pick_cache_location(rel: str) -> Path:
    """캐시 디렉토리 위치를 결정하고 필요 시 생성한다.

    알고리즘:
        1. 기존 비어있지 않은 캐시가 있으면 즉시 반환 (find_cached)
        2. 없으면 최우선 쓰기 가능 후보에 새 디렉토리 생성

    Args:
        rel: 캐시 상대 경로 (예: "browser/playwright").

    Returns:
        캐시 디렉토리 Path (생성됨 또는 기존).

    Raises:
        RuntimeError: 쓰기 가능한 후보가 없을 때.
    """
    # 기존 캐시 우선
    cached = find_cached(rel)
    if cached is not None:
        return cached

    # 최우선 쓰기 가능 후보에 신규 생성
    for root in _candidate_roots():
        target = root / _ITDA_DIR / rel
        try:
            target.mkdir(parents=True, exist_ok=True)
            return target
        except OSError:
            continue

    raise RuntimeError("No writable cache location")


def find_env_files() -> list[Path]:
    """모든 후보 경로에서 .env 파일을 탐색한다.

    각 후보 경로의 <root>/.env 를 검사하여 존재하는 파일만
    후보 우선순위 순으로 리스트로 반환한다.

    Returns:
        존재하는 .env 파일 Path 리스트 (우선순위 순).
    """
    result: list[Path] = []
    for root in _candidate_roots():
        env_file = root / ".env"
        if env_file.exists():
            result.append(env_file)
    return result


def resolve_data_dir(skill_name: str, subdir: str = "") -> Path:
    """스킬의 데이터 디렉토리 경로를 결정하고 자동 생성한다.

    Args:
        skill_name: 스킬 이름 (예: "law-korean").
        subdir: 하위 디렉토리 (예: "cache"). 빈 문자열이면 스킬 루트.

    Returns:
        생성된 디렉토리의 절대 경로.
    """
    # pick_cache_location을 사용하되 rel에 skill_name을 포함시킴
    rel_parts = skill_name
    if subdir:
        rel_parts = f"{skill_name}/{subdir}"

    # ITDA_DATA_ROOT가 설정된 경우 해당 경로를 직접 사용
    env_root = os.environ.get("ITDA_DATA_ROOT")
    if env_root:
        base = Path(env_root).resolve()
        path = base / skill_name
        if subdir:
            path = path / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 후보 경로 중 최우선 쓰기 가능 경로 사용
    return pick_cache_location(rel_parts)


def resolve_cache_dir(skill_name: str) -> Path:
    """스킬의 캐시 디렉토리를 반환한다.

    캐시는 재생성 가능한 데이터이므로 세션 종료 시 소멸해도 무방하다.
    호스트 마운트가 있으면 마운트 경로를 우선 사용하여 세션 간 공유한다.

    Args:
        skill_name: 스킬 이름 (예: "law-korean").

    Returns:
        생성된 캐시 디렉토리의 절대 경로.
    """
    return resolve_data_dir(skill_name, "cache")


def resolve_browsers_dir() -> Path:
    """Playwright 브라우저 바이너리 캐시 디렉토리를 반환한다.

    세션 간 바이너리를 공유하여 재설치를 방지한다.
    pick_cache_location("browser/playwright")을 내부적으로 사용한다.

    Returns:
        생성된 브라우저 캐시 디렉토리의 절대 경로.
    """
    return pick_cache_location("browser/playwright")


def ensure_playwright_env() -> None:
    """Playwright 바이너리 영속성을 보장한다.

    PLAYWRIGHT_BROWSERS_PATH 환경변수가 이미 설정되어 있으면 덮어쓰지 않는다
    (외부 설정 존중). 미설정 시 pick_cache_location("browser/playwright")
    결과로 설정한다.

    Side effect:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"]를 설정할 수 있다.
    """
    if "PLAYWRIGHT_BROWSERS_PATH" in os.environ:
        return
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(
        pick_cache_location("browser/playwright")
    )
