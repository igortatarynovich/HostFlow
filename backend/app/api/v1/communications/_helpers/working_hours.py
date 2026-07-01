"""Working-hours / time-off date utilities for the communications package.

Extracted from ``communications/__init__.py`` (Phase 1 god-module split).

Depends only on :mod:`backend.app.api.v1.communications._helpers.utils` and
``HTTPException`` from FastAPI.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException

from .utils import _as_dict

__all__ = [
    "_CLOCK_RE",
    "_parse_clock_minutes",
    "_normalize_working_hours",
    "_validate_iso_date_range",
    "_partial_day_blocks_now",
]


_CLOCK_RE = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d$")


def _parse_clock_minutes(value: str) -> int:
    s = str(value or "").strip()
    if not _CLOCK_RE.match(s):
        raise ValueError("Invalid time format (expected HH:MM)")
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _normalize_working_hours(payload: Any) -> Dict[str, Any]:
    """
    Canonical weekly working hours contract (v1).

    Stored in User.extra under key `working_hours_v1`:
      {
        "tz": "Europe/Warsaw" | null,
        "days": [
          {"weekday": 0..6, "enabled": bool, "windows": [{"from":"09:00","to":"17:00"}]}
        ]
      }
    weekday: 0=Mon .. 6=Sun (ISO-like, aligned with frontend usage).
    """
    root = _as_dict(payload)
    tz = root.get("tz")
    tz_norm = str(tz).strip() if isinstance(tz, str) else None

    raw_days = root.get("days")
    days_in = raw_days if isinstance(raw_days, list) else []
    seen: set[int] = set()
    days_out: list[dict[str, Any]] = []
    for item in days_in:
        row = _as_dict(item)
        try:
            weekday = int(row.get("weekday"))
        except Exception:
            continue
        if weekday < 0 or weekday > 6:
            continue
        if weekday in seen:
            continue
        seen.add(weekday)
        enabled = bool(row.get("enabled", True))
        windows_in = row.get("windows") if isinstance(row.get("windows"), list) else []
        windows_out: list[dict[str, str]] = []
        for w in windows_in:
            wr = _as_dict(w)
            f = str(wr.get("from") or "").strip()
            t = str(wr.get("to") or "").strip()
            if not f or not t:
                continue
            fm = _parse_clock_minutes(f)
            tm = _parse_clock_minutes(t)
            if tm <= fm:
                continue
            windows_out.append({"from": f, "to": t})
        days_out.append({"weekday": weekday, "enabled": enabled, "windows": windows_out})
    days_out.sort(key=lambda x: int(x["weekday"]))
    return {"tz": tz_norm, "days": days_out}


def _validate_iso_date_range(start_date: str, end_date: str) -> None:
    try:
        start = str(start_date).strip()
        end = str(end_date).strip()
        if not start or not end:
            raise ValueError("empty")
        if end < start:
            raise ValueError("end_before_start")
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid date range")


def _partial_day_blocks_now(
    partial_day: str | None,
    now_local: datetime,
    payload: Dict[str, Any] | None = None,
) -> bool:
    token = str(partial_day or "").strip().lower()
    payload = payload if isinstance(payload, dict) else {}
    time_window = _as_dict(payload.get("time_window"))
    try:
        from_raw = str(time_window.get("from") or "").strip()
        to_raw = str(time_window.get("to") or "").strip()
        if from_raw and to_raw and ":" in from_raw and ":" in to_raw:
            fh, fm = [int(x) for x in from_raw.split(":", 1)]
            th, tm = [int(x) for x in to_raw.split(":", 1)]
            cur = now_local.hour * 60 + now_local.minute
            start_min = fh * 60 + fm
            end_min = th * 60 + tm
            if 0 <= start_min <= 1439 and 0 <= end_min <= 1439:
                return start_min <= cur <= end_min
    except Exception:
        pass
    if not token:
        return True
    hour = int(now_local.hour)
    if token in {"am", "first_half", "morning"}:
        return hour < 13
    if token in {"pm", "second_half", "afternoon"}:
        return hour >= 13
    return True
