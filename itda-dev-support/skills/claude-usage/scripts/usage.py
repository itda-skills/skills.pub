#!/usr/bin/env python3
"""claude-usage — 이 머신의 Claude Code 자격증명으로 사용량을 조회해 JSON 으로 낸다.

    python3 usage.py             # JSON 출력, exit 0
    python3 usage.py --max 20    # 5시간 창 사용률이 20% 이하면 exit 0, 초과 exit 1
    python3 usage.py --window weekly --max 80

조회 실패(자격증명 없음·토큰 만료·응답 형식 변경·네트워크)는 에러 JSON + **exit 2** 다 —
게이트로 쓸 때 모를 때는 통과시키지 않는다(fail-closed).

계약은 sheriff(Core/UsageStatus.swift·UsageFetcher.swift) 실측을 옮긴 것이다:
- 자격증명: macOS 키체인 "Claude Code-credentials"(`/usr/bin/security`) 와
  `~/.claude/.credentials.json` **둘 다** 읽어 expiresAt 이 늦은 쪽을 쓴다(파일에 폐기된
  옛 토큰이 남는 실측). Windows/Linux 는 파일만.
- 요청: GET https://api.anthropic.com/api/oauth/usage, `anthropic-beta: oauth-2025-04-20`
  (없으면 401).
- 응답: `five_hour`·`seven_day` 상시, `seven_day_opus` 등은 있을 때만, 모델별 주간 한도는
  `limits[]` 의 `weekly_scoped` 로만 온다.

토큰 값은 어떤 출력에도 싣지 않는다. Python 3.9 호환(stdlib 전용).
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
PROFILE_URL = "https://api.anthropic.com/api/oauth/profile"
KEYCHAIN_SERVICE = "Claude Code-credentials"
KNOWN_WINDOWS = (
    ("five_hour", "session", "5시간"),
    ("seven_day", "weekly", "7일"),
    ("seven_day_opus", "other", "7일 Opus"),
    ("seven_day_sonnet", "other", "7일 Sonnet"),
)


class UsageError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# ── 자격증명 ──────────────────────────────────────────────────────────────

def parse_credential(text):
    """자격증명 JSON → {access_token, plan, expires_at(epoch s|None)}. 형식이 틀리면 None."""
    try:
        root = json.loads(text)
    except Exception:
        return None
    oauth = root.get("claudeAiOauth") if isinstance(root, dict) else None
    if not isinstance(oauth, dict):
        return None
    token = oauth.get("accessToken")
    if not isinstance(token, str) or not token:
        return None
    expires = oauth.get("expiresAt")
    expires_at = expires / 1000 if isinstance(expires, (int, float)) else None
    return {
        "access_token": token,
        "plan": plan_name(oauth.get("subscriptionType"), oauth.get("rateLimitTier")),
        "expires_at": expires_at,
    }


def plan_name(subscription, tier):
    """"max" + "default_claude_max_20x" → "Max 20x", "pro" → "Pro"."""
    if not subscription:
        return None
    name = subscription[:1].upper() + subscription[1:]
    if isinstance(tier, str):
        tail = tier.rsplit("_", 1)[-1]
        if tail.endswith("x") and tail[:-1].isdigit():
            name += " " + tail
    return name


def read_keychain():
    if sys.platform != "darwin":
        return None
    try:
        proc = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return None
    return proc.stdout if proc.returncode == 0 else None


def read_file(home=None):
    path = os.path.join(home or os.path.expanduser("~"), ".claude", ".credentials.json")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def pick_credential(sources):
    """여러 자격증명 중 만료가 가장 늦은 것. 없으면 None."""
    creds = [c for c in (parse_credential(s) for s in sources if s) if c]
    if not creds:
        return None
    return max(creds, key=lambda c: c["expires_at"] if c["expires_at"] is not None else float("-inf"))


def load_credential():
    cred = pick_credential([read_keychain(), read_file()])
    if not cred:
        raise UsageError("no_credential",
                         "Claude Code 자격증명이 없다 — `claude` 로 로그인하면 생긴다 "
                         "(키체인 'Claude Code-credentials' 또는 ~/.claude/.credentials.json)")
    return cred


# ── 요청 ──────────────────────────────────────────────────────────────────

def http_get(url, token, timeout=15):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "anthropic-beta": "oauth-2025-04-20",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        raise UsageError("network", "네트워크 오류: " + str(e))


def fetch_usage(token):
    status, body = http_get(USAGE_URL, token)
    if status in (401, 403):
        raise UsageError("token_expired", "토큰 만료 — `claude` 를 한 번 실행하면 갱신된다 (HTTP %d)" % status)
    if status != 200:
        raise UsageError("http_%d" % status, "HTTP %d" % status)
    return body


def fetch_email(token):
    try:
        status, body = http_get(PROFILE_URL, token)
    except UsageError:
        return None
    if status != 200:
        return None
    try:
        email = json.loads(body).get("account", {}).get("email")
    except Exception:
        return None
    return email or None


# ── 응답 파싱 ─────────────────────────────────────────────────────────────

def parse_iso8601(text):
    if not isinstance(text, str):
        return None
    t = text.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    if "." in t:  # 소수 초는 6자리로 맞춘다 (3.9 fromisoformat 은 3·6자리만)
        head, rest = t.split(".", 1)
        frac = ""
        tz = ""
        for i, ch in enumerate(rest):
            if ch.isdigit():
                frac += ch
            else:
                tz = rest[i:]
                break
        t = head + "." + (frac + "000000")[:6] + tz
    try:
        from datetime import datetime
        return datetime.fromisoformat(t).timestamp()
    except Exception:
        return None


def parse_usage(body):
    """응답 JSON → windows 목록. sheriff.parseClaude 와 같은 규칙."""
    try:
        root = json.loads(body)
    except Exception:
        raise UsageError("bad_response", "응답이 JSON 이 아니다")
    if not isinstance(root, dict):
        raise UsageError("bad_response", "응답이 객체가 아니다")
    windows = []
    for key, kind, label in KNOWN_WINDOWS:
        bucket = root.get(key)
        if not isinstance(bucket, dict) or not isinstance(bucket.get("utilization"), (int, float)):
            continue
        windows.append({
            "key": key, "kind": kind, "label": label,
            "percent": float(bucket["utilization"]),
            "resets_at": parse_iso8601(bucket.get("resets_at")),
        })
    for item in root.get("limits") or []:
        if not isinstance(item, dict) or item.get("kind") != "weekly_scoped":
            continue
        if not isinstance(item.get("percent"), (int, float)):
            continue
        scope = item.get("scope") or {}
        model = (scope.get("model") or {}).get("display_name") if isinstance(scope, dict) else None
        surface = (scope.get("surface") or {}).get("display_name") if isinstance(scope, dict) else None
        name = model or surface
        if not name:
            continue
        label = "7일 " + name
        if any(w["label"] == label for w in windows):
            continue
        windows.append({
            "key": "weekly_scoped:" + name, "kind": "other", "label": label,
            "percent": float(item["percent"]),
            "resets_at": parse_iso8601(item.get("resets_at")),
        })
    if not windows:
        raise UsageError("bad_response", "응답 형식이 바뀜 — five_hour 가 없다")
    return windows


def pick_window(windows, kind):
    for w in windows:
        if w["kind"] == kind:
            return w
    return None


def with_reset_text(windows, now=None):
    now = time.time() if now is None else now
    for w in windows:
        r = w.get("resets_at")
        w["resets_in_seconds"] = int(r - now) if r else None
        w["resets_at_local"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(r)) if r else None
    return windows


# ── 진입 ──────────────────────────────────────────────────────────────────

def build_report(cred, body, email, now=None):
    windows = with_reset_text(parse_usage(body), now)
    return {
        "ok": True,
        "provider": "claude",
        "plan": cred.get("plan"),
        "email": email,
        "windows": windows,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
    }


def gate(report, kind, max_percent):
    """--max 판정 → (exit_code, verdict dict)."""
    w = pick_window(report["windows"], kind)
    if w is None:
        return 2, {"passed": False, "reason": "창 없음: " + kind}
    passed = w["percent"] <= max_percent
    return (0 if passed else 1), {
        "passed": passed, "window": w["label"], "percent": w["percent"], "max": max_percent,
    }


def main(argv=None):
    # Windows 콘솔은 기본 cp949 라 한국어·— 가 UnicodeEncodeError 로 죽는다(surface 실측) — 출력은 UTF-8 로
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max", type=float, default=None, help="이 %% 이하일 때만 exit 0 (게이트)")
    ap.add_argument("--window", choices=["session", "weekly"], default="session",
                    help="게이트 대상 창 (기본 session=5시간)")
    ap.add_argument("--no-email", action="store_true", help="프로필 조회 생략")
    a = ap.parse_args(argv)
    try:
        cred = load_credential()
        body = fetch_usage(cred["access_token"])
        email = None if a.no_email else fetch_email(cred["access_token"])
        report = build_report(cred, body, email)
    except UsageError as e:
        print(json.dumps({"ok": False, "provider": "claude", "error": e.code, "message": e.message},
                         ensure_ascii=False))
        return 2
    code = 0
    if a.max is not None:
        code, verdict = gate(report, a.window, a.max)
        report["gate"] = verdict
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
