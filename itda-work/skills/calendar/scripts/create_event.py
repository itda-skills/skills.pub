#!/usr/bin/env python3
"""itda-calendar: create_event.py — create a VEVENT (PUT)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from caldav_client import find_calendar, save_event  # noqa: E402
from cli_common import (classify_error, connect_or_exit, emit, emit_error,  # noqa: E402
                        resolve_provider_or_exit)
from event_model import build_vevent  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Create a calendar event.")
    ap.add_argument("--provider", required=True)
    ap.add_argument("--account")
    ap.add_argument("--calendar", required=True, help="target calendar name or id")
    ap.add_argument("--summary", required=True)
    ap.add_argument("--start", required=True, help="ISO date (all-day) or datetime")
    ap.add_argument("--end", help="ISO date/datetime (default: +1h, or +1d for all-day)")
    ap.add_argument("--all-day", action="store_true")
    ap.add_argument("--tz", default="Asia/Seoul")
    ap.add_argument("--location")
    ap.add_argument("--description")
    ap.add_argument("--rrule", help="e.g. 'FREQ=WEEKLY;BYDAY=MO'")
    ap.add_argument("--alarm-minutes", type=int, help="DISPLAY alarm N minutes before")
    args = ap.parse_args()

    prov = resolve_provider_or_exit(args.provider, args.account)
    _client, principal = connect_or_exit(prov)
    cal = find_calendar(principal, args.calendar)
    if cal is None:
        emit_error("calendar_not_found", args.calendar, code=1)

    ical, uid = build_vevent(
        args.summary, args.start, args.end,
        all_day=args.all_day, tz=args.tz,
        location=args.location, description=args.description,
        rrule=args.rrule, alarm_minutes=args.alarm_minutes,
    )
    try:
        ev = save_event(cal, ical)
    except Exception as e:  # noqa: BLE001
        emit_error(classify_error(e), e, code=1)

    emit({
        "status": "ok",
        "uid": uid,
        "url": str(ev.url),
        "etag": getattr(ev, "etag", None),
        "calendar": args.calendar,
        "summary": args.summary,
        "start": args.start,
    })


if __name__ == "__main__":
    main()
