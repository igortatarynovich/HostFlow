"""Forms Sprint 6 — submission envelope persistence (append-only content)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.answers import ANSWER_CONTRACT
from backend.app.forms_platform.errors import (
    FormsEnvelopeImmutableError,
    FormsEnvelopeNotFoundError,
    FormsEnvelopeStatusError,
    FormsMissingKeyError,
    FormsNotFoundError,
    FormsVersionNotFoundError,
)
from backend.app.forms_platform.publication_versions import register_submission_pin
from backend.app.models.form_submission_envelope import (
    STATUS_ACCEPTED,
    STATUS_FAILED,
    STATUS_HANDED_OFF,
    STATUS_RECEIVED,
    STATUS_REJECTED,
    FormSubmissionEnvelope,
)
from backend.app.models.mixins import now_utc
from backend.app.models.tenant_lead_form import TenantLeadForm

ALLOWED_STATUSES = frozenset(
    {
        STATUS_RECEIVED,
        STATUS_ACCEPTED,
        STATUS_REJECTED,
        STATUS_HANDED_OFF,
        STATUS_FAILED,
    }
)


def envelope_to_dict(row: FormSubmissionEnvelope) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "form_id": str(row.form_id),
        "published_version": int(row.published_version),
        "schema_contract": row.schema_contract,
        "answer_contract": row.answer_contract,
        "raw_values": dict(row.raw_values or {}),
        "normalized_values": dict(row.normalized_values or {}),
        "errors": list(row.errors or []),
        "processing_status": str(row.processing_status),
        "idempotency_key": row.idempotency_key,
        "intake_handoff": dict(row.intake_handoff or {}),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "status_updated_at": row.status_updated_at.isoformat() if row.status_updated_at else None,
        "content_immutable": True,
    }


async def find_envelope_by_idempotency(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    idempotency_key: str,
) -> FormSubmissionEnvelope | None:
    key = str(idempotency_key or "").strip()
    if not key:
        return None
    return await db.scalar(
        select(FormSubmissionEnvelope).where(
            FormSubmissionEnvelope.tenant_id == str(tenant_id),
            FormSubmissionEnvelope.form_id == str(form_id),
            FormSubmissionEnvelope.idempotency_key == key,
        )
    )


async def persist_submission_envelope(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    answer: dict[str, Any],
    idempotency_key: str | None = None,
    pin_publication_version: bool = True,
) -> dict[str, Any]:
    """Append-only persist of normalized answers. Idempotent by key when provided."""
    if not form_id:
        raise FormsMissingKeyError("form_id is required")
    form = await db.get(TenantLeadForm, str(form_id))
    if form is None or str(form.tenant_id) != str(tenant_id):
        raise FormsNotFoundError(details={"form_id": form_id})

    if idempotency_key:
        existing = await find_envelope_by_idempotency(
            db, tenant_id=tenant_id, form_id=form_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            out = envelope_to_dict(existing)
            out["idempotent_replay"] = True
            return out

    published_version = answer.get("published_version")
    if published_version is None:
        published_version = int(form.published_version or 1)
    ok = bool(answer.get("ok"))
    status = STATUS_ACCEPTED if ok else STATUS_REJECTED

    row = FormSubmissionEnvelope(
        tenant_id=str(tenant_id),
        form_id=str(form_id),
        published_version=int(published_version),
        schema_contract=answer.get("schema_contract"),
        answer_contract=str(answer.get("answer_contract") or ANSWER_CONTRACT),
        raw_values=dict(answer.get("raw_values") or {}),
        normalized_values=dict(answer.get("normalized_values") or {}),
        errors=list(answer.get("errors") or []),
        processing_status=status,
        idempotency_key=(str(idempotency_key).strip() or None) if idempotency_key else None,
        intake_handoff=dict(answer.get("intake_handoff") or {}),
    )
    db.add(row)
    await db.flush()

    if pin_publication_version and ok:
        try:
            await register_submission_pin(
                db,
                tenant_id=tenant_id,
                form_id=form_id,
                version=int(published_version),
            )
        except FormsVersionNotFoundError:
            # Pre-ledger publications may lack a version row; envelope still persists.
            pass

    return envelope_to_dict(row)


async def get_submission_envelope(
    db: AsyncSession,
    *,
    tenant_id: str,
    envelope_id: str,
) -> dict[str, Any]:
    row = await db.get(FormSubmissionEnvelope, str(envelope_id))
    if row is None or str(row.tenant_id) != str(tenant_id):
        raise FormsEnvelopeNotFoundError(details={"envelope_id": envelope_id})
    return envelope_to_dict(row)


async def list_submission_envelopes(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> list[dict[str, Any]]:
    form = await db.get(TenantLeadForm, str(form_id))
    if form is None or str(form.tenant_id) != str(tenant_id):
        raise FormsNotFoundError(details={"form_id": form_id})
    rows = (
        await db.scalars(
            select(FormSubmissionEnvelope)
            .where(
                FormSubmissionEnvelope.tenant_id == str(tenant_id),
                FormSubmissionEnvelope.form_id == str(form_id),
            )
            .order_by(FormSubmissionEnvelope.created_at.asc())
        )
    ).all()
    return [envelope_to_dict(r) for r in rows]


async def set_envelope_processing_status(
    db: AsyncSession,
    *,
    tenant_id: str,
    envelope_id: str,
    status: str,
) -> dict[str, Any]:
    """Mutate processing status only — never raw/normalized content."""
    row = await db.get(FormSubmissionEnvelope, str(envelope_id))
    if row is None or str(row.tenant_id) != str(tenant_id):
        raise FormsEnvelopeNotFoundError(details={"envelope_id": envelope_id})
    next_status = str(status or "").strip()
    if next_status not in ALLOWED_STATUSES:
        raise FormsEnvelopeStatusError(details={"status": status})
    row.processing_status = next_status
    row.status_updated_at = now_utc()
    await db.flush()
    return envelope_to_dict(row)


def assert_envelope_content_immutable(row: FormSubmissionEnvelope) -> None:
    """Guard for callers — content fields must not be reassigned."""
    raise FormsEnvelopeImmutableError(details={"envelope_id": str(row.id)})
