"""Outbox row lifecycle statuses."""

from __future__ import annotations

from enum import Enum


class OutboxStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    published = "published"
    failed = "failed"
    dead_letter = "dead_letter"
