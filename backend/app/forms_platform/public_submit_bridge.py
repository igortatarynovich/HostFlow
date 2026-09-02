"""Forms Platform C6 — production Shared Intake → Execution bridge.

Composes Adapter resolve → C4 serve → C5 persist_execution on the existing
public apply-submit path. Not a second submit engine. Not a Builder/Runtime contract.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.adapter import resolve_publication
from backend.app.forms_platform.errors import FormsNotFoundError, FormsVersionNotFoundError
from backend.app.forms_platform.execution import persist_execution
from backend.app.forms_platform.runtime import serve

# Stable Shared Intake apply-submit surface (existing HTTP — do not invent /forms/submit).
PUBLIC_APPLY_SUBMIT_PATH = "/api/v1/public/apply/{token}/submit"


def hostflow_form_keys_from_intake_state(
    intake_state: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    """Return (form_id, public_slug) when this session is bound to a HostFlow Form."""
    if not isinstance(intake_state, dict):
        return None, None
    lf = intake_state.get("lead_form")
    if not isinstance(lf, dict):
        return None, None
    form_id = str(lf.get("id") or "").strip() or None
    public_slug = str(lf.get("public_slug") or "").strip() or None
    return form_id, public_slug


def is_hostflow_form_public_submit(intake_state: dict[str, Any] | None) -> bool:
    form_id, public_slug = hostflow_form_keys_from_intake_state(intake_state)
    return bool(form_id or public_slug)


def payload_values_from_intake_state(intake_state: dict[str, Any] | None) -> dict[str, Any]:
    """Map intake session state → Forms validate payload (values map)."""
    state = intake_state if isinstance(intake_state, dict) else {}
    raw = state.get("presentation_values_v1")
    if isinstance(raw, dict) and raw:
        return {"values": {str(k): v for k, v in raw.items()}}
    # Nested contacts/personal often hold answers when presentation_values_v1 is absent.
    values: dict[str, Any] = {}
    for bucket in ("contacts", "personal", "experience", "custom"):
        block = state.get(bucket)
        if isinstance(block, dict):
            for key, val in block.items():
                values[str(key)] = val
    return {"values": values}


async def maybe_execute_hostflow_form_public_submit(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_state: dict[str, Any] | None,
    idempotency_key: str | None = None,
) -> dict[str, Any] | None:
    """If session is HostFlow Form-bound: resolve → serve → persist_execution.

    Returns None when the session is not a HostFlow Form publication submit
    (unbound / Meta / questionnaire stay outside this bridge).
    Constructor Entity Profile forms have a TenantLeadForm pointer (published_version=1)
    but no ``form_publication_versions`` ledger row — skip C6 and let Shared Intake
    dispatch create the Sales inquiry. Fail-closed on other FormsAdapterError when a
    frozen publication exists (inactive / archived / stale pin).
    """
    if not is_hostflow_form_public_submit(intake_state):
        return None

    form_id, public_slug = hostflow_form_keys_from_intake_state(intake_state)
    try:
        publication = await resolve_publication(
            db,
            tenant_id=str(tenant_id),
            form_id=form_id,
            public_slug=public_slug if not form_id else None,
            require_active=True,
        )
    except (FormsVersionNotFoundError, FormsNotFoundError):
        return None
    model = serve(publication)
    return await persist_execution(
        db,
        tenant_id=str(tenant_id),
        model=model,
        payload=payload_values_from_intake_state(intake_state),
        idempotency_key=idempotency_key,
        raise_on_error=True,
    )
