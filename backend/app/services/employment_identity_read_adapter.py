"""Trusted read adapter for canonical employment identity (PR6).

Downstream automation must use this module instead of candidate snapshot,
employee profile, reviewed_fields_json, or document meta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_hr_review import WorkforceHrReview
from backend.app.services import hr_verified_fields as vf_svc
from backend.app.services.employment_identity_projection import (
    PROJECTION_STATUS_COMPLETE,
    PROJECTION_STATUS_CONFLICTED,
    PROJECTION_STATUS_INCOMPLETE,
    PROJECTION_STATUS_STALE,
    build_employment_identity_projection,
)

# v1 consumers
CONSUMER_CONTRACT_GENERATION = "contract_generation"
CONSUMER_ZUS_PREPARATION = "zus_preparation"
CONSUMER_PAYROLL_PREP = "payroll_prep"
CONSUMER_PERMIT_APPLICATION = "permit_application"
CONSUMER_EXPORT = "export"
CONSUMER_CLIENT_FORM = "client_form"
CONSUMER_HR_REVIEW_DISPLAY = "hr_review_display"

ALL_CONSUMERS: frozenset[str] = frozenset(
    {
        CONSUMER_CONTRACT_GENERATION,
        CONSUMER_ZUS_PREPARATION,
        CONSUMER_PAYROLL_PREP,
        CONSUMER_PERMIT_APPLICATION,
        CONSUMER_EXPORT,
        CONSUMER_CLIENT_FORM,
        CONSUMER_HR_REVIEW_DISPLAY,
    }
)

# stale blocks automation consumers; export/client_form may read stale identity for review
_STALE_STRICT_CONSUMERS: frozenset[str] = frozenset(
    {
        CONSUMER_CONTRACT_GENERATION,
        CONSUMER_ZUS_PREPARATION,
        CONSUMER_PAYROLL_PREP,
        CONSUMER_PERMIT_APPLICATION,
    }
)

_STALE_LENIENT_CONSUMERS: frozenset[str] = frozenset(
    {
        CONSUMER_EXPORT,
        CONSUMER_CLIENT_FORM,
        CONSUMER_HR_REVIEW_DISPLAY,
    }
)


class TrustedIdentityAccessError(Exception):
    """Raised when a consumer may not read identity for side-effect/automation use."""

    def __init__(
        self,
        *,
        code: str,
        consumer: str,
        projection_status: str,
        message: str,
        review_id: str,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.consumer = consumer
        self.projection_status = projection_status
        self.review_id = review_id
        self.details = details or {}
        super().__init__(message)


@dataclass(frozen=True)
class TrustedEmploymentIdentityRead:
    tenant_id: str
    review_id: str
    employee_id: Optional[str]
    handoff_id: Optional[str]
    consumer: str
    projection: dict[str, Any]
    attributes: dict[str, Optional[str]]
    projection_status: str
    access_allowed: bool
    denial_code: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "review_id": self.review_id,
            "employee_id": self.employee_id,
            "handoff_id": self.handoff_id,
            "consumer": self.consumer,
            "projection": self.projection,
            "attributes": self.attributes,
            "projection_status": self.projection_status,
            "access_allowed": self.access_allowed,
            "denial_code": self.denial_code,
        }


def _normalize_consumer(consumer: str) -> str:
    c = str(consumer or "").strip().lower()
    if c not in ALL_CONSUMERS:
        raise ValueError("INVALID_IDENTITY_CONSUMER")
    return c


def evaluate_consumer_access(consumer: str, projection_status: str) -> tuple[bool, Optional[str]]:
    """Return (allowed, denial_code). Display consumer never denied for read."""
    c = _normalize_consumer(consumer)
    st = str(projection_status or "").strip().lower()

    if c == CONSUMER_HR_REVIEW_DISPLAY:
        return True, None

    if st == PROJECTION_STATUS_COMPLETE:
        return True, None

    if st == PROJECTION_STATUS_STALE:
        if c in _STALE_LENIENT_CONSUMERS:
            return True, None
        if c in _STALE_STRICT_CONSUMERS:
            return False, "TRUSTED_IDENTITY_STALE"
        return False, "TRUSTED_IDENTITY_STALE"

    if st == PROJECTION_STATUS_CONFLICTED:
        return False, "TRUSTED_IDENTITY_CONFLICTED"

    if st == PROJECTION_STATUS_INCOMPLETE:
        return False, "TRUSTED_IDENTITY_INCOMPLETE"

    return False, "TRUSTED_IDENTITY_UNKNOWN_STATUS"


async def _load_review(
    db: AsyncSession, tenant_id: str, review_id: str
) -> WorkforceHrReview:
    tid = str(tenant_id).strip()
    rid = str(review_id).strip()
    row = (
        await db.execute(
            select(WorkforceHrReview).where(
                WorkforceHrReview.tenant_id == tid,
                WorkforceHrReview.id == rid,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise ValueError("HR_REVIEW_NOT_FOUND")
    return row


async def load_employment_identity_projection(
    db: AsyncSession,
    *,
    tenant_id: str,
    review_id: str,
) -> dict[str, Any]:
    """Build projection from verified fields SoT (no consumer guard, no profile/snapshot)."""
    review = await _load_review(db, tenant_id, review_id)
    await vf_svc.ensure_critical_field_placeholders(
        db, tenant_id=tenant_id, review=review, employee_id=review.employee_id
    )
    fields = await vf_svc.list_for_review(db, tenant_id, review.id)
    return build_employment_identity_projection(fields)


async def get_trusted_employment_identity(
    db: AsyncSession,
    *,
    tenant_id: str,
    review_id: str,
    consumer: str,
    raise_on_denied: bool = True,
) -> TrustedEmploymentIdentityRead:
    """Single entry for downstream trusted identity reads.

    - ``hr_review_display``: always returns projection (incomplete/conflicted visible in UI).
    - Automation consumers: raise ``TrustedIdentityAccessError`` when access denied
      (unless ``raise_on_denied=False``).
    """
    c = _normalize_consumer(consumer)
    review = await _load_review(db, tenant_id, review_id)
    await vf_svc.ensure_critical_field_placeholders(
        db, tenant_id=tenant_id, review=review, employee_id=review.employee_id
    )
    fields = await vf_svc.list_for_review(db, tenant_id, review.id)
    projection = build_employment_identity_projection(fields)
    status = str(projection.get("status") or "")
    allowed, denial_code = evaluate_consumer_access(c, status)

    if not allowed and raise_on_denied and c != CONSUMER_HR_REVIEW_DISPLAY:
        raise TrustedIdentityAccessError(
            code=str(denial_code or "TRUSTED_IDENTITY_DENIED"),
            consumer=c,
            projection_status=status,
            review_id=review_id,
            message=f"Trusted employment identity not available for consumer '{c}' (status={status})",
            details={
                "missing_required": projection.get("missing_required") or [],
                "conflicts": projection.get("conflicts") or [],
            },
        )

    attrs = dict(projection.get("attributes") or {})
    return TrustedEmploymentIdentityRead(
        tenant_id=str(tenant_id),
        review_id=str(review_id),
        employee_id=review.employee_id,
        handoff_id=review.handoff_id,
        consumer=c,
        projection=projection,
        attributes=attrs,
        projection_status=status,
        access_allowed=allowed,
        denial_code=denial_code,
    )


async def get_trusted_employment_identity_for_employee(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    consumer: str,
    raise_on_denied: bool = True,
) -> TrustedEmploymentIdentityRead:
    """Resolve active HR review for employee, then delegate to ``get_trusted_employment_identity``."""
    from backend.app.services import workforce_employees as we_svc
    from backend.app.services.workforce_hr_review import ensure_hr_review_for_employee

    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise ValueError("EMPLOYEE_NOT_FOUND")
    # Avoid re-entering _sync_review_from_sources → journey → evaluate_permit → here (RecursionError).
    review = await ensure_hr_review_for_employee(db, tenant_id, emp, sync_from_sources=False)
    return await get_trusted_employment_identity(
        db,
        tenant_id=tenant_id,
        review_id=review.id,
        consumer=consumer,
        raise_on_denied=raise_on_denied,
    )
