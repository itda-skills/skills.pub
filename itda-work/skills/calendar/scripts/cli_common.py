#!/usr/bin/env python3
"""itda-calendar: cli_common — shared CLI helpers (env resolve, connect, errors)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from caldav_providers import detect_providers, get_provider  # noqa: E402
from env_loader import merged_env  # noqa: E402
import caldav_client  # noqa: E402


def emit(obj, code: int = 0) -> None:
    """Print JSON to stdout and exit with code."""
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(code)


def emit_error(error: str, detail=None, code: int = 1) -> None:
    out = {"status": "error", "error": error}
    if detail is not None:
        out["detail"] = str(detail)[:300]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(code)


def resolve_provider_or_exit(provider: str, account: str | None = None) -> dict:
    """Resolve credentials, or exit 1 (missing) / 2 (ambiguous account)."""
    env = merged_env()
    prov = get_provider(provider, env, account)
    if prov is not None:
        return prov

    detected = detect_providers(env)
    match = next((p for p in detected
                  if p["provider"] == provider or provider in p.get("aliases", [])),
                 None)
    if match and account is None:
        ready = [a["account_id"] for a in match["accounts"] if a["status"] == "ready"]
        if len(ready) > 1:
            emit_error("account_required",
                       f"multiple accounts for {provider}: {ready}; pass --account",
                       code=2)
    emit_error("credentials_missing",
               f"provider '{provider}' not configured (set its env vars; "
               f"see GUIDE.md)", code=1)


def classify_error(exc) -> str:
    """Map an exception to a stable error code."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "authorization" in name or "401" in msg or "unauthorized" in msg:
        return "auth_failed"
    if "notfound" in name or "404" in msg:
        return "not_found"
    if "timed out" in msg or "timeout" in msg:
        return "timeout"
    if any(s in msg for s in ("getaddrinfo", "name or service", "connection",
                              "ssl", "certificate")):
        return "network_error"
    return "caldav_error"


def connect_or_exit(prov: dict, timeout: int = 30):
    """Connect + discover principal, or exit 1 with a classified error."""
    client = caldav_client.connect(prov, timeout=timeout)
    try:
        principal = caldav_client.get_principal(client)
    except Exception as e:  # noqa: BLE001
        emit_error(classify_error(e), e, code=1)
    return client, principal
