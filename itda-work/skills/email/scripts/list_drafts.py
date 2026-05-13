#!/usr/bin/env python3
"""itda-email: list_drafts.py — IMAP Drafts 폴더 메시지 목록 조회.

SPEC-EMAIL-DRAFTS-001 REQ-DRAFTS-009:
  - UID SEARCH + FETCH로 최근 N개 메시지 메타데이터 반환
  - --limit (기본 20), --since YYYY-MM-DD 지원
  - INTERNALDATE 내림차순 정렬
  - 빈 폴더는 [] 반환, exit code 0
"""
from __future__ import annotations

import argparse
import email
import email.header
import imaplib
import json
import re
import sys
from datetime import datetime
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


def _parse_fetch_response(fetch_data: list, uid: int) -> dict | None:
    """IMAP FETCH 응답에서 헤더 필드를 파싱한다."""
    raw_bytes: bytes | None = None
    for item in fetch_data:
        if isinstance(item, tuple) and len(item) >= 2:
            raw_bytes = item[1]
            break

    if not raw_bytes:
        return None

    msg = email.message_from_bytes(raw_bytes)

    subject = _decode_header(msg.get("Subject", ""))
    from_ = _decode_header(msg.get("From", ""))
    to_raw = msg.get("To", "")
    to_list = [a.strip() for a in to_raw.split(",") if a.strip()] if to_raw else []
    date_str = msg.get("Date", "")

    # RFC822.SIZE는 fetch spec에서 별도 파싱 필요
    size = 0

    return {
        "uid": uid,
        "subject": subject,
        "from": from_,
        "to": to_list,
        "date": date_str,
        "size": size,
    }


def list_drafts(
    provider: str,
    limit: int = 20,
    since: str | None = None,
    account: str | None = None,
) -> list[dict]:
    """Drafts 폴더에서 최근 메시지 목록을 반환한다.

    반환값: uid, subject, from, to, date, size 필드를 포함하는 딕셔너리 리스트 (최신순)
    """
    env = merged_env()
    provider_cfg = get_provider(provider, env, account=account)

    if not provider_cfg or not provider_cfg.get("email") or not provider_cfg.get("password"):
        print(
            json.dumps({
                "error": "credentials_missing",
                "detail": f"provider '{provider}'에 대한 인증 정보가 없습니다.",
            }),
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

        # UID SEARCH
        if since:
            # --since YYYY-MM-DD → IMAP date format: 13-May-2026
            try:
                dt = datetime.strptime(since, "%Y-%m-%d")
                since_imap = dt.strftime("%d-%b-%Y")
                _status, search_data = imap.uid("SEARCH", None, f"SINCE {since_imap}")
            except ValueError:
                _status, search_data = imap.uid("SEARCH", None, "ALL")
        else:
            _status, search_data = imap.uid("SEARCH", None, "ALL")

        if not search_data or not search_data[0]:
            return []

        uid_list_bytes = search_data[0].split() if search_data[0] else []
        if not uid_list_bytes:
            return []

        # 최신순(내림차순) — 마지막 N개
        uid_list = [int(u) for u in uid_list_bytes]
        uid_list.reverse()  # 최신순
        uid_list = uid_list[:limit]

        results: list[dict] = []
        for uid in uid_list:
            uid_str = str(uid).encode()
            _fs, fetch_data = imap.uid(
                "FETCH",
                uid_str,
                "(RFC822.SIZE BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE)])",
            )
            item = _parse_fetch_response(fetch_data, uid)
            if item:
                # RFC822.SIZE 추출 시도
                for raw in fetch_data:
                    if isinstance(raw, bytes):
                        m = re.search(rb"RFC822\.SIZE\s+(\d+)", raw)
                        if m:
                            item["size"] = int(m.group(1))
                results.append(item)

        return results

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
    parser = argparse.ArgumentParser(description="IMAP Drafts 폴더 메시지 목록을 조회합니다.")
    parser.add_argument("--provider", required=True, choices=["naver", "google", "gmail", "daum", "custom"])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--since", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--account", default=None)
    args = parser.parse_args()

    result = list_drafts(
        provider=args.provider,
        limit=args.limit,
        since=args.since,
        account=args.account,
    )
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
