#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""동적 fetch 백엔드 — Lightpanda subprocess wrapper.

SPEC-WEBREADER-DYNAMIC-LIGHTPANDA-001 (web-reader v5.0.0).

`lightpanda fetch` CLI를 호출하여 JavaScript 렌더링이 필요한 페이지를 가져온다.
Playwright/Chromium 대비 단일 바이너리(65~135MB), 24MB 메모리, 100ms 부팅.

바이너리 검출 우선순위 (REQ-INST-006):
    --lightpanda-bin → $ITDA_LIGHTPANDA_BIN → $ITDA_LIGHTPANDA_DIR/lightpanda
    → $PATH → ~/.itda-skills/bin/lightpanda
미설치 시 install_lightpanda.py를 자동 호출해 최신 안정 버전을 설치한다
(REQ-INST-007, --no-auto-install로 비활성). 자동 설치는 절대 덮어쓰지 않는다.

CLI 사용법:
    fetch_dynamic.py --url URL [--wait-until X] [--wait-selector CSS] [--wait-ms N]
                     [--terminate-ms N] [--strip-mode js,css] [--dump-markdown]
                     [--cookie-file FILE] [--http-proxy URL] [--output FILE]
                     [--lightpanda-bin PATH] [--no-auto-install]

Exit codes:
    0: 성공
    1: Lightpanda 런타임 오류 (subprocess rc != 0)
    2: 잘못된 인자
    3: Lightpanda 바이너리 미설치 (자동 설치 OFF/실패 — stderr에 설치 안내)
    4: Bot challenge 감지 (Access Denied / Cloudflare 등 — stderr에 hyve MCP escalation 안내)

Non-goals (hyve MCP escalation 권장):
    - Anti-bot 우회 (Akamai/Cloudflare stealth)
    - SNS 인증 (인스타·X 로그인 토큰)
    - 네이버 부동산 (SPA — web_browse observe{network}로 XHR 캡처)
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# 차단 시그널 패턴 — body가 작거나 이들이 검출되면 bot challenge로 판정
BOT_CHALLENGE_PATTERNS = [
    r"Access Denied",
    r"Just a moment",
    r"Checking your browser",
    r"cf-(challenge|chl-)",
    r"errors\.edgesuite\.net",
    r"<title>\s*(Attention Required|Forbidden|403\s*Forbidden|Access Denied)\s*</title>",
    r"PerimeterX",
]


def _detect_bot_challenge(body: str) -> str | None:
    """차단 시그널 검출. 매치된 패턴을 반환, 없으면 None.

    짧은 차단 응답(coupang Access Denied 등 ~300바이트)도 검출되도록
    최소 길이는 15자로 완화. 빈 본문이나 단일 토큰은 제외.
    """
    if not body or len(body) < 15:
        return None
    for pat in BOT_CHALLENGE_PATTERNS:
        m = re.search(pat, body[:4000], re.IGNORECASE)
        if m:
            return m.group(0)[:60]
    return None


def _is_executable_file(p: Path) -> bool:
    # 접근 불가 경로(부모 디렉터리 권한 부족 등)에서 stat 이 OSError 를 던져도
    # 검출이 크래시하지 않고 '없음'으로 흐르게 한다.
    try:
        return p.is_file() and os.access(p, os.X_OK)
    except OSError:
        return False


def _find_lightpanda(explicit_bin: str | None = None) -> str | None:
    """Lightpanda 바이너리 검출 (REQ-INST-006).

    명시 입력 우선 체인. cwd 상대 추측 경로(`./mnt/...`·`./.itda-skills/...`)는
    Cowork 세션에서 마운트와 어긋나 헛다리 + 세션 휘발 문제가 있어 제거했다.

    우선순위:
        1. --lightpanda-bin 인자 (명시 바이너리 경로)
        2. $ITDA_LIGHTPANDA_BIN (명시 바이너리 경로)
        3. $ITDA_LIGHTPANDA_DIR/lightpanda (영속 설치 디렉터리 — 설치 위치와 대칭)
        4. $PATH (which lightpanda)
        5. ~/.itda-skills/bin/lightpanda (기본 설치 위치)
    """
    # 1. 명시 인자
    if explicit_bin:
        p = Path(explicit_bin).expanduser()
        if _is_executable_file(p):
            return str(p)

    # 2. $ITDA_LIGHTPANDA_BIN (바이너리 경로)
    env_bin = os.environ.get("ITDA_LIGHTPANDA_BIN")
    if env_bin:
        p = Path(env_bin).expanduser()
        if _is_executable_file(p):
            return str(p)

    # 3. $ITDA_LIGHTPANDA_DIR/lightpanda (설치 디렉터리)
    env_dir = os.environ.get("ITDA_LIGHTPANDA_DIR")
    if env_dir:
        p = Path(env_dir).expanduser() / "lightpanda"
        if _is_executable_file(p):
            return str(p)

    # 4. PATH
    found = shutil.which("lightpanda")
    if found:
        return found

    # 5. 기본 설치 위치
    p = Path.home() / ".itda-skills" / "bin" / "lightpanda"
    if _is_executable_file(p):
        return str(p)

    return None


def _auto_install_lightpanda(timeout: int = 600) -> str | None:
    """미설치 시 install_lightpanda.py(ensure 모드)를 subprocess로 자동 호출.

    REQ-INST-007: 기본 ON. ensure 모드라 기존 바이너리를 절대 덮어쓰지 않는다
    (REQ-INST-008 — 검출 실패, 즉 바이너리 부재일 때만 도달). installer가 진행
    상황을 stderr로 직접 출력하므로 여기서는 stderr를 inherit한다. 설치된
    바이너리 경로(검증 통과 시)를 반환하고, 실패하면 None.
    """
    script = Path(__file__).resolve().parent / "install_lightpanda.py"
    if not script.is_file():
        return None
    print(
        "[web-reader] Lightpanda 미설치 — 최신 안정 버전을 자동 설치합니다...",
        file=sys.stderr,
    )
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            stdout=subprocess.PIPE,
            stderr=None,  # inherit → 다운로드 진행 상황 실시간 표시
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as e:
        print(f"[web-reader] 자동 설치 실패: {e}", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"[web-reader] 자동 설치 실패 (exit {proc.returncode}). "
            "수동 설치: python3 scripts/install_lightpanda.py",
            file=sys.stderr,
        )
        return None
    lines = (proc.stdout or "").strip().splitlines()
    if not lines:
        return None
    candidate = Path(lines[-1].strip()).expanduser()
    return str(candidate) if _is_executable_file(candidate) else None


def install_guide() -> str:
    """Lightpanda 설치 안내 — 관리 스크립트(install_lightpanda.py) 호출 기준."""
    system = platform.system()

    base = (
        "Lightpanda 바이너리를 찾을 수 없습니다.\n"
        "관리 스크립트로 설치하세요 (플랫폼/아키텍처 자동 감지, 표준 라이브러리만 사용):\n\n"
    )

    if system == "Windows":
        guide = (
            "  # Windows 네이티브 미지원 — WSL2 필수\n"
            "  # WSL2 설치 후 WSL2 내부(Linux)에서 실행:\n"
            "  python3 scripts/install_lightpanda.py\n"
            "  # 또는 hyve MCP의 web_browse 사용\n"
        )
    else:
        guide = (
            "  # 최신 안정 버전 자동 설치\n"
            "  python3 scripts/install_lightpanda.py\n\n"
            "  # 세션 간 재사용을 위해 영속 경로 지정 (권장)\n"
            "  ITDA_LIGHTPANDA_DIR=<project>/tools python3 scripts/install_lightpanda.py\n\n"
            "  # 특정 버전 / 다운그레이드\n"
            "  python3 scripts/install_lightpanda.py --version 0.3.0\n"
        )

    detect_order = (
        "\n검출 우선순위:\n"
        "  1. --lightpanda-bin 인자\n"
        "  2. $ITDA_LIGHTPANDA_BIN (바이너리 경로)\n"
        "  3. $ITDA_LIGHTPANDA_DIR/lightpanda (설치 디렉터리)\n"
        "  4. $PATH (which lightpanda)\n"
        "  5. ~/.itda-skills/bin/lightpanda (기본)\n"
    )

    return base + guide + detect_order


def hyve_escalation_message(url: str, signal: str) -> str:
    """bot challenge 감지 시 hyve MCP escalation 안내."""
    return (
        f"[web-reader] Bot challenge 감지: {signal!r}\n"
        f"Lightpanda는 anti-bot 우회 기능이 없습니다. 다음 경로를 시도하세요:\n\n"
        f"1. hyve MCP web_browse (Bun playwright + stealth)\n"
        f"   예: \"hyve의 web_browse로 {url} 가져와줘\"\n\n"
        f"2. 네이버 부동산 등 SPA(XHR 로 데이터 로드): web_browse 의 observe{{network}} 로 API 원본 캡처\n"
        f"   예: \"web_browse로 단지 페이지 열고 observe network 로 매물 API 캡처해줘\"\n\n"
        f"3. SNS 로그인 필요 콘텐츠 (인스타·X): 별도 인증 흐름 필요 — 현재 미지원\n"
    )


def fetch_dynamic(
    url: str,
    *,
    wait_until: str = "domcontentloaded",
    wait_selector: str | None = None,
    wait_ms: int | None = None,
    terminate_ms: int = 15000,
    http_timeout_ms: int = 10000,
    strip_mode: str | None = None,
    cookie_file: str | None = None,
    http_proxy: str | None = None,
    dump_markdown: bool = False,
    block_private_networks: bool = True,
    lightpanda_bin: str | None = None,
    auto_install: bool = True,
) -> dict:
    """Lightpanda를 호출하여 동적 페이지를 가져온다.

    Returns:
        {
            "content": str,           # HTML 또는 markdown
            "format": "html"|"markdown",
            "exit_code": int,         # 0=ok, 1=runtime, 3=not_found, 4=bot_challenge
            "stderr_tail": str,       # 에러 메시지 (앞 200자)
            "lightpanda_path": str,   # 사용된 바이너리 경로
            "parse_time_ms": int,
            "size": int,
            "bot_signal": str|None,   # 차단 시그널 매치 시 패턴 이름
        }
    """
    t0 = time.time()

    lp = _find_lightpanda(lightpanda_bin)
    if lp is None and auto_install:
        # REQ-INST-007: 미설치 시 추가 토큰 없이 자동 ensure 설치 후 진행.
        installed = _auto_install_lightpanda()
        lp = installed or _find_lightpanda(lightpanda_bin)
    if lp is None:
        return {
            "content": "",
            "format": "html" if not dump_markdown else "markdown",
            "exit_code": 3,
            "stderr_tail": install_guide(),
            "lightpanda_path": "",
            "parse_time_ms": int((time.time() - t0) * 1000),
            "size": 0,
            "bot_signal": None,
        }

    cmd = [lp, "fetch"]
    cmd.extend(["--dump", "markdown" if dump_markdown else "html"])
    cmd.extend(["--wait-until", wait_until])
    if wait_selector:
        cmd.extend(["--wait-selector", wait_selector])
    if wait_ms is not None:
        cmd.extend(["--wait-ms", str(wait_ms)])
    cmd.extend(["--terminate-ms", str(terminate_ms)])
    cmd.extend(["--http-timeout", str(http_timeout_ms)])
    if strip_mode:
        cmd.extend(["--strip-mode", strip_mode])
    if cookie_file:
        cmd.extend(["--cookie", cookie_file])
    if http_proxy:
        cmd.extend(["--http-proxy", http_proxy])
    if block_private_networks:
        cmd.append("--block-private-networks")
    cmd.append(url)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(30, terminate_ms // 1000 + 10),
        )
    except subprocess.TimeoutExpired as e:
        return {
            "content": "",
            "format": "html" if not dump_markdown else "markdown",
            "exit_code": 1,
            "stderr_tail": f"subprocess timeout after {e.timeout}s",
            "lightpanda_path": lp,
            "parse_time_ms": int((time.time() - t0) * 1000),
            "size": 0,
            "bot_signal": None,
        }
    except OSError as e:
        return {
            "content": "",
            "format": "html" if not dump_markdown else "markdown",
            "exit_code": 1,
            "stderr_tail": f"subprocess OSError: {e}",
            "lightpanda_path": lp,
            "parse_time_ms": int((time.time() - t0) * 1000),
            "size": 0,
            "bot_signal": None,
        }

    body = proc.stdout or ""
    stderr_tail = (proc.stderr or "")[-200:]
    elapsed_ms = int((time.time() - t0) * 1000)

    if proc.returncode != 0:
        return {
            "content": body,
            "format": "html" if not dump_markdown else "markdown",
            "exit_code": 1,
            "stderr_tail": stderr_tail,
            "lightpanda_path": lp,
            "parse_time_ms": elapsed_ms,
            "size": len(body),
            "bot_signal": None,
        }

    bot_signal = _detect_bot_challenge(body)
    if bot_signal:
        return {
            "content": body,
            "format": "html" if not dump_markdown else "markdown",
            "exit_code": 4,
            "stderr_tail": stderr_tail,
            "lightpanda_path": lp,
            "parse_time_ms": elapsed_ms,
            "size": len(body),
            "bot_signal": bot_signal,
        }

    return {
        "content": body,
        "format": "html" if not dump_markdown else "markdown",
        "exit_code": 0,
        "stderr_tail": stderr_tail,
        "lightpanda_path": lp,
        "parse_time_ms": elapsed_ms,
        "size": len(body),
        "bot_signal": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lightpanda 기반 동적 페이지 fetch (web-reader v5.0.0)"
    )
    parser.add_argument("--url", required=True, help="가져올 URL")
    parser.add_argument("--output", "-o", help="출력 파일 (기본: stdout)")
    parser.add_argument(
        "--dump-markdown",
        action="store_true",
        help="Lightpanda의 --dump markdown 사용 (기본: --dump html)",
    )
    parser.add_argument(
        "--wait-until",
        choices=["load", "domcontentloaded", "networkidle", "done"],
        default="domcontentloaded",
        help="Lightpanda --wait-until (기본: domcontentloaded)",
    )
    parser.add_argument("--wait-selector", help="Lightpanda --wait-selector (CSS)")
    parser.add_argument("--wait-ms", type=int, help="Lightpanda --wait-ms")
    parser.add_argument(
        "--terminate-ms",
        type=int,
        default=15000,
        help="Lightpanda --terminate-ms (기본 15000)",
    )
    parser.add_argument(
        "--http-timeout-ms",
        type=int,
        default=10000,
        help="Lightpanda --http-timeout (기본 10000)",
    )
    parser.add_argument(
        "--strip-mode",
        choices=["js", "css", "ui", "full", "js,css"],
        help="Lightpanda --strip-mode (예: js,css)",
    )
    parser.add_argument("--cookie-file", help="Lightpanda --cookie (JSON 파일)")
    parser.add_argument("--http-proxy", help="Lightpanda --http-proxy")
    parser.add_argument(
        "--allow-private",
        action="store_true",
        help="--block-private-networks 비활성화 (기본: 활성)",
    )
    parser.add_argument(
        "--lightpanda-bin",
        help="Lightpanda 바이너리 경로 명시 (검출 체인 최우선)",
    )
    parser.add_argument(
        "--no-auto-install",
        action="store_true",
        help="미설치 시 자동 설치 비활성화 (CI/테스트). 기본은 자동 설치 ON.",
    )

    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as e:
        # --help → 0, argparse 오류 → 2. 코드를 삼키지 않는다.
        return e.code if isinstance(e.code, int) else 2

    result = fetch_dynamic(
        args.url,
        wait_until=args.wait_until,
        wait_selector=args.wait_selector,
        wait_ms=args.wait_ms,
        terminate_ms=args.terminate_ms,
        http_timeout_ms=args.http_timeout_ms,
        strip_mode=args.strip_mode,
        cookie_file=args.cookie_file,
        http_proxy=args.http_proxy,
        dump_markdown=args.dump_markdown,
        block_private_networks=not args.allow_private,
        lightpanda_bin=args.lightpanda_bin,
        auto_install=not args.no_auto_install,
    )

    # 미설치
    if result["exit_code"] == 3:
        print(result["stderr_tail"], file=sys.stderr)
        return 3

    # bot challenge
    if result["exit_code"] == 4:
        print(hyve_escalation_message(args.url, result["bot_signal"] or "unknown"), file=sys.stderr)
        # 본문도 함께 출력 (사용자가 차단 페이지 내용 확인할 수 있도록)
        if result["content"]:
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result["content"])
            else:
                print(result["content"])
        return 4

    # runtime 오류
    if result["exit_code"] == 1:
        print(
            f"[web-reader] Lightpanda 호출 실패 ({result['lightpanda_path']}):\n  {result['stderr_tail']}",
            file=sys.stderr,
        )
        return 1

    # 정상
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result["content"])
    else:
        print(result["content"])

    print(
        f"size={result['size']} time={result['parse_time_ms']}ms "
        f"format={result['format']} lightpanda={result['lightpanda_path']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
