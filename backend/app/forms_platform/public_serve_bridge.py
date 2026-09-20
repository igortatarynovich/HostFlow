"""FP-3 — public request → Adapter resolve live publication → Form Runtime serve.

One serve surface for public link and later embed. Not a second renderer.
Not a second submit engine. Not FP-4 snippet / distribution UX.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.adapter import resolve_publication
from backend.app.forms_platform.errors import FormsAdapterError
from backend.app.forms_platform.public_submit_bridge import (
    hostflow_form_keys_from_intake_state,
    is_hostflow_form_public_submit,
    payload_values_from_intake_state,
)
from backend.app.forms_platform.runtime import serve
from backend.app.forms_platform.runtime.model import RuntimeModel

RUNTIME_MODEL_CONTRACT = "forms.runtime.model.v1"


def public_serve_http_exception(exc: FormsAdapterError) -> HTTPException:
    """Map Adapter / Runtime errors onto the public HTTP surface."""
    return HTTPException(
        status_code=int(getattr(exc, "http_status", 404) or 404),
        detail={
            "code": getattr(exc, "code", "forms_adapter_error"),
            "message": str(getattr(exc, "message", None) or exc),
            "details": dict(getattr(exc, "details", None) or {}),
        },
    )


async def resolve_live_public_runtime(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str | None = None,
    public_slug: str | None = None,
) -> RuntimeModel:
    """Live publication only: require_active + frozen ledger snapshot → serve."""
    publication = await resolve_publication(
        db,
        tenant_id=str(tenant_id),
        form_id=form_id,
        public_slug=public_slug if not form_id else None,
        require_active=True,
    )
    return serve(publication)


async def maybe_serve_hostflow_form_public_request(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_state: dict[str, Any] | None,
) -> RuntimeModel | None:
    """Serve a HostFlow-Form session from the frozen publication.

    Returns None when the session is unbound (legacy leftover, not this write).
    Raises FormsAdapterError when a bound form is unpublished or inactive.
    """
    if not is_hostflow_form_public_submit(intake_state):
        return None
    form_id, public_slug = hostflow_form_keys_from_intake_state(intake_state)
    return await resolve_live_public_runtime(
        db,
        tenant_id=str(tenant_id),
        form_id=form_id,
        public_slug=public_slug,
    )


def missing_required_runtime_fields(
    model: RuntimeModel,
    intake_state: dict[str, Any] | None,
) -> list[str]:
    """Required field ids from the frozen schema that have no value."""
    values = payload_values_from_intake_state(intake_state).get("values") or {}
    schema = dict(model.field_schema or {})
    missing: list[str] = []
    for row in schema.get("fields") or []:
        if not isinstance(row, dict) or not row.get("required"):
            continue
        field_id = str(row.get("id") or "").strip()
        if not field_id:
            continue
        raw = values.get(field_id)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            missing.append(field_id)
    return missing


def runtime_fields_for_render(model: RuntimeModel) -> list[dict[str, Any]]:
    """Project frozen schema fields for the existing public form renderer.

    Field identity / requiredness come from the snapshot, not from
    ``form_presentation_runtime_v1``.
    """
    schema = dict(model.field_schema or {})
    out: list[dict[str, Any]] = []
    for index, row in enumerate(schema.get("fields") or []):
        if not isinstance(row, dict):
            continue
        field_id = str(row.get("id") or "").strip()
        if not field_id:
            continue
        required = bool(row.get("required"))
        out.append(
            {
                "qualified_code": field_id,
                "sort_order": (index + 1) * 10,
                "intake_level": "required" if required else "optional",
                "label": field_id.rsplit(".", 1)[-1].replace("_", " "),
                "field_type": str(row.get("type") or "text"),
            }
        )
    return out


def runtime_model_public_dict(model: RuntimeModel) -> dict[str, Any]:
    payload = model.to_dict()
    schema = dict(model.field_schema or {})
    payload["fields"] = runtime_fields_for_render(model)
    payload["entity_profile_code"] = schema.get("entity_profile_code")
    payload["presentation_code"] = schema.get("presentation_code")
    return payload
