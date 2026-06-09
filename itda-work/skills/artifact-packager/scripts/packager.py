#!/usr/bin/env python3
"""정적 웹 산출물을 Go serve 바이너리로 패키징하는 P1 오케스트레이터."""

from __future__ import annotations

import argparse
import contextlib
import os
import platform
import queue
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path


if sys.version_info < (3, 10):
    version = ".".join(str(part) for part in sys.version_info[:3])
    print(
        f"artifact-packager는 Python 3.10 이상이 필요합니다. 현재 Python: {version}",
        file=sys.stderr,
    )
    raise SystemExit(2)


DEFAULT_OUT_DIR = "artifact-packager-out"
SERVER_ADDR = "127.0.0.1:0"
SERVING_RE = re.compile(r"serving (http://\S+)")


class PackagerError(Exception):
    """사용자에게 그대로 보여도 되는 패키징 오류."""


@dataclass(frozen=True, order=True)
class Target:
    os: str
    arch: str

    @property
    def label(self) -> str:
        return f"{self.os}/{self.arch}"

    @property
    def filename_suffix(self) -> str:
        return f"{self.arch}-{self.os}"


DEFAULT_TARGET = Target("windows", "amd64")
SUPPORTED_TARGETS = frozenset(
    {
        DEFAULT_TARGET,
        Target("windows", "arm64"),
        Target("darwin", "amd64"),
        Target("darwin", "arm64"),
        Target("linux", "amd64"),
        Target("linux", "arm64"),
    }
)
OS_ALIASES = {
    "win": "windows",
    "windows": "windows",
    "darwin": "darwin",
    "mac": "darwin",
    "macos": "darwin",
    "linux": "linux",
}
ARCH_ALIASES = {
    "amd64": "amd64",
    "x64": "amd64",
    "x86_64": "amd64",
    "arm64": "arm64",
    "aarch64": "arm64",
    "386": "386",
}


@dataclass
class CollectResult:
    source: Path
    dist: Path
    entrypoint: Path
    files: list[Path]
    temp_dir: tempfile.TemporaryDirectory[str] | None = field(default=None, repr=False)

    def cleanup(self) -> None:
        if self.temp_dir is not None:
            self.temp_dir.cleanup()
            self.temp_dir = None

    def __enter__(self) -> "CollectResult":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()


@dataclass(frozen=True)
class PackagePlan:
    adapter: str
    out_dir: Path
    artifact_path: Path
    name: str
    target: Target


@dataclass(frozen=True)
class PackageArtifact:
    adapter: str
    path: Path
    target: Target


@dataclass(frozen=True)
class CurlResult:
    status: int
    body: str


@dataclass(frozen=True)
class VerifyResult:
    skipped: bool
    message: str
    checks: tuple[str, ...] = ()


@dataclass
class RunningServer:
    process: subprocess.Popen[str]
    url: str
    stderr_lines: list[str]

    def stop(self) -> None:
        try:
            if self.process.poll() is not None:
                return

            self.process.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.process.wait(timeout=3)
                return

            self.process.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.process.wait(timeout=3)
        finally:
            _close_process_stderr(self.process)


def collect(src: Path | str) -> CollectResult:
    source = Path(src).expanduser()
    if not source.exists():
        raise PackagerError(f"입력 경로가 존재하지 않습니다: {source}")

    if source.is_file():
        if source.suffix.lower() != ".html":
            raise PackagerError("단일 파일 입력은 .html 파일만 지원합니다.")

        temp_dir = tempfile.TemporaryDirectory(prefix="artifact-packager-dist-")
        dist = Path(temp_dir.name) / "dist"
        dist.mkdir()
        shutil.copy2(source, dist / "index.html")
        files = _collect_files(dist)
        return CollectResult(
            source=source,
            dist=dist,
            entrypoint=dist / "index.html",
            files=files,
            temp_dir=temp_dir,
        )

    if not source.is_dir():
        raise PackagerError(f"지원하지 않는 입력 경로입니다: {source}")

    dist = source
    entrypoint = dist / "index.html"
    if not entrypoint.is_file():
        raise PackagerError(f"진입점 index.html을 찾을 수 없습니다: {entrypoint}")

    return CollectResult(
        source=source,
        dist=dist,
        entrypoint=entrypoint,
        files=_collect_files(dist),
    )


def build_plan(
    adapter: str,
    source: Path,
    out: Path | str | None,
    target: Target | None = None,
) -> PackagePlan:
    target = target or DEFAULT_TARGET
    if target not in SUPPORTED_TARGETS:
        raise PackagerError(
            f"지원하지 않는 target 조합입니다: {target.label}. 지원: {_supported_targets_text()}"
        )
    out_dir = Path(out).expanduser() if out is not None else Path.cwd() / DEFAULT_OUT_DIR
    name = _artifact_name(source)
    if adapter == "embed":
        artifact_path = out_dir / serve_filename(target, qualified=True)
    elif adapter == "zip":
        artifact_path = out_dir / f"{name}-{target.filename_suffix}.zip"
    else:
        raise PackagerError(f"지원하지 않는 어댑터입니다: {adapter}")

    return PackagePlan(
        adapter=adapter,
        out_dir=out_dir,
        artifact_path=artifact_path,
        name=name,
        target=target,
    )


def build_plans(
    adapter: str,
    source: Path,
    out: Path | str | None,
    targets: Sequence[Target],
) -> list[PackagePlan]:
    return [build_plan(adapter, source, out, target) for target in targets]


def confirm(
    collected: CollectResult,
    plans: Sequence[PackagePlan],
    auth: str | None,
    yes: bool,
) -> bool:
    if not plans:
        raise PackagerError("빌드할 target이 없습니다.")

    print("artifact-packager 패키징 요약")
    print(f"- 어댑터: {plans[0].adapter}")
    print(f"- 타깃: {', '.join(plan.target.label for plan in plans)}")
    print(f"- 진입점: {collected.entrypoint}")
    print(f"- 파일 수: {len(collected.files)}")
    for rel_path in _summarize_files(collected.files):
        print(f"  - {rel_path.as_posix()}")
    hidden_count = max(0, len(collected.files) - 12)
    if hidden_count:
        print(f"  - ... 외 {hidden_count}개")
    print(f"- 인증: {'사용' if auth else '미사용'}")
    print("- 산출물:")
    for plan in plans:
        print(f"  - {plan.target.label}: {plan.artifact_path}")

    if not yes:
        print("승인하려면 --yes 로 재실행하세요. 패키징은 수행하지 않았습니다.")
        return False

    return True


def package_embed(collected: CollectResult, plan: PackagePlan) -> PackageArtifact:
    _require_go()
    _prepare_out_dir(plan.out_dir)

    with tempfile.TemporaryDirectory(prefix="artifact-packager-embed-build-") as temp:
        build_dir = Path(temp)
        _copy_go_sources(build_dir)
        _copy_dir_contents(collected.dist, build_dir / "web")

        _run_build(
            ["go", "build", "-tags", "embed", "-o", str(plan.artifact_path), "."],
            build_dir,
            plan.target,
        )

    return PackageArtifact(adapter="embed", path=plan.artifact_path, target=plan.target)


def package_zip(collected: CollectResult, plan: PackagePlan) -> PackageArtifact:
    _require_go()
    _prepare_out_dir(plan.out_dir)

    with tempfile.TemporaryDirectory(prefix="artifact-packager-zip-build-") as temp:
        build_dir = Path(temp) / "build"
        package_dir = Path(temp) / "package"
        build_dir.mkdir()
        package_dir.mkdir()

        _copy_go_sources(build_dir)
        serve_path = package_dir / serve_filename(plan.target)
        _run_build(["go", "build", "-o", str(serve_path), "."], build_dir, plan.target)
        _copy_dir_contents(collected.dist, package_dir / "dist")
        _write_run_scripts(package_dir)
        _write_zip(package_dir, plan.artifact_path)

    return PackageArtifact(adapter="zip", path=plan.artifact_path, target=plan.target)


def verify_artifact(artifact: PackageArtifact, auth: str | None) -> VerifyResult:
    _ensure_artifact_exists(artifact)
    host = host_target()
    if artifact.target != host:
        return VerifyResult(
            skipped=True,
            message=_non_host_verify_message(artifact.target, host),
        )

    if shutil.which("curl") is None:
        return VerifyResult(
            skipped=True,
            message="curl 실행 파일을 찾을 수 없어 verify 단계만 생략했습니다.",
        )

    if artifact.adapter == "embed":
        return _verify_embed(artifact.path, auth)
    if artifact.adapter == "zip":
        return _verify_zip(artifact, auth)
    raise PackagerError(f"지원하지 않는 verify 어댑터입니다: {artifact.adapter}")


def verify_artifacts(artifacts: Sequence[PackageArtifact], auth: str | None) -> list[VerifyResult]:
    if not artifacts:
        return []

    for artifact in artifacts:
        _ensure_artifact_exists(artifact)

    host = host_target()
    if not any(artifact.target == host for artifact in artifacts):
        targets = ", ".join(artifact.target.label for artifact in artifacts)
        return [
            VerifyResult(
                skipped=True,
                message=(
                    "호스트에서 실행 가능한 타깃이 없어 빌드 산출물 존재만 확인했습니다. "
                    f"현재 호스트: {host.label}, 타깃: {targets}"
                ),
            )
        ]

    return [verify_artifact(artifact, auth) for artifact in artifacts]


def start_server(args: list[str], auth: str | None = None, timeout: float = 10.0) -> RunningServer:
    env = os.environ.copy()
    if auth:
        env["WEBDEPLOY_AUTH"] = auth

    process = subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )
    assert process.stderr is not None

    lines: list[str] = []
    line_queue: queue.Queue[str | None] = queue.Queue()

    def read_stderr() -> None:
        assert process.stderr is not None
        for line in process.stderr:
            line_queue.put(line.rstrip("\n"))
        line_queue.put(None)

    threading.Thread(target=read_stderr, daemon=True).start()
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if process.poll() is not None:
            _drain_lines(line_queue, lines)
            _close_process_stderr(process)
            raise PackagerError(_server_failed_message(process.returncode, lines))

        try:
            line = line_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        if line is None:
            continue
        lines.append(line)

        match = SERVING_RE.search(line)
        if match:
            return RunningServer(process=process, url=match.group(1), stderr_lines=lines)

    process.terminate()
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=3)
    if process.poll() is None:
        process.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=3)
    _close_process_stderr(process)
    raise PackagerError(_server_timeout_message(lines))


def curl_request(url: str, auth: str | None = None) -> CurlResult:
    args = [
        "curl",
        "--silent",
        "--show-error",
        "--max-time",
        "5",
        "--output",
        "-",
        "--write-out",
        "\n%{http_code}",
    ]
    input_text = None
    if auth:
        input_text = f'user = "{_curl_config_quote(auth)}"\n'
        args.extend(["--config", "-"])
    args.append(url)

    result = subprocess.run(
        args,
        input=input_text,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise PackagerError(f"curl 검증 실패(exit {result.returncode}): {_tail(result.stderr)}")

    body, status_text = result.stdout.rsplit("\n", 1)
    try:
        status = int(status_text)
    except ValueError as exc:
        raise PackagerError(f"curl 상태 코드를 해석할 수 없습니다: {status_text!r}") from exc
    return CurlResult(status=status, body=body)


def serve_filename(target: Target | None = None, qualified: bool = False) -> str:
    target = target or host_target()
    base = f"serve-{target.filename_suffix}" if qualified else "serve"
    return f"{base}.exe" if target.os == "windows" else base


def run_cli(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        auth = _validate_auth(args.auth)
        targets = parse_targets(args.target)
        with collect(args.src) as collected:
            plans = build_plans(args.adapter, collected.source, args.out, targets)
            if not confirm(collected, plans, auth, args.yes):
                return 0

            artifacts: list[PackageArtifact] = []
            for plan in plans:
                if args.adapter == "embed":
                    artifacts.append(package_embed(collected, plan))
                else:
                    artifacts.append(package_zip(collected, plan))

            for artifact in artifacts:
                print(f"패키징 완료({artifact.target.label}): {artifact.path}")
            sys.stdout.flush()

            if args.no_verify:
                print("verify 단계는 --no-verify 지정으로 생략했습니다.")
                return 0

            for verify in verify_artifacts(artifacts, auth):
                if verify.skipped:
                    print(verify.message)
                else:
                    for check in verify.checks:
                        print(f"verify: {check}")
                    print(verify.message)
            return 0
    except PackagerError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="정적 웹 산출물을 Go serve 기반 embed 바이너리 또는 zip으로 패키징합니다."
    )
    parser.add_argument("src", help="단일 .html 파일 또는 index.html을 포함한 디렉토리")
    parser.add_argument("--adapter", choices=("embed", "zip"), required=True, help="패키징 어댑터")
    parser.add_argument("--auth", help='Basic Auth 값. 형식은 "USER:PASS"')
    parser.add_argument("--out", help=f"산출물 디렉토리. 기본값은 ./{DEFAULT_OUT_DIR}")
    parser.add_argument(
        "--target",
        action="append",
        metavar="os/arch",
        help="빌드 타깃. 여러 번 지정 가능하며 기본값은 windows/amd64",
    )
    parser.add_argument("--yes", action="store_true", help="confirm 후 실제 패키징을 수행")
    parser.add_argument("--no-verify", action="store_true", help="패키징 후 curl 검증 생략")
    return parser


def parse_targets(values: Sequence[str] | None) -> list[Target]:
    raw_values = list(values) if values else [DEFAULT_TARGET.label]
    targets: list[Target] = []
    seen: set[Target] = set()

    for raw_value in raw_values:
        target = parse_target(raw_value)
        if target not in SUPPORTED_TARGETS:
            raise PackagerError(
                f"지원하지 않는 --target 조합입니다: {raw_value!r}. "
                f"지원: {_supported_targets_text()}"
            )
        if target in seen:
            raise PackagerError(f"중복된 --target 입니다: {target.label}")
        seen.add(target)
        targets.append(target)

    return targets


def parse_target(value: str) -> Target:
    raw = value.strip().lower()
    parts = raw.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise PackagerError(
            f"--target 형식은 os/arch 여야 합니다: {value!r}. 예: windows/amd64"
        )

    os_name = OS_ALIASES.get(parts[0])
    arch = ARCH_ALIASES.get(parts[1])
    if os_name is None or arch is None:
        raise PackagerError(
            f"알 수 없는 --target 값입니다: {value!r}. 지원: {_supported_targets_text()}"
        )
    return Target(os_name, arch)


def host_target() -> Target:
    system = platform.system().lower()
    if system == "darwin":
        goos = "darwin"
    elif system == "windows":
        goos = "windows"
    elif system == "linux":
        goos = "linux"
    else:
        goos = system or "unknown"

    machine = platform.machine().lower()
    arch = ARCH_ALIASES.get(machine, machine or "unknown")
    return Target(goos, arch)


def _supported_targets_text() -> str:
    return ", ".join(target.label for target in sorted(SUPPORTED_TARGETS))


def _ensure_artifact_exists(artifact: PackageArtifact) -> None:
    if not artifact.path.is_file():
        raise PackagerError(
            f"{artifact.target.label} 산출물을 찾을 수 없습니다: {artifact.path}"
        )


def _non_host_verify_message(target: Target, host: Target) -> str:
    return (
        f"{target.label}: 현재 호스트 {host.label}와 달라 실행 검증을 생략하고 "
        "빌드 산출물 존재만 확인했습니다."
    )


def _verify_embed(binary_path: Path, auth: str | None) -> VerifyResult:
    server = start_server([str(binary_path), "-addr", SERVER_ADDR], auth=auth)
    try:
        checks = _run_http_checks(server.url, auth)
        return VerifyResult(
            skipped=False,
            message="verify 완료",
            checks=tuple(checks),
        )
    finally:
        server.stop()


def _verify_zip(artifact: PackageArtifact, auth: str | None) -> VerifyResult:
    with tempfile.TemporaryDirectory(prefix="artifact-packager-verify-zip-") as temp:
        extract_dir = Path(temp)
        with zipfile.ZipFile(artifact.path) as archive:
            archive.extractall(extract_dir)

        serve_name = serve_filename(artifact.target)
        serve_path = extract_dir / serve_name
        if not serve_path.exists():
            raise PackagerError(f"zip 안에서 {serve_name} 파일을 찾을 수 없습니다.")
        _ensure_executable(serve_path)

        server = start_server(
            [str(serve_path), "-dir", str(extract_dir / "dist"), "-addr", SERVER_ADDR],
            auth=auth,
        )
        try:
            checks = _run_http_checks(server.url, auth)
            return VerifyResult(
                skipped=False,
                message="verify 완료",
                checks=tuple(checks),
            )
        finally:
            server.stop()


def _run_http_checks(base_url: str, auth: str | None) -> list[str]:
    url = base_url.rstrip("/") + "/"
    checks: list[str] = []

    if auth:
        no_auth = curl_request(url)
        if no_auth.status != 401:
            raise PackagerError(f"무인증 요청 상태가 401이 아닙니다: {no_auth.status}")
        checks.append("무인증 요청 401")

        wrong_auth = curl_request(url, _wrong_auth(auth))
        if wrong_auth.status != 401:
            raise PackagerError(f"잘못된 인증 요청 상태가 401이 아닙니다: {wrong_auth.status}")
        checks.append("잘못된 인증 요청 401")

        ok = curl_request(url, auth)
    else:
        ok = curl_request(url)

    if ok.status != 200:
        raise PackagerError(f"진입점 요청 상태가 200이 아닙니다: {ok.status}")
    if not ok.body.strip():
        raise PackagerError("진입점 응답 본문이 비어 있습니다.")
    checks.append("진입점 요청 200")
    return checks


def _validate_auth(auth: str | None) -> str | None:
    if auth is None:
        return None
    if "\n" in auth or "\r" in auth:
        raise PackagerError("인증 값에는 줄바꿈을 사용할 수 없습니다.")
    user, sep, password = auth.partition(":")
    if not sep or not user or not password:
        raise PackagerError("인증 형식은 USER:PASS여야 합니다.")
    return auth


def _wrong_auth(auth: str) -> str:
    user, _, password = auth.partition(":")
    wrong_password = password + "-wrong"
    return f"{user}:{wrong_password}"


def _collect_files(dist: Path) -> list[Path]:
    return sorted(path.relative_to(dist) for path in dist.rglob("*") if path.is_file())


def _summarize_files(files: list[Path], limit: int = 12) -> list[Path]:
    return files[:limit]


def _artifact_name(source: Path) -> str:
    base = source.name if source.is_dir() else source.stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip(".-")
    return safe or "site"


def _prepare_out_dir(out_dir: Path) -> None:
    if out_dir.exists() and not out_dir.is_dir():
        raise PackagerError(f"산출물 경로가 디렉토리가 아닙니다: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)


def _require_go() -> None:
    if shutil.which("go") is None:
        raise PackagerError("go 실행 파일을 찾을 수 없어 패키징 산출물을 빌드할 수 없습니다.")


def _copy_go_sources(destination: Path) -> None:
    source_dir = Path(__file__).resolve().parent / "serve"
    for path in source_dir.glob("*.go"):
        shutil.copy2(path, destination / path.name)
    for name in ("go.mod", "go.sum"):
        path = source_dir / name
        if path.exists():
            shutil.copy2(path, destination / name)


def _copy_dir_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target, symlinks=False)
        else:
            shutil.copy2(child, target)


def _run_build(args: list[str], cwd: Path, target: Target) -> None:
    env = os.environ.copy()
    cache_dir = cwd.parent / ".gocache"
    cache_dir.mkdir(exist_ok=True)
    env["GOCACHE"] = str(cache_dir)
    env["GOOS"] = target.os
    env["GOARCH"] = target.arch
    env["CGO_ENABLED"] = "0"

    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        raise PackagerError(f"Go 빌드 실패(exit {result.returncode}): {_tail(output)}")


def _write_run_scripts(package_dir: Path) -> None:
    run_sh = package_dir / "run.sh"
    run_sh.write_text(
        """#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SERVE="$SCRIPT_DIR/serve"
if [ ! -x "$SERVE" ] && [ -x "$SCRIPT_DIR/serve.exe" ]; then
  SERVE="$SCRIPT_DIR/serve.exe"
fi
exec "$SERVE" -dir "$SCRIPT_DIR/dist" "$@"
""",
        encoding="utf-8",
    )
    run_sh.chmod(run_sh.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    (package_dir / "run.bat").write_text(
        """@echo off
set "SCRIPT_DIR=%~dp0"
set "SERVE=%SCRIPT_DIR%serve.exe"
if not exist "%SERVE%" set "SERVE=%SCRIPT_DIR%serve"
"%SERVE%" -dir "%SCRIPT_DIR%dist" %*
""",
        encoding="utf-8",
    )


def _write_zip(package_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                rel_path = path.relative_to(package_dir).as_posix()
                _zip_write(archive, path, rel_path)


def _zip_write(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    info = zipfile.ZipInfo.from_file(path, arcname)
    info.compress_type = zipfile.ZIP_DEFLATED
    with path.open("rb") as handle:
        archive.writestr(info, handle.read())


def _ensure_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _curl_config_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _drain_lines(line_queue: queue.Queue[str | None], lines: list[str]) -> None:
    while True:
        try:
            line = line_queue.get_nowait()
        except queue.Empty:
            return
        if line is not None:
            lines.append(line)


def _close_process_stderr(process: subprocess.Popen[str]) -> None:
    if process.stderr is not None:
        with contextlib.suppress(Exception):
            process.stderr.close()


def _server_failed_message(returncode: int | None, lines: list[str]) -> str:
    return f"서버 기동 실패(exit {returncode}): {_tail(os.linesep.join(lines))}"


def _server_timeout_message(lines: list[str]) -> str:
    return f"서버 기동 대기 시간이 초과되었습니다: {_tail(os.linesep.join(lines))}"


def _tail(text: str, limit: int = 1200) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return "..." + text[-limit:]


if __name__ == "__main__":
    raise SystemExit(run_cli())
