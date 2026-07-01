from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_lifecycle_event import WorkforceLifecycleEvent

log = logging.getLogger(__name__)

LEDGER_EVENT_CODES: tuple[str, ...] = (
    "employee_hired",
    "probation_passed",
    "permit_requested",
    "permit_approved",
    "contract_issued",
    "contract_signed",
    "contract_renewed",
    "contract_expiring",
    "contract_terminated",
    "medical_expired",
    "vehicle_assigned",
    "vacation_approved",
    "insurance_changed",
    "employee_terminated",
)

LEDGER_CATEGORIES: tuple[str, ...] = ("employment", "legal", "compliance", "fleet", "leave", "payroll")
LEDGER_STATUSES: tuple[str, ...] = ("open", "done", "cancelled")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _s(x: Any) -> str:
    return str(x or "").strip()


async def _has_column(db: AsyncSession, table_name: str, column_name: str) -> bool:
    q = text(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table_name
          AND column_name = :column_name
        LIMIT 1
        """
    )
    row = await db.execute(q, {"table_name": table_name, "column_name": column_name})
    return row.scalar_one_or_none() is not None


async def list_events(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    category: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    occurred_from: date | None = None,
    occurred_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[WorkforceLifecycleEvent]:
    stmt = select(WorkforceLifecycleEvent).where(
        WorkforceLifecycleEvent.tenant_id == _s(tenant_id),
        WorkforceLifecycleEvent.employee_id == _s(employee_id),
    )
    if _s(category):
        stmt = stmt.where(WorkforceLifecycleEvent.category == _s(category))
    if _s(status):
        stmt = stmt.where(WorkforceLifecycleEvent.status == _s(status))
    if _s(owner):
        stmt = stmt.where(WorkforceLifecycleEvent.owner == _s(owner))
    if occurred_from:
        stmt = stmt.where(WorkforceLifecycleEvent.occurred_at >= datetime.combine(occurred_from, datetime.min.time(), tzinfo=timezone.utc))
    if occurred_to:
        stmt = stmt.where(WorkforceLifecycleEvent.occurred_at <= datetime.combine(occurred_to, datetime.max.time(), tzinfo=timezone.utc))
    stmt = stmt.order_by(WorkforceLifecycleEvent.occurred_at.desc(), WorkforceLifecycleEvent.created_at.desc())
    stmt = stmt.offset(max(offset, 0)).limit(min(max(limit, 1), 500))
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def create_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    event_code: str,
    category: str,
    title: str,
    occurred_at: datetime | None = None,
    effective_date: date | None = None,
    due_date: date | None = None,
    owner: str | None = None,
    created_by: str | None = None,
    status: str | None = None,
    dedupe_key: str | None = None,
    source_type: str | None = None,
    source_ref: str | None = None,
    description: str | None = None,
    references: dict[str, Any] | None = None,
    attachments: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> WorkforceLifecycleEvent:
    ecode = _s(event_code)
    cat = _s(category)
    st = _s(status) or "open"
    dkey = _s(dedupe_key)[:160] or None
    if ecode not in LEDGER_EVENT_CODES:
        raise ValueError("LEDGER_EVENT_CODE_INVALID")
    if cat not in LEDGER_CATEGORIES:
        raise ValueError("LEDGER_CATEGORY_INVALID")
    if st not in LEDGER_STATUSES:
        raise ValueError("LEDGER_STATUS_INVALID")
    has_dedupe_key = await _has_column(db, "workforce_lifecycle_events", "dedupe_key")
    has_created_by = await _has_column(db, "workforce_lifecycle_events", "created_by")
    if not has_dedupe_key:
        log.warning(
            "workforce_lifecycle_events schema is incomplete (missing dedupe_key); skipping ledger write",
            extra={"tenant_id": _s(tenant_id), "employee_id": _s(employee_id), "event_code": ecode},
        )
        return WorkforceLifecycleEvent(
            id=str(uuid4()),
            tenant_id=_s(tenant_id),
            employee_id=_s(employee_id),
            event_code=ecode,
            category=cat,
            occurred_at=occurred_at or _now(),
            title=_s(title)[:256],
            status=st,
        )
    if dkey and has_created_by:
        existing = (
            await db.execute(
                select(WorkforceLifecycleEvent).where(
                    WorkforceLifecycleEvent.tenant_id == _s(tenant_id),
                    WorkforceLifecycleEvent.employee_id == _s(employee_id),
                    WorkforceLifecycleEvent.dedupe_key == dkey,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
    if dkey and not has_created_by:
        existing_id = (
            await db.execute(
                text(
                    """
                    SELECT id
                    FROM workforce_lifecycle_events
                    WHERE tenant_id = :tenant_id
                      AND employee_id = :employee_id
                      AND dedupe_key = :dedupe_key
                    LIMIT 1
                    """
                ),
                {
                    "tenant_id": _s(tenant_id),
                    "employee_id": _s(employee_id),
                    "dedupe_key": dkey,
                },
            )
        ).scalar_one_or_none()
        if existing_id is not None:
            return WorkforceLifecycleEvent(
                id=str(existing_id),
                tenant_id=_s(tenant_id),
                employee_id=_s(employee_id),
                event_code=ecode,
                category=cat,
                occurred_at=occurred_at or _now(),
                title=_s(title)[:256],
                status=st,
            )
    if not has_created_by:
        eid = str(uuid4())
        await db.execute(
            text(
                """
                INSERT INTO workforce_lifecycle_events (
                    id, tenant_id, employee_id, event_code, category,
                    occurred_at, effective_date, due_date, owner,
                    status, dedupe_key, source_type, source_ref,
                    title, description, references_json, attachments_json, meta
                ) VALUES (
                    :id, :tenant_id, :employee_id, :event_code, :category,
                    :occurred_at, :effective_date, :due_date, :owner,
                    :status, :dedupe_key, :source_type, :source_ref,
                    :title, :description, :references_json, :attachments_json, :meta
                )
                """
            ),
            {
                "id": eid,
                "tenant_id": _s(tenant_id),
                "employee_id": _s(employee_id),
                "event_code": ecode,
                "category": cat,
                "occurred_at": occurred_at or _now(),
                "effective_date": effective_date,
                "due_date": due_date,
                "owner": _s(owner)[:64] or None,
                "status": st,
                "dedupe_key": dkey,
                "source_type": _s(source_type)[:64] or None,
                "source_ref": _s(source_ref)[:96] or None,
                "title": _s(title)[:256],
                "description": (_s(description)[:2000] or None),
                "references_json": references if isinstance(references, dict) else {},
                "attachments_json": attachments if isinstance(attachments, dict) else {},
                "meta": meta if isinstance(meta, dict) else {},
            },
        )
        return WorkforceLifecycleEvent(
            id=eid,
            tenant_id=_s(tenant_id),
            employee_id=_s(employee_id),
            event_code=ecode,
            category=cat,
            occurred_at=occurred_at or _now(),
            effective_date=effective_date,
            due_date=due_date,
            owner=_s(owner)[:64] or None,
            status=st,
            dedupe_key=dkey,
            source_type=_s(source_type)[:64] or None,
            source_ref=_s(source_ref)[:96] or None,
            title=_s(title)[:256],
            description=(_s(description)[:2000] or None),
            references_json=references if isinstance(references, dict) else {},
            attachments_json=attachments if isinstance(attachments, dict) else {},
            meta=meta if isinstance(meta, dict) else {},
        )

    row = WorkforceLifecycleEvent(
        tenant_id=_s(tenant_id),
        employee_id=_s(employee_id),
        event_code=ecode,
        category=cat,
        title=_s(title)[:256],
        occurred_at=occurred_at or _now(),
        effective_date=effective_date,
        due_date=due_date,
        owner=_s(owner)[:64] or None,
        created_by=_s(created_by)[:36] or None,
        status=st,
        dedupe_key=dkey,
        source_type=_s(source_type)[:64] or None,
        source_ref=_s(source_ref)[:96] or None,
        description=(_s(description)[:2000] or None),
        references_json=references if isinstance(references, dict) else {},
        attachments_json=attachments if isinstance(attachments, dict) else {},
        meta=meta if isinstance(meta, dict) else {},
    )
    db.add(row)
    await db.flush()
    return row


async def patch_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    event_id: str,
    patch: dict[str, Any],
) -> WorkforceLifecycleEvent | None:
    row = (
        await db.execute(
            select(WorkforceLifecycleEvent).where(
                WorkforceLifecycleEvent.id == _s(event_id),
                WorkforceLifecycleEvent.tenant_id == _s(tenant_id),
                WorkforceLifecycleEvent.employee_id == _s(employee_id),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    if "status" in patch and _s(patch.get("status")) in LEDGER_STATUSES:
        row.status = _s(patch.get("status"))
    if "owner" in patch:
        row.owner = _s(patch.get("owner"))[:64] or None
    if "due_date" in patch:
        row.due_date = patch.get("due_date") if isinstance(patch.get("due_date"), date) or patch.get("due_date") is None else row.due_date
    if "description" in patch:
        row.description = _s(patch.get("description"))[:2000] or None
    if "references" in patch and isinstance(patch.get("references"), dict):
        row.references_json = patch.get("references") or {}
    await db.flush()
    return row
