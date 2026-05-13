#!/usr/bin/env python3
"""itda-email: delete_draft.py — Drafts 폴더에서 초안 삭제.

SPEC-EMAIL-DRAFTS-001:
  - UID에 \\Deleted 플래그 설정 + EXPUNGE
  - UID 없음/인증 실패: exit code 1
"""
from __future__ import annotations

import argparse
import imaplib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from email_providers import get_provider, resolve_provider_name  # noqa: E402
from env_loader import merged_env  # noqa: E402
from save_draft import _get_drafts_folder  # noqa: E402


def delete_draft(
    provider: str,
    uid: int,
    account: str | None = None,
) -> dict:
    """Drafts 폴더에서 UID에 해당하는 초안을 삭제한다.

    반환값:
        {"status": "deleted", "uid": N, "expunged": true}

    오류 시 SystemExit(1)을 발생시킨다.
    """
    env = merged_env()
    provider_cfg = get_provider(provider, env, account=account)

    if not provider_cfg or not provider_cfg.get("email") or not provider_cfg.get("password"):
        print(json.dumps({"error": "credentials_missing"}), file=sys.stderr)
        sys.exit(1)

    canonical = resolve_provider_name(provider)
    drafts_folder = _get_drafts_folder(canonical)

    imap: imaplib.IMAP4_SSL | None = None
    try:
        imap = imaplib.IMAP4_SSL(
            provider_cfg["imap_host"],
            provider_cfg["imap_port"],
        )
        imap.login(provider_cfg["email"], provider_cfg["password"])
        imap.select(drafts_folder)

        # UID STORE +FLAGS (\Deleted)
        status, store_data = imap.uid("STORE", str(uid).encode(), "+FLAGS", "(\\Deleted)")

        if status != "OK":
            print(
                json.dumps({"error": "uid_not_found", "uid": uid}),
                file=sys.stderr,
            )
            sys.exit(1)

        # UID EXPUNGE (RFC 4315 UIDPLUS — 해당 UID만 삭제)
        imap.uid("EXPUNGE", str(uid).encode())

        return {
            "status": "deleted",
            "uid": uid,
            "expunged": True,
        }

    except imaplib.IMAP4.error as e:
        print(json.dumps({"error": "auth_failed", "detail": str(e)}), file=sys.stderr)
        sys.exit(1)
    except (ConnectionError, TimeoutError, OSError) as e:
        print(json.dumps({"error": "network_error", "detail": str(e)}), file=sys.stderr)
        sys.exit(1)
    finally:
        if imap is not None:
            try:
                imap.logout()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Drafts 폴더에서 초안을 삭제합니다.")
    parser.add_argument("--provider", required=True, choices=["naver", "google", "gmail", "daum", "custom"])
    parser.add_argument("--uid", required=True, type=int)
    parser.add_argument("--account", default=None)
    args = parser.parse_args()

    result = delete_draft(
        provider=args.provider,
        uid=args.uid,
        account=args.account,
    )
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
