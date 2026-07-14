"""Reaction Orchestrator consumer skeleton (log-only, PR 3A-1)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.platform.events.envelope import EventEnvelope
from backend.app.platform.events.outbox.model import DomainEventConsumerReceipt

logger = logging.getLogger(__name__)

CONSUMER_NAME = "reaction_orchestrator_skeleton_v1"


class ReactionOrchestratorSkeleton:
    """Idempotent log-only consumer — no business actions in PR 3A-1."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self.handled_event_ids: list[str] = []

    async def handle(self, envelope: EventEnvelope) -> None:
        if await self._already_processed(envelope.event_id):
            logger.info(
                "domain_event.consumer.duplicate consumer=%s event_id=%s",
                CONSUMER_NAME,
                envelope.event_id,
            )
            return

        await self._execute(envelope)

        self._db.add(
            DomainEventConsumerReceipt(
                consumer_name=CONSUMER_NAME,
                event_id=envelope.event_id,
                tenant_id=envelope.tenant_id,
            )
        )
        await self._db.flush()
        self.handled_event_ids.append(envelope.event_id)

    async def _execute(self, envelope: EventEnvelope) -> None:
        """Consumer work — receipt is written only after this succeeds."""
        if envelope.event_type == "candidate.requirements_evaluated":
            self._assert_no_legacy_side_effects(envelope)

        logger.info(
            "domain_event.consumer.received consumer=%s event_id=%s type=%s version=%s "
            "aggregate=%s:%s correlation=%s causation=%s",
            CONSUMER_NAME,
            envelope.event_id,
            envelope.event_type,
            envelope.event_version,
            envelope.aggregate_type,
            envelope.aggregate_id,
            envelope.correlation_id,
            envelope.causation_id or "",
        )

    async def _already_processed(self, event_id: str) -> bool:
        row = (
            await self._db.execute(
                select(DomainEventConsumerReceipt.id).where(
                    DomainEventConsumerReceipt.consumer_name == CONSUMER_NAME,
                    DomainEventConsumerReceipt.event_id == event_id,
                )
            )
        ).scalar_one_or_none()
        return row is not None

    @staticmethod
    def _assert_no_legacy_side_effects(envelope: EventEnvelope) -> None:
        payload = envelope.payload or {}
        forbidden_actions = ("change_stage", "open_transfer", "execute_transfer", "create_reminder")
        for key in forbidden_actions:
            if key in payload:
                raise ValueError(f"event payload must not include action hint: {key}")
