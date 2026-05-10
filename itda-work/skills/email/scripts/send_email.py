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


# Errors that indicate a network/connectivity issue worth retrying on 587/STARTTLS.
# Auth-related errors are NOT retried — credentials are wrong on either port.
_RETRY_ON_587 = (
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPConnectError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def _send_via_465(host: str, email: str, password: str, recipients: list[str],
                  msg_str: str) -> None:
    """Primary send path via SMTPS (port 465)."""
    with smtplib.SMTP_SSL(host, 465, timeout=20) as smtp:
        smtp.login(email, password)
        smtp.sendmail(email, recipients, msg_str)


def _send_via_587(host: str, email: str, password: str, recipients: list[str],
                  msg_str: str) -> None:
    """Fallback send path via SMTP submission (port 587 + STARTTLS).

    Activated when 465 fails with a network-level error (not auth).
    Useful in sandboxed networks where 465 is blocked but 587 is open
    (very common in container/Cowork environments).
    """
    with smtplib.SMTP(host, 587, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(email, password)
        smtp.sendmail(email, recipients, msg_str)


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
    parser.add_argument("--force-587", action="store_true",
                        help="465 SMTPS를 건너뛰고 처음부터 587 STARTTLS로 발송. "
                             "465가 항상 차단되는 환경에서 fallback 대기 시간 절약.")
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

    msg_str = msg.as_string()
    transport_used = "smtps_465"
    primary_error: Exception | None = None

    if args.force_587:
        # @MX:NOTE: --force-587 skips 465 entirely.
        try:
            _send_via_587(
                provider["smtp_host"], provider["email"], provider["password"],
                recipients, msg_str,
            )
            transport_used = "starttls_587_forced"
        except smtplib.SMTPAuthenticationError as e:
            print(json.dumps({"status": "error", "error": "auth_failed", "detail": str(e)}))
            sys.exit(1)
        except smtplib.SMTPRecipientsRefused as e:
            print(json.dumps({"status": "error", "error": "invalid_recipient", "detail": str(e)}))
            sys.exit(1)
        except Exception as e:
            print(json.dumps({
                "status": "error",
                "error": "send_failed_forced_587",
                "detail": f"{type(e).__name__}: {e}",
                "hint": (
                    f"`python3 scripts/diagnose_smtp.py --provider {args.provider}` "
                    "로 어느 레이어에서 실패했는지 확인하세요."
                ),
            }))
            sys.exit(1)
        print(json.dumps({
            "status": "ok",
            "message_id": msg["Message-ID"],
            "to": args.to,
            "subject": args.subject,
            "transport": transport_used,
        }))
        sys.exit(0)

    try:
        _send_via_465(
            provider["smtp_host"], provider["email"], provider["password"],
            recipients, msg_str,
        )
    except smtplib.SMTPAuthenticationError as e:
        # Credentials wrong — same on 587, no point retrying.
        print(json.dumps({"status": "error", "error": "auth_failed", "detail": str(e)}))
        sys.exit(1)
    except smtplib.SMTPRecipientsRefused as e:
        print(json.dumps({"status": "error", "error": "invalid_recipient", "detail": str(e)}))
        sys.exit(1)
    except _RETRY_ON_587 as e:
        # @MX:NOTE: 465 connection-level failure → automatic 587/STARTTLS fallback.
        # Common in sandboxed networks (Cowork, container egress filters).
        primary_error = e
        print(
            f"warning: SMTPS(465) failed ({type(e).__name__}: {e}); "
            f"retrying via STARTTLS(587)...",
            file=sys.stderr,
        )
        try:
            _send_via_587(
                provider["smtp_host"], provider["email"], provider["password"],
                recipients, msg_str,
            )
            transport_used = "starttls_587_fallback"
        except smtplib.SMTPAuthenticationError as e2:
            print(json.dumps({"status": "error", "error": "auth_failed", "detail": str(e2)}))
            sys.exit(1)
        except smtplib.SMTPRecipientsRefused as e2:
            print(json.dumps({"status": "error", "error": "invalid_recipient", "detail": str(e2)}))
            sys.exit(1)
        except Exception as e2:
            print(json.dumps({
                "status": "error",
                "error": "send_failed_both_ports",
                "detail_465": f"{type(primary_error).__name__}: {primary_error}",
                "detail_587": f"{type(e2).__name__}: {e2}",
                "hint": (
                    "양쪽 포트 모두 실패. `python3 scripts/diagnose_smtp.py "
                    f"--provider {args.provider}` 로 레이어별 진단 실행 권장."
                ),
            }))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": "send_failed",
            "detail": str(e),
            "hint": (
                f"`python3 scripts/diagnose_smtp.py --provider {args.provider}` "
                "로 어느 레이어에서 실패했는지 확인하세요."
            ),
        }))
        sys.exit(1)

    print(json.dumps({
        "status": "ok",
        "message_id": msg["Message-ID"],
        "to": args.to,
        "subject": args.subject,
        "transport": transport_used,
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
