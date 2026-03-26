"""
Working-hours helpers for User.extra.working_hours_v1 (same shape as communications._normalize_working_hours).

Used by lead auto-distribution when `working_hours` is in criteria_order.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

_CLOCK_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


def _parse_clock_minutes(value: str) -> int | None:
    s = str(value or "").strip()
    if not _CLOCK_RE.match(s):
        return None
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _extra_dict(extra: Any) -> dict[str, Any]:
    return dict(extra) if isinstance(extra, dict) else {}


def schedule_applies(extra: Any) -> bool:
    """True if user has at least one enabled day with a non-empty window (hours affect routing)."""
    wh = _extra_dict(extra).get("working_hours_v1")
    if not isinstance(wh, dict):
        return False
    days = wh.get("days")
    if not isinstance(days, list):
        return False
    for d in days:
        if not isinstance(d, dict):
            continue
        if not bool(d.get("enabled", True)):
            continue
        wins = d.get("windows")
        if isinstance(wins, list) and len(wins) > 0:
            return True
    return False


def is_within_working_hours(extra: Any, now_utc: datetime | None = None) -> bool:
    """
    Whether `now_utc` falls inside an enabled window (in user's tz, default UTC).

    If schedule_applies is False, returns True (no calendar → do not block distribution).
    """
    if not schedule_applies(extra):
        return True
    wh = _extra_dict(extra).get("working_hours_v1")
    assert isinstance(wh, dict)
    tz_name = wh.get("tz")
    tz_str = str(tz_name).strip() if isinstance(tz_name, str) else ""
    ref = now_utc if now_utc is not None else datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    if tz_str:
        try:
            local = ref.astimezone(ZoneInfo(tz_str))
        except Exception:
            local = ref.astimezone(timezone.utc)
    else:
        local = ref.astimezone(timezone.utc)

    weekday = int(local.weekday())  # 0=Mon .. 6=Sun
    minutes = local.hour * 60 + local.minute

    days = wh.get("days")
    if not isinstance(days, list):
        return False
    for d in days:
        if not isinstance(d, dict):
            continue
        try:
            wd = int(d.get("weekday"))
        except Exception:
            continue
        if wd != weekday:
            continue
        if not bool(d.get("enabled", True)):
            return False
        wins = d.get("windows") if isinstance(d.get("windows"), list) else []
        for w in wins:
            wr = w if isinstance(w, dict) else {}
            fm = _parse_clock_minutes(str(wr.get("from") or ""))
            tm = _parse_clock_minutes(str(wr.get("to") or ""))
            if fm is None or tm is None or tm <= fm:
                continue
            if fm <= minutes < tm:
                return True
        return False
    return False
