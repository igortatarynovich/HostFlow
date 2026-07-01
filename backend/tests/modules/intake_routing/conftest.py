"""Isolate intake routing unit tests from shared tenant settings pollution."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text

from backend.tests.conftest import DEFAULT_TENANT_ID


@pytest_asyncio.fixture(autouse=True)
async def _reset_tenant_intake_routing_settings(db) -> None:
    """Remove intake_routing_v1 default profile between tests (shared db session)."""
    await db.execute(
        text(
            """
            UPDATE tenants
            SET settings = COALESCE(settings::jsonb, '{}'::jsonb) - 'intake_routing_v1'
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": DEFAULT_TENANT_ID},
    )
    await db.flush()
