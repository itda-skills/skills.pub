#!/usr/bin/env python3
"""itda-email: send_draft.py — Drafts의 초안을 SMTP로 발송.

SPEC-EMAIL-DRAFTS-001 REQ-DRAFTS-003, REQ-DRAFTS-004, REQ-DRAFTS-005:
  - UID FETCH → SMTP 발송 → EXPUNGE (기본)
  - --keep: EXPUNGE 건너뜀
  - --dry-run: SMTP/EXPUNGE 없이 preview JSON 반환
  - UID 없음: exit code 1, stderr uid_not_found
  - SMTP 실패: EXPUNGE 안 함, exit code 1
"""
from __future__ import annotations

import argparse
import email
import email.header
import imaplib
import json
import smtplib
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from email_providers import get_provider, resolve_provider_name  # noqa: E402
from env_loader import merged_env  # noqa: E402
from save_draft import _get_drafts_folder  # noqa: E402


def _decode_header(raw: str) -> str:
    """RFC 2047 인코딩된 이메일 헤더를 UTF-8 문자열로 디코딩한다."""
    parts = []
    for chunk, charset in email.header.decode_header(raw or ""):
        if isinstance(chunk, bytes):
            for enc in [charset or "utf-8", "utf-8", "euc-kr", "cp949", "latin-1"]:
                try:
                    parts.append(chunk.decode(enc))
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                parts.append(chunk.decode("latin-1", errors="replace"))
        else:
            parts.append(chunk or "")
    return "".join(parts)


def _fetch_message(imap: imaplib.IMAP4_SSL, uid: int) -> bytes | None:
    """IMAP에서 UID로 전체 메시지 바이트를 가져온다. UID가 없으면 None을 반환한다."""
    _status, fetch_data = imap.uid("FETCH", str(uid).encode(), "(BODY[])")
    if not fetch_data or fetch_data[0] is None:
        return None
    for item in fetch_data:
        if isinstance(item, tuple) and len(item) >= 2:
            return item[1]
    return None


def _send_via_smtp(
    provider_cfg: dict,
    recipients: list[str],
    raw_message: bytes,
) -> None:
    """SSL(465) 또는 STARTTLS(587)로 SMTP 발송을 시도한다."""
    host = provider_cfg["smtp_host"]
    email_addr = provider_cfg["email"]
    password = provider_cfg["password"]
    ctx = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(host, 465, timeout=20, context=ctx) as smtp:
            smtp.login(email_addr, password)
            smtp.sendmail(email_addr, recipients, raw_message)
        return
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused):
        raise
    except Exception:
        pass  # 465 실패 시 587 시도

    with smtplib.SMTP(host, 587, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ctx)
        smtp.ehlo()
        smtp.login(email_addr, password)
        smtp.sendmail(email_addr, recipients, raw_message)


def send_draft(
    provider: str,
    uid: int,
    keep: bool = False,
    dry_run: bool = False,
    account: str | None = None,
) -> dict:
    """Drafts 폴더의 초안을 SMTP로 발송하고 결과를 반환한다.

    반환값:
        성공: {"status": "sent", "uid": N, "expunged": bool}
        dry-run: {"status": "dry_run", "uid": N, "preview": {...}}

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

        raw_bytes = _fetch_message(imap, uid)
        if raw_bytes is None:
            print(
                json.dumps({"error": "uid_not_found", "uid": uid}),
                file=sys.stderr,
            )
            sys.exit(1)

        # MIME 파싱
        msg = email.message_from_bytes(raw_bytes)
        subject = _decode_header(msg.get("Subject", ""))
        to_raw = msg.get("To", "")
        cc_raw = msg.get("Cc", "")
        bcc_raw = msg.get("Bcc", "")

        recipients: list[str] = []
        for addr_field in (to_raw, cc_raw, bcc_raw):
            recipients += [a.strip() for a in addr_field.split(",") if a.strip()]

        if dry_run:
            # 본문 앞 200자 미리보기
            body_preview = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            charset = part.get_content_charset() or "utf-8"
                            body_preview = payload.decode(charset, errors="replace")[:200]
                            break
            else:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = msg.get_content_charset() or "utf-8"
                    body_preview = payload.decode(charset, errors="replace")[:200]

            attachments_preview = []
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_filename():
                        attachments_preview.append(part.get_filename())

            return {
                "status": "dry_run",
                "uid": uid,
                "preview": {
                    "to": to_raw,
                    "cc": cc_raw,
                    "bcc": bcc_raw,
                    "subject": subject,
                    "body_preview": body_preview,
                    "attachments": attachments_preview,
                },
            }

        # SMTP 발송
        try:
            _send_via_smtp(provider_cfg, recipients, raw_bytes)
        except smtplib.SMTPAuthenticationError as e:
            print(json.dumps({"error": "auth_failed", "detail": str(e)}), file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(json.dumps({"error": "smtp_failed", "detail": str(e)}), file=sys.stderr)
            sys.exit(1)

        # 발송 성공 후 EXPUNGE (--keep 없을 때)
        expunged = False
        if not keep:
            imap.uid("STORE", str(uid).encode(), "+FLAGS", "(\\Deleted)")
            imap.uid("EXPUNGE", str(uid).encode())
            expunged = True

        return {
            "status": "sent",
            "uid": uid,
            "expunged": expunged,
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
    parser = argparse.ArgumentParser(description="Drafts 초안을 SMTP로 발송합니다.")
    parser.add_argument("--provider", required=True, choices=["naver", "google", "gmail", "daum", "custom"])
    parser.add_argument("--uid", required=True, type=int)
    parser.add_argument("--keep", action="store_true", help="발송 후 초안을 Drafts에 보존합니다.")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="SMTP/EXPUNGE 없이 MIME 파싱 결과만 출력합니다.")
    parser.add_argument("--account", default=None)
    args = parser.parse_args()

    result = send_draft(
        provider=args.provider,
        uid=args.uid,
        keep=args.keep,
        dry_run=args.dry_run,
        account=args.account,
    )
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
