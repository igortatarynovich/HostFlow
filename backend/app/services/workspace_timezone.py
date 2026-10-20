"""Workspace business-calendar zone.

A new tenant must carry an explicit IANA zone. This module does not choose
Europe/Warsaw, the viewer's zone, or the communications zone.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class WorkspaceTimezoneError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def require_iana_timezone(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise WorkspaceTimezoneError("workspace_timezone_required")
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise WorkspaceTimezoneError("workspace_timezone_invalid") from exc
    return name


__all__ = ["WorkspaceTimezoneError", "require_iana_timezone"]
