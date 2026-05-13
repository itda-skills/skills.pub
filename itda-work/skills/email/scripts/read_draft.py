#!/usr/bin/env python3
"""itda-email: read_draft.py — IMAP Drafts 폴더에서 초안 본문 조회.

SPEC-EMAIL-DRAFTS-001 REQ-DRAFTS-001:
  - UID로 본문(text/plain, text/html, 첨부 메타) 조회
  - UID 없으면 exit code 1, stderr에 uid_not_found
"""
from __future__ import annotations

import argparse
import email
import email.header
import imaplib
import json
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


def _extract_body_and_attachments(msg: email.message.Message) -> tuple[str, str | None, list[dict]]:
    """MIME 메시지에서 본문(text), HTML 본문, 첨부파일 메타를 추출한다."""
    body_text = ""
    body_html: str | None = None
    attachments: list[dict] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get("Content-Disposition", "")
            filename = part.get_filename()

            if filename or "attachment" in disposition.lower():
                # 첨부파일 메타데이터
                payload = part.get_payload(decode=True)
                size = len(payload) if isinstance(payload, bytes) else 0
                attachments.append({
                    "filename": filename or "unknown",
                    "size": size,
                    "content_type": content_type,
                })
            elif content_type == "text/plain" and not body_text:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")
            elif content_type == "text/html" and body_html is None:
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    body_html = payload.decode(charset, errors="replace")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if content_type == "text/html":
                body_html = decoded
            else:
                body_text = decoded

    return body_text, body_html, attachments


def read_draft(
    provider: str,
    uid: int,
    account: str | None = None,
) -> dict:
    """UID로 Drafts 폴더에서 초안 본문을 조회한다.

    반환값:
        uid, subject, from, to, cc, bcc, date, body_text, body_html, attachments

    UID가 없으면 SystemExit(1)을 발생시킨다.
    """
    env = merged_env()
    provider_cfg = get_provider(provider, env, account=account)

    if not provider_cfg or not provider_cfg.get("email") or not provider_cfg.get("password"):
        print(
            json.dumps({"error": "credentials_missing"}),
            file=sys.stderr,
        )
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
        imap.select(drafts_folder, readonly=True)

        # UID FETCH 전체 메시지
        _status, fetch_data = imap.uid("FETCH", str(uid).encode(), "(BODY[])")

        if not fetch_data or fetch_data[0] is None:
            print(
                json.dumps({"error": "uid_not_found", "uid": uid}),
                file=sys.stderr,
            )
            sys.exit(1)

        # 실제 메시지 바이트 추출
        raw_bytes: bytes | None = None
        for item in fetch_data:
            if isinstance(item, tuple) and len(item) >= 2:
                raw_bytes = item[1]
                break

        if not raw_bytes:
            print(
                json.dumps({"error": "uid_not_found", "uid": uid}),
                file=sys.stderr,
            )
            sys.exit(1)

        msg = email.message_from_bytes(raw_bytes)

        subject = _decode_header(msg.get("Subject", ""))
        from_ = _decode_header(msg.get("From", ""))
        to_raw = msg.get("To", "")
        to_list = [a.strip() for a in to_raw.split(",") if a.strip()]
        cc_raw = msg.get("Cc", "")
        cc_list = [a.strip() for a in cc_raw.split(",") if a.strip()]
        bcc_raw = msg.get("Bcc", "")
        bcc_list = [a.strip() for a in bcc_raw.split(",") if a.strip()]
        date_str = msg.get("Date", "")

        body_text, body_html, attachments = _extract_body_and_attachments(msg)

        return {
            "uid": uid,
            "subject": subject,
            "from": from_,
            "to": to_list,
            "cc": cc_list,
            "bcc": bcc_list,
            "date": date_str,
            "body_text": body_text,
            "body_html": body_html,
            "attachments": attachments,
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
    parser = argparse.ArgumentParser(description="IMAP Drafts 폴더에서 초안 본문을 조회합니다.")
    parser.add_argument("--provider", required=True, choices=["naver", "google", "gmail", "daum", "custom"])
    parser.add_argument("--uid", required=True, type=int)
    parser.add_argument("--account", default=None)
    args = parser.parse_args()

    result = read_draft(
        provider=args.provider,
        uid=args.uid,
        account=args.account,
    )
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
