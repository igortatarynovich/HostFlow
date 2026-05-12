"""System paths must not move recruitment stage/status when workforce HR row exists."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.core.audit_events import AuditEventType
from backend.app.services.candidate_workforce_lock import (
    SKIP_SOURCE_REMINDER_EXPIRY,
    observe_skipped_system_candidate_mutation_due_to_workforce_lock,
)
from backend.app.services.candidate_telegram_notifications import sync_candidate_ready_for_handoff_gate
from backend.app.services.contact_attempts import create_attempt
from backend.app.services.reminders import REMINDER_TYPE_DOCUMENT_EXPIRY, run_expiry_notifications
from backend.tests.conftest import _init_data, _set_tenant


@pytest.mark.anyio
async def test_run_expiry_notifications_skips_docs_wait_stage_when_workforce_locked(
    candidate_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    now = datetime.now(timezone.utc)
    doc_id = str(uuid.uuid4())
    reminder_id = str(uuid.uuid4())
    emp_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand = await session.get(Candidate, candidate_id)
        assert cand is not None
        cand.stage = "interview"
        cand.status = "interview"
        await session.flush()

        session.add(
            WorkforceEmployee(
                id=emp_id,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                display_name="LockProbe",
                status="onboarding",
            )
        )
        session.add(
            Document(
                id=doc_id,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                company_id=data["company_id"],
                kind=DocumentKind.driver,
                doc_type="driver_license",
                status=DocumentStatus.approved,
                requested_from=DocumentRequestedFrom.driver,
                process_type=DocumentProcessType.none,
                expire_date=date.today(),
                owner_id=candidate_id,
            )
        )
        session.add(
            Reminder(
                id=reminder_id,
                tenant_id=tenant_id,
                type=REMINDER_TYPE_DOCUMENT_EXPIRY,
                entity_type="document",
                entity_id=doc_id,
                due_at=now,
                status=ReminderStatus.pending,
                payload={"offset_hours": 0},
            )
        )
        await session.commit()

    async def _noop_notify(*args, **kwargs):
        return None

    monkeypatch.setattr("backend.app.services.reminders.notify", _noop_notify)

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        await run_expiry_notifications(session, tenant_id)
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand2 = await session.get(Candidate, candidate_id)
        assert cand2 is not None
        assert str(cand2.stage or "").lower() == "interview"


@pytest.mark.anyio
async def test_create_attempt_skips_stage_when_workforce_locked(
    candidate_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    emp_id = str(uuid.uuid4())

    async def _policy_on(*args, **kwargs):
        return {
            "enabled": True,
            "max_attempts": 5,
            "post_action": "stage_change",
            "stage_code": "rejected",
            "rodo_sent": True,
            "tracking_disabled_reason": None,
        }

    async def _rodo_ok(*args, **kwargs):
        return object()

    monkeypatch.setattr(
        "backend.app.services.contact_attempts.get_effective_contact_policy",
        _policy_on,
    )
    monkeypatch.setattr(
        "backend.app.services.contact_attempts.get_first_rodo_sent",
        _rodo_ok,
    )

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand = await session.get(Candidate, candidate_id)
        assert cand is not None
        cand.stage = "ready_for_hr"
        cand.status = "ready_for_hr"
        session.add(
            WorkforceEmployee(
                id=emp_id,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                display_name="CtLock",
                status="onboarding",
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        att, err = await create_attempt(
            session,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            channel="phone",
            result="answered",
            actor_id=data["recruiter_id"],
        )
        assert err is None, err
        assert att is not None
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand2 = await session.get(Candidate, candidate_id)
        assert cand2 is not None
        assert str(cand2.stage or "").lower() == "ready_for_hr"
        assert str(cand2.status or "").lower() == "ready_for_hr"


@pytest.mark.anyio
async def test_sync_ready_for_handoff_gate_skips_when_workforce_locked(
    candidate_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    emp_id = str(uuid.uuid4())

    async def _snap(*args, **kwargs):
        return {"total": 2, "ready": 2, "missing": [], "in_progress": [], "problematic": []}

    monkeypatch.setattr(
        "backend.app.services.candidate_telegram_notifications.get_candidate_required_docs_snapshot",
        _snap,
    )

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand = await session.get(Candidate, candidate_id)
        assert cand is not None
        cand.stage = "docs_wait"
        cand.status = "docs_wait"
        cand.intake_status = "submitted"
        session.add(
            WorkforceEmployee(
                id=emp_id,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                display_name="GateLock",
                status="onboarding",
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand = await session.get(Candidate, candidate_id)
        assert cand is not None
        promoted = await sync_candidate_ready_for_handoff_gate(
            session, tenant_id=tenant_id, candidate=cand, source="test"
        )
        assert promoted is False
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand2 = await session.get(Candidate, candidate_id)
        assert cand2 is not None
        assert str(cand2.stage or "").lower() == "docs_wait"


@pytest.mark.anyio
async def test_observe_skip_records_audit_payload_with_employee_id(
    candidate_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    emp_id = str(uuid.uuid4())
    audit_calls: list = []

    async def _capture_audit(db, **kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr("backend.app.services.audit.log_audit_event", _capture_audit)

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        session.add(
            WorkforceEmployee(
                id=emp_id,
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                display_name="Obs",
                status="onboarding",
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        await observe_skipped_system_candidate_mutation_due_to_workforce_lock(
            session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            source=SKIP_SOURCE_REMINDER_EXPIRY,
            intended_transition="Candidate.stage -> docs_wait",
        )
        await session.commit()

    assert len(audit_calls) == 1
    ac = audit_calls[0]
    assert ac["event_type"] == AuditEventType.system_automation_skipped_workforce_lock
    pl = ac["payload"]
    assert pl["candidate_id"] == candidate_id
    assert pl["tenant_id"] == tenant_id
    assert pl["source"] == SKIP_SOURCE_REMINDER_EXPIRY
    assert pl["workforce_employee_id"] == emp_id
