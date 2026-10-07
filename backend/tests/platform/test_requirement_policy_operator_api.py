"""RPM-2 operator API companion (Postgres).

Optimistic concurrency, atomic audit, isolation markers.
Named Operator Gate stays Postgres-free; this file covers DB paths.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import UserAuditLog
from backend.app.models.document_policy_tenant_overlay import DocumentPolicyTenantOverlay
from backend.app.models.user import User
from backend.app.reference.document_policy_tenant_overlay_repository import (
    OverlayRevisionConflict,
    load_tenant_overlay,
    save_tenant_overlay,
)
from backend.app.reference.requirement_policy_operator import (
    AUDIT_ACTION,
    EMPTY_REVISION,
    compile_operator_overlay_delta,
)

pytestmark = pytest.mark.postgres_integration

TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"


async def _set_tenant(session: AsyncSession, tenant_id: str) -> None:
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
        {"tenant_id": tenant_id},
    )


async def _actor_id(session: AsyncSession) -> str:
    user = (await session.execute(select(User).limit(1))).scalar_one()
    return str(user.id)


@pytest_asyncio.fixture
async def overlay_session(app_with_db):
    """Reuse app DB fixture session factory when available."""
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        await _set_tenant(session, TENANT_A)
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_rpm2_save_revision_conflict_and_audit(overlay_session: AsyncSession) -> None:
    db = overlay_session
    # clean prior row if any
    existing = (
        await db.execute(
            select(DocumentPolicyTenantOverlay).where(
                DocumentPolicyTenantOverlay.tenant_id == TENANT_A
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        await db.delete(existing)
        await db.commit()
        await _set_tenant(db, TENANT_A)

    actor = await _actor_id(db)
    delta = compile_operator_overlay_delta(require=["adr_certificate"], remove=[])
    snap = await save_tenant_overlay(
        db,
        tenant_id=TENANT_A,
        delta=delta,
        reason="need ADR for fleet",
        expected_revision=EMPTY_REVISION,
        actor_id=actor,
    )
    await db.commit()
    assert snap.revision == 1

    with pytest.raises(OverlayRevisionConflict) as exc:
        await save_tenant_overlay(
            db,
            tenant_id=TENANT_A,
            delta={},
            reason="stale overwrite attempt",
            expected_revision=EMPTY_REVISION,
            actor_id=actor,
        )
    assert exc.value.current_revision == 1
    await db.rollback()
    await _set_tenant(db, TENANT_A)

    loaded = await load_tenant_overlay(db, tenant_id=TENANT_A)
    assert loaded is not None
    assert loaded.revision == 1
    assert "adr_certificate" in str(loaded.delta)

    audit = (
        await db.execute(
            select(UserAuditLog)
            .where(
                UserAuditLog.tenant_id == TENANT_A,
                UserAuditLog.action == AUDIT_ACTION,
            )
            .order_by(UserAuditLog.created_at.desc())
        )
    ).scalars().first()
    assert audit is not None
    assert audit.actor_id == actor
    payload = audit.payload or {}
    assert "previous_delta" in payload
    assert "new_delta" in payload
    assert payload.get("reason") == "need ADR for fleet"
    assert payload.get("previous_revision") == 0
    assert payload.get("new_revision") == 1
    assert "actor_id" not in payload
    assert "tenant_id" not in payload

    # reset
    snap2 = await save_tenant_overlay(
        db,
        tenant_id=TENANT_A,
        delta={},
        reason="reset to platform base",
        expected_revision=1,
        actor_id=actor,
    )
    await db.commit()
    assert snap2.revision == 2
    assert snap2.delta == {}


@pytest.mark.asyncio
async def test_rpm2_rls_policy_registered(overlay_session: AsyncSession) -> None:
    """Companion isolation marker: policy + FORCE (TI coverage sees tenant_id SoT)."""
    db = overlay_session
    row = (
        await db.execute(
            text(
                """
                SELECT policyname, cmd, qual, with_check
                FROM pg_policies
                WHERE tablename = 'document_policy_tenant_overlays'
                  AND policyname = 'rls_document_policy_tenant_overlays_tenant'
                """
            )
        )
    ).mappings().first()
    assert row is not None
    assert "app.tenant_id" in (row["qual"] or "")
    assert "app.tenant_id" in (row["with_check"] or "")
    forced = (
        await db.execute(
            text(
                """
                SELECT c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = 'document_policy_tenant_overlays'
                """
            )
        )
    ).one()
    assert forced[0] is True
    assert forced[1] is True


@pytest.mark.asyncio
async def test_rpm2_repository_scoped_load_by_tenant_id(
    overlay_session: AsyncSession,
) -> None:
    """Loader keys by tenant_id — wrong tenant does not surface another overlay row."""
    db = overlay_session
    actor = await _actor_id(db)
    # ensure A has a row
    existing = (
        await db.execute(
            select(DocumentPolicyTenantOverlay).where(
                DocumentPolicyTenantOverlay.tenant_id == TENANT_A
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        await save_tenant_overlay(
            db,
            tenant_id=TENANT_A,
            delta=compile_operator_overlay_delta(require=["passport"], remove=[]),
            reason="seed A",
            expected_revision=EMPTY_REVISION,
            actor_id=actor,
        )
        await db.commit()
        await _set_tenant(db, TENANT_A)

    other = await load_tenant_overlay(db, tenant_id=TENANT_B)
    assert other is None
    own = await load_tenant_overlay(db, tenant_id=TENANT_A)
    assert own is not None
