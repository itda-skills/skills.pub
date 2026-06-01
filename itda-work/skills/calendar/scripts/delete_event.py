#!/usr/bin/env python3
"""itda-calendar: delete_event.py — delete a VEVENT with a confirmation gate.

`--yes` 없이 호출하면 삭제 대상 요약을 반환하고 삭제하지 않는다(되돌리기 어려운
작업 보호). `--etag`를 주면 If-Match 의미로 충돌을 감지한다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from caldav_client import find_calendar, find_event_by_uid  # noqa: E402
from cli_common import (classify_error, connect_or_exit, emit, emit_error,  # noqa: E402
                        resolve_provider_or_exit)
from event_model import normalize_event  # noqa: E402
from sanitize import sanitize_for_llm  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Delete a calendar event by UID.")
    ap.add_argument("--provider", required=True)
    ap.add_argument("--account")
    ap.add_argument("--calendar", required=True)
    ap.add_argument("--uid", required=True)
    ap.add_argument("--etag", help="If-Match etag for optimistic concurrency")
    ap.add_argument("--yes", action="store_true", help="confirm deletion (required)")
    args = ap.parse_args()

    prov = resolve_provider_or_exit(args.provider, args.account)
    _client, principal = connect_or_exit(prov)
    cal = find_calendar(principal, args.calendar)
    if cal is None:
        emit_error("calendar_not_found", args.calendar, code=1)
    ev = find_event_by_uid(cal, args.uid)
    if ev is None:
        emit_error("event_not_found", args.uid, code=1)

    target = normalize_event(
        ev.icalendar_component,
        sanitize_fn=sanitize_for_llm,
        url=str(ev.url),
        etag=getattr(ev, "etag", None),
    )

    if not args.yes:
        emit({
            "status": "confirm_required",
            "action": "delete",
            "target": target,
            "hint": "re-run with --yes to delete this event",
        }, code=0)

    current_etag = getattr(ev, "etag", None)
    if args.etag and current_etag and args.etag != current_etag:
        emit_error("etag_conflict",
                   f"event changed on server (current etag={current_etag}); re-fetch",
                   code=2)

    try:
        ev.delete()
    except Exception as e:  # noqa: BLE001
        emit_error(classify_error(e), e, code=1)

    emit({"status": "deleted", "uid": args.uid, "calendar": args.calendar})


if __name__ == "__main__":
    main()
