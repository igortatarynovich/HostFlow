"""HR verified fields SoT — employment case data for contracts / ZUS / payroll (PR4)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_hr_review import WorkforceHrReview, HR_REVIEW_TERMINAL_STATUSES
from backend.app.models.workforce_hr_document_verification import (
    VERIFICATION_VERIFIED,
    WorkforceHrDocumentVerification,
)
from backend.app.models.workforce_hr_verified_field import (
    FIELD_STATUS_APPROVE_OK,
    FIELD_STATUS_CONFLICT,
    FIELD_STATUS_OVERRIDDEN,
    FIELD_STATUS_PENDING,
    FIELD_STATUS_VERIFIED,
    WorkforceHrVerifiedField,
)
from backend.app.services.audit import log_activity
from backend.app.services.hr_verified_field_catalog import BASE_CRITICAL_FIELD_CODES, FIELD_CATALOG, FIELD_SPECS


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_value(value: Any) -> str:
    return str(value or "").strip()


def _field_meta(field_code: str, spec: Optional[dict[str, Any]] = None) -> tuple[str, list[str]]:
    if spec:
        return str(spec.get("label") or field_code), list(spec.get("downstream_use") or [])
    cat = FIELD_CATALOG.get(field_code) or {}
    return str(cat.get("label") or field_code), list(cat.get("downstream_use") or [])


def _serialize_row(
    row: WorkforceHrVerifiedField,
    *,
    critical_field_codes: Optional[frozenset[str]] = None,
) -> dict[str, Any]:
    codes = critical_field_codes or BASE_CRITICAL_FIELD_CODES
    return {
        "id": row.id,
        "field_code": row.field_code,
        "field_label": row.field_label,
        "downstream_use": list(row.downstream_use_json or []),
        "status": row.status,
        "verified_value": row.verified_value,
        "source_document_id": row.source_document_id,
        "source_document_key": row.source_document_key,
        "document_verification_id": row.document_verification_id,
        "profile_values": dict(row.profile_values_json or {}),
        "verified_by_user_id": row.verified_by_user_id,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "override_reason": row.override_reason,
        "conflict_reason": row.conflict_reason,
        "is_critical": row.field_code in codes,
    }


async def _get_row(
    db: AsyncSession, tenant_id: str, hr_review_id: str, field_code: str
) -> Optional[WorkforceHrVerifiedField]:
    res = await db.execute(
        select(WorkforceHrVerifiedField).where(
            WorkforceHrVerifiedField.tenant_id == tenant_id,
            WorkforceHrVerifiedField.hr_review_id == hr_review_id,
            WorkforceHrVerifiedField.field_code == field_code,
        )
    )
    return res.scalar_one_or_none()


async def ensure_critical_field_placeholders(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    employee_id: Optional[str] = None,
    critical_field_codes: Optional[frozenset[str]] = None,
) -> None:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        return
    emp_id = employee_id or review.employee_id
    codes = critical_field_codes or BASE_CRITICAL_FIELD_CODES
    for code in sorted(codes):
        existing = await _get_row(db, tenant_id, review.id, code)
        if existing:
            continue
        label, downstream = _field_meta(code)
        row = WorkforceHrVerifiedField(
            tenant_id=tenant_id,
            hr_review_id=review.id,
            employee_id=emp_id,
            field_code=code,
            field_label=label,
            downstream_use_json=downstream,
            status=FIELD_STATUS_PENDING,
        )
        db.add(row)
    await db.flush()


def _profile_value_from_snapshot(field_code: str, snap: dict[str, Any]) -> Optional[str]:
    if not isinstance(snap, dict):
        return None
    hr_identity = snap.get("hr_identity") if isinstance(snap.get("hr_identity"), dict) else {}
    personal = snap.get("personal_data") if isinstance(snap.get("personal_data"), dict) else {}
    doc_fields = snap.get("document_field_values") if isinstance(snap.get("document_field_values"), dict) else {}

    def pick(*keys: str) -> Optional[str]:
        for key in keys:
            for src in (hr_identity, personal, doc_fields, snap):
                if not isinstance(src, dict):
                    continue
                val = src.get(key)
                if val not in (None, ""):
                    return _normalize_value(val)
        return None

    mapping: dict[str, tuple[str, ...]] = {
        "full_name": ("legal_name", "full_name"),
        "citizenship": ("citizenship",),
        "work_country": ("work_country",),
        "pesel": ("pesel",),
        "document_expiry": ("passport_expiry", "passport_valid_to", "document_expiry"),
        "permit_type": ("legal_status", "residency_status", "legal_stay_document_type", "permit_type"),
    }
    keys = mapping.get(field_code)
    if not keys:
        return None
    if field_code == "full_name":
        name = pick(*keys)
        if name:
            return name
        parts = [str(snap.get("first_name") or "").strip(), str(snap.get("last_name") or "").strip()]
        joined = " ".join(p for p in parts if p).strip()
        return joined or None
    return pick(*keys)


async def seed_profile_values_from_candidate_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    snapshot: dict[str, Any] | None,
) -> None:
    """PR17: pre-fill verified field profile_values from recruitment handoff snapshot."""
    if review.status in HR_REVIEW_TERMINAL_STATUSES or not isinstance(snapshot, dict):
        return
    res = await db.execute(
        select(WorkforceHrVerifiedField).where(
            WorkforceHrVerifiedField.tenant_id == tenant_id,
            WorkforceHrVerifiedField.hr_review_id == review.id,
        )
    )
    for row in res.scalars().all():
        if str(row.status or "") != FIELD_STATUS_PENDING:
            continue
        existing_profile = dict(row.profile_values_json or {})
        if existing_profile:
            continue
        val = _profile_value_from_snapshot(str(row.field_code), snapshot)
        if not val:
            continue
        row.profile_values_json = {"recruitment": val, "candidate_snapshot": val}
    await db.flush()


async def list_for_review(
    db: AsyncSession,
    tenant_id: str,
    hr_review_id: str,
    *,
    critical_field_codes: Optional[frozenset[str]] = None,
) -> list[dict[str, Any]]:
    res = await db.execute(
        select(WorkforceHrVerifiedField)
        .where(
            WorkforceHrVerifiedField.tenant_id == tenant_id,
            WorkforceHrVerifiedField.hr_review_id == hr_review_id,
        )
        .order_by(WorkforceHrVerifiedField.field_code.asc())
    )
    return [_serialize_row(r, critical_field_codes=critical_field_codes) for r in res.scalars().all()]


def summarize_critical(
    fields: list[dict[str, Any]],
    *,
    critical_field_codes: Optional[frozenset[str]] = None,
) -> dict[str, Any]:
    codes = critical_field_codes or BASE_CRITICAL_FIELD_CODES
    critical = [f for f in fields if str(f.get("field_code") or "") in codes]
    pending = [f for f in critical if str(f.get("status") or "") == FIELD_STATUS_PENDING]
    conflicts = [f for f in critical if str(f.get("status") or "") == FIELD_STATUS_CONFLICT]
    not_ready = [
        f
        for f in critical
        if str(f.get("status") or "") not in FIELD_STATUS_APPROVE_OK
    ]
    blockers: list[str] = []
    for f in conflicts:
        blockers.append(
            f"Verified field conflict: {f.get('field_label') or f.get('field_code')} "
            f"({f.get('conflict_reason') or 'values disagree across documents'})"
        )
    for f in pending:
        blockers.append(
            f"Critical field not verified: {f.get('field_label') or f.get('field_code')} (pending)"
        )
    for f in not_ready:
        st = str(f.get("status") or "")
        if st in (FIELD_STATUS_PENDING, FIELD_STATUS_CONFLICT):
            continue
        blockers.append(
            f"Critical field not ready: {f.get('field_label') or f.get('field_code')} ({st})"
        )
    ready = len(critical) >= len(codes) and len(not_ready) == 0
    if not critical:
        blockers.append("Critical verified fields not initialized")
    return {
        "ready": ready,
        "critical_total": len(critical),
        "critical_verified": sum(
            1 for f in critical if str(f.get("status") or "") in FIELD_STATUS_APPROVE_OK
        ),
        "pending_codes": [str(f["field_code"]) for f in pending],
        "conflict_codes": [str(f["field_code"]) for f in conflicts],
        "blockers": blockers,
    }


def critical_fields_block_approval(fields: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    summary = summarize_critical(fields)
    if summary["critical_total"] == 0:
        return False, []
    return not summary["ready"], list(summary["blockers"])


async def _audit_field(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_user_id: str,
    review: WorkforceHrReview,
    field_code: str,
    action: str,
    payload: dict[str, Any],
) -> None:
    await log_activity(
        db,
        tenant_id=tenant_id,
        action=f"workforce.hr_review.verified_field.{action}",
        actor_id=actor_user_id,
        target_type="workforce_hr_review",
        target_id=review.id,
        payload={"field_code": field_code, "employee_id": review.employee_id, **payload},
    )


async def sync_from_document_verification(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    doc_verification: WorkforceHrDocumentVerification,
    actor_user_id: str,
) -> list[WorkforceHrVerifiedField]:
    if doc_verification.verification_status != VERIFICATION_VERIFIED:
        return []
    reviewed = doc_verification.reviewed_fields_json if isinstance(doc_verification.reviewed_fields_json, dict) else {}
    specs = FIELD_SPECS.get(doc_verification.document_key or "", [])
    updated: list[WorkforceHrVerifiedField] = []
    now = _now()

    for spec in specs:
        code = str(spec.get("field_code") or "")
        if not code:
            continue
        entry = reviewed.get(code)
        if not isinstance(entry, dict) or not entry.get("confirmed"):
            continue
        value = _normalize_value(entry.get("value") or entry.get("reviewed_value"))
        if not value:
            continue

        label, downstream = _field_meta(code, spec)
        row = await _get_row(db, tenant_id, review.id, code)
        if not row:
            row = WorkforceHrVerifiedField(
                tenant_id=tenant_id,
                hr_review_id=review.id,
                employee_id=review.employee_id,
                field_code=code,
                field_label=label,
                downstream_use_json=downstream,
                status=FIELD_STATUS_PENDING,
            )
            db.add(row)

        profile_vals = entry.get("current_profile_values")
        if isinstance(profile_vals, dict):
            row.profile_values_json = profile_vals

        existing_value = _normalize_value(row.verified_value)
        if row.status in FIELD_STATUS_APPROVE_OK and existing_value and existing_value != value:
            row.status = FIELD_STATUS_CONFLICT
            row.conflict_reason = (
                f"Document '{doc_verification.document_key}' proposes '{value}' "
                f"but verified value is '{existing_value}'"
            )
            await db.flush()
            await _audit_field(
                db,
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                review=review,
                field_code=code,
                action="conflict",
                payload={
                    "proposed_value": value,
                    "verified_value": existing_value,
                    "source_document_key": doc_verification.document_key,
                },
            )
            updated.append(row)
            continue

        if row.status == FIELD_STATUS_OVERRIDDEN:
            continue

        row.field_label = label
        row.downstream_use_json = downstream
        row.status = FIELD_STATUS_VERIFIED
        row.verified_value = value
        row.document_verification_id = doc_verification.id
        row.source_document_id = doc_verification.document_id
        row.source_document_key = doc_verification.document_key
        row.verified_by_user_id = actor_user_id
        row.verified_at = now
        row.conflict_reason = None
        row.override_reason = None
        await db.flush()
        await _audit_field(
            db,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            review=review,
            field_code=code,
            action="verified",
            payload={
                "verified_value": value,
                "source_document_key": doc_verification.document_key,
                "document_verification_id": doc_verification.id,
            },
        )
        updated.append(row)

    await ensure_critical_field_placeholders(
        db, tenant_id=tenant_id, review=review, employee_id=review.employee_id
    )
    return updated


async def override_verified_field(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    field_code: str,
    actor_user_id: str,
    verified_value: str,
    override_reason: str,
) -> WorkforceHrVerifiedField:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    code = str(field_code or "").strip()
    if not code:
        raise ValueError("INVALID_FIELD_CODE")
    value = _normalize_value(verified_value)
    reason = _normalize_value(override_reason)
    if not value:
        raise ValueError("VERIFIED_VALUE_REQUIRED")
    if not reason:
        raise ValueError("OVERRIDE_REASON_REQUIRED")

    label, downstream = _field_meta(code)
    row = await _get_row(db, tenant_id, review.id, code)
    if not row:
        row = WorkforceHrVerifiedField(
            tenant_id=tenant_id,
            hr_review_id=review.id,
            employee_id=review.employee_id,
            field_code=code,
            field_label=label,
            downstream_use_json=downstream,
        )
        db.add(row)

    row.field_label = label
    row.downstream_use_json = downstream or row.downstream_use_json
    row.status = FIELD_STATUS_OVERRIDDEN
    row.verified_value = value
    row.verified_by_user_id = actor_user_id
    row.verified_at = _now()
    row.override_reason = reason
    row.conflict_reason = None
    await db.flush()
    await _audit_field(
        db,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        review=review,
        field_code=code,
        action="override",
        payload={"verified_value": value, "override_reason": reason[:500]},
    )
    return row


async def assert_critical_fields_for_approve(
    db: AsyncSession, tenant_id: str, review: WorkforceHrReview
) -> None:
    fields = await list_for_review(db, tenant_id, review.id)
    blocked, blockers = critical_fields_block_approval(fields)
    if blocked:
        raise ValueError("CRITICAL_VERIFIED_FIELDS_INCOMPLETE")
    conflicts = [f for f in fields if str(f.get("status") or "") == FIELD_STATUS_CONFLICT]
    if conflicts:
        raise ValueError("CRITICAL_VERIFIED_FIELDS_CONFLICT")
