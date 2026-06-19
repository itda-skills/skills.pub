#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightpanda 바이너리 설치/업그레이드/다운그레이드 관리 스크립트.

SPEC-WEBREADER-LIGHTPANDA-INSTALLER-001 (#513).

web-reader 동적 fetch(`fetch_dynamic.py`)가 의존하는 `lightpanda` 바이너리를
영속 경로에 1회 설치하여 세션 간 재사용하게 한다. 표준 라이브러리만 사용한다
(urllib/json) — 신규 의존성 0.

핵심 설계:
    - 최신 안정 해석은 `/releases/latest`(=nightly, rolling)를 **쓰지 않는다**.
      `/releases` 목록에서 semver 태그(`v?X.Y.Z`)만 추리고, prerelease/draft를
      제외한 뒤 가장 높은 버전을 고른다. (lightpanda의 `nightly` 태그는
      prerelease=false 라서 prerelease 플래그만으로는 걸러지지 않는다 — semver
      정규식이 nightly 제외의 실제 장치다.)
    - 다운로드 → chmod +x → (macOS) xattr 제거 → `lightpanda version` 검증 →
      검증 통과 시에만 기존 바이너리를 원자적으로 교체(os.replace). 손상된
      다운로드가 멀쩡한 바이너리를 덮어쓰지 않는다.
    - 인자 없이 호출하면 멱등(ensure): 있으면 skip, 없으면 최신 안정 설치.
      `--version`/`--force` 를 줄 때만 덮어쓴다.

CLI:
    install_lightpanda.py [--version X.Y.Z|vX.Y.Z|nightly|latest]
                          [--install-dir DIR] [--force] [--timeout SEC]

설치 위치 우선순위 (REQ-INST-005):
    --install-dir → $ITDA_LIGHTPANDA_DIR → ~/.itda-skills/bin

Exit codes:
    0 = 성공 (설치 또는 skip)
    1 = 설치 실패 (네트워크/디스크/검증 오류)
    2 = 잘못된 인자
    3 = 미지원 플랫폼 (Windows 네이티브 → WSL2 안내)
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 or later is required.")

__all__ = [
    "InstallError",
    "UnsupportedPlatform",
    "InstallResult",
    "detect_platform",
    "asset_name",
    "resolve_install_dir",
    "resolve_release",
    "install",
    "ensure",
    "main",
]

GITHUB_REPO = "lightpanda-io/browser"
API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}"
USER_AGENT = "itda-web-reader-installer/1.0 (+https://skills.pub)"

# semver 태그만 매치 — `nightly` 같은 rolling 태그를 구조적으로 제외한다.
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
# 바이너리 자체가 출력하는 버전 토큰(검증·로그용)
VERSION_TOKEN_RE = re.compile(r"\d+\.\d+\.\d+")


class InstallError(Exception):
    """설치 실패 (네트워크/디스크/검증)."""


class UnsupportedPlatform(Exception):
    """미지원 플랫폼 (Windows 네이티브 등)."""


class _NotFound(Exception):
    """내부용 — GitHub API 404 (태그 후보 순회 시 다음 후보로)."""


@dataclass
class InstallResult:
    path: str
    action: str  # "install" | "skip"
    tag: str | None = None
    version: str | None = None


# ---------------------------------------------------------------------------
# 플랫폼 / 에셋
# ---------------------------------------------------------------------------
def detect_platform() -> tuple[str, str]:
    """(os_name, arch) 반환. os_name∈{macos,linux}, arch∈{aarch64,x86_64}.

    Windows 또는 미지원 아키텍처면 UnsupportedPlatform.
    """
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        raise UnsupportedPlatform(
            "Windows 네이티브는 미지원입니다 — WSL2가 필요합니다.\n"
            "  WSL2 설치 후 WSL2 내부(Linux)에서 이 스크립트를 실행하세요.\n"
            "  또는 hyve MCP의 web_browse를 사용하세요."
        )
    if system == "Darwin":
        os_name = "macos"
    elif system == "Linux":
        os_name = "linux"
    else:
        raise UnsupportedPlatform(f"미지원 OS: {system} (macOS/Linux만 지원)")

    if machine in ("arm64", "aarch64"):
        arch = "aarch64"
    elif machine in ("x86_64", "amd64"):
        arch = "x86_64"
    else:
        raise UnsupportedPlatform(
            f"미지원 아키텍처: {machine} (aarch64/x86_64만 지원)"
        )
    return os_name, arch


def asset_name(os_name: str, arch: str) -> str:
    """릴리즈 에셋 파일명. 예: lightpanda-aarch64-macos."""
    return f"lightpanda-{arch}-{os_name}"


def _is_executable_file(p: Path) -> bool:
    """fetch_dynamic._find_lightpanda 와 동일 기준 — 실행 가능한 '파일'만 유효.

    (디렉터리·비실행 파일을 '설치됨'으로 오판하지 않기 위함.)
    접근 불가 경로(부모 디렉터리 권한 부족 등)에서 stat 이 OSError 를 던지면
    크래시하지 않고 '유효하지 않음'(False)으로 본다.
    """
    try:
        return p.is_file() and os.access(p, os.X_OK)
    except OSError:
        return False


# ---------------------------------------------------------------------------
# 설치 위치
# ---------------------------------------------------------------------------
def resolve_install_dir(install_dir: str | None = None) -> Path:
    """설치 디렉터리 결정 (REQ-INST-005).

    우선순위: --install-dir → $ITDA_LIGHTPANDA_DIR → ~/.itda-skills/bin
    """
    if install_dir:
        return Path(install_dir).expanduser()
    env = os.environ.get("ITDA_LIGHTPANDA_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".itda-skills" / "bin"


# ---------------------------------------------------------------------------
# GitHub API / 릴리즈 해석
# ---------------------------------------------------------------------------
def _http_get_json(url: str, *, timeout: int = 30):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise _NotFound(url)
        if e.code == 403:
            raise InstallError(
                f"GitHub API rate limit 또는 접근 거부 (HTTP 403): {url}\n"
                "  잠시 후 다시 시도하거나, 다른 네트워크를 사용하세요."
            )
        raise InstallError(f"GitHub API 오류 (HTTP {e.code}): {url}")
    except urllib.error.URLError as e:
        raise InstallError(f"네트워크 오류: {e.reason} ({url})")
    except OSError as e:
        raise InstallError(f"네트워크 오류: {e} ({url})")

    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise InstallError(f"GitHub API 응답 파싱 실패: {e}")


def _semver_key(tag: str | None) -> tuple[int, int, int] | None:
    m = SEMVER_RE.match(tag or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _pick_asset(release: dict, want: str) -> dict | None:
    for asset in release.get("assets", []) or []:
        if asset.get("name") == want:
            return asset
    return None


def _resolve_latest_stable(*, timeout: int = 30) -> dict:
    """`/releases` 목록에서 semver 태그 + 비prerelease + 비draft 중 최고 버전.

    `/releases/latest` 는 lightpanda에서 rolling `nightly` 를 반환하므로 쓰지 않는다.
    """
    data = _http_get_json(f"{API_BASE}/releases?per_page=100", timeout=timeout)
    if not isinstance(data, list):
        raise InstallError("GitHub API 응답 형식 오류 (releases 목록이 아님).")

    best: dict | None = None
    best_key: tuple[int, int, int] | None = None
    for rel in data:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        key = _semver_key(rel.get("tag_name"))
        if key is None:  # nightly 등 비semver 태그 제외
            continue
        if best_key is None or key > best_key:
            best_key, best = key, rel

    if best is None:
        raise InstallError(
            "안정 버전(semver 태그)을 찾을 수 없습니다 — 릴리즈 목록을 확인하세요."
        )
    return best


def _tag_candidates(version: str) -> list[str]:
    """`v` 접두사 유무 양쪽을 후보로 (신버전=0.3.2, 구버전=v0.2.6)."""
    if version == "nightly":
        return ["nightly"]
    stripped = version.lstrip("v")
    return [stripped, f"v{stripped}"]


def _resolve_tagged(version: str, *, timeout: int = 30) -> dict:
    candidates = _tag_candidates(version)
    for tag in candidates:
        try:
            return _http_get_json(f"{API_BASE}/releases/tags/{tag}", timeout=timeout)
        except _NotFound:
            continue
    raise InstallError(
        f"버전 '{version}' 릴리즈를 찾을 수 없습니다 (시도한 태그: {', '.join(candidates)})."
    )


def resolve_release(
    version: str | None,
    os_name: str,
    arch: str,
    *,
    timeout: int = 30,
) -> tuple[str, str, int]:
    """(tag, download_url, size_bytes) 반환.

    version: None/"latest" → 최신 안정, "nightly" → nightly, 그 외 → 지정 버전.
    """
    if version is None or version == "latest":
        release = _resolve_latest_stable(timeout=timeout)
    else:
        release = _resolve_tagged(version, timeout=timeout)

    tag = release.get("tag_name") or "(unknown)"
    want = asset_name(os_name, arch)
    asset = _pick_asset(release, want)
    if asset is None:
        raise InstallError(
            f"릴리즈 '{tag}'에 이 플랫폼 에셋이 없습니다: {want}"
        )
    url = asset.get("browser_download_url")
    if not url:
        raise InstallError(f"에셋 '{want}'의 다운로드 URL이 비어 있습니다.")
    return tag, url, int(asset.get("size") or 0)


# ---------------------------------------------------------------------------
# 다운로드 / 검증
# ---------------------------------------------------------------------------
def _download(url: str, dest: Path, *, timeout: int = 120) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
            shutil.copyfileobj(resp, f, length=256 * 1024)
    except urllib.error.HTTPError as e:
        raise InstallError(f"다운로드 실패 (HTTP {e.code}): {url}")
    except urllib.error.URLError as e:
        raise InstallError(f"다운로드 네트워크 오류: {e.reason}")
    except OSError as e:  # 디스크 가득참 / 권한
        raise InstallError(f"다운로드 파일 쓰기 실패: {e}")


def _strip_quarantine(path: Path) -> None:
    """macOS com.apple.quarantine 제거 (best-effort)."""
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        subprocess.run(
            ["xattr", "-d", "com.apple.quarantine", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )


def _verify_binary(path: Path, *, timeout: int = 30) -> str:
    """`<bin> version` 실행. rc!=0 면 InstallError. 출력에서 버전 토큰 반환."""
    try:
        proc = subprocess.run(
            [str(path), "version"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise InstallError(f"바이너리 실행 검증 실패: {e}")
    if proc.returncode != 0:
        tail = ((proc.stderr or "") + (proc.stdout or ""))[-200:]
        raise InstallError(f"바이너리 검증 실패 (rc={proc.returncode}): {tail}")
    out = (proc.stdout or "") + (proc.stderr or "")
    m = VERSION_TOKEN_RE.search(out)
    return m.group(0) if m else ""


# ---------------------------------------------------------------------------
# 설치 오케스트레이션
# ---------------------------------------------------------------------------
def _default_log(msg: str) -> None:
    print(f"[install_lightpanda] {msg}", file=sys.stderr)


def _commit_binary(tmp: Path, dest: Path, *, explicit: bool, log) -> str:
    """검증된 임시 바이너리를 dest 에 반영. 반환: "install" | "skip".

    - explicit(force/version): os.replace 로 덮어쓴다(명시 요청).
    - ensure(비명시): os.link 로 **원자적 create-if-absent**. dest 가 이미
      존재하면(FileExistsError) — 유효 실행 바이너리는 보존(skip, REQ-INST-008
      "절대 덮어쓰지 않음"), 디렉터리/비실행 junk 면 os.replace 로 교체한다.
      os.link 는 같은 파일시스템 하드링크라 check-then-replace 의 TOCTOU race가
      없다(임시파일은 dest_dir 안에 만들어 같은 fs 보장).
    """
    try:
        # dest 가 디렉터리면 자동 삭제하지 않는다 — 사용자 데이터/마운트일 수 있어
        # rm -rf 는 위험. 명확한 actionable 에러로 막는다(IsADirectory traceback 회피).
        if dest.is_dir():
            raise InstallError(
                f"설치 경로가 디렉터리입니다: {dest} — 데이터 손상 방지를 위해 자동 삭제하지 않습니다. "
                "해당 디렉터리를 제거하거나 다른 --install-dir / $ITDA_LIGHTPANDA_DIR 를 지정하세요."
            )
        if explicit:
            os.replace(str(tmp), str(dest))
            return "install"
        try:
            os.link(str(tmp), str(dest))  # dest 없을 때만 성공(원자적)
            return "install"
        except FileExistsError:
            if _is_executable_file(dest):
                log(f"이미 설치되어 있어 보존(덮어쓰지 않음): {dest}")
                return "skip"
            # dest 가 비실행 일반 파일(부분 다운로드 등) → 교체(overwrite 의도)
            os.replace(str(tmp), str(dest))
            return "install"
    except OSError as e:
        # 예: 권한 부족, 교차 파일시스템(EXDEV) — traceback 대신 명확한 에러
        raise InstallError(f"바이너리 설치 실패 ({dest}): {e}")
    finally:
        # os.link 성공 시 임시 이름(여분 하드링크) 정리. os.replace 성공 시 이미 소비됨.
        with contextlib.suppress(OSError):
            tmp.unlink()


def install(
    version: str | None = None,
    install_dir: str | None = None,
    *,
    force: bool = False,
    timeout: int = 30,
    log=None,
) -> InstallResult:
    """lightpanda 설치/교체. ensure 의미는 version=None & force=False.

    - version/force 둘 다 없고 바이너리가 이미 있으면 skip (멱등, REQ-INST-002).
    - version 또는 force 가 있으면 덮어쓴다 (REQ-INST-004/008).
    """
    log = log or _default_log
    os_name, arch = detect_platform()  # UnsupportedPlatform 전파
    dest_dir = resolve_install_dir(install_dir)
    dest = dest_dir / "lightpanda"
    if not dest_dir.is_absolute():
        # 상대경로면 설치 cwd와 검출 cwd가 다를 때 어긋난다(세션 간 재사용 깨짐).
        log(f"경고: 설치 경로가 상대경로입니다({dest_dir}). 세션 간 재사용을 위해 절대경로를 권장합니다.")

    explicit = version is not None or force
    # ensure(비명시) 멱등: 유효한 '실행 파일'이 이미 있을 때만 skip.
    # dest.exists() 가 아니라 _is_executable_file 로 봐야 검출 체인과 일치한다
    # (디렉터리·비실행 파일을 '설치됨'으로 오판하지 않음).
    if not explicit and _is_executable_file(dest):
        log(f"이미 설치됨: {dest} — skip (재설치는 --force 또는 --version 지정)")
        return InstallResult(path=str(dest), action="skip")

    want = asset_name(os_name, arch)
    label = "최신 안정" if version in (None, "latest") else version
    log(f"릴리즈 해석 중... ({label})")
    tag, url, size = resolve_release(version, os_name, arch, timeout=timeout)
    size_mb = f"{size / 1024 / 1024:.0f} MB" if size else "크기 미상"
    log(f"다운로드 중: {tag} ({want}, {size_mb}) → {dest}")

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise InstallError(f"설치 디렉터리 생성 실패 ({dest_dir}): {e}")

    try:
        fd, tmp_name = tempfile.mkstemp(prefix=".lightpanda.dl.", dir=str(dest_dir))
        os.close(fd)
    except OSError as e:
        raise InstallError(f"임시 파일 생성 실패 ({dest_dir}): {e}")
    tmp = Path(tmp_name)
    try:
        _download(url, tmp, timeout=max(120, timeout))
        try:
            tmp.chmod(0o755)
            if os_name == "macos":
                _strip_quarantine(tmp)
        except OSError as e:
            raise InstallError(f"바이너리 권한 설정 실패: {e}")
        ver = _verify_binary(tmp, timeout=timeout)
        # 검증 통과 후에만 dest 에 반영 — 손상 다운로드가 기존 바이너리를 덮어쓰지 않음.
        action = _commit_binary(tmp, dest, explicit=explicit, log=log)
        if action == "skip":
            return InstallResult(path=str(dest), action="skip")
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise

    log(f"설치 완료: {dest} (version={ver or tag})")
    return InstallResult(path=str(dest), action="install", tag=tag, version=ver or None)


def ensure(install_dir: str | None = None, *, timeout: int = 30, log=None) -> InstallResult:
    """멱등 보장 — 있으면 skip, 없으면 최신 안정 설치. 절대 덮어쓰지 않는다."""
    return install(version=None, install_dir=install_dir, force=False, timeout=timeout, log=log)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lightpanda 바이너리 설치/업그레이드/다운그레이드 (web-reader)",
    )
    parser.add_argument(
        "--version",
        help="설치할 버전: X.Y.Z | vX.Y.Z | nightly | latest. 생략 시 최신 안정.",
    )
    parser.add_argument(
        "--install-dir",
        help="설치 디렉터리. 생략 시 $ITDA_LIGHTPANDA_DIR 또는 ~/.itda-skills/bin.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 바이너리를 덮어쓴다 (업그레이드/재설치).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="API/검증 타임아웃(초). 다운로드는 최소 120초.",
    )

    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as e:
        # --help → 0, argparse 오류 → 2. 코드를 삼키지 않는다.
        return e.code if isinstance(e.code, int) else 2

    try:
        result = install(
            version=args.version,
            install_dir=args.install_dir,
            force=args.force,
            timeout=args.timeout,
        )
    except UnsupportedPlatform as e:
        print(f"[install_lightpanda] {e}", file=sys.stderr)
        return 3
    except InstallError as e:
        print(f"[install_lightpanda] 설치 실패: {e}", file=sys.stderr)
        return 1

    # stdout: 최종 바이너리 경로 (호출자가 캡처) — 진행 로그는 전부 stderr
    print(result.path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
