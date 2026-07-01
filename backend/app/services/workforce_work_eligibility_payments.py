"""Work eligibility fee rows + onboarding checklist tasks (foreign driver)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_onboarding_task import WorkforceOnboardingTask
from backend.app.models.workforce_work_eligibility_payment_requirement import (
    WorkforceWorkEligibilityPaymentRequirement,
)
from backend.app.services.workforce_work_eligibility_rules import (
    REQUIREMENT_RED_PAPER_FEE,
    REQUIREMENT_WORK_PERMIT_FEE,
    foreign_driver_fee_rows_expected,
)

_NOW = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(_NOW)


async def list_payment_requirements(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> list[WorkforceWorkEligibilityPaymentRequirement]:
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    rows = (
        (
            await db.execute(
                select(WorkforceWorkEligibilityPaymentRequirement)
                .where(
                    WorkforceWorkEligibilityPaymentRequirement.tenant_id == tid,
                    WorkforceWorkEligibilityPaymentRequirement.employee_id == eid,
                )
                .order_by(WorkforceWorkEligibilityPaymentRequirement.requirement_type.asc())
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def ensure_foreign_driver_payment_requirements(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    wel: Any,
) -> None:
    """Upsert default fee rows when third-country driver profile applies."""
    if not foreign_driver_fee_rows_expected(wel):
        return
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    existing = {r.requirement_type: r for r in await list_payment_requirements(db, tid, eid)}

    def _upsert(
        req_type: str,
        *,
        blocks_step: str,
        default_status: str,
    ) -> None:
        row = existing.get(req_type)
        if row:
            if not (row.blocks_step or "").strip():
                row.blocks_step = blocks_step
            return
        db.add(
            WorkforceWorkEligibilityPaymentRequirement(
                tenant_id=tid,
                employee_id=eid,
                requirement_type=req_type,
                amount=None,
                currency="PLN",
                payment_status=default_status,
                blocks_step=blocks_step,
            )
        )

    _upsert(
        REQUIREMENT_WORK_PERMIT_FEE,
        blocks_step="work_permit_application",
        default_status="required",
    )
    red_required = "required" if (wel.red_paper_required is not False) else "not_required"
    _upsert(
        REQUIREMENT_RED_PAPER_FEE,
        blocks_step="red_paper_order",
        default_status=red_required,
    )
    await db.flush()


_FEE_ONBOARDING: tuple[tuple[str, str, int], ...] = (
    ("pay_work_permit_fee", "Pay work permit fee (stamp duty / tłumaczenia)", 100),
    ("upload_work_permit_fee_confirmation", "Upload work permit fee payment confirmation", 101),
    ("pay_red_paper_fee", "Pay red paper (Zaświadczenie o niekaralności) fee", 102),
    ("upload_red_paper_fee_confirmation", "Upload red paper fee payment confirmation", 103),
)


async def ensure_fee_onboarding_tasks(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> None:
    """Idempotent HR checklist rows keyed by meta.task_kind."""
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    rows = (
        (
            await db.execute(
                select(WorkforceOnboardingTask).where(
                    WorkforceOnboardingTask.tenant_id == tid,
                    WorkforceOnboardingTask.employee_id == eid,
                )
            )
        )
        .scalars()
        .all()
    )
    existing_kinds: set[str] = set()
    for t in rows:
        meta = t.meta if isinstance(t.meta, dict) else {}
        k = str(meta.get("task_kind") or "").strip()
        if k:
            existing_kinds.add(k)

    for kind, title, sort_order in _FEE_ONBOARDING:
        if kind in existing_kinds:
            continue
        db.add(
            WorkforceOnboardingTask(
                tenant_id=tid,
                employee_id=eid,
                title=title,
                sort_order=sort_order,
                status="open",
                meta={"source": "work_eligibility_fee", "task_kind": kind},
            )
        )
    await db.flush()


_PATCH_KEYS = frozenset(
    {
        "amount",
        "currency",
        "payment_status",
        "due_at",
        "paid_at",
        "payment_reference",
        "receipt_document_id",
    }
)


async def patch_payment_requirement(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    requirement_id: str,
    patch: dict[str, Any],
) -> Optional[WorkforceWorkEligibilityPaymentRequirement]:
    tid, eid, rid = str(tenant_id).strip(), str(employee_id).strip(), str(requirement_id).strip()
    row = (
        await db.execute(
            select(WorkforceWorkEligibilityPaymentRequirement).where(
                WorkforceWorkEligibilityPaymentRequirement.id == rid,
                WorkforceWorkEligibilityPaymentRequirement.tenant_id == tid,
                WorkforceWorkEligibilityPaymentRequirement.employee_id == eid,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    for k, v in patch.items():
        if k not in _PATCH_KEYS:
            continue
        if k == "amount":
            if v is None:
                row.amount = None
            elif isinstance(v, (int, float, Decimal)):
                row.amount = Decimal(str(v))
            elif isinstance(v, str) and v.strip():
                row.amount = Decimal(v.strip())
            else:
                row.amount = None
            continue
        if k == "due_at":
            row.due_at = v if isinstance(v, date) else None
            continue
        if k == "paid_at":
            if isinstance(v, datetime):
                row.paid_at = v
            elif isinstance(v, str) and v.strip():
                row.paid_at = datetime.fromisoformat(v.replace("Z", "+00:00"))
            else:
                row.paid_at = None
            continue
        setattr(row, k, v)

    st = (row.payment_status or "").strip().lower()
    if st == "paid" and row.paid_at is None:
        row.paid_at = _utcnow()

    row.updated_at = _utcnow()
    await db.flush()
    return row


async def count_payment_requirements_for_employee(db: AsyncSession, tenant_id: str, employee_id: str) -> int:
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    n = (
        await db.execute(
            select(func.count())
            .select_from(WorkforceWorkEligibilityPaymentRequirement)
            .where(
                WorkforceWorkEligibilityPaymentRequirement.tenant_id == tid,
                WorkforceWorkEligibilityPaymentRequirement.employee_id == eid,
            )
        )
    ).scalar_one()
    return int(n or 0)
