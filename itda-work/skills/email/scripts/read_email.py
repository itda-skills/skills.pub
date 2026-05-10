#!/usr/bin/env python3
"""itda-email: read_email.py — read email via IMAP SSL."""
from __future__ import annotations

import argparse
import email
import email.header
import imaplib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from email_imap_utf7 import encode_modified_utf7  # noqa: E402
from email_providers import detect_providers, get_provider, resolve_provider_name  # noqa: E402
from email_security import (  # noqa: E402
    WRAPPER_OVERHEAD,
    build_auth_label,
    parse_auth_results,
    reply_to_differs,
    sanitize_for_llm,
    wrap_email_content,
)
from email_state import (  # noqa: E402
    get_account_state,
    load_state,
    reset_account_state,
    save_state,
    update_account_state,
)
from env_loader import merged_env  # noqa: E402
from itda_path import resolve_data_dir  # noqa: E402

DEFAULT_MAX_CHARS = 1500  # default body length for --max-chars (token-optimized: most emails fit in 1500 chars)
# @MX:NOTE: Reduced from 5000 to 1500 in v0.17.0. Use --max-chars -1 for full body.

# Headers required for sanitization, dates, and phishing signal extraction.
# Used by --headers-only mode to fetch only required header fields, not the full RFC822 body.
_HEADER_FIELDS = (
    "FROM SUBJECT DATE REPLY-TO TO CC AUTHENTICATION-RESULTS"
)
_HEADERS_ONLY_FETCH_SPEC = f"(BODY.PEEK[HEADER.FIELDS ({_HEADER_FIELDS})])"
# Full message fetch via PEEK (does NOT mark \Seen flag, unlike RFC822).
_FULL_FETCH_SPEC = "(BODY.PEEK[])"
BODY_PREVIEW_LIMIT = 500  # deprecated body_preview field limit (AC-08)
# Reserve budget for wrap_email_content markers so body_preview total stays
# within BODY_PREVIEW_LIMIT (ISS-89e62b86).
_BODY_PREVIEW_SANITIZE_LIMIT = BODY_PREVIEW_LIMIT - WRAPPER_OVERHEAD  # 450 chars

# Truncation notice appended when body exceeds max_chars (FR-03).
TRUNCATE_NOTICE_TEMPLATE = (
    "\n\n...[이하 {n}자 생략. --max-chars=-1로 재실행하면 전체 본문을 볼 수 있습니다.]"
)


def _strip_tags(html: str) -> str:
    """Remove HTML tags from string."""
    return re.sub(r"<[^>]+>", "", html)


def _decode_header(raw: str) -> str:
    """Decode RFC 2047 encoded email header."""
    parts = []
    for chunk, charset in email.header.decode_header(raw):
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
            parts.append(chunk)
    return "".join(parts)


def _get_raw_body_text(msg: email.message.Message) -> str:
    """Extract full raw text body from email message, stripping HTML tags if needed.

    Returns the complete text body without truncation. Callers are responsible
    for applying max_chars limits via _build_body_field().
    """
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
            elif ct == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = _strip_tags(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            raw_text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                body = _strip_tags(raw_text)
            else:
                body = raw_text
    return body


def _build_body_field(
    raw: str,
    max_chars: int,
) -> tuple[str, int, bool]:
    """Build the body JSON field with sanitization, wrapping, and truncation.

    Args:
        raw: Full raw text body (from _get_raw_body_text).
        max_chars: Maximum content characters. -1 = unlimited, 0 = empty.

    Returns:
        (wrapped_body, total_chars, truncated) tuple where:
        - wrapped_body: wrap_email_content(sanitized_body [+ notice])
        - total_chars: length of raw before any sanitize/truncation
        - truncated: True if raw exceeded max_chars
    """
    total = len(raw)

    if max_chars == 0:
        # Return empty wrapped body; truncated only when there was content.
        return wrap_email_content(""), total, total > 0

    if max_chars < 0:
        # Unlimited — pass full length to sanitize (at most total chars).
        sanitized = sanitize_for_llm(raw, max_len=max(total, 1))
        return wrap_email_content(sanitized), total, False

    # Bounded mode: sanitize to max_chars, then check if original was longer.
    sanitized = sanitize_for_llm(raw, max_len=max_chars)
    is_truncated = total > max_chars

    if is_truncated:
        n_omitted = total - max_chars
        notice = TRUNCATE_NOTICE_TEMPLATE.format(n=n_omitted)
        body_text = sanitized + notice
    else:
        body_text = sanitized

    return wrap_email_content(body_text), total, is_truncated


def _encode_folder(folder: str) -> str:
    """Prepare *folder* for the IMAP wire protocol.

    Applies, in order:
    1. Modified UTF-7 encoding for non-ASCII names (RFC 3501 §5.1.3).
    2. Double-quote wrapping when the result contains a space or other
       IMAP atom-unsafe characters. imaplib's ``select`` / ``status`` do
       NOT quote arguments, so callers must hand them wire-ready strings.
    3. Backslash escaping of embedded quotes and backslashes inside the
       quoted form.

    Naver's canonical folders (``Sent Messages``, ``Deleted Messages``)
    require this because imaplib would otherwise emit ``SELECT Sent
    Messages`` — two tokens — and the server returns ``BAD Invalid
    arguments``. Modified UTF-7 output never contains spaces so the
    quoting only kicks in for ASCII-with-spaces names.
    """
    try:
        folder.encode("ascii")
        encoded = folder
    except UnicodeEncodeError:
        encoded = encode_modified_utf7(folder)

    # Quote if the name contains any character outside the IMAP "atom-specials"
    # safe set. Spaces and double-quotes are the common offenders here.
    if re.search(r'[\s"\\(){}%*\]]', encoded):
        escaped = encoded.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return encoded


def _fetch_uidvalidity(imap: imaplib.IMAP4, folder_enc: str) -> int:
    """Return the UIDVALIDITY for the selected folder, or ``0`` if unavailable.

    Tries ``imap.response('UIDVALIDITY')`` first (populated by the preceding
    SELECT), falling back to an explicit ``STATUS`` call on *folder_enc*.
    """
    try:
        typ, data = imap.response("UIDVALIDITY")
        if typ == "OK" and data:
            for item in data:
                if item is None:
                    continue
                try:
                    return int(item)
                except (TypeError, ValueError):
                    continue
    except imaplib.IMAP4.error:
        pass

    try:
        typ, data = imap.status(folder_enc, "(UIDVALIDITY)")
        if typ == "OK" and data and data[0]:
            raw = data[0].decode() if isinstance(data[0], bytes) else str(data[0])
            match = re.search(r"UIDVALIDITY\s+(\d+)", raw)
            if match:
                return int(match.group(1))
    except imaplib.IMAP4.error:
        pass
    return 0


def _parse_uid_search_result(data: list) -> list[bytes]:
    """Normalize an imap.uid('SEARCH', ...) response into a list of UID bytes."""
    if not data or data[0] is None:
        return []
    first = data[0]
    if isinstance(first, bytes):
        return first.split()
    if isinstance(first, str):
        return first.encode().split()
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Read email via IMAP SSL.")
    parser.add_argument("--provider", required=True, choices=["naver", "google", "gmail", "daum", "custom"])
    parser.add_argument("--account", default=None,
                        help="Account suffix (default, work, personal, 1, 2, ...)")
    parser.add_argument("--folder", default="INBOX")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--search", default="ALL")
    parser.add_argument("--unread-only", action="store_true")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=(
            "Maximum body characters to return. "
            f"Default: {DEFAULT_MAX_CHARS}. "
            "-1 = full body. 0 = empty body."
        ),
    )
    parser.add_argument(
        "--headers-only",
        action="store_true",
        help=(
            "Fetch only headers (from/subject/date/reply-to/auth) without "
            "message body. Drastically reduces network and token usage when "
            "listing mail. Sets body to empty, total_chars=0, truncated=false."
        ),
    )
    parser.add_argument(
        "--since-last-run",
        action="store_true",
        help=(
            "Only fetch messages with UID greater than the last seen UID. "
            "State is kept at .itda-skills/email/state.json per "
            "(provider, email, folder). UIDVALIDITY changes trigger an "
            "automatic reset."
        ),
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help=(
            "Drop the incremental state entry for this (provider, email, "
            "folder) before fetching. Combine with --since-last-run to "
            "reseed from a clean slate."
        ),
    )
    args = parser.parse_args()

    if args.max_chars < -1:
        parser.error("--max-chars must be >= -1")


    env = merged_env()
    provider = get_provider(args.provider, env, account=args.account)
    provider_name = str((provider or {}).get("name", args.provider)).lower()

    if not provider or not provider.get("email") or not provider.get("password"):
        # Check if failure is due to ambiguous multi-account selection (AC-04, FR-05 rule #3)
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

    if not provider.get("imap_host"):
        error = f"{provider_name} provider does not support reading email via IMAP."
        print(json.dumps({
            "status": "error",
            "provider": provider_name,
            "error": error,
        }))
        sys.exit(1)

    search_criteria = "UNSEEN" if args.unread_only else args.search

    # --since-last-run state bookkeeping (SPEC-EMAIL-007)
    state_path = resolve_data_dir("email") / "state.json"
    state = load_state(state_path)
    account_email = provider["email"]

    if args.reset_state:
        state = reset_account_state(state, provider_name, account_email, args.folder)

    prev_entry = get_account_state(state, provider_name, account_email, args.folder)
    prev_uid = int(prev_entry["last_uid"]) if prev_entry else None
    prev_validity = int(prev_entry["uidvalidity"]) if prev_entry else None
    uidvalidity_changed = False

    # Non-ASCII folder names (Korean mailboxes like "보낸메일함") must be
    # Modified UTF-7 encoded before being handed to imaplib (RFC 3501 §5.1.3).
    folder_enc = _encode_folder(args.folder)

    try:
        imap = imaplib.IMAP4_SSL(provider["imap_host"], provider["imap_port"])
        imap.login(provider["email"], provider["password"])
        imap.select(folder_enc)
        current_validity = _fetch_uidvalidity(imap, folder_enc)

        if (
            args.since_last_run
            and prev_validity is not None
            and current_validity
            and prev_validity != current_validity
        ):
            uidvalidity_changed = True
            print(
                f"warning: UIDVALIDITY changed for {args.folder}, resetting state",
                file=sys.stderr,
            )
            prev_uid = None  # Fall back to normal fetch with fresh cursor.

        incremental_fetch = (
            args.since_last_run and prev_uid is not None and not uidvalidity_changed
        )
        # When since-last-run is active we operate exclusively on UIDs so the
        # cursor we persist is stable across sessions.
        uid_mode = args.since_last_run

        if incremental_fetch:
            _, uid_data = imap.uid("SEARCH", None, f"UID {prev_uid + 1}:*")
            all_ids = _parse_uid_search_result(uid_data)
            # ``UID n:*`` always returns the highest UID even when none qualify,
            # so filter defensively to UIDs strictly greater than the cursor.
            all_ids = [uid for uid in all_ids if int(uid) > prev_uid]
        elif uid_mode:
            # First run in since-last-run mode: seed the cursor via UID SEARCH.
            _, uid_data = imap.uid("SEARCH", None, search_criteria)
            all_ids = _parse_uid_search_result(uid_data)
        else:
            _, msg_ids = imap.search(None, search_criteria)
            all_ids = msg_ids[0].split() if msg_ids[0] else []

        fetch_ids = all_ids[-args.count :] if len(all_ids) > args.count else all_ids

        results = []
        fetched_uids: list[int] = []
        # @MX:NOTE: BODY.PEEK[] avoids marking \Seen flag (unlike RFC822).
        # HEADER.FIELDS variant only transfers required headers — major token saver.
        fetch_spec = _HEADERS_ONLY_FETCH_SPEC if args.headers_only else _FULL_FETCH_SPEC
        for mid in reversed(fetch_ids):
            if uid_mode:
                _, data = imap.uid("FETCH", mid, fetch_spec)
            else:
                _, data = imap.fetch(mid, fetch_spec)
            if not data or data[0] is None:
                continue
            raw = data[0][1]
            msg = email.message_from_bytes(raw)
            if uid_mode:
                try:
                    fetched_uids.append(int(mid))
                except (TypeError, ValueError):
                    pass
            raw_from = _decode_header(msg.get("From", ""))
            raw_subject = _decode_header(msg.get("Subject", ""))
            if args.headers_only:
                raw_body = ""
                body_str, total_chars, truncated = wrap_email_content(""), 0, False
            else:
                raw_body = _get_raw_body_text(msg)
                body_str, total_chars, truncated = _build_body_field(raw_body, args.max_chars)
            # Deprecated body_preview field: kept for backward compatibility.
            # Will be removed in v0.13.0+.
            body_preview_str = wrap_email_content(
                sanitize_for_llm(
                    raw_body[:BODY_PREVIEW_LIMIT],
                    max_len=_BODY_PREVIEW_SANITIZE_LIMIT,
                )
            )
            # Phishing signal extraction (SPEC-EMAIL-005)
            raw_auth = msg.get("Authentication-Results")
            auth = parse_auth_results(raw_auth)
            auth_label = build_auth_label(auth)
            raw_reply_to = msg.get("Reply-To", "")
            differs = reply_to_differs(raw_from, raw_reply_to)
            warnings_list: list[str] = []
            if differs:
                warnings_list.append("reply_to_differs")
            if auth.get("spf") == "fail":
                warnings_list.append("spf_fail")
            if auth.get("dmarc") == "fail":
                warnings_list.append("dmarc_fail")
            results.append({
                "id": mid.decode(),
                "from": sanitize_for_llm(raw_from, max_len=BODY_PREVIEW_LIMIT),
                "subject": sanitize_for_llm(raw_subject, max_len=BODY_PREVIEW_LIMIT),
                "date": sanitize_for_llm(msg.get("Date", ""), max_len=100),
                "body": body_str,
                "total_chars": total_chars,
                "truncated": truncated,
                "spf": auth.get("spf"),
                "dkim": auth.get("dkim"),
                "dmarc": auth.get("dmarc"),
                "auth_label": auth_label,
                "reply_to": sanitize_for_llm(raw_reply_to, max_len=200) or None,
                "reply_to_differs": differs,
                "warnings": warnings_list,
                "body_preview": body_preview_str,  # deprecated: use body
            })

        imap.logout()

        if args.since_last_run:
            # Persist a cursor that advances to the highest UID we actually
            # saw (fetched in this run OR the previous cursor if nothing new).
            if fetched_uids:
                new_last_uid = max(fetched_uids)
            elif prev_uid is not None and not uidvalidity_changed:
                new_last_uid = prev_uid
            else:
                new_last_uid = 0

            state = update_account_state(
                state,
                provider_name,
                account_email,
                args.folder,
                new_last_uid,
                current_validity,
            )
            try:
                save_state(state_path, state)
            except OSError as exc:
                print(f"warning: failed to save state ({exc})", file=sys.stderr)

            output: object = {
                "since_last_run": True,
                "previous_last_uid": prev_uid,
                "current_last_uid": new_last_uid,
                "uidvalidity_changed": uidvalidity_changed,
                "new_count": len(results),
                "messages": results,
            }
        else:
            output = results

        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)
    except imaplib.IMAP4.error as e:
        print(json.dumps({"status": "error", "error": "imap_error", "detail": str(e)}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": "unexpected", "detail": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
