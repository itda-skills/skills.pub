"""hwpx CLI 바이너리를 탐색하고 경로를 JSON으로 출력하는 스크립트.

탐색 순서:
1. 캐시: .itda-skills/bin/hwpx (CWD 기준, 실행 가능한 경우)
2. 번들: {skill_dir}/bin/hwpx_linux_{arch}.tar.gz 추출
3. PATH: shutil.which("hwpx")
4. 모두 실패 → error JSON, exit code 1

출력 형식:
- 성공: {"path": "...", "version": "...", "arch": "..."}
- 실패: {"error": "..."}

사용법:
    python3 find_hwpx.py --skill-dir /path/to/itda-hwpx
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

# ---------------------------------------------------------------------------
# 플랫폼 상수 — 테스트에서 mock.patch 로 교체 가능
# ---------------------------------------------------------------------------

def _detect_platform() -> tuple[str, str]:
    """(platform_str, arch_str) 를 반환한다.

    platform_str: "linux" | "darwin" | "windows"
    arch_str: "amd64" | "arm64"
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        arch = machine

    if system == "windows":
        plat = "windows"
    elif system == "darwin":
        plat = "darwin"
    else:
        plat = "linux"

    return plat, arch


PLATFORM, ARCH = _detect_platform()
CWD = Path.cwd()

# PATH에 hwpx가 없을 때 메시지
_UNSUPPORTED_MSG = (
    "hwpx 바이너리를 찾을 수 없습니다. "
    "PATH에 hwpx를 설치하세요."
)


# ---------------------------------------------------------------------------
# 내부 유틸
# ---------------------------------------------------------------------------

def _parse_version(stdout: str) -> str:
    """hwpx version 명령 출력에서 버전 문자열을 추출한다.

    패턴 우선순위:
    1. vX.Y.Z 형태 (선택적 suffix 포함)
    2. X.Y.Z 형태
    3. 파싱 불가 → strip 된 원본
    """
    text = stdout.strip()
    # vX.Y.Z(-suffix)? 패턴
    m = re.search(r"v\d+\.\d+\.\d+[\w.-]*", text)
    if m:
        return m.group(0)
    # X.Y.Z 패턴 (v 없이)
    m = re.search(r"\d+\.\d+\.\d+[\w.-]*", text)
    if m:
        return m.group(0)
    return text


def _run_version(binary_path: str) -> str:
    """binary_path version 서브커맨드로 버전 문자열을 가져온다."""
    try:
        result = subprocess.run(
            [binary_path, "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
        return _parse_version(result.stdout)
    except Exception as exc:  # noqa: BLE001
        return str(exc)


def _extract_bundle(bundle_path: Path, dest_dir: Path, arch: str) -> Path:
    """tar.gz 번들에서 hwpx 바이너리를 추출하고 경로를 반환한다.

    bundle 내부 파일명: hwpx_linux_{arch}
    추출 후 이름: hwpx
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    inner_name = f"hwpx_linux_{arch}"
    dest_bin = dest_dir / "hwpx"

    with tarfile.open(bundle_path, "r:gz") as tf:
        members = tf.getmembers()
        # inner_name 과 일치하는 멤버 탐색
        target = next(
            (m for m in members if Path(m.name).name == inner_name or m.name == inner_name),
            None,
        )
        if target is None:
            # fallback: 첫 번째 파일 멤버
            target = next((m for m in members if m.isfile()), None)
        if target is None:
            raise FileNotFoundError(f"번들 내에 바이너리를 찾을 수 없습니다: {bundle_path}")

        with tf.extractfile(target) as f_in:  # type: ignore[arg-type]
            dest_bin.write_bytes(f_in.read())

    os.chmod(dest_bin, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    return dest_bin


# ---------------------------------------------------------------------------
# 핵심 탐색 로직
# ---------------------------------------------------------------------------

def find_binary(skill_dir: Path) -> dict:
    """hwpx 바이너리를 탐색하고 결과 dict를 반환한다.

    성공: {"path": str, "version": str, "arch": str}
    실패: {"error": str}
    """
    # darwin/windows: PATH 우선 탐색, 없으면 설치 안내
    if PLATFORM in ("darwin", "windows"):
        which_result = shutil.which("hwpx")
        if which_result:
            version = _run_version(which_result)
            return {"path": which_result, "version": version, "arch": ARCH}
        return {"error": _UNSUPPORTED_MSG}

    arch = ARCH
    bin_dir = CWD / ".itda-skills" / "hwpx" / "bin"
    cache_bin = bin_dir / "hwpx"

    # 이전 경로 마이그레이션 (.itda-skills/bin/hwpx → .itda-skills/hwpx/bin/hwpx)
    old_bin = CWD / ".itda-skills" / "bin" / "hwpx"
    if old_bin.exists() and not cache_bin.exists():
        try:
            bin_dir.mkdir(parents=True, exist_ok=True)
            old_bin.rename(cache_bin)
        except OSError:
            pass

    # 1) 캐시 확인
    if cache_bin.exists() and os.access(str(cache_bin), os.X_OK):
        version = _run_version(str(cache_bin))
        return {"path": str(cache_bin), "version": version, "arch": arch}

    # 2) 번들 추출
    bundle_path = skill_dir / "bin" / f"hwpx_linux_{arch}.tar.gz"
    if bundle_path.exists():
        try:
            dest_dir = bin_dir
            extracted = _extract_bundle(bundle_path, dest_dir, arch)
            version = _run_version(str(extracted))
            return {"path": str(extracted), "version": version, "arch": arch}
        except Exception as exc:  # noqa: BLE001
            # 번들 추출 실패 → stderr 에 경고 출력 후 PATH fallback
            print(f"[find_hwpx] 번들 추출 실패: {exc}", file=sys.stderr)

    # 3) PATH fallback
    which_result = shutil.which("hwpx")
    if which_result:
        version = _run_version(which_result)
        return {"path": which_result, "version": version, "arch": arch}

    # 4) 모두 실패
    return {"error": "hwpx 바이너리를 찾을 수 없습니다. 번들이 없거나 PATH에도 존재하지 않습니다."}


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------

def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="hwpx CLI 바이너리를 탐색하고 JSON으로 출력합니다."
    )
    parser.add_argument(
        "--skill-dir",
        required=True,
        help="itda-hwpx 스킬 디렉토리 경로 (번들 bin/ 폴더 위치)",
    )
    parsed = parser.parse_args(args)

    result = find_binary(skill_dir=Path(parsed.skill_dir))
    print(json.dumps(result, ensure_ascii=False))

    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
