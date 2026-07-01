"""Intake-channel bootstrap: Telegram idempotency on telegram_chat_id."""

from __future__ import annotations

import uuid

import pytest

from backend.app.services.intake_channel_candidate import (
    create_telegram_intake_bootstrap_via_service,
)

TENANT_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_telegram_intake_bootstrap_same_chat_idempotent(db):
    chat = f"tg-{uuid.uuid4().hex[:16]}"
    c1 = await create_telegram_intake_bootstrap_via_service(
        db,
        tenant_id=TENANT_ID,
        chat_id=chat,
        username="testuser",
        sender_label="Test User",
        sender_address=None,
        contact_phone=None,
    )
    c2 = await create_telegram_intake_bootstrap_via_service(
        db,
        tenant_id=TENANT_ID,
        chat_id=chat,
        username="testuser",
        sender_label="Test User",
        sender_address=None,
        contact_phone=None,
    )
    assert str(c1.id) == str(c2.id)
