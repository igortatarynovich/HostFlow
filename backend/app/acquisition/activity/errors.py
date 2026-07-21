"""Errors for Acquisition Activity Timeline append / query."""

from __future__ import annotations


class ActivityTimelineError(ValueError):
    """Base error for Activity Timeline foundation."""


class UnknownActivityEventType(ActivityTimelineError):
    def __init__(self, event_type: str) -> None:
        super().__init__(f"unknown activity event_type: {event_type!r}")
        self.event_type = event_type


class UnsupportedActivityEventVersion(ActivityTimelineError):
    def __init__(self, event_type: str, event_version: str, expected: str) -> None:
        super().__init__(
            f"unsupported event_version for {event_type!r}: {event_version!r}; "
            f"expected {expected!r}"
        )
        self.event_type = event_type
        self.event_version = event_version
        self.expected = expected


class InvalidActivityPayload(ActivityTimelineError):
    def __init__(self, event_type: str, detail: str) -> None:
        super().__init__(f"invalid payload for {event_type!r}: {detail}")
        self.event_type = event_type
        self.detail = detail


class InvalidActivityActor(ActivityTimelineError):
    def __init__(self, actor_type: str) -> None:
        super().__init__(f"invalid actor_type: {actor_type!r}")
        self.actor_type = actor_type


__all__ = [
    "ActivityTimelineError",
    "UnknownActivityEventType",
    "UnsupportedActivityEventVersion",
    "InvalidActivityPayload",
    "InvalidActivityActor",
]
