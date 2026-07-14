"""Canonical domain event envelope (ADR-019 PR 3A-1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    event_type: str
    event_version: str
    aggregate_type: str
    aggregate_id: str
    tenant_id: str
    company_id: Optional[str]
    payload: dict[str, Any]
    occurred_at: datetime
    correlation_id: str
    causation_id: Optional[str]

    @classmethod
    def new(
        cls,
        *,
        event_type: str,
        event_version: str,
        aggregate_type: str,
        aggregate_id: str,
        tenant_id: str,
        payload: dict[str, Any],
        occurred_at: datetime,
        company_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> EventEnvelope:
        return cls(
            event_id=event_id or str(uuid4()),
            event_type=event_type,
            event_version=event_version,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            tenant_id=tenant_id,
            company_id=company_id,
            payload=dict(payload),
            occurred_at=occurred_at,
            correlation_id=correlation_id or str(uuid4()),
            causation_id=causation_id,
        )
