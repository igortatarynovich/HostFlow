"""PR 3A-1 — transactional outbox + event contract + consumer skeleton."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.db.base import Base
from backend.app.platform.events.consumer.skeleton import CONSUMER_NAME, ReactionOrchestratorSkeleton
from backend.app.platform.events.envelope import EventEnvelope
from backend.app.platform.events.outbox.dispatcher import (
    claim_outbox_batch,
    dispatch_outbox_batch,
    mark_outbox_failed,
)
from backend.app.platform.events.outbox.model import DomainEventConsumerReceipt, DomainEventOutbox, RequirementEvaluationResultRecord
from backend.app.platform.events.outbox.publisher import build_envelope, publish_domain_event
from backend.app.platform.events.outbox.statuses import OutboxStatus
from backend.app.platform.events.registry import get_event_contract_registry

EVENT_TYPE = "candidate.requirements_evaluated"
EVENT_VERSION = "v1"


@pytest.fixture(autouse=True)
def _enable_outbox_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PLATFORM_EVENT_OUTBOX_ENABLED", "1")


def _sample_result(*, can_transition: bool = True) -> MagicMock:
    blocking = () if can_transition else ("identity_document",)
    evaluated_at = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)
    result = MagicMock()
    result.entity_type = "candidate"
    result.entity_id = "cand-1"
    result.policy_ref = "recruitment.driver_ce.pl/v1"
    result.policy_version = "v1"
    result.target_stage = "docs_received"
    result.evaluated_at = evaluated_at
    result.input_fingerprint = "fp-rev-1"
    result.can_transition = can_transition
    result.blocking_requirements = blocking
    result.to_dict.return_value = {
        "entity_type": "candidate",
        "entity_id": "cand-1",
        "policy_ref": "recruitment.driver_ce.pl/v1",
        "can_transition": can_transition,
        "blocking_requirements": list(blocking),
    }
    return result


def _valid_payload(**overrides) -> dict:
    base = {
        "candidate_id": "cand-1",
        "evaluation_result_id": "eval-1",
        "entity_revision": "fp-rev-1",
        "policy_ref": "recruitment.driver_ce.pl/v1",
        "can_transition": True,
        "target_stage": "docs_received",
        "blocker_codes": [],
        "evaluated_at": "2026-07-13T12:00:00+00:00",
    }
    base.update(overrides)
    return base


_OUTBOX_TABLES = (
    DomainEventOutbox.__table__,
    DomainEventConsumerReceipt.__table__,
    RequirementEvaluationResultRecord.__table__,
)


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=list(_OUTBOX_TABLES)))
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.anyio
async def test_mutation_and_outbox_commit_together(db_session: AsyncSession) -> None:
    from backend.app.platform.events.candidate_requirements_publisher import (
        publish_candidate_requirements_evaluated_event,
        persist_requirement_evaluation_record,
    )

    result = _sample_result()
    record = await persist_requirement_evaluation_record(
        db_session, tenant_id="tenant-1", result=result, company_id="co-1"
    )
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.company_id = "co-1"
    candidate.entity_profile_code = "driver_ce"
    event_id = await publish_candidate_requirements_evaluated_event(
        db_session,
        tenant_id="tenant-1",
        candidate=candidate,
        result=result,
        evaluation_result_id=record.id,
        correlation_id="corr-1",
        causation_id="cause-1",
    )
    await db_session.commit()

    saved_eval = await db_session.get(RequirementEvaluationResultRecord, record.id)
    saved_outbox = await db_session.get(DomainEventOutbox, event_id)
    assert saved_eval is not None
    assert saved_outbox is not None
    assert saved_outbox.event_type == EVENT_TYPE
    assert saved_outbox.correlation_id == "corr-1"
    assert saved_outbox.causation_id == "cause-1"


@pytest.mark.anyio
async def test_rollback_mutation_removes_outbox(db_session: AsyncSession) -> None:
    from backend.app.platform.events.candidate_requirements_publisher import (
        persist_requirement_evaluation_record,
        publish_candidate_requirements_evaluated_event,
    )

    result = _sample_result()
    record = await persist_requirement_evaluation_record(
        db_session, tenant_id="tenant-1", result=result
    )
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.company_id = None
    candidate.entity_profile_code = None
    event_id = await publish_candidate_requirements_evaluated_event(
        db_session,
        tenant_id="tenant-1",
        candidate=candidate,
        result=result,
        evaluation_result_id=record.id,
    )
    await db_session.rollback()

    assert await db_session.get(RequirementEvaluationResultRecord, record.id) is None
    assert await db_session.get(DomainEventOutbox, event_id) is None


def test_contract_validation_rejects_invalid_payload() -> None:
    registry = get_event_contract_registry()
    with pytest.raises(ValueError, match="payload.candidate_id"):
        registry.validate_envelope(
            event_type=EVENT_TYPE,
            event_version=EVENT_VERSION,
            payload={"can_transition": True},
        )


def test_contract_rejects_internal_evaluator_fields() -> None:
    registry = get_event_contract_registry()
    payload = _valid_payload(requirements=[{"code": "identity_document"}])
    with pytest.raises(ValueError, match="internal evaluator fields"):
        registry.validate_envelope(
            event_type=EVENT_TYPE,
            event_version=EVENT_VERSION,
            payload=payload,
        )


def test_unknown_event_version_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported event version"):
        build_envelope(
            event_type=EVENT_TYPE,
            event_version="v99",
            aggregate_type="candidate",
            aggregate_id="cand-1",
            tenant_id="tenant-1",
            payload=_valid_payload(),
            occurred_at=datetime.now(timezone.utc),
        )


@pytest.mark.anyio
async def test_dispatcher_does_not_double_claim_while_processing(db_session: AsyncSession) -> None:
    envelope = build_envelope(
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id="cand-1",
        tenant_id="tenant-1",
        payload=_valid_payload(),
        occurred_at=datetime.now(timezone.utc),
    )
    await publish_domain_event(db_session, envelope)
    await db_session.commit()

    claimed_a = await claim_outbox_batch(db_session, worker_id="worker-a", batch_size=5)
    await db_session.commit()
    assert len(claimed_a) == 1
    assert claimed_a[0].status == OutboxStatus.processing.value

    claimed_b = await claim_outbox_batch(db_session, worker_id="worker-b", batch_size=5)
    assert len(claimed_b) == 0


@pytest.mark.anyio
async def test_consumer_idempotent_on_redelivery(db_session: AsyncSession) -> None:
    envelope = EventEnvelope.new(
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id="cand-1",
        tenant_id="tenant-1",
        payload=_valid_payload(),
        occurred_at=datetime.now(timezone.utc),
    )
    consumer = ReactionOrchestratorSkeleton(db_session)
    await consumer.handle(envelope)
    await db_session.commit()
    await consumer.handle(envelope)
    await db_session.commit()

    rows = (
        await db_session.execute(
            select(DomainEventConsumerReceipt).where(
                DomainEventConsumerReceipt.consumer_name == CONSUMER_NAME,
                DomainEventConsumerReceipt.event_id == envelope.event_id,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert consumer.handled_event_ids == [envelope.event_id]


@pytest.mark.anyio
async def test_retry_increments_attempt_count(db_session: AsyncSession) -> None:
    row = DomainEventOutbox(
        event_id="evt-retry",
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id="cand-1",
        tenant_id="tenant-1",
        company_id=None,
        payload=_valid_payload(),
        occurred_at=datetime.now(timezone.utc),
        correlation_id="c1",
        causation_id=None,
        status=OutboxStatus.processing.value,
        attempt_count=1,
        available_at=datetime.now(timezone.utc),
    )
    db_session.add(row)
    await db_session.flush()

    status = await mark_outbox_failed(db_session, row, error="boom", max_attempts=5)
    assert status == OutboxStatus.failed
    assert row.attempt_count == 1
    assert row.status == OutboxStatus.pending.value


@pytest.mark.anyio
async def test_exhausted_retry_moves_to_dead_letter(db_session: AsyncSession) -> None:
    row = DomainEventOutbox(
        event_id="evt-dlq",
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id="cand-1",
        tenant_id="tenant-1",
        company_id=None,
        payload=_valid_payload(),
        occurred_at=datetime.now(timezone.utc),
        correlation_id="c1",
        causation_id=None,
        status=OutboxStatus.processing.value,
        attempt_count=5,
        available_at=datetime.now(timezone.utc),
    )
    db_session.add(row)
    await db_session.flush()

    status = await mark_outbox_failed(db_session, row, error="boom", max_attempts=5)
    assert status == OutboxStatus.dead_letter
    assert row.status == OutboxStatus.dead_letter.value


@pytest.mark.anyio
async def test_dispatch_publishes_via_consumer_skeleton(db_session: AsyncSession) -> None:
    envelope = build_envelope(
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id="cand-1",
        tenant_id="tenant-1",
        payload=_valid_payload(),
        occurred_at=datetime.now(timezone.utc),
        correlation_id="corr-dispatch",
        causation_id="cause-dispatch",
    )
    await publish_domain_event(db_session, envelope)
    await db_session.commit()

    consumer = ReactionOrchestratorSkeleton(db_session)
    stats = await dispatch_outbox_batch(db_session, consumer, worker_id="test-worker", batch_size=10)
    assert stats.claimed == 1
    assert stats.published == 1

    row = await db_session.get(DomainEventOutbox, envelope.event_id)
    assert row is not None
    assert row.status == OutboxStatus.published.value
    assert row.correlation_id == "corr-dispatch"
    assert row.causation_id == "cause-dispatch"


@pytest.mark.anyio
async def test_persist_publish_does_not_run_legacy_automation(db_session: AsyncSession) -> None:
    result = _sample_result()
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.company_id = "co-1"
    candidate.entity_profile_code = "driver_ce"

    with patch(
        "backend.app.services.automation_rules.run_rules",
        new=AsyncMock(),
    ) as legacy_mock:
        from backend.app.platform.events.candidate_requirements_publisher import (
            persist_requirement_evaluation_record,
            publish_candidate_requirements_evaluated_event,
        )

        record = await persist_requirement_evaluation_record(
            db_session, tenant_id="tenant-1", result=result, company_id="co-1"
        )
        event_id = await publish_candidate_requirements_evaluated_event(
            db_session,
            tenant_id="tenant-1",
            candidate=candidate,
            result=result,
            evaluation_result_id=record.id,
        )
        await db_session.commit()

    legacy_mock.assert_not_called()
    assert event_id
    outbox = await db_session.get(DomainEventOutbox, event_id)
    assert outbox is not None
    assert outbox.payload.get("can_transition") is True
    assert "requirements" not in outbox.payload


@pytest.mark.anyio
async def test_consumer_does_not_execute_business_actions(db_session: AsyncSession) -> None:
    consumer = ReactionOrchestratorSkeleton(db_session)
    envelope = EventEnvelope.new(
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id="cand-1",
        tenant_id="tenant-1",
        payload=_valid_payload(),
        occurred_at=datetime.now(timezone.utc),
    )
    await consumer.handle(envelope)
    await db_session.commit()
    assert consumer.handled_event_ids == [envelope.event_id]

    with pytest.raises(ValueError, match="action hint"):
        bad = EventEnvelope.new(
            event_type=EVENT_TYPE,
            event_version=EVENT_VERSION,
            aggregate_type="candidate",
            aggregate_id="cand-1",
            tenant_id="tenant-1",
            payload={**_valid_payload(), "change_stage": True},
            occurred_at=datetime.now(timezone.utc),
        )
        await consumer.handle(bad)


@pytest.mark.anyio
async def test_failed_consumer_does_not_write_receipt(db_session: AsyncSession) -> None:
    consumer = ReactionOrchestratorSkeleton(db_session)
    envelope = EventEnvelope.new(
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id="cand-1",
        tenant_id="tenant-1",
        payload={**_valid_payload(), "change_stage": True},
        occurred_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError, match="action hint"):
        await consumer.handle(envelope)
    await db_session.rollback()

    rows = (
        await db_session.execute(
            select(DomainEventConsumerReceipt).where(
                DomainEventConsumerReceipt.consumer_name == CONSUMER_NAME,
                DomainEventConsumerReceipt.event_id == envelope.event_id,
            )
        )
    ).scalars().all()
    assert rows == []
    assert consumer.handled_event_ids == []


@pytest.mark.anyio
async def test_dispatch_failure_rolls_back_receipt(db_session: AsyncSession) -> None:
    envelope = build_envelope(
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id="cand-1",
        tenant_id="tenant-1",
        payload=_valid_payload(),
        occurred_at=datetime.now(timezone.utc),
    )
    await publish_domain_event(db_session, envelope)
    await db_session.commit()

    class FailingConsumer(ReactionOrchestratorSkeleton):
        async def _execute(self, envelope: EventEnvelope) -> None:
            raise RuntimeError("consumer boom")

    stats = await dispatch_outbox_batch(
        db_session,
        FailingConsumer(db_session),
        worker_id="test-worker",
        batch_size=10,
    )
    assert stats.failed == 1

    receipt_rows = (
        await db_session.execute(
            select(DomainEventConsumerReceipt).where(
                DomainEventConsumerReceipt.event_id == envelope.event_id,
            )
        )
    ).scalars().all()
    assert receipt_rows == []

    row = await db_session.get(DomainEventOutbox, envelope.event_id)
    assert row is not None
    assert row.status == OutboxStatus.pending.value


def test_outbox_flag_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PLATFORM_EVENT_OUTBOX_ENABLED", raising=False)
    from backend.app.platform.events.candidate_requirements_publisher import _outbox_enabled

    assert _outbox_enabled() is False


def test_ensure_domain_events_schema_skips_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.services.ensure_domain_events_schema import should_run_domain_events_schema_fallback

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://hostflow:secret@localhost/hostflow")
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert should_run_domain_events_schema_fallback() is False


def test_ensure_domain_events_schema_skips_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.services.ensure_domain_events_schema import should_run_domain_events_schema_fallback

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert should_run_domain_events_schema_fallback() is False
