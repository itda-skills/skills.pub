#!/usr/bin/env python3
"""itda-calendar: event_model — icalendar VEVENT <-> normalized dict.

Timezone-aware (default Asia/Seoul). Handles all-day (VALUE=DATE) vs timed
events, RRULE, and DISPLAY alarms. Uses the `icalendar` library for RFC 5545
serialization (line-folding, escaping, VTIMEZONE).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from icalendar import Alarm, Calendar, Event
from icalendar.prop import vRecur

DEFAULT_TZ = "Asia/Seoul"
PRODID = "-//itda-skills//calendar//KO"


# ---------------------------------------------------------------------------
# parsing helpers
# ---------------------------------------------------------------------------


def parse_dt(value: str, default_tz: str = DEFAULT_TZ):
    """Parse an ISO-ish string into date (all-day) or tz-aware datetime.

    'YYYY-MM-DD'              -> date  (all-day)
    'YYYY-MM-DDTHH:MM[:SS]'   -> datetime (naive -> default_tz applied)
    '...+09:00' / '...Z'      -> datetime (offset preserved)
    """
    value = value.strip()
    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        return date.fromisoformat(value)
    iso = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(default_tz))
    return dt


def _is_pure_date(value) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


def parse_rrule(spec: str) -> vRecur:
    """'FREQ=WEEKLY;BYDAY=MO,WE;COUNT=10' (or with 'RRULE:' prefix) -> vRecur."""
    spec = spec.strip()
    if spec.upper().startswith("RRULE:"):
        spec = spec[6:]
    return vRecur.from_ical(spec)


# ---------------------------------------------------------------------------
# build (dict/args -> VEVENT)
# ---------------------------------------------------------------------------


def build_vevent(summary: str, start: str, end: str | None = None, *,
                 all_day: bool = False, tz: str = DEFAULT_TZ,
                 location: str | None = None, description: str | None = None,
                 rrule: str | None = None, alarm_minutes: int | None = None,
                 uid: str | None = None, sequence: int = 0) -> tuple[bytes, str]:
    """Build a VCALENDAR wrapping one VEVENT. Returns (ical_bytes, uid)."""
    ev = Event()
    uid = uid or f"{uuid.uuid4()}@itda-calendar"
    ev.add("uid", uid)
    ev.add("summary", summary)

    dtstart = parse_dt(start, tz)
    if all_day and not _is_pure_date(dtstart):
        dtstart = dtstart.date()

    if _is_pure_date(dtstart):
        ev.add("dtstart", dtstart)
        if end:
            dtend = parse_dt(end, tz)
            dtend = dtend if _is_pure_date(dtend) else dtend.date()
        else:
            dtend = dtstart + timedelta(days=1)
        ev.add("dtend", dtend)
    else:
        ev.add("dtstart", dtstart)
        if end:
            dtend = parse_dt(end, tz)
            if _is_pure_date(dtend):
                dtend = datetime.combine(dtend, dtstart.timetz())
        else:
            dtend = dtstart + timedelta(hours=1)
        ev.add("dtend", dtend)

    if location:
        ev.add("location", location)
    if description:
        ev.add("description", description)
    if rrule:
        ev.add("rrule", parse_rrule(rrule))
    ev.add("dtstamp", datetime.now(timezone.utc))
    ev.add("sequence", sequence)

    if alarm_minutes is not None:
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", summary)
        alarm.add("trigger", timedelta(minutes=-abs(alarm_minutes)))
        ev.add_component(alarm)

    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add_component(ev)
    return cal.to_ical(), uid


# ---------------------------------------------------------------------------
# normalize (VEVENT component -> dict)
# ---------------------------------------------------------------------------


def _dt_to_iso(value) -> tuple[str | None, bool]:
    """Return (iso_string, is_all_day)."""
    if value is None:
        return None, False
    dt = value.dt if hasattr(value, "dt") else value
    if _is_pure_date(dt):
        return dt.isoformat(), True
    if isinstance(dt, datetime):
        return dt.isoformat(), False
    return str(dt), False


def normalize_event(component, *, sanitize_fn=None,
                    url: str | None = None, etag: str | None = None) -> dict:
    """icalendar VEVENT component -> normalized dict (LLM-safe if sanitize_fn given)."""
    def text(key):
        v = component.get(key)
        return str(v) if v is not None else None

    summary = text("SUMMARY") or ""
    description = text("DESCRIPTION")
    location = text("LOCATION")
    if sanitize_fn is not None:
        summary = sanitize_fn(summary)
        description = sanitize_fn(description) if description else None
        location = sanitize_fn(location) if location else None

    start, all_day = _dt_to_iso(component.get("DTSTART"))
    end, _ = _dt_to_iso(component.get("DTEND"))

    rrule_prop = component.get("RRULE")
    rrule = rrule_prop.to_ical().decode() if rrule_prop is not None else None

    alarms = []
    for sub in getattr(component, "subcomponents", []):
        if sub.name == "VALARM":
            trig = sub.get("TRIGGER")
            if trig is not None:
                alarms.append(str(trig.dt) if hasattr(trig, "dt") else str(trig))

    out = {
        "uid": text("UID"),
        "summary": summary,
        "start": start,
        "end": end,
        "all_day": all_day,
        "location": location,
        "description": description,
        "rrule": rrule,
        "status": text("STATUS"),
        "alarms": alarms,
    }
    if url is not None:
        out["url"] = url
    if etag is not None:
        out["etag"] = etag
    return out
