"""Forms Sprint 6 — submission envelope persistence (append-only content)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.answers import ANSWER_CONTRACT
from backend.app.forms_platform.constants import LIFECYCLE_ARCHIVED
from backend.app.forms_platform.contract_identity import identity_from_snapshot
from backend.app.forms_platform.errors import (
    FormsArchivedError,
    FormsEnvelopeImmutableError,
    FormsEnvelopeNotFoundError,
    FormsEnvelopeStatusError,
    FormsMissingKeyError,
    FormsNotFoundError,
)
from backend.app.forms_platform.publication_versions import (
    get_publication_version,
    register_submission_pin,
)
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


def envelope_to_dict(
    row: FormSubmissionEnvelope,
    *,
    contract_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = {
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
        "publication_version_pin": {
            "form_id": str(row.form_id),
            "version": int(row.published_version),
        },
    }
    if contract_identity is not None:
        out["contract_identity"] = dict(contract_identity)
    return out


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


async def _identity_dict_for_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    version: int,
) -> dict[str, Any]:
    row = await get_publication_version(
        db, tenant_id=tenant_id, form_id=form_id, version=int(version)
    )
    return identity_from_snapshot(dict(row.snapshot or {})).to_dict()


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
    if str(form.lifecycle_status) == LIFECYCLE_ARCHIVED:
        raise FormsArchivedError(details={"form_id": form_id})

    if idempotency_key:
        existing = await find_envelope_by_idempotency(
            db, tenant_id=tenant_id, form_id=form_id, idempotency_key=idempotency_key
        )
        if existing is not None:
            identity = await _identity_dict_for_version(
                db,
                tenant_id=tenant_id,
                form_id=form_id,
                version=int(existing.published_version),
            )
            out = envelope_to_dict(existing, contract_identity=identity)
            out["idempotent_replay"] = True
            return out

    published_version = answer.get("published_version")
    if published_version is None:
        published_version = int(form.published_version or 0)
    if int(published_version) <= 0:
        raise FormsMissingKeyError("published_version is required for submission pin")

    identity = await _identity_dict_for_version(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        version=int(published_version),
    )
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
        await register_submission_pin(
            db,
            tenant_id=tenant_id,
            form_id=form_id,
            version=int(published_version),
        )

    return envelope_to_dict(row, contract_identity=identity)


async def get_submission_envelope(
    db: AsyncSession,
    *,
    tenant_id: str,
    envelope_id: str,
) -> dict[str, Any]:
    row = await db.get(FormSubmissionEnvelope, str(envelope_id))
    if row is None or str(row.tenant_id) != str(tenant_id):
        raise FormsEnvelopeNotFoundError(details={"envelope_id": envelope_id})
    identity = await _identity_dict_for_version(
        db,
        tenant_id=tenant_id,
        form_id=str(row.form_id),
        version=int(row.published_version),
    )
    return envelope_to_dict(row, contract_identity=identity)


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
    return [
        envelope_to_dict(
            r,
            contract_identity=await _identity_dict_for_version(
                db,
                tenant_id=tenant_id,
                form_id=form_id,
                version=int(r.published_version),
            ),
        )
        for r in rows
    ]


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
    identity = await _identity_dict_for_version(
        db,
        tenant_id=tenant_id,
        form_id=str(row.form_id),
        version=int(row.published_version),
    )
    return envelope_to_dict(row, contract_identity=identity)


def assert_envelope_content_immutable(row: FormSubmissionEnvelope) -> None:
    """Guard for callers — content fields must not be reassigned."""
    raise FormsEnvelopeImmutableError(details={"envelope_id": str(row.id)})
