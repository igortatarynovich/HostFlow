from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any, Dict, List
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.enums import DocumentKind, DocumentStatus
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.services import reminders as reminders_service
from backend.app.services import document_catalog
from backend.tests.conftest import DEFAULT_TENANT_ID


pytestmark = pytest.mark.anyio


@pytest.mark.asyncio
async def test_schedule_document_expiry_reminders_matrix() -> None:
    tenant_id = DEFAULT_TENANT_ID
    async with async_session_maker() as session:
        candidate = Candidate(
            id=str(uuid4()),
            tenant_id=tenant_id,
            first_name="Test",
            last_name="Candidate",
            email="candidate@example.com",
            stage="screening",
        )
        document = Document(
            id=str(uuid4()),
            tenant_id=tenant_id,
            candidate_id=candidate.id,
            doc_type="passport",
            kind=DocumentKind.driver,
            status=DocumentStatus.submitted,
            expire_date=date.today() + timedelta(days=1),
            reminder_days_before=2,
        )
        session.add_all([candidate, document])
        await session.flush()

        await reminders_service.schedule_document_expiry_reminders(
            session, tenant_id, document
        )
        await session.flush()

        rows = await session.execute(
            select(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "document",
                Reminder.entity_id == document.id,
                Reminder.status == ReminderStatus.pending,
            )
            .order_by(Reminder.due_at.asc())
        )
        reminders = rows.scalars().all()
        assert len(reminders) == 5

        reminders_by_key = {rem.payload["schedule_key"]: rem for rem in reminders}
        assert set(reminders_by_key) == {
            "document_expiry:-48",
            "document_expiry:-24",
            "document_expiry:-4",
            "document_expiry:0",
            "document_expiry:+24",
        }

        template_slugs = {
            rem.payload.get("template_slug") for rem in reminders_by_key.values()
        }
        assert template_slugs == {
            "document.expiry.pre_custom",
            "document.expiry.pre_24",
            "document.expiry.pre_4",
            "document.expiry.due",
            "document.expiry.overdue",
        }

        overdue_payload = reminders_by_key["document_expiry:+24"].payload
        assert overdue_payload["repeat_interval_hours"] == 24
        assert set(overdue_payload["channel_templates"]) == {
            "in_app",
            "email",
            "webhook",
        }
        assert overdue_payload["channel_templates"]["email"]["template_key"] == "email.document_expiry.overdue"
        assert "email.document_expiry.overdue.subject" in overdue_payload["localization_keys"]

        ids_by_key = {key: reminder.id for key, reminder in reminders_by_key.items()}

        metadata_phases = {
            rem.payload.get("template_metadata", {}).get("phase")
            for rem in reminders
        }
        assert metadata_phases == {"pre", "post", "due"}

        ids_by_key = {rem.payload["schedule_key"]: rem.id for rem in reminders}

        # повторный пересчёт не создаёт дублей и переиспользует записи
        await reminders_service.schedule_document_expiry_reminders(
            session, tenant_id, document
        )
        await session.flush()

        rows = await session.execute(
            select(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "document",
                Reminder.entity_id == document.id,
                Reminder.status == ReminderStatus.pending,
            )
            .order_by(Reminder.due_at.asc())
        )
        reminders_second = rows.scalars().all()
        assert len(reminders_second) == 5
        ids_by_key_second = {
            rem.payload["schedule_key"]: rem.id for rem in reminders_second
        }
        assert ids_by_key == ids_by_key_second


@pytest.mark.asyncio
async def test_run_expiry_notifications_emits_template_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = DEFAULT_TENANT_ID
    captured: List[Dict[str, Any]] = []

    async def fake_notify(
        to: str,
        subject: str,
        text: str,
        *,
        template_key: str | None = None,
        template_context: Dict[str, Any] | None = None,
        channels: List[str] | None = None,
    ) -> None:
        captured.append(
            {
                "to": to,
                "subject": subject,
                "text": text,
                "template_key": template_key,
                "template_context": template_context,
                "channels": channels,
            }
        )

    monkeypatch.setattr(reminders_service, "notify", fake_notify)

    async with async_session_maker() as session:
        candidate = Candidate(
            id=str(uuid4()),
            tenant_id=tenant_id,
            first_name="Test",
            last_name="Candidate",
            email="candidate@example.com",
            stage="screening",
        )
        document = Document(
            id=str(uuid4()),
            tenant_id=tenant_id,
            candidate_id=candidate.id,
            doc_type="passport",
            kind=DocumentKind.driver,
            status=DocumentStatus.submitted,
            expire_date=date.today(),
            reminder_days_before=2,
        )
        session.add_all([candidate, document])
        await session.flush()

        await reminders_service.schedule_document_expiry_reminders(
            session, tenant_id, document
        )
        await session.flush()
        seen, sent = await reminders_service.run_expiry_notifications(
            session, tenant_id
        )

        assert seen == 5
        assert sent == 5
        assert len(captured) == 5

        template_keys = {call["template_key"] for call in captured}
        assert template_keys == {
            "email.document_expiry.pre_custom",
            "email.document_expiry.pre_24",
            "email.document_expiry.pre_4",
            "email.document_expiry.due",
            "email.document_expiry.overdue",
        }
        assert all(call["channels"] == ["email"] for call in captured)
        assert all(
            call["template_context"]["document_name"] == document.doc_type
            for call in captured
        )

        rows = await session.execute(
            select(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "document",
                Reminder.entity_id == document.id,
            )
        )
        reminders = rows.scalars().all()
        assert all(rem.status == ReminderStatus.sent for rem in reminders)
        assert all(rem.payload.get("template_context") for rem in reminders)
        await session.refresh(candidate)
        assert candidate.stage == "docs_wait"


@pytest.mark.asyncio
async def test_schedule_respects_catalog_reminder_days(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = DEFAULT_TENANT_ID
    custom_days = [90, 10]
    original_defaults = document_catalog.DOCUMENT_TYPE_DEFAULTS["driver_license"]
    custom_rule = dict(original_defaults.expiry_rule or {})
    custom_rule["reminders_days"] = custom_days
    monkeypatch.setitem(
        document_catalog.DOCUMENT_TYPE_DEFAULTS,
        "driver_license",
        replace(original_defaults, expiry_rule=custom_rule),
    )

    async with async_session_maker() as session:
        candidate = Candidate(
            id=str(uuid4()),
            tenant_id=tenant_id,
            first_name="Custom",
            last_name="Reminders",
            email="candidate@example.com",
            stage="screening",
        )
        document = Document(
            id=str(uuid4()),
            tenant_id=tenant_id,
            candidate_id=candidate.id,
            doc_type="driver_license",
            kind=DocumentKind.driver,
            status=DocumentStatus.submitted,
            expire_date=date.today() + timedelta(days=120),
        )
        session.add_all([candidate, document])
        await session.flush()

        await reminders_service.schedule_document_expiry_reminders(
            session, tenant_id, document
        )
        await session.flush()

        rows = await session.execute(
            select(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "document",
                Reminder.entity_id == document.id,
            )
            .order_by(Reminder.due_at.asc())
        )
        reminders = rows.scalars().all()
        keys = {rem.payload.get("schedule_key") for rem in reminders}
        assert "document_expiry:-2160" in keys  # 90 days
        assert "document_expiry:-240" in keys  # 10 days
