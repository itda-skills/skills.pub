"""pptx-design 갤러리 공용 MCP stdio 클라이언트.

`go run ./cmd/hyve mcp stdio --experimental` 를 서브프로세스로 띄우고 표준 MCP
프로토콜(newline-delimited JSON-RPC)로 통신한다. HTTP 데몬 불요(자체완결).
stdout=JSON-RPC 프레임, stderr=진단 로그.

HYVE_DIR(저장소 루트) 해석 순서:
  1) 환경변수 HYVE_DIR
  2) 이 파일 기준 저장소 루트(gallery/_shared/mcp_stdio.py → parents[6])
저장소 루트에서 `go run ./cmd/hyve` 가 동작하고, COM 백엔드(hyve-office.exe)는
해당 루트의 빌드 산출물에서 탐색된다(재현성: 절대경로 하드코딩 금지).
"""
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path


def resolve_hyve_dir():
    env = os.environ.get("HYVE_DIR")
    if env:
        return env
    # gallery/_shared/mcp_stdio.py → <root>/skills/itda-work/skills/pptx-design/gallery/_shared/mcp_stdio.py
    return str(Path(__file__).resolve().parents[6])


def resolve_office_exe(root):
    """COM 백엔드 hyve-office.exe 경로 해석.

    go 서버 auto-discovery tier 0 은 net10.0-windows/hyve-office.exe(비-RID)를 보지만,
    이 저장소의 Debug 빌드는 RID 하위(win-x64/)에 산출되므로 tier 1(HYVE_OFFICE_PATH)로
    명시 주입한다. 절대경로 하드코딩 대신 저장소 빌드 산출물을 glob 하여 재현성 유지.
    """
    env = os.environ.get("HYVE_OFFICE_PATH")
    if env and os.path.exists(env):
        return env
    base = Path(root) / "dotnet/hyve-office/src/HyveOffice.Cli/bin/Debug/net10.0-windows"
    cands = list(base.glob("**/hyve-office.exe"))
    if not cands:
        return None
    return str(max(cands, key=lambda p: p.stat().st_mtime))  # 최신 빌드 우선


HYVE_DIR = resolve_hyve_dir()
HYVE_OFFICE_EXE = resolve_office_exe(HYVE_DIR)


def ensure_write_root(path, hyve_dir):
    """갤러리 출력 폴더(OUT)를 등록-root(rw)로 1회 등록한다.

    SPEC-FILES-ACCESS-001 #410: REQ-7 PoC 전면허용 스위치(HYVE_FILES_ALLOW_ALL) 제거에 따라,
    MCP 가 OUT 에 쓰려면 정식 등록이 필요하다. CLI `files add-root` + `set-permission rw`
    (MCP 와 동일 files.toml)로 등록·rw 권한 보장하며 멱등(이미 등록·rw 면 no-op).
    dev 한정 — 사용자 files.toml 에 출력 폴더가 등록된다.
    """
    if not path:
        return
    os.makedirs(path, exist_ok=True)
    # add-root(신규 등록; 이미 등록 시 ErrRootDuplicate 무시) → set-permission rw.
    # AddRoot 는 중복 시 권한을 올리지 않으므로, OUT 이 사전에 r(읽기전용)로 등록돼 있어도
    # set-permission 으로 rw 를 보장한다(이미 rw 면 no-op). 둘 다 멱등.
    for sub in (["add-root", path, "--permission", "rw"], ["set-permission", path, "--permission", "rw"]):
        try:
            subprocess.run(
                ["go", "run", "./cmd/hyve", "files"] + sub,
                cwd=hyve_dir, capture_output=True, text=True, timeout=300,
            )
        except Exception as e:
            print(f"[ensure_write_root] files {sub[0]} 경고(무시): {e}", file=sys.stderr)


class MCPStdio:
    def __init__(self, experimental=True, compile_timeout=240, write_root=None):
        # SPEC-FILES-ACCESS-001 #410: PoC 전면허용 스위치(HYVE_FILES_ALLOW_ALL) 제거.
        # MCP 가 출력(OUT)에 쓰려면 write_root 를 등록-root(rw)로 등록한다(정식 경로).
        if write_root:
            ensure_write_root(write_root, HYVE_DIR)
        args = ["go", "run", "./cmd/hyve", "mcp", "stdio"]
        if experimental:
            args.append("--experimental")
        env = dict(os.environ)
        if HYVE_OFFICE_EXE and "HYVE_OFFICE_PATH" not in env:
            env["HYVE_OFFICE_PATH"] = HYVE_OFFICE_EXE  # COM 백엔드 명시 주입
        self.p = subprocess.Popen(
            args, cwd=HYVE_DIR, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
        )
        self._q = queue.Queue()
        self._err = []
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        self._id = 0
        self.compile_timeout = compile_timeout

    def _read_stdout(self):
        for line in self.p.stdout:
            line = line.strip()
            if line:
                self._q.put(line)

    def _read_stderr(self):
        for line in self.p.stderr:
            self._err.append(line.rstrip())

    def _send(self, obj):
        self.p.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.p.stdin.flush()

    def _recv(self, timeout):
        try:
            return json.loads(self._q.get(timeout=timeout))
        except queue.Empty:
            tail = "\n".join(self._err[-15:])
            raise TimeoutError(f"no JSON-RPC response in {timeout}s. stderr tail:\n{tail}")

    def call(self, method, params=None, timeout=60):
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self._recv(timeout=max(1, deadline - time.time()))
            if msg.get("id") == rid:
                return msg
        raise TimeoutError(f"no response for id={rid} ({method})")

    def notify(self, method, params=None):
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def initialize(self, client_name="pptx-gallery"):
        r = self.call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": "0.1"},
        }, timeout=self.compile_timeout)
        self.notify("notifications/initialized")
        return r

    def tools_call(self, name, arguments, timeout=120):
        return self.call("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)

    def close(self):
        try:
            self.p.stdin.close()
        except Exception:
            pass
        try:
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def mcp_text(resp):
    """MCP tools/call 결과의 content[].text 를 합쳐 반환 (보통 JSON 문자열)."""
    r = resp.get("result", {})
    if isinstance(r, dict) and "content" in r:
        return "".join(c.get("text", "") for c in r["content"] if c.get("type") == "text")
    return json.dumps(r, ensure_ascii=False)


def hyve(m, domain="", action="", params=None, timeout=120):
    args = {"domain": domain, "action": action}
    if params is not None:
        args["params"] = json.dumps(params, ensure_ascii=False)
    return m.tools_call("hyve", args, timeout=timeout)


# ── 고수준 호출 헬퍼 (덱 빌드 공용) ──────────────────────────────────────────
def call(m, domain, command, params, timeout=240):
    return json.loads(mcp_text(hyve(m, domain, command, {"command": command, **params}, timeout=timeout)))


def oe(m, command, params, timeout=240):
    return call(m, "office_edit", command, params, timeout)


def batch(m, pptx, cmds, timeout=300):
    r = oe(m, "batch", {"file": pptx, "commands": json.dumps(cmds, ensure_ascii=False)}, timeout)
    errs = [x for x in r.get("results", []) if not x.get("success")]
    return r, errs
