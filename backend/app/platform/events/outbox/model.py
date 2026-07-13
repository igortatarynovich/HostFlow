"""Transactional domain event outbox model."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.mixins import now_utc

JSONType = JSON().with_variant(JSONB, "postgresql")


class DomainEventOutbox(Base):
    __tablename__ = "domain_event_outbox"
    __table_args__ = (
        Index("ix_domain_event_outbox_status_available", "status", "available_at"),
        Index("ix_domain_event_outbox_tenant_type", "tenant_id", "event_type"),
        Index("ix_domain_event_outbox_aggregate", "aggregate_type", "aggregate_id"),
    )

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    event_version: Mapped[str] = mapped_column(String(16), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    causation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class DomainEventConsumerReceipt(Base):
    """Idempotent consumer processing ledger."""

    __tablename__ = "domain_event_consumer_receipts"
    __table_args__ = (
        Index("uq_domain_event_consumer_receipt", "consumer_name", "event_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    consumer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class RequirementEvaluationResultRecord(Base):
    """Materialized requirement evaluation (ADR-019 PR 3A-1)."""

    __tablename__ = "requirement_evaluation_results"
    __table_args__ = (
        Index("ix_req_eval_results_entity", "entity_type", "entity_id", "evaluated_at"),
        Index("ix_req_eval_results_tenant_entity", "tenant_id", "entity_type", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    policy_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    target_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_revision: Mapped[str] = mapped_column(String(128), nullable=False)
    can_transition: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blocker_codes: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
