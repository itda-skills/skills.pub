#!/usr/bin/env python3
"""itda-email: send_email.py — send email via SMTP SSL."""
from __future__ import annotations

import argparse
import json
import mimetypes
import smtplib
import sys
import uuid
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from attachment_validator import validate_attachments  # noqa: E402
from email_providers import detect_providers, get_provider, resolve_provider_name  # noqa: E402
from env_loader import merged_env  # noqa: E402


def _build_attachment_part(filepath: str) -> MIMEBase:
    """파일을 MIMEBase 파트로 변환 (RFC 2231 한글 파일명 지원)."""
    path = Path(filepath)
    mime_guess, _ = mimetypes.guess_type(filepath)
    if mime_guess:
        maintype, subtype = mime_guess.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"

    part = MIMEBase(maintype, subtype)
    with open(filepath, "rb") as f:
        part.set_payload(f.read())
    encoders.encode_base64(part)
    # RFC 2231 인코딩으로 한글 파일명 지원
    part.add_header(
        "Content-Disposition",
        "attachment",
        filename=("utf-8", "", path.name),
    )
    return part


def main() -> None:
    parser = argparse.ArgumentParser(description="Send email via SMTP SSL.")
    parser.add_argument("--provider", required=True, choices=["naver", "google", "gmail", "daum", "custom"])
    parser.add_argument("--to", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--cc", default="")
    parser.add_argument("--bcc", default="")
    parser.add_argument("--account", default=None,
                        help="Account suffix (default, work, personal, 1, 2, ...)")
    parser.add_argument("--html", action="store_true")
    parser.add_argument("--attach", action="append", default=[], metavar="FILE",
                        help="첨부파일 경로 (복수 지정 가능: --attach a.pdf --attach b.xlsx)")
    args = parser.parse_args()

    env = merged_env()
    provider = get_provider(args.provider, env, account=args.account)
    if not provider or not provider.get("email") or not provider.get("password"):
        # Check if the failure is due to ambiguous multi-account selection
        all_providers = detect_providers(env)
        canonical = resolve_provider_name(args.provider)
        matching = next((p for p in all_providers if p["provider"] == canonical), None)
        if matching and len(matching["accounts"]) > 1 and args.account is None:
            available = ", ".join(
                a["account_id"] for a in matching["accounts"] if a["status"] == "ready"
            )
            print(
                json.dumps({
                    "status": "error",
                    "error": "account_required",
                    "detail": f"Multiple accounts configured. Use --account. Available: {available}",
                }),
                file=sys.stderr,
            )
            sys.exit(2)
        print(json.dumps({"status": "error", "error": "credentials_missing"}))
        sys.exit(1)

    # 첨부파일 사전 검증
    if args.attach:
        violations, warnings = validate_attachments(args.provider, args.attach)
        for w in warnings:
            print(w, file=sys.stderr)
        if violations:
            detail = "; ".join(
                f"파일 '{v['file']}': {v['reason']}" for v in violations
            )
            print(json.dumps({
                "status": "error",
                "error": "attachment_validation_failed",
                "detail": detail,
                "violations": violations,
            }))
            sys.exit(1)

    mime_type = "html" if args.html else "plain"

    # 첨부파일 유무에 따라 메시지 구조 결정
    if args.attach:
        msg: MIMEMultipart | MIMEText = MIMEMultipart("mixed")
        msg.attach(MIMEText(args.body, mime_type, "utf-8"))
        for fp in args.attach:
            msg.attach(_build_attachment_part(fp))
    else:
        msg = MIMEText(args.body, mime_type, "utf-8")

    msg["From"] = provider["email"]
    msg["To"] = args.to
    msg["Subject"] = args.subject
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = f"<{uuid.uuid4()}@itda-email>"
    if args.cc:
        msg["Cc"] = args.cc

    recipients = [args.to]
    if args.cc:
        recipients += [a.strip() for a in args.cc.split(",") if a.strip()]
    if args.bcc:
        recipients += [a.strip() for a in args.bcc.split(",") if a.strip()]

    try:
        with smtplib.SMTP_SSL(provider["smtp_host"], provider["smtp_port"]) as smtp:
            smtp.login(provider["email"], provider["password"])
            smtp.sendmail(provider["email"], recipients, msg.as_string())
        print(json.dumps({
            "status": "ok",
            "message_id": msg["Message-ID"],
            "to": args.to,
            "subject": args.subject,
        }))
        sys.exit(0)
    except smtplib.SMTPAuthenticationError as e:
        print(json.dumps({"status": "error", "error": "auth_failed", "detail": str(e)}))
        sys.exit(1)
    except smtplib.SMTPRecipientsRefused as e:
        print(json.dumps({"status": "error", "error": "invalid_recipient", "detail": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": "send_failed", "detail": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
