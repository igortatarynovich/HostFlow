"""HR workforce materialization lock for system/background code paths (no HTTP UserCtx).

HTTP routes use ``ensure_candidate_operational_write_allowed`` (``candidate_operational_write``);
schedulers and similar call sites use ``is_candidate_locked_by_workforce`` so automation does not
move recruitment stage/status while a ``WorkforceEmployee`` row exists for the candidate.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.workforce_employees import find_employee_by_candidate

logger = logging.getLogger(__name__)

# Stable ``source`` values for logs, metrics labels, and audit payload
SKIP_SOURCE_READY_FOR_HANDOFF_GATE = "ready_for_handoff_gate"
SKIP_SOURCE_REMINDER_EXPIRY = "reminder_expiry"
SKIP_SOURCE_CONTACT_ATTEMPT = "contact_attempt"


async def is_candidate_locked_by_workforce(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> bool:
    """True when an active workforce row links this candidate (HR ownership / materialization)."""
    cid = str(candidate_id or "").strip()
    tid = str(tenant_id or "").strip()
    if not cid or not tid:
        return False
    emp = await find_employee_by_candidate(db, tid, cid)
    if emp is None:
        return False
    status = str(getattr(emp, "status", "") or "").strip().lower()
    if status in ("returned_to_recruitment", "returned", "terminated"):
        return False
    return True


async def observe_skipped_system_candidate_mutation_due_to_workforce_lock(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    source: str,
    intended_transition: str,
    workforce_employee_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Structured visibility when automation intentionally skips a recruitment stage/status write."""
    cid = str(candidate_id or "").strip()
    tid = str(tenant_id or "").strip()
    emp_id = (str(workforce_employee_id).strip() if workforce_employee_id else "") or None
    if not emp_id:
        emp = await find_employee_by_candidate(db, tid, cid)
        emp_id = str(emp.id) if emp else None

    payload: dict[str, Any] = {
        "candidate_id": cid,
        "tenant_id": tid,
        "source": str(source or "").strip() or "unknown",
        "intended_transition": str(intended_transition or "").strip() or "unknown",
        "workforce_employee_id": emp_id,
    }
    if extra:
        payload["extra"] = extra

    logger.info(
        "system_automation_skipped_due_to_workforce_lock",
        extra={"event": "system_automation_skipped_due_to_workforce_lock", **payload},
    )

    try:
        from backend.app.observability.metrics import increment_system_automation_workforce_lock_skip

        increment_system_automation_workforce_lock_skip(tid, payload["source"])
    except Exception:
        logger.exception(
            "observe_skipped_system_candidate_mutation: metrics failed candidate_id=%s", cid
        )

    try:
        from backend.app.core.audit_events import AuditEntityType, AuditEventType
        from backend.app.services.audit import log_audit_event

        await log_audit_event(
            db,
            tenant_id=tid,
            event_type=AuditEventType.system_automation_skipped_workforce_lock,
            entity_type=AuditEntityType.candidate,
            entity_id=cid,
            actor_id=None,
            payload=payload,
        )
    except Exception:
        logger.exception(
            "observe_skipped_system_candidate_mutation: audit failed candidate_id=%s", cid
        )
