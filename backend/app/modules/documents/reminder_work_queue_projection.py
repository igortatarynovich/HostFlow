from __future__ import annotations

from typing import Any, Literal, Optional

ReminderReason = Literal["expiring_soon", "expired", "missing_expiry", "missing"]
WorkQueueAction = Literal["upload_document", "request_update", "renew_document", "capture_expiry_date"]

_REASON_ACTION: dict[ReminderReason, WorkQueueAction] = {
    "missing": "upload_document",
    "expired": "request_update",
    "expiring_soon": "renew_document",
    "missing_expiry": "capture_expiry_date",
}

_REASON_TITLE: dict[ReminderReason, str] = {
    "missing": "missing",
    "expired": "expired",
    "expiring_soon": "expiring soon",
    "missing_expiry": "expiry date required",
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _humanize_document_code(code: str) -> str:
    raw = _norm(code).replace("_", " ").replace("-", " ")
    if not raw:
        return "Document"
    return " ".join(part.capitalize() for part in raw.split())


def _task_key(*, document_code: str, reason: str, owner_type: str, owner_id: str) -> str:
    return f"document:{document_code}:{reason}:{owner_type}:{owner_id}"


def _title_for(document_code: str, reason: ReminderReason) -> str:
    label = _humanize_document_code(document_code)
    suffix = _REASON_TITLE[reason]
    return f"{label} {suffix}"


def _action_for_reason(reason: ReminderReason) -> WorkQueueAction:
    return _REASON_ACTION[reason]


def resolve_owner_identity(ctx: dict[str, Any]) -> tuple[str, str]:
    """Prefer employee identity when present in owner context."""
    employee_id = _norm(ctx.get("employee_id"))
    candidate_id = _norm(ctx.get("candidate_id"))
    if employee_id:
        return "employee", employee_id
    return "candidate", candidate_id


def project_reminder_work_queue(
    reminder_candidates: list[dict[str, Any]],
    *,
    owner_type: str,
    owner_id: str,
) -> list[dict[str, Any]]:
    """
    Projection-only work queue derived from reminder candidates.

    Does not persist tasks, schedule jobs, or send notifications.
    """
    normalized_owner_type = owner_type if owner_type in {"candidate", "employee"} else "candidate"
    normalized_owner_id = _norm(owner_id)
    if not normalized_owner_id:
        return []

    out: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for row in reminder_candidates:
        if not isinstance(row, dict):
            continue
        document_code = _norm(row.get("document_code"))
        reason_raw = _norm(row.get("reason"))
        if not document_code or reason_raw not in _REASON_ACTION:
            continue
        reason: ReminderReason = reason_raw  # type: ignore[assignment]

        task_key = _task_key(
            document_code=document_code,
            reason=reason,
            owner_type=normalized_owner_type,
            owner_id=normalized_owner_id,
        )
        if task_key in seen_keys:
            continue
        seen_keys.add(task_key)

        out.append(
            {
                "task_key": task_key,
                "title": _title_for(document_code, reason),
                "severity": _norm(row.get("severity")) or "medium",
                "owner_type": normalized_owner_type,
                "owner_id": normalized_owner_id,
                "recipient_role": _norm(row.get("recipient_role")) or "hr",
                "due_date": row.get("due_date"),
                "source_pack": _norm(row.get("source_pack")),
                "action": _action_for_reason(reason),
                "document_code": document_code,
                "reason": reason,
            }
        )

    out.sort(
        key=lambda item: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(str(item.get("severity")), 9),
            str(item.get("due_date") or ""),
            str(item.get("title") or ""),
        )
    )
    return out
