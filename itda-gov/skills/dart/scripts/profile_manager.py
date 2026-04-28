#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
profile_manager.py - 영속 브라우저 프로필 관리 CLI.

{CWD}/.itda-skills/browser/profiles/ 아래에 Playwright 브라우저 프로필을 관리한다.
web-reader, naver-place 등 여러 스킬이 프로필을 공유한다.
list, delete, info, warmup 서브커맨드를 지원한다.

SPEC: SPEC-WEBREADER-004 REQ-2.1~REQ-2.9
SPEC: SPEC-NAVER-PLACE-001 (browser namespace)

종료 코드:
    0 - 성공
    1 - 런타임 에러 (프로필 미존재, 부분 삭제 실패 등)
    2 - 인자/검증 에러 (프로필 이름 검증 실패 등)
    3 - 프로필 lock 충돌 (다른 프로세스가 사용 중)
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import shutil
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from itda_path import resolve_data_dir

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

# Windows 예약 디바이스 이름 (대소문자 무시)
_WINDOWS_RESERVED = frozenset([
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
])

# 허용 문자: 알파벳, 숫자, 하이픈, 언더스코어만 허용 (점, 슬래시, 공백 불가)
_PROFILE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

# 이전 경로 (마이그레이션용)
_OLD_PROFILE_ROOT_V1_RELPATH = Path(".itda-skills") / "browser-profiles"  # v1
_OLD_PROFILE_ROOT_V2_RELPATH = Path(".itda-skills") / "web-reader" / "profiles"  # v2

# 메타데이터 파일명
_META_FILENAME = ".profile-meta.json"

# 마이그레이션 완료 플래그
_migrated = False


# ---------------------------------------------------------------------------
# 경로 유틸리티
# ---------------------------------------------------------------------------


def _migrate_old_profiles(new_root: Path) -> None:
    """이전 경로에서 새 경로(browser/profiles/)로 프로필을 이동한다.

    마이그레이션 순서:
    1. v2: .itda-skills/web-reader/profiles/ → .itda-skills/browser/profiles/
    2. v1: .itda-skills/browser-profiles/ → .itda-skills/browser/profiles/

    1회성 마이그레이션. 실패 시 무시하고 새 경로로 진행한다.
    """
    global _migrated  # noqa: PLW0603
    if _migrated:
        return
    _migrated = True

    # 새 경로에 이미 프로필이 있으면 마이그레이션 불필요
    if any(new_root.iterdir()):
        return

    # v2 → v3 (web-reader/profiles → browser/profiles)
    old_root_v2 = Path.cwd() / _OLD_PROFILE_ROOT_V2_RELPATH
    if old_root_v2.is_dir():
        try:
            for item in old_root_v2.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    item.rename(new_root / item.name)
            return  # v2 마이그레이션 성공 시 v1 시도 불필요
        except OSError:
            pass  # 마이그레이션 실패는 무시하고 v1 시도

    # v1 → v3 (browser-profiles → browser/profiles)
    old_root_v1 = Path.cwd() / _OLD_PROFILE_ROOT_V1_RELPATH
    if old_root_v1.is_dir():
        try:
            for item in old_root_v1.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    item.rename(new_root / item.name)
        except OSError:
            pass  # 마이그레이션 실패는 무시


def _get_profile_root() -> Path:
    """프로필 루트 경로를 반환한다 (환경 자동 감지)."""
    root = resolve_data_dir("browser", "profiles")
    _migrate_old_profiles(root)
    return root


def get_profile_root() -> Path:
    """프로필 루트 경로를 반환한다 (환경 자동 감지)."""
    return _get_profile_root()


# ---------------------------------------------------------------------------
# 프로필 이름 검증 (REQ-2.8)
# ---------------------------------------------------------------------------


def validate_profile_name(name: str, profile_root: Path | None = None) -> None:
    """프로필 이름을 검증한다. 위반 시 stderr 출력 후 SystemExit(2)를 발생시킨다.

    Args:
        name: 검증할 프로필 이름.
        profile_root: 프로필 루트 경로 (None이면 _get_profile_root() 사용).

    Raises:
        SystemExit(2): 이름 검증 실패 시.
    """
    # 1. 빈 문자열
    if not name:
        print("Error: 프로필 이름이 비어있습니다.", file=sys.stderr)
        raise SystemExit(2)

    # 2. 길이 제한 (최대 64자)
    if len(name) > 64:
        print(
            f"Error: 프로필 이름이 너무 깁니다 (최대 64자): {name!r}",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # 3. 허용 문자 검사 (점, 슬래시, 공백 등 금지)
    if not _PROFILE_NAME_RE.match(name):
        print(
            f"Error: 잘못된 프로필 이름 {name!r}. [a-zA-Z0-9_-]만 허용됩니다.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # 4. 금지 이름 (.과 .. 및 Windows 예약어)
    if name in (".", "..") or name.lower() in _WINDOWS_RESERVED:
        print(
            f"Error: 프로필 이름 {name!r}은 예약된 이름입니다.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # 5. resolve() 경로 탈출 방지 (path traversal 방어)
    root = profile_root if profile_root is not None else _get_profile_root()
    root.mkdir(parents=True, exist_ok=True)
    root_resolved = root.resolve()
    name_resolved = (root / name).resolve()
    try:
        name_resolved.relative_to(root_resolved)
    except ValueError:
        print(
            f"Error: 프로필 이름 {name!r}이 프로필 루트를 벗어납니다.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if name_resolved == root_resolved:
        print(
            f"Error: 프로필 이름 {name!r}이 프로필 루트 자체로 해석됩니다.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # 6. symlink 거부
    candidate = root / name
    if candidate.exists() and candidate.is_symlink():
        print(
            f"Error: 프로필 경로가 심볼릭 링크입니다: {candidate}",
            file=sys.stderr,
        )
        raise SystemExit(2)


# ---------------------------------------------------------------------------
# 메타데이터 유틸리티 (REQ-2.2)
# ---------------------------------------------------------------------------


def read_profile_meta(profile_dir: Path) -> dict[str, Any]:
    """프로필 메타데이터를 읽는다.

    Args:
        profile_dir: 프로필 디렉토리 경로.

    Returns:
        메타데이터 dict. 파일이 없으면 빈 dict 반환.
    """
    meta_file = profile_dir / _META_FILENAME
    if not meta_file.exists():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def write_profile_meta(profile_dir: Path, meta: dict[str, Any]) -> None:
    """프로필 메타데이터를 원자적으로 기록한다.

    tempfile.NamedTemporaryFile + os.replace() 패턴을 사용해
    쓰기 도중 crash가 발생해도 부분적으로 쓰인 파일이 남지 않는다.

    Args:
        profile_dir: 프로필 디렉토리 경로.
        meta: 저장할 메타데이터 dict.
    """
    import tempfile
    meta_file = profile_dir / _META_FILENAME
    content = json.dumps(meta, ensure_ascii=False, indent=2)
    # 같은 디렉토리에 임시 파일 생성 (다른 파티션 cross-device 방지)
    fd, tmp_path = tempfile.mkstemp(dir=profile_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, meta_file)
    except Exception:
        # 임시 파일 정리
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _create_default_meta(name: str) -> dict[str, Any]:
    """기본 메타데이터 dict를 생성한다."""
    now = datetime.now(tz=timezone.utc).isoformat()
    return {
        "name": name,
        "created_at": now,
        "last_used_at": now,
        "domains_visited": [],
        "stealth_version": _get_stealth_version(),
        "viewport": {"width": 1920, "height": 1080},
    }


def create_default_meta(name: str) -> dict[str, Any]:
    """기본 메타데이터 dict를 생성한다."""
    return _create_default_meta(name)


def _get_stealth_version() -> str:
    """stealth 모듈의 버전을 반환한다 (import 실패 시 'unknown')."""
    try:
        import stealth
        return stealth.STEALTH_VERSION
    except ImportError:
        return "unknown"


# ---------------------------------------------------------------------------
# 프로세스 시작 시각 취득
# ---------------------------------------------------------------------------


def _get_boot_time() -> float | None:
    """Linux /proc/stat에서 btime(부팅 시각 UNIX epoch)을 취득한다."""
    try:
        proc_stat = Path("/proc/stat")
        if not proc_stat.exists():
            return None
        for line in proc_stat.read_text().splitlines():
            if line.startswith("btime "):
                return float(line.split()[1])
    except Exception:
        pass
    return None


def _get_process_start_epoch(pid: int) -> float | None:
    """프로세스 시작 시각을 UNIX epoch seconds로 취득한다.

    취득 우선순위:
    1. Linux /proc/<pid>/stat + btime epoch 정규화
    2. psutil.Process(pid).create_time() fallback
    3. None (시작 시각 취득 불가)

    Args:
        pid: 대상 프로세스 ID.

    Returns:
        시작 시각 (UNIX epoch seconds) 또는 None.
    """
    # 1. Linux /proc 파싱
    try:
        boot_time = _get_boot_time()
        if boot_time is not None:
            sc_clk_tck = os.sysconf("SC_CLK_TCK")
            stat_path = Path(f"/proc/{pid}/stat")
            if stat_path.exists():
                stat_content = stat_path.read_text()
                # comm 끝 위치 (마지막 ')') 이후부터 필드 파싱
                comm_end = stat_content.rfind(")")
                if comm_end != -1:
                    fields = stat_content[comm_end + 2:].split()
                    # field 20 (0-indexed: 19) = starttime in jiffies (after state, ppid, ...)
                    if len(fields) >= 20:
                        starttime_ticks = int(fields[19])
                        return boot_time + starttime_ticks / sc_clk_tck
    except Exception:
        pass

    # 2. psutil fallback
    try:
        import psutil
        return psutil.Process(pid).create_time()
    except Exception:
        pass

    # 3. 시작 시각 취득 불가
    return None


# ---------------------------------------------------------------------------
# ProfileLock (REQ-2.9)
# ---------------------------------------------------------------------------


class ProfileLockError(Exception):
    """프로필이 다른 프로세스에 의해 사용 중."""

    def __init__(self, name: str, pid: int) -> None:
        self.name = name
        self.pid = pid
        super().__init__(f"프로필 '{name}'이 PID {pid}에 의해 사용 중입니다")


class ProfileLock:
    """O_EXCL 원자 lock으로 프로필의 단일 프로세스 접근을 보장한다.

    context manager로 사용. REQ-2.9.

    Example:
        with ProfileLock(profile_dir, "myprofile"):
            # 프로필 사용
    """

    def __init__(self, profile_dir: Path, profile_name: str) -> None:
        self._lock_path = profile_dir / ".lock"
        self._name = profile_name
        self._acquired = False
        # REQ-3.1: 원래 signal handler 저장용 (복원을 위해)
        self._original_sigint: object = None
        self._original_sigterm: object = None

    def __enter__(self) -> "ProfileLock":
        self._acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self._release()

    def _setup_signal_handlers(self) -> None:
        """SIGINT/SIGTERM 핸들러를 설치한다.

        REQ-2.1: 원래 핸들러를 저장하고, stale lock 재획득 시에도 재설치된다.
        REQ-3.1: _release() 시 원래 핸들러를 복원할 수 있도록 저장한다.
        """
        def _sighandler(signum: int, _frame: object) -> None:
            # 정리 중 재진입 방지: 후속 신호는 무시
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            # Lock 해제는 with ProfileLock 블록의 __exit__에 위임한다.
            # 예외를 발생시키면 Python 스택이 정상 언와인드되면서
            # Playwright context.close() → ProfileLock._release() 순서로 정리된다.
            if signum == signal.SIGINT:
                raise KeyboardInterrupt()
            raise SystemExit(1)

        try:
            # REQ-3.1: 원래 핸들러 저장
            self._original_sigint = signal.getsignal(signal.SIGINT)
            self._original_sigterm = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGTERM, _sighandler)
            signal.signal(signal.SIGINT, _sighandler)
        except (OSError, ValueError):
            # signal 등록 실패는 무시 (비메인 스레드 등)
            pass

    def _acquire(self) -> None:
        """O_EXCL 원자 lock 획득. 실패 시 ProfileLockError 발생."""
        try:
            fd = os.open(
                str(self._lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            lock_data = {"pid": os.getpid(), "created_at": time.time()}
            os.write(fd, json.dumps(lock_data).encode())
            os.close(fd)
            self._acquired = True
            # 프로세스 종료 시 lock 해제 등록
            atexit.register(self._release)
            # REQ-2.1: signal handler 설치 (별도 메서드로 추출)
            self._setup_signal_handlers()
        except FileExistsError:
            # 기존 lock 파일 읽기 및 stale 판정
            try:
                lock_data = json.loads(self._lock_path.read_text(encoding="utf-8"))
                pid = int(lock_data.get("pid", 0))
                created_at = float(lock_data.get("created_at", 0.0))
            except (json.JSONDecodeError, OSError, ValueError):
                # JSON 파싱 실패: 보수적으로 lock 파일을 삭제하지 않고 에러 발생
                import logging
                logging.warning(
                    "ProfileLock._acquire: lock 파일 JSON 파싱 실패, "
                    "보수적으로 unlink 생략"
                )
                raise ProfileLockError(self._name, 0)

            if self._is_stale(pid, created_at):
                # stale lock 삭제 후 1회 재시도
                try:
                    self._lock_path.unlink(missing_ok=True)
                except OSError:
                    pass
                try:
                    fd = os.open(
                        str(self._lock_path),
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    )
                    new_lock = {"pid": os.getpid(), "created_at": time.time()}
                    os.write(fd, json.dumps(new_lock).encode())
                    os.close(fd)
                    self._acquired = True
                    atexit.register(self._release)
                    # REQ-2.1: stale lock 재획득 후에도 signal handler 재설치
                    self._setup_signal_handlers()
                except FileExistsError:
                    raise ProfileLockError(self._name, pid)
            else:
                raise ProfileLockError(self._name, pid)

    def _restore_signal_handlers(self) -> None:
        """원래 signal handler를 복원한다 (REQ-3.1)."""
        try:
            if self._original_sigint is not None:
                signal.signal(signal.SIGINT, self._original_sigint)  # type: ignore[arg-type]
            if self._original_sigterm is not None:
                signal.signal(signal.SIGTERM, self._original_sigterm)  # type: ignore[arg-type]
        except (OSError, ValueError):
            # 복원 실패는 무시 (비메인 스레드 등)
            pass

    def _release(self) -> None:
        """lock 파일을 삭제하고 원래 signal handler를 복원한다.

        REQ-1.5: lock 파일에 기록된 PID가 현재 PID와 일치하는 경우에만 삭제한다.
        다른 프로세스의 lock 파일을 실수로 삭제하는 것을 방지한다.
        REQ-3.1: 설치한 signal handler를 원래 핸들러로 복원한다.
        """
        if self._acquired:
            # PID 검증: lock 파일이 현재 프로세스 소유인지 확인
            try:
                lock_data = json.loads(self._lock_path.read_text(encoding="utf-8"))
                lock_pid = int(lock_data.get("pid", 0))
                if lock_pid != os.getpid():
                    # PID 불일치: 다른 프로세스의 lock이므로 삭제하지 않는다
                    import logging
                    logging.warning(
                        "ProfileLock._release: PID mismatch (lock=%d, current=%d), "
                        "skipping unlink",
                        lock_pid,
                        os.getpid(),
                    )
                    self._acquired = False
                    # PID mismatch 경로에서도 signal handler 복원
                    self._restore_signal_handlers()
                    return
            except (OSError, json.JSONDecodeError, ValueError):
                # 파일 읽기/파싱 실패: 보수적으로 unlink하지 않고 경고만 출력
                import logging
                logging.warning(
                    "ProfileLock._release: lock 파일 읽기/파싱 실패, "
                    "보수적으로 unlink 생략"
                )
                self._acquired = False
                self._restore_signal_handlers()
                return
            try:
                self._lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._acquired = False

            # REQ-3.1: 원래 signal handler 복원
            self._restore_signal_handlers()

    def _is_stale(self, pid: int, lock_created_at: float) -> bool:
        """stale lock 여부를 판정한다.

        4단계 판정:
        1. PID 존재 여부 (os.kill(pid, 0))
        2. 프로세스 시작 시각 비교 (PID 재사용 방어)
        3. macOS 전용: PID 존재하나 시작 시각 취득 불가 시 4h 휴리스틱 (REQ-2.2)
        4. PID-only fallback (시작 시각 취득 불가 시 보수적으로 활성 판정)

        Args:
            pid: lock 파일에 기록된 프로세스 ID.
            lock_created_at: lock 파일 생성 시각 (UNIX epoch).

        Returns:
            True이면 stale (lock 삭제 가능), False이면 활성 프로세스.
        """
        # 1. PID 존재 여부 확인
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True  # 프로세스 없음 → stale
        except PermissionError:
            # 프로세스 존재하지만 신호 보낼 권한 없음 → 활성으로 간주
            return False
        except OSError:
            # 기타 오류 → 보수적으로 활성 판정
            return False

        # 2. 프로세스 살아있음 → 시작 시각으로 PID 재사용 감지
        process_start = _get_process_start_epoch(pid)
        if process_start is not None:
            # lock 생성 시각보다 프로세스 시작 시각이 나중이면 PID 재사용
            return process_start > lock_created_at

        # 3. macOS 전용: PID는 존재하나 시작 시각 취득 불가 시
        # 4h 타임스탬프 휴리스틱을 마지막 fallback으로 적용 (REQ-2.2)
        _MACOS_STALE_THRESHOLD = 4 * 3600  # 4시간
        if sys.platform == "darwin":
            if time.time() - lock_created_at > _MACOS_STALE_THRESHOLD:
                return True

        # 4. 시작 시각 취득 불가 → 보수적으로 활성 판정
        return False


# ---------------------------------------------------------------------------
# Playwright 가용성 확인 (warmup 용)
# ---------------------------------------------------------------------------


def is_playwright_available() -> bool:
    """playwright 패키지 import 가능 여부를 반환한다."""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def sync_playwright():  # type: ignore[return]
    """sync_playwright context manager를 반환한다 (테스트에서 mock 가능)."""
    from playwright.sync_api import sync_playwright as _sp  # type: ignore[import]
    return _sp()


# ---------------------------------------------------------------------------
# CLI 서브커맨드 구현
# ---------------------------------------------------------------------------


def _cmd_list(args: argparse.Namespace) -> int:
    """list 서브커맨드: 저장된 프로필 목록을 출력한다."""
    root = _get_profile_root()
    if not root.exists():
        print("프로필이 없습니다.")
        return 0

    profiles = [
        d for d in root.iterdir()
        if d.is_dir() and not d.is_symlink() and not d.name.startswith(".")
    ]

    if not profiles:
        print("프로필이 없습니다.")
        return 0

    print(f"{'이름':<20} {'크기':>10}  마지막 사용")
    print("-" * 55)
    for profile_dir in sorted(profiles, key=lambda d: d.name):
        meta = read_profile_meta(profile_dir)
        last_used = meta.get("last_used_at", "알 수 없음")
        # 디렉토리 크기 계산
        try:
            size = sum(f.stat().st_size for f in profile_dir.rglob("*") if f.is_file())
            size_str = f"{size // 1024:,} KB"
        except OSError:
            size_str = "N/A"
        print(f"{profile_dir.name:<20} {size_str:>10}  {last_used}")

    return 0


def _cmd_delete(args: argparse.Namespace) -> int:
    """delete 서브커맨드: 프로필을 삭제한다.

    REQ-1.4: TOCTOU 방지 — ProfileLock을 획득한 뒤 디렉토리 존재를 재확인하고 삭제한다.
    """
    validate_profile_name(args.name)
    root = _get_profile_root()
    profile_dir = root / args.name

    # 디렉토리 사전 확인 (사용자 피드백용 — 실제 삭제는 lock 내에서)
    if not profile_dir.exists():
        print(f"Error: 프로필 '{args.name}'을 찾을 수 없습니다.", file=sys.stderr)
        return 1

    force = getattr(args, "force", False)

    if force:
        print(f"Warning: 강제 삭제 중 '{args.name}'...", file=sys.stderr)

    # REQ-1.4: lock 획득 먼저, 그 내부에서 존재 확인 및 삭제
    try:
        with ProfileLock(profile_dir, args.name):
            # lock 내에서 디렉토리 존재 재확인 (TOCTOU 방어)
            if not profile_dir.exists():
                print(
                    f"Error: 프로필 '{args.name}'이 이미 삭제되었습니다.",
                    file=sys.stderr,
                )
                return 1
            try:
                shutil.rmtree(profile_dir)
                print(f"프로필 '{args.name}'을 삭제했습니다.")
                return 0
            except OSError as e:
                print(f"Error: 일부 파일 삭제 실패: {e}", file=sys.stderr)
                return 1
    except ProfileLockError as exc:
        if force:
            # --force: lock 무시하고 강제 삭제
            try:
                shutil.rmtree(profile_dir)
                print(f"프로필 '{args.name}'을 강제 삭제했습니다.")
                return 0
            except OSError as e:
                print(f"Error: 강제 삭제 실패: {e}", file=sys.stderr)
                return 1
        print(
            f"Error: 프로필 '{args.name}'이 PID {exc.pid}에 의해 사용 중입니다.",
            file=sys.stderr,
        )
        return 3


def _cmd_info(args: argparse.Namespace) -> int:
    """info 서브커맨드: 프로필 메타데이터를 출력한다."""
    validate_profile_name(args.name)
    root = _get_profile_root()
    profile_dir = root / args.name

    if not profile_dir.exists():
        print(f"Error: 프로필 '{args.name}'을 찾을 수 없습니다.", file=sys.stderr)
        return 1

    meta = read_profile_meta(profile_dir)
    if not meta:
        print(f"프로필 '{args.name}' (메타데이터 없음)")
        return 0

    print(f"프로필: {meta.get('name', args.name)}")
    print(f"  생성일:      {meta.get('created_at', 'N/A')}")
    print(f"  마지막 사용: {meta.get('last_used_at', 'N/A')}")
    print(f"  Stealth:     {meta.get('stealth_version', 'N/A')}")
    viewport = meta.get("viewport", {})
    if viewport:
        print(f"  뷰포트:      {viewport.get('width')}x{viewport.get('height')}")
    domains = meta.get("domains_visited", [])
    if domains:
        print(f"  방문 도메인: {', '.join(domains[:5])}")
        if len(domains) > 5:
            print(f"               ... 외 {len(domains) - 5}개")

    return 0


def _cmd_warmup(args: argparse.Namespace) -> int:
    """warmup 서브커맨드: 프로필로 URL에 접속하여 초기화한다."""
    if not is_playwright_available():
        print(
            "Error: playwright가 설치되지 않았습니다. "
            "uv pip install --system playwright && playwright install chromium",
            file=sys.stderr,
        )
        return 2

    validate_profile_name(args.name)
    root = _get_profile_root()
    profile_dir = root / args.name
    profile_dir.mkdir(parents=True, exist_ok=True)

    url = getattr(args, "url", "https://example.com")
    print(f"프로필 '{args.name}' warm-up 중: {url}", file=sys.stderr)

    try:
        with ProfileLock(profile_dir, args.name):
            with sync_playwright() as pw:
                context = pw.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=True,
                )
                page = context.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                final_url = page.url
                context.close()

            meta = read_profile_meta(profile_dir)
            if not meta:
                meta = _create_default_meta(args.name)
            meta["last_used_at"] = datetime.now(tz=timezone.utc).isoformat()
            from urllib.parse import urlparse
            domain = urlparse(final_url).netloc
            domains = meta.get("domains_visited", [])
            if domain and domain not in domains:
                domains.append(domain)
            meta["domains_visited"] = domains
            write_profile_meta(profile_dir, meta)

        print(f"warm-up 완료: {final_url}", file=sys.stderr)
        return 0

    except ProfileLockError as e:
        print(
            f"Error: 프로필 '{args.name}'이 PID {e.pid}에 의해 사용 중입니다.",
            file=sys.stderr,
        )
        return 3
    except Exception as e:
        print(f"Error: warm-up 실패: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# CLI 진입점
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점.

    Returns:
        종료 코드 (0=성공, 1=런타임 에러, 2=인자 오류, 3=lock 충돌).
    """
    parser = argparse.ArgumentParser(
        description="itda-web-reader 브라우저 프로필 관리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # list 서브커맨드
    subparsers.add_parser("list", help="저장된 프로필 목록 출력")

    # delete 서브커맨드
    delete_parser = subparsers.add_parser("delete", help="프로필 삭제")
    delete_parser.add_argument("name", help="삭제할 프로필 이름")
    delete_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="lock 무시하고 강제 삭제",
    )

    # info 서브커맨드
    info_parser = subparsers.add_parser("info", help="프로필 정보 출력")
    info_parser.add_argument("name", help="조회할 프로필 이름")

    # warmup 서브커맨드
    warmup_parser = subparsers.add_parser("warmup", help="프로필 초기화 (브라우저 접속)")
    warmup_parser.add_argument("name", help="초기화할 프로필 이름")
    warmup_parser.add_argument(
        "--url",
        default="https://example.com",
        help="warm-up 접속 URL (기본: https://example.com)",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "list":
        return _cmd_list(args)
    elif args.command == "delete":
        return _cmd_delete(args)
    elif args.command == "info":
        return _cmd_info(args)
    elif args.command == "warmup":
        return _cmd_warmup(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
