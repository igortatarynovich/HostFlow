"""
Working-hours helpers for User.extra.working_hours_v1 (same shape as communications._normalize_working_hours).

Used by:
  - lead auto-distribution when `working_hours` is in criteria_order
    (`is_within_working_hours`, `schedule_applies`);
  - G-4: reminder/planner scheduling — `next_working_window_after`
    shifts a target time forward to the next opening of the user's
    weekly schedule (no shift if the schedule is empty/disabled, so
    callers don't need to special-case "no working hours configured").
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
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


def _windows_by_weekday(extra: Any) -> dict[int, list[tuple[int, int]]]:
    """Index the weekly schedule by `weekday → sorted [(from_min, to_min)]`,
    discarding malformed/disabled entries. Empty dict if schedule absent.
    Internal helper for `next_working_window_after`."""
    out: dict[int, list[tuple[int, int]]] = {}
    wh = _extra_dict(extra).get("working_hours_v1")
    if not isinstance(wh, dict):
        return out
    days = wh.get("days")
    if not isinstance(days, list):
        return out
    for d in days:
        if not isinstance(d, dict):
            continue
        try:
            wd = int(d.get("weekday"))
        except Exception:
            continue
        if wd < 0 or wd > 6:
            continue
        if not bool(d.get("enabled", True)):
            continue
        wins_raw = d.get("windows") if isinstance(d.get("windows"), list) else []
        wins: list[tuple[int, int]] = []
        for w in wins_raw:
            wr = w if isinstance(w, dict) else {}
            fm = _parse_clock_minutes(str(wr.get("from") or ""))
            tm = _parse_clock_minutes(str(wr.get("to") or ""))
            if fm is None or tm is None or tm <= fm:
                continue
            wins.append((fm, tm))
        if wins:
            # Multiple PUTs to the same weekday merge — last write wins on
            # the bucket but we sort defensively. The frontend currently
            # writes one entry per weekday, but the API does not enforce
            # uniqueness so we accept multi-entry inputs.
            out.setdefault(wd, [])
            out[wd].extend(wins)
            out[wd].sort()
    return out


def _resolve_tz(extra: Any) -> ZoneInfo | timezone:
    """Resolve the user's working-hours tz, falling back to UTC. Centralised
    so `is_within_working_hours` and `next_working_window_after` use the
    exact same fallback policy (otherwise a malformed tz string could
    produce inconsistent answers across the two helpers)."""
    wh = _extra_dict(extra).get("working_hours_v1")
    if not isinstance(wh, dict):
        return timezone.utc
    tz_name = wh.get("tz")
    tz_str = str(tz_name).strip() if isinstance(tz_name, str) else ""
    if not tz_str:
        return timezone.utc
    try:
        return ZoneInfo(tz_str)
    except Exception:
        return timezone.utc


def next_working_window_after(extra: Any, after_utc: datetime) -> datetime:
    """
    Return the earliest UTC datetime ≥ `after_utc` that falls inside the
    user's working-hours schedule.

    Contract:
      * If `schedule_applies(extra)` is False (no schedule, no enabled
        days, no valid windows), return `after_utc` unchanged. Callers
        treat "no schedule" as "anytime is fine".
      * If `after_utc` is already inside an enabled window, return it
        unchanged.
      * Otherwise, return the start of the next enabled window — same
        day if a later window opens today, otherwise the first window
        of the next enabled day. Walks up to 14 days forward; if no
        match (pathological schedule, e.g. all weekdays disabled but
        `schedule_applies` somehow True), returns `after_utc` unchanged
        as a safe fallback.

    Semantic notes:
      * Comparison uses the user's local tz. The returned datetime is
        normalised to UTC (tzinfo set), matching what the rest of the
        codebase persists.
      * Seconds and microseconds on the original `after_utc` are NOT
        preserved when a shift happens — the next window opens on a
        whole-minute boundary. When no shift happens, the original
        precision is returned untouched.
      * G-4 callers: this helper is the *contract* — there's no
        per-caller schedule logic. The reminder/planner shift policy
        layers on top (decide whether to shift, then call this).

    Args:
        extra: User.extra dict (or anything that quacks); we look up
            `working_hours_v1` defensively.
        after_utc: Reference instant. If naive, treated as UTC (matches
            `is_within_working_hours`'s policy).
    """
    if not schedule_applies(extra):
        return after_utc

    by_weekday = _windows_by_weekday(extra)
    if not by_weekday:
        # `schedule_applies` returned True but every window failed
        # validation. Treat as "no schedule" — safe fallback.
        return after_utc

    tz = _resolve_tz(extra)
    ref = after_utc if after_utc.tzinfo else after_utc.replace(tzinfo=timezone.utc)
    local = ref.astimezone(tz)
    current_minutes = local.hour * 60 + local.minute

    # Walk forward up to 14 days. Two weeks covers any biweekly
    # rotation pattern; longer-than-14-day gaps mean the user is
    # effectively offline (vacation territory — outside this helper's
    # responsibility, see G-4 stage 4 time-off cleanup).
    for offset in range(15):
        candidate_local = local + timedelta(days=offset)
        weekday = candidate_local.weekday()
        wins = by_weekday.get(weekday)
        if not wins:
            continue
        if offset == 0:
            # Same-day: respect current_minutes. If we're already inside
            # a window, return ref unchanged (preserves seconds).
            for fm, tm in wins:
                if fm <= current_minutes < tm:
                    return ref
                if fm > current_minutes:
                    target_local = candidate_local.replace(
                        hour=fm // 60,
                        minute=fm % 60,
                        second=0,
                        microsecond=0,
                    )
                    return target_local.astimezone(timezone.utc)
            # Past today's last window — keep walking to tomorrow.
            continue
        # Future day: jump to the first window of that day.
        fm, _tm = wins[0]
        target_local = candidate_local.replace(
            hour=fm // 60,
            minute=fm % 60,
            second=0,
            microsecond=0,
        )
        return target_local.astimezone(timezone.utc)

    # Pathological: schedule_applies True but no day in 2 weeks matched.
    # Could happen if every enabled day's only window is malformed AND
    # somehow slipped past `_windows_by_weekday`'s validation. Caller
    # gets the original time back — safer than raising.
    return ref


__all__ = [
    "schedule_applies",
    "is_within_working_hours",
    "next_working_window_after",
]
