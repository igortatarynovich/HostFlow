"""Regression: shared Meta webhook verify_token must not resolve to legacy superadmin when a real tenant also has the same token."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID
from backend.app.db.session import async_session_maker
from backend.app.modules.leads import crud


LEGACY = str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)


@pytest.mark.anyio
async def test_meta_settings_by_verify_token_deprioritizes_legacy_tenant() -> None:
    client_tid = str(uuid.uuid4())
    token = f"dup-verify-{uuid.uuid4().hex}"

    async with async_session_maker() as session:
        legacy_token_before = (
            await session.execute(
                sa.text("SELECT webhook_verify_token FROM meta_lead_settings WHERE tenant_id = :t"),
                {"t": LEGACY},
            )
        ).scalar_one_or_none()

    async with async_session_maker() as session:
        row_exists = (
            await session.execute(
                sa.text("SELECT 1 FROM meta_lead_settings WHERE tenant_id = :t LIMIT 1"),
                {"t": LEGACY},
            )
        ).scalar_one_or_none()
    if row_exists is None:
        pytest.skip("meta_lead_settings row for legacy tenant is required for this regression test")

    async with async_session_maker() as session:
        await session.execute(
            sa.text("DELETE FROM meta_lead_settings WHERE tenant_id = :client"),
            {"client": client_tid},
        )
        await session.execute(
            sa.text(
                """
                INSERT INTO meta_lead_settings (
                    tenant_id, auto_create_enabled, mask_pii_in_logs, pull_field_data_from_graph,
                    webhook_verify_token, created_at, updated_at
                )
                VALUES (
                    :tenant_id, true, true, true, :token, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {"tenant_id": client_tid, "token": token},
        )
        await session.execute(
            sa.text(
                "UPDATE meta_lead_settings SET webhook_verify_token = :token, updated_at = CURRENT_TIMESTAMP "
                "WHERE tenant_id = :legacy"
            ),
            {"token": token, "legacy": LEGACY},
        )
        await session.commit()

    try:
        async with async_session_maker() as session:
            row = await crud.get_meta_settings_by_verify_token(session, verify_token=token)
            assert row is not None
            assert row.tenant_id == client_tid, "non-legacy tenant must win when verify_token is duplicated"
    finally:
        async with async_session_maker() as session:
            await session.execute(
                sa.text("DELETE FROM meta_lead_settings WHERE tenant_id = :client"),
                {"client": client_tid},
            )
            await session.execute(
                sa.text(
                    "UPDATE meta_lead_settings SET webhook_verify_token = :pt, updated_at = CURRENT_TIMESTAMP "
                    "WHERE tenant_id = :legacy"
                ),
                {"pt": legacy_token_before, "legacy": LEGACY},
            )
            await session.commit()
