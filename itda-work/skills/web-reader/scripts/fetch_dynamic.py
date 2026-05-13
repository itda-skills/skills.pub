#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""동적 fetch 백엔드 — Lightpanda subprocess wrapper.

SPEC-WEBREADER-DYNAMIC-LIGHTPANDA-001 (web-reader v5.0.0).

`lightpanda fetch` CLI를 호출하여 JavaScript 렌더링이 필요한 페이지를 가져온다.
Playwright/Chromium 대비 단일 바이너리(65~135MB), 24MB 메모리, 100ms 부팅.

CLI 사용법:
    fetch_dynamic.py --url URL [--wait-until X] [--wait-selector CSS] [--wait-ms N]
                     [--terminate-ms N] [--strip-mode js,css] [--dump-markdown]
                     [--cookie-file FILE] [--http-proxy URL] [--output FILE]

Exit codes:
    0: 성공
    1: Lightpanda 런타임 오류 (subprocess rc != 0)
    2: 잘못된 인자
    3: Lightpanda 바이너리 미설치 (stderr에 설치 안내)
    4: Bot challenge 감지 (Access Denied / Cloudflare 등 — stderr에 hyve MCP escalation 안내)

Non-goals (hyve MCP escalation 권장):
    - Anti-bot 우회 (Akamai/Cloudflare stealth)
    - SNS 인증 (인스타·X 로그인 토큰)
    - 네이버 부동산 (naverplace 도메인 어댑터)
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


def _find_lightpanda() -> str | None:
    """Lightpanda 바이너리 검출 (REQ-LP-007).

    우선순위:
        1. $PATH (which lightpanda)
        2. $HOME/.itda-skills/bin/lightpanda
        3. ./mnt/.itda-skills/bin/lightpanda (Cowork 마운트)
        4. ./.itda-skills/bin/lightpanda (Cowork 세션 한정)
    """
    # 1. PATH
    found = shutil.which("lightpanda")
    if found:
        return found

    # 2~4. 후보 경로 순회
    home = Path.home()
    cwd = Path.cwd()
    candidates = [
        home / ".itda-skills" / "bin" / "lightpanda",
        cwd / "mnt" / ".itda-skills" / "bin" / "lightpanda",
        cwd / ".itda-skills" / "bin" / "lightpanda",
    ]
    for p in candidates:
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    return None


def install_guide() -> str:
    """플랫폼별 Lightpanda 설치 안내 메시지."""
    system = platform.system()
    arch = platform.machine().lower()

    base = (
        "Lightpanda 바이너리를 찾을 수 없습니다.\n"
        "설치 후 다시 시도하세요:\n\n"
    )

    if system == "Darwin":
        guide = (
            "  # macOS (Homebrew)\n"
            "  brew install lightpanda\n\n"
            "  # 또는 nightly 직접 다운로드\n"
        )
        if arch in ("arm64", "aarch64"):
            guide += (
                "  curl -L https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-aarch64-macos \\\n"
                "    -o ~/.itda-skills/bin/lightpanda && chmod +x ~/.itda-skills/bin/lightpanda\n"
                "  xattr -d com.apple.quarantine ~/.itda-skills/bin/lightpanda 2>/dev/null\n"
            )
        else:
            guide += (
                "  curl -L https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-macos \\\n"
                "    -o ~/.itda-skills/bin/lightpanda && chmod +x ~/.itda-skills/bin/lightpanda\n"
                "  xattr -d com.apple.quarantine ~/.itda-skills/bin/lightpanda 2>/dev/null\n"
            )
    elif system == "Linux":
        url = (
            "https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-aarch64-linux"
            if arch in ("arm64", "aarch64")
            else "https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux"
        )
        guide = (
            "  # Linux (glibc 기반, musl/Alpine 미지원)\n"
            f"  mkdir -p ~/.itda-skills/bin && curl -L {url} \\\n"
            "    -o ~/.itda-skills/bin/lightpanda && chmod +x ~/.itda-skills/bin/lightpanda\n"
        )
    elif system == "Windows":
        guide = (
            "  # Windows 네이티브 미지원 — WSL2 필수\n"
            "  # WSL2 설치 후 WSL2 내부에서 Linux 명령으로 설치하세요.\n"
            "  # 또는 hyve MCP의 web_browse.render 사용 (SPEC-WEB-MCP-002).\n"
        )
    else:
        guide = "  https://github.com/lightpanda-io/browser/releases 에서 플랫폼 바이너리를 다운로드하세요.\n"

    detect_order = (
        "\n검출 우선순위:\n"
        "  1. $PATH (which lightpanda)\n"
        "  2. ~/.itda-skills/bin/lightpanda\n"
        "  3. ./mnt/.itda-skills/bin/lightpanda (Cowork 마운트)\n"
        "  4. ./.itda-skills/bin/lightpanda (Cowork 세션)\n"
    )

    return base + guide + detect_order


def hyve_escalation_message(url: str, signal: str) -> str:
    """bot challenge 감지 시 hyve MCP escalation 안내."""
    return (
        f"[web-reader] Bot challenge 감지: {signal!r}\n"
        f"Lightpanda는 anti-bot 우회 기능이 없습니다. 다음 경로를 시도하세요:\n\n"
        f"1. hyve MCP web_browse.render (chromedp + stealth)\n"
        f"   예: \"hyve의 web_browse.render로 {url} 가져와줘\"\n\n"
        f"2. 네이버 부동산이면: naverplace 도메인 사용\n"
        f"   예: \"naverplace로 단지 정보 받아줘\"\n\n"
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

    lp = _find_lightpanda()
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

    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit:
        return 2

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
