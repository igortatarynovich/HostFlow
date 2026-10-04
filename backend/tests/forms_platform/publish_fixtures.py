"""Test helpers: freeze a live publication without changing production seed writers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.adapter import commit_publish


async def commit_live_publication(
    session: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    idempotency_key: str | None = None,
    presentation_runtime: dict[str, Any] | None = None,
    fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return await commit_publish(
        session,
        tenant_id=str(tenant_id),
        form_id=str(form_id),
        activate=True,
        idempotency_key=idempotency_key,
        presentation_runtime=presentation_runtime,
        fields=fields,
    )
