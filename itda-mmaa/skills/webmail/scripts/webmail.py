"""웹메일 raw 결과 정규화 CLI.

브라우저 자동화 자체는 에이전트가 hyve web_browse MCP로 수행한다. 이 모듈은
fetch/extract/download raw JSON을 읽어 목록·본문·첨부 결과를 공통 스키마로 정규화한다.
지원 provider는 군인공제회(kacem)와 테스트 목적의 nate로 제한한다.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_PROVIDER = "kacem"
SUPPORTED_PROVIDERS = ("kacem", "nate")
DEFAULT_PROFILE_ID = "default"


def normalize_provider(provider: str | None = None) -> str:
    """지원 provider 이름을 검증하고 정규화한다."""
    normalized = (provider or DEFAULT_PROVIDER).strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported provider: {normalized or '<empty>'}")
    return normalized


def load_json(path: Path) -> Any:
    """JSON 파일을 읽는다."""
    return json.loads(path.read_text(encoding="utf-8"))


def render_list(raw: Any, folder: str = "inbox", provider: str | None = None) -> dict[str, Any]:
    """메일 목록 raw를 정규화한다."""
    provider = normalize_provider(provider)
    rows = _find_list(raw)
    items = [_normalize_list_item(row) for row in rows]
    return {
        "provider": provider,
        "folder": folder,
        "items": items,
        "count": len(items),
    }


def render_message(raw: Any, message_id: str | None = None, provider: str | None = None) -> dict[str, Any]:
    """메일 본문 raw를 정규화한다."""
    provider = normalize_provider(provider)
    payload = _unwrap_object(raw)
    message = _first_dict(payload, ("message", "mail", "data", "result", "item")) or payload

    sender = _pick_text(message, "sender", "from", "from_name", "fromName", "senderName")
    subject = _pick_text(message, "subject", "title", "mailSubject")
    date = _pick_text(message, "date", "received_at", "receivedAt", "sendDate", "sent_at")
    body_text = _pick_text(message, "body_text", "bodyText", "text", "plain", "contentText")
    body_html_path = _pick_text(message, "body_html_path", "bodyHtmlPath", "html_path")

    if not body_text:
        body_html = _pick_text(message, "body_html", "bodyHtml", "html", "content", "contents")
        body_text = _html_to_text(body_html) if body_html else ""

    normalized_id = (
        message_id
        or _pick_text(message, "id", "message_id", "messageId", "mailId", "uid")
        or _stable_id(sender, subject, date)
    )

    return {
        "provider": provider,
        "id": normalized_id,
        "sender": sender,
        "to": _normalize_address_list(_pick_any(message, "to", "recipients", "toList")),
        "cc": _normalize_address_list(_pick_any(message, "cc", "ccList")),
        "subject": subject,
        "date": date,
        "body_text": body_text,
        "body_html_path": body_html_path or None,
        "attachments": [
            _normalize_attachment(item, include_path=False)
            for item in _find_attachments(message)
        ],
    }


def render_attachments(
    raw: Any,
    message_id: str | None = None,
    require_existing: bool = False,
    provider: str | None = None,
) -> dict[str, Any]:
    """첨부 다운로드 raw를 정규화한다."""
    provider = normalize_provider(provider)
    payload = _unwrap_object(raw)
    attachments = [_normalize_attachment(item, include_path=True) for item in _find_attachments(payload)]
    if require_existing:
        missing = [
            item["path"]
            for item in attachments
            if item.get("path") and not Path(item["path"]).exists()
        ]
        if missing:
            raise ValueError(f"downloaded attachment path not found: {missing[0]}")
    return {
        "provider": provider,
        "message_id": message_id
        or _pick_text(payload, "message_id", "messageId", "mailId", "id")
        or "",
        "attachments": attachments,
    }


def render_draft(raw: Any, draft_id: str | None = None, provider: str | None = None) -> dict[str, Any]:
    """임시보관 저장/조회 raw를 정규화한다."""
    provider = normalize_provider(provider)
    payload = _unwrap_object(raw)
    draft = _first_dict(payload, ("draft", "message", "mail", "data", "result", "item")) or payload
    saved = _truthy(_pick_any(draft, "saved", "success", "ok", "created", "updated")) or _pick_text(
        draft,
        "draftId",
        "draft_id",
        "id",
    ) != ""
    return {
        "provider": provider,
        "draft_id": draft_id
        or _pick_text(draft, "draft_id", "draftId", "id", "messageId", "mailId")
        or "",
        "saved": saved,
        "to": _normalize_address_list(_pick_any(draft, "to", "recipients", "toList")),
        "cc": _normalize_address_list(_pick_any(draft, "cc", "ccList")),
        "bcc": _normalize_address_list(_pick_any(draft, "bcc", "bccList")),
        "subject": _pick_text(draft, "subject", "title", "mailSubject"),
        "body_preview": _preview_body(draft),
        "attachments": [
            _normalize_attachment(item, include_path=False)
            for item in _find_attachments(draft)
        ],
    }


def render_send(raw: Any, provider: str | None = None) -> dict[str, Any]:
    """발송 결과 raw를 정규화한다."""
    provider = normalize_provider(provider)
    payload = _unwrap_object(raw)
    result = _first_dict(payload, ("send", "message", "mail", "data", "result", "item")) or payload
    sent = _truthy(_pick_any(result, "sent", "success", "ok", "completed"))
    error = _pick_text(result, "error", "error_message", "errorMessage", "message")
    return {
        "provider": provider,
        "sent": sent,
        "message_id": _pick_text(result, "message_id", "messageId", "mailId", "id"),
        "timestamp": _pick_text(result, "timestamp", "sent_at", "sentAt", "date"),
        "error": "" if sent else error,
    }


def build_send_gate(
    *,
    to: list[str],
    subject: str,
    body_summary: str,
    provider: str | None = None,
    attachments: list[str] | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict[str, Any]:
    """전송 직전 사용자 확인 payload를 만든다. 실제 발송은 하지 않는다."""
    provider = normalize_provider(provider)
    attachments = attachments or []
    cc = cc or []
    bcc = bcc or []
    missing: list[str] = []
    if not to:
        missing.append("to")
    if not subject.strip():
        missing.append("subject")
    if not body_summary.strip():
        missing.append("body_summary")
    return {
        "provider": provider,
        "action": "send",
        "requires_user_confirmation": True,
        "ready": not missing,
        "missing": missing,
        "confirmation": {
            "to": to,
            "cc": cc,
            "bcc": bcc,
            "subject": _scrub_text(subject),
            "body_summary": _scrub_text(body_summary),
            "attachments": attachments,
        },
    }


def auth_status(env: dict[str, str] | None = None, provider: str | None = None) -> dict[str, Any]:
    """무인 로그인 계약 충족 여부를 비밀값 없이 보고한다."""
    provider = normalize_provider(provider)
    env = env if env is not None else os.environ
    profile_id = env.get("HYVE_WEB_BROWSE_PROFILE_ID", DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID
    if provider == "nate":
        return {
            "provider": provider,
            "authorized_unattended": False,
            "mode": "manual_profile_required",
            "profile_id": profile_id,
            "base_url": env.get("NATE_WEBMAIL_BASE_URL", "https://mail.nate.com").strip()
            or "https://mail.nate.com",
            "auth_flow": "manual_profile",
            "credential_fields_present": {
                "username": False,
                "password": False,
            },
            "blockers": ["nate_test_provider_manual_login_only"],
        }

    enabled = _truthy(env.get("KACEM_WEBMAIL_UNATTENDED"))
    approved = _truthy(env.get("KACEM_WEBMAIL_ADMIN_APPROVED"))
    base_url = env.get("KACEM_WEBMAIL_BASE_URL", "").strip()
    flow = env.get("KACEM_WEBMAIL_AUTH_FLOW", "").strip()
    username_present = bool(env.get("KACEM_WEBMAIL_USERNAME"))
    password_present = bool(env.get("KACEM_WEBMAIL_PASSWORD"))

    blockers: list[str] = []
    if not enabled:
        blockers.append("unattended_disabled")
    if not approved:
        blockers.append("admin_approval_missing")
    if not base_url:
        blockers.append("base_url_missing")
    if flow not in {"simple_form", "automation_endpoint"}:
        blockers.append("unsupported_auth_flow")
    if not username_present:
        blockers.append("username_missing")
    if not password_present:
        blockers.append("password_missing")

    authorized = not blockers
    return {
        "provider": provider,
        "authorized_unattended": authorized,
        "mode": "authorized_unattended" if authorized else "manual_auth_required",
        "profile_id": profile_id,
        "base_url": base_url or None,
        "auth_flow": flow or None,
        "credential_fields_present": {
            "username": username_present,
            "password": password_present,
        },
        "blockers": blockers,
    }


def render_auth_challenge(raw: Any, provider: str | None = None) -> dict[str, Any]:
    """추가 인증 화면을 자동 처리하지 않고 단일 에러로 보고한다.

    2FA/OTP/push/CAPTCHA/가상 키패드/보안키 등은 종류를 분류하거나 전파·대기하지
    않는다(자동 우회 금지·범위 외). 화면 메시지는 비밀값을 가린 뒤 진단용으로만 전달한다.
    """
    provider = normalize_provider(provider)
    safe_message = _redact_challenge_text(_extract_visible_text(raw))
    return {
        "provider": provider,
        "action": "auth_challenge",
        "error_code": "auth_challenge_required",
        "requires_user_action": True,
        "message": safe_message,
        "detail": "2FA/OTP/CAPTCHA/보안키 등 추가 인증은 자동 처리하지 않습니다. 사용자가 직접 처리하세요.",
    }


def _find_list(raw: Any) -> list[dict[str, Any]]:
    payload = _unwrap_object(raw)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    found = _find_first_list(payload, ("items", "messages", "mails", "mailList", "rows", "list", "results"))
    return found or []


def _find_attachments(raw: Any) -> list[dict[str, Any]]:
    payload = _unwrap_object(raw)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    found = _find_first_list(payload, ("attachments", "attachment", "files", "downloads", "downloaded"))
    return found or []


def _extract_visible_text(raw: Any) -> str:
    payload = _unwrap_object(raw)
    if isinstance(payload, str):
        return _html_to_text(payload)
    if isinstance(payload, dict):
        text_parts: list[str] = []
        for key in (
            "message",
            "error",
            "alert",
            "text",
            "snapshot",
            "html",
            "body",
            "title",
            "description",
        ):
            value = payload.get(key)
            if isinstance(value, str):
                text_parts.append(_html_to_text(value))
        if text_parts:
            return _scrub_text(" ".join(text_parts))
        return _scrub_text(" ".join(_walk_text_values(payload)))
    if isinstance(payload, list):
        return _scrub_text(" ".join(_walk_text_values(payload)))
    return _scrub_text(str(payload))


def _walk_text_values(value: Any, depth: int = 0) -> list[str]:
    if depth > 4:
        return []
    if isinstance(value, str):
        return [_html_to_text(value)]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_walk_text_values(item, depth + 1))
        return result
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            if key.lower() in {"password", "token", "cookie", "authorization"}:
                continue
            result.extend(_walk_text_values(item, depth + 1))
        return result
    return []


def _redact_challenge_text(text: str, limit: int = 500) -> str:
    cleaned = _scrub_text(text)
    cleaned = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email>", cleaned)
    cleaned = re.sub(r"\b(?:\+?\d[\d -]{7,}\d)\b", "<phone>", cleaned)
    cleaned = re.sub(r"\b\d{4,}\b", "<number>", cleaned)
    cleaned = re.sub(r"\b[A-Za-z0-9_-]{20,}\b", "<token>", cleaned)
    return cleaned[:limit]


def _unwrap_object(raw: Any) -> Any:
    """web_browse fetch/extract wrapper에서 실제 payload를 꺼낸다."""
    current = raw
    for _ in range(4):
        if not isinstance(current, dict):
            return current
        for key in ("json", "data", "result", "payload", "body"):
            value = current.get(key)
            if isinstance(value, (dict, list)):
                current = value
                break
        else:
            return current
    return current


def _find_first_list(value: Any, keys: tuple[str, ...], depth: int = 0) -> list[dict[str, Any]] | None:
    if depth > 5:
        return None
    if isinstance(value, dict):
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        for candidate in value.values():
            found = _find_first_list(candidate, keys, depth + 1)
            if found is not None:
                return found
    return None


def _first_dict(value: Any, keys: tuple[str, ...]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, dict):
            return candidate
    return None


def _normalize_list_item(row: dict[str, Any]) -> dict[str, Any]:
    sender = _pick_text(row, "sender", "from", "from_name", "fromName", "senderName")
    subject = _pick_text(row, "subject", "title", "mailSubject")
    date = _pick_text(row, "date", "received_at", "receivedAt", "sendDate", "sent_at")
    item_id = _pick_text(row, "id", "message_id", "messageId", "mailId", "uid") or _stable_id(
        sender,
        subject,
        date,
    )
    return {
        "id": item_id,
        "sender": sender,
        "subject": subject,
        "date": date,
        "unread": _normalize_unread(row),
        "has_attachment": _normalize_has_attachment(row),
    }


def _normalize_attachment(item: dict[str, Any], include_path: bool) -> dict[str, Any]:
    name = _pick_text(item, "name", "filename", "file_name", "fileName", "originalName") or "attachment"
    size_value = _pick_any(item, "bytes", "size_bytes", "sizeBytes", "fileSize")
    path = _pick_text(item, "path", "download_path", "downloadPath", "saved_path", "savedPath")
    result: dict[str, Any] = {
        "name": name,
        "size": _pick_text(item, "size", "displaySize", "sizeText") or (str(size_value) if size_value else ""),
        "downloadable": bool(path) or _truthy(_pick_any(item, "downloadable", "canDownload")) or bool(_pick_text(item, "url", "download_url", "downloadUrl")),
    }
    if include_path:
        result["path"] = str(Path(path).expanduser().resolve()) if path else ""
        result["bytes"] = _int_or_zero(size_value)
        result["mime_guess"] = _pick_text(item, "mime", "mime_guess", "mimeGuess", "contentType") or None
    return result


def _normalize_unread(row: dict[str, Any]) -> bool:
    unread = _pick_any(row, "unread", "isUnread", "new", "is_new")
    if unread is not None:
        return _truthy(unread)
    read = _pick_any(row, "read", "isRead")
    if read is not None:
        return not _truthy(read)
    status = _pick_text(row, "status", "readStatus", "class", "state")
    if "unread" in status.lower() or "안읽" in status or "읽지" in status:
        return True
    if "read" in status.lower() or "읽음" in status:
        return False
    return False


def _normalize_has_attachment(row: dict[str, Any]) -> bool:
    value = _pick_any(row, "has_attachment", "hasAttachment", "attach", "attachment", "isAttach")
    if value is not None:
        if isinstance(value, list):
            return len(value) > 0
        return _truthy(value)
    count = _int_or_zero(_pick_any(row, "attachment_count", "attachmentCount", "attachCount"))
    return count > 0


def _normalize_address_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_scrub_text(str(item)) for item in value if _scrub_text(str(item))]
    text = _scrub_text(str(value))
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,;]", text) if part.strip()]


def _preview_body(mapping: dict[str, Any], limit: int = 240) -> str:
    body_text = _pick_text(mapping, "body_text", "bodyText", "text", "plain", "contentText")
    if not body_text:
        body_html = _pick_text(mapping, "body_html", "bodyHtml", "html", "content", "contents")
        body_text = _html_to_text(body_html) if body_html else ""
    return body_text[:limit]


def _pick_any(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _pick_text(mapping: dict[str, Any], *keys: str) -> str:
    value = _pick_any(mapping, *keys)
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return ""
    return _scrub_text(str(value))


def _scrub_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _html_to_text(value: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return _scrub_text(text)


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"derived-{digest[:16]}"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "unread", "new", "첨부", "있음"}


def _int_or_zero(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    text = str(value).replace(",", "")
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else 0


def _write_result(data: dict[str, Any], output: Path | None, fmt: str) -> None:
    if fmt == "json":
        text = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        text = _to_markdown(data)
    if output:
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def _to_markdown(data: dict[str, Any]) -> str:
    if "items" in data:
        lines = [f"# {data.get('provider', DEFAULT_PROVIDER)} {data.get('folder', '')} 목록", ""]
        for item in data["items"]:
            marker = "안읽음" if item.get("unread") else "읽음"
            attach = " / 첨부" if item.get("has_attachment") else ""
            lines.append(f"- [{marker}{attach}] {item.get('date', '')} {item.get('sender', '')} — {item.get('subject', '')}")
        return "\n".join(lines)
    if "body_text" in data:
        lines = [
            f"# {data.get('subject', '')}",
            "",
            f"- 발신자: {data.get('sender', '')}",
            f"- 날짜: {data.get('date', '')}",
            f"- 첨부: {len(data.get('attachments', []))}개",
            "",
            data.get("body_text", ""),
        ]
        return "\n".join(lines)
    if "attachments" in data:
        lines = [f"# 첨부 다운로드 ({len(data['attachments'])}개)", ""]
        for item in data["attachments"]:
            lines.append(f"- {item.get('name', '')}: {item.get('path', '')}")
        return "\n".join(lines)
    if data.get("action") == "send":
        confirmation = data.get("confirmation", {})
        lines = ["# 발송 확인", ""]
        lines.append(f"- 수신자: {', '.join(confirmation.get('to', []))}")
        lines.append(f"- 제목: {confirmation.get('subject', '')}")
        lines.append(f"- 본문 요지: {confirmation.get('body_summary', '')}")
        lines.append(f"- 첨부: {', '.join(confirmation.get('attachments', [])) or '없음'}")
        return "\n".join(lines)
    if data.get("action") == "auth_challenge":
        return "\n".join(
            [
                "# 추가 인증 필요 (자동 처리 불가)",
                "",
                f"- 메시지: {data.get('message', '')}",
                f"- 안내: {data.get('detail', '')}",
            ]
        )
    if "draft_id" in data:
        return f"# 임시보관\n\n- 저장됨: {data.get('saved')}\n- 제목: {data.get('subject', '')}"
    if "sent" in data:
        return f"# 발송 결과\n\n- 성공: {data.get('sent')}\n- 메시지 ID: {data.get('message_id', '')}"
    return json.dumps(data, ensure_ascii=False, indent=2)


def _delete_input(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="웹메일 raw 정규화")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser("render", help="raw JSON 정규화")
    render.add_argument("target", choices=["list", "message", "attachments", "draft", "send"])
    render.add_argument("--provider", choices=SUPPORTED_PROVIDERS, default=DEFAULT_PROVIDER)
    render.add_argument("--input", required=True, type=Path)
    render.add_argument("--folder", default="inbox")
    render.add_argument("--message-id")
    render.add_argument("--draft-id")
    render.add_argument("--format", choices=["json", "markdown"], default="json")
    render.add_argument("--output", type=Path)
    render.add_argument("--delete-input", action="store_true")
    render.add_argument("--require-existing", action="store_true")

    auth = subparsers.add_parser("auth-status", help="무인 로그인 계약 충족 여부 확인")
    auth.add_argument("--provider", choices=SUPPORTED_PROVIDERS, default=DEFAULT_PROVIDER)
    auth.add_argument("--format", choices=["json", "markdown"], default="json")
    auth.add_argument("--output", type=Path)

    auth_challenge = subparsers.add_parser("auth-challenge", help="추가 인증 화면 메시지 정규화")
    auth_challenge.add_argument("--provider", choices=SUPPORTED_PROVIDERS, default=DEFAULT_PROVIDER)
    auth_challenge.add_argument("--input", required=True, type=Path)
    auth_challenge.add_argument("--format", choices=["json", "markdown"], default="json")
    auth_challenge.add_argument("--output", type=Path)
    auth_challenge.add_argument("--delete-input", action="store_true")

    send_gate = subparsers.add_parser("send-gate", help="전송 직전 사용자 확인 payload 생성")
    send_gate.add_argument("--provider", choices=SUPPORTED_PROVIDERS, default=DEFAULT_PROVIDER)
    send_gate.add_argument("--to", action="append", default=[])
    send_gate.add_argument("--cc", action="append", default=[])
    send_gate.add_argument("--bcc", action="append", default=[])
    send_gate.add_argument("--subject", default="")
    send_gate.add_argument("--body-summary", default="")
    send_gate.add_argument("--attachment", action="append", default=[])
    send_gate.add_argument("--format", choices=["json", "markdown"], default="json")
    send_gate.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "auth-status":
            _write_result(auth_status(provider=args.provider), args.output, args.format)
            return 0
        if args.command == "auth-challenge":
            result = render_auth_challenge(load_json(args.input), provider=args.provider)
            _write_result(result, args.output, args.format)
            if args.delete_input:
                _delete_input(args.input)
            return 0
        if args.command == "send-gate":
            result = build_send_gate(
                to=args.to,
                cc=args.cc,
                bcc=args.bcc,
                subject=args.subject,
                body_summary=args.body_summary,
                provider=args.provider,
                attachments=args.attachment,
            )
            _write_result(result, args.output, args.format)
            return 0

        raw = load_json(args.input)
        if args.target == "list":
            result = render_list(raw, folder=args.folder, provider=args.provider)
        elif args.target == "message":
            result = render_message(raw, message_id=args.message_id, provider=args.provider)
        elif args.target == "attachments":
            result = render_attachments(
                raw,
                message_id=args.message_id,
                require_existing=args.require_existing,
                provider=args.provider,
            )
        elif args.target == "draft":
            result = render_draft(raw, draft_id=args.draft_id, provider=args.provider)
        else:
            result = render_send(raw, provider=args.provider)
        _write_result(result, args.output, args.format)
        if args.delete_input:
            _delete_input(args.input)
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
