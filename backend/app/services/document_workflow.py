from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Set

from backend.app.models.enums import DocumentProcessType, DocumentStatus


@dataclass(frozen=True)
class WorkflowStepDefinition:
    code: str
    title: str
    default_due_in_days: Optional[int] = None


@dataclass(frozen=True)
class WorkflowDefinition:
    process_type: DocumentProcessType
    steps: Tuple[WorkflowStepDefinition, ...]
    final_status: DocumentStatus


@dataclass(frozen=True)
class WorkflowState:
    total_steps: int
    completed_steps: int
    in_progress_steps: int
    pending_steps: int
    overdue: bool
    has_started: bool
    final_status: DocumentStatus
    current_step: Optional[str] = None
    completed_codes: frozenset[str] = frozenset()


STATUS_ORDER: Dict[DocumentStatus, int] = {
    DocumentStatus.missing: 0,
    DocumentStatus.requested: 1,
    DocumentStatus.in_progress: 2,
    DocumentStatus.submitted: 3,
    DocumentStatus.received: 4,
    DocumentStatus.delivered: 5,
    DocumentStatus.approved: 6,
    DocumentStatus.completed: 7,
    DocumentStatus.overdue: 8,
    DocumentStatus.rejected: 9,
    DocumentStatus.expired: 10,
}

# Statuses that mean "the document exists / is confirmed". They are invalid
# without an uploaded file.
FILE_REQUIRED_STATUSES: Set[DocumentStatus] = {
    DocumentStatus.received,
    DocumentStatus.delivered,
    DocumentStatus.approved,
    DocumentStatus.completed,
    DocumentStatus.verified,
}

FILE_REQUIRED_STATUS_ALIASES = frozenset({"verified"})


def status_requires_uploaded_file(status: DocumentStatus | str | None) -> bool:
    if status is None:
        return False
    if isinstance(status, DocumentStatus):
        return status in FILE_REQUIRED_STATUSES
    raw = str(status).strip().lower()
    if raw in FILE_REQUIRED_STATUS_ALIASES:
        return True
    try:
        return DocumentStatus(raw) in FILE_REQUIRED_STATUSES
    except ValueError:
        return False


NO_FILE_STATUS_ERROR = "Cannot approve or confirm a document without an uploaded file"


def _file_entries(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def document_has_stored_file(doc: Any) -> bool:
    """True when a Hub document (ORM or snapshot dict) has an uploaded file.

    File presence is independent of workflow status: an ``approved`` row without
    a file still counts as missing for operators.
    """
    if doc is None:
        return False
    getter = doc.get if isinstance(doc, dict) else lambda key, default=None: getattr(doc, key, default)
    files = getter("files", None)
    entries = _file_entries(files)
    if entries:
        for entry in entries:
            for key in ("url", "storage_path", "path", "name", "key"):
                value = entry.get(key)
                if value is not None and str(value).strip():
                    return True
        return False
    if isinstance(files, list):
        return False
    if getter("has_files") is True:
        return True
    filename = getter("filename", None)
    path = getter("path", None)
    return bool(str(filename or "").strip() or str(path or "").strip())


WORKFLOW_DEFINITIONS: Dict[DocumentProcessType, WorkflowDefinition] = {
    DocumentProcessType.work_permit: WorkflowDefinition(
        process_type=DocumentProcessType.work_permit,
        steps=(
            WorkflowStepDefinition("ordered", "Заявка оформлена"),
            WorkflowStepDefinition("submitted", "Пакет подан в воеводство", default_due_in_days=14),
            WorkflowStepDefinition("approved", "Решение одобрено"),
            WorkflowStepDefinition("delivered", "Разрешение получено"),
        ),
        final_status=DocumentStatus.approved,
    ),
    DocumentProcessType.visa: WorkflowDefinition(
        process_type=DocumentProcessType.visa,
        steps=(
            WorkflowStepDefinition("applied", "Заявка подана"),
            WorkflowStepDefinition("interview", "Собеседование/биометрия", default_due_in_days=7),
            WorkflowStepDefinition("approved", "Решение принято"),
            WorkflowStepDefinition("received", "Виза получена"),
        ),
        final_status=DocumentStatus.approved,
    ),
    DocumentProcessType.residence_card: WorkflowDefinition(
        process_type=DocumentProcessType.residence_card,
        steps=(
            WorkflowStepDefinition("applied", "Заявка подана"),
            WorkflowStepDefinition("fingerprints", "Отпечатки сданы", default_due_in_days=30),
            WorkflowStepDefinition("approved", "Решение одобрено"),
            WorkflowStepDefinition("received", "Карта получена"),
        ),
        final_status=DocumentStatus.approved,
    ),
    DocumentProcessType.tachograph_card: WorkflowDefinition(
        process_type=DocumentProcessType.tachograph_card,
        steps=(
            WorkflowStepDefinition("applied", "Заявка подана"),
            WorkflowStepDefinition("received", "Карта тахографа получена"),
        ),
        final_status=DocumentStatus.received,
    ),
    DocumentProcessType.driver_license_exchange: WorkflowDefinition(
        process_type=DocumentProcessType.driver_license_exchange,
        steps=(
            WorkflowStepDefinition("submitted", "Документы поданы"),
            WorkflowStepDefinition("approved", "Обмен подтверждён"),
            WorkflowStepDefinition("received", "Новое удостоверение получено"),
        ),
        final_status=DocumentStatus.received,
    ),
    DocumentProcessType.swiadectwo_kierowcy: WorkflowDefinition(
        process_type=DocumentProcessType.swiadectwo_kierowcy,
        steps=(
            WorkflowStepDefinition("ordered", "Świadectwo заказано"),
            WorkflowStepDefinition("issued", "Świadectwo оформлено"),
            WorkflowStepDefinition("delivered", "Świadectwo выдано"),
        ),
        final_status=DocumentStatus.approved,
    ),
}


def promote_status(current: DocumentStatus, target: DocumentStatus) -> DocumentStatus:
    if current in (DocumentStatus.rejected, DocumentStatus.expired):
        return current
    current_rank = STATUS_ORDER.get(current, 0)
    target_rank = STATUS_ORDER.get(target, current_rank)
    return current if current_rank >= target_rank else target


def default_workflow(process_type: DocumentProcessType) -> Optional[Dict[str, Any]]:
    definition = WORKFLOW_DEFINITIONS.get(process_type)
    if not definition:
        return None
    steps = [
        {
            "code": step.code,
            "title": step.title,
            "status": "pending",
            "due_at": _iso_date_from_delta(step.default_due_in_days),
            "completed_at": None,
        }
        for step in definition.steps
    ]
    current_step = steps[0]["code"] if steps else None
    return {
        "process_type": process_type.value,
        "steps": steps,
        "current_step": current_step,
        "completed": False,
    }


def normalize_workflow(
    process_type: DocumentProcessType,
    new_workflow: Optional[Mapping[str, Any]],
    *,
    existing_workflow: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    definition = WORKFLOW_DEFINITIONS.get(process_type)
    if not definition:
        return dict(new_workflow) if isinstance(new_workflow, Mapping) else None

    sources: List[Mapping[str, Any]] = []
    if isinstance(existing_workflow, Mapping):
        sources.append(existing_workflow)
    if isinstance(new_workflow, Mapping):
        sources.append(new_workflow)

    incoming_steps: Dict[str, Dict[str, Any]] = {}
    for source in sources:
        steps = source.get("steps")
        if isinstance(steps, Iterable):
            for raw_step in steps:
                if not isinstance(raw_step, Mapping):
                    continue
                code = str(raw_step.get("code") or "").strip()
                if not code:
                    continue
                data = incoming_steps.setdefault(code, {})
                for key, value in raw_step.items():
                    data[key] = value

    normalized_steps: List[Dict[str, Any]] = []
    current_step_code: Optional[str] = None
    completed_all = True

    for index, step_def in enumerate(definition.steps):
        data = incoming_steps.pop(step_def.code, {})
        completed_at = _normalize_iso_date(data.get("completed_at"))
        due_at = _normalize_iso_date(data.get("due_at"))
        status = str(data.get("status") or "").lower()
        due_in_hours_val: Optional[int] = None
        due_in_hours_raw = data.get("due_in_hours")
        if due_in_hours_raw is not None:
            try:
                due_in_hours_val = int(due_in_hours_raw)
            except (TypeError, ValueError):
                due_in_hours_val = None
        if due_in_hours_val is not None and due_at is None:
            due_at_dt = _iso_datetime_from_hours(due_in_hours_val)
            if due_at_dt is not None:
                due_at = due_at_dt.isoformat()

        if completed_at:
            status = "done"
        else:
            completed_all = False
            normalized = status if status in {"in_progress", "pending"} else None
            if normalized == "in_progress":
                status = "in_progress"
                if current_step_code is None:
                    current_step_code = step_def.code
            elif normalized == "pending":
                status = "pending"
                if current_step_code is None:
                    current_step_code = step_def.code
            else:
                status = "pending"
                if current_step_code is None:
                    current_step_code = step_def.code

        normalized_step = {
            "code": step_def.code,
            "title": data.get("title") or step_def.title,
            "status": status or "pending",
            "due_at": due_at or _iso_date_from_delta(step_def.default_due_in_days),
            "completed_at": completed_at,
        }

        if due_in_hours_val is not None:
            normalized_step["due_in_hours"] = due_in_hours_val
        notes = data.get("notes")
        if notes:
            normalized_step["notes"] = notes
        ordered_at = _normalize_iso_date(data.get("ordered_at"))
        if ordered_at:
            normalized_step["ordered_at"] = ordered_at
        assignee = data.get("assignee")
        if assignee:
            normalized_step["assignee"] = assignee
        actor_id = data.get("actor_id")
        if actor_id:
            normalized_step["actor_id"] = str(actor_id)
        reminder_id = data.get("reminder_id")
        if reminder_id:
            normalized_step["reminder_id"] = str(reminder_id)

        normalized_steps.append(normalized_step)

    for code, leftover in incoming_steps.items():
        # Preserve unknown steps rather than dropping user data
        due_in_hours_val = None
        if leftover.get("due_in_hours") is not None:
            try:
                due_in_hours_val = int(leftover.get("due_in_hours"))
            except (TypeError, ValueError):
                due_in_hours_val = None
        due_at = _normalize_iso_date(leftover.get("due_at"))
        if due_in_hours_val is not None and due_at is None:
            due_at_dt = _iso_datetime_from_hours(due_in_hours_val)
            if due_at_dt:
                due_at = due_at_dt.isoformat()

        extra_fields: Dict[str, Any] = {}
        if due_in_hours_val is not None:
            extra_fields["due_in_hours"] = due_in_hours_val
        ordered_at = _normalize_iso_date(leftover.get("ordered_at"))
        if ordered_at:
            extra_fields["ordered_at"] = ordered_at
        notes = leftover.get("notes")
        if notes:
            extra_fields["notes"] = notes
        actor_id = leftover.get("actor_id")
        if actor_id:
            extra_fields["actor_id"] = str(actor_id)
        reminder_id = leftover.get("reminder_id")
        if reminder_id:
            extra_fields["reminder_id"] = str(reminder_id)
        attachments = leftover.get("attachments")
        if isinstance(attachments, Iterable):
            extra_fields["attachments"] = list(attachments)
        assignee = leftover.get("assignee")
        if assignee:
            extra_fields["assignee"] = assignee

        status_value = str(leftover.get("status") or "").lower()
        if leftover.get("completed_at"):
            status_value = "done"
        elif status_value not in {"pending", "in_progress", "active"}:
            status_value = "pending"
        elif status_value == "active":
            status_value = "in_progress"

        normalized_steps.append(
            {
                "code": code,
                "title": leftover.get("title") or code,
                "status": status_value,
                "due_at": due_at,
                "completed_at": _normalize_iso_date(leftover.get("completed_at")),
                **extra_fields,
            }
        )
        completed_all = False
        if current_step_code is None and str(leftover.get("status") or "").lower() in {"in_progress", "pending"}:
            current_step_code = code

    if not normalized_steps:
        return None

    if current_step_code is None:
        current_step_code = normalized_steps[-1]["code"]

    return {
        "process_type": process_type.value,
        "steps": normalized_steps,
        "current_step": current_step_code,
        "completed": completed_all,
    }


def _status_from_workflow_state(
    process_type: DocumentProcessType,
    state: WorkflowState,
) -> Optional[DocumentStatus]:
    if state.total_steps <= 0:
        return None

    completed_codes = {code.lower() for code in state.completed_codes}

    # Process-specific transitions
    if process_type == DocumentProcessType.work_permit:
        if "delivered" in completed_codes:
            return DocumentStatus.delivered
        if "approved" in completed_codes:
            return DocumentStatus.approved
        if {"ordered", "submitted"}.issubset(completed_codes) or "submitted" in completed_codes:
            return DocumentStatus.submitted
        if "ordered" in completed_codes:
            return DocumentStatus.in_progress

    elif process_type == DocumentProcessType.visa:
        if "received" in completed_codes:
            return DocumentStatus.delivered
        if "approved" in completed_codes:
            return DocumentStatus.approved
        if {"applied", "interview"}.issubset(completed_codes) or "interview" in completed_codes:
            return DocumentStatus.submitted
        if "applied" in completed_codes:
            return DocumentStatus.in_progress

    elif process_type == DocumentProcessType.residence_card:
        if "received" in completed_codes:
            return DocumentStatus.delivered
        if "approved" in completed_codes:
            return DocumentStatus.approved
        if {"applied", "fingerprints"}.issubset(completed_codes) or "fingerprints" in completed_codes:
            return DocumentStatus.submitted
        if "applied" in completed_codes:
            return DocumentStatus.in_progress

    elif process_type == DocumentProcessType.tachograph_card:
        if "received" in completed_codes:
            return DocumentStatus.delivered
        if "applied" in completed_codes:
            return DocumentStatus.in_progress

    elif process_type == DocumentProcessType.driver_license_exchange:
        if "received" in completed_codes:
            return DocumentStatus.delivered
        if "approved" in completed_codes:
            return DocumentStatus.approved
        if "submitted" in completed_codes:
            return DocumentStatus.submitted

    elif process_type == DocumentProcessType.swiadectwo_kierowcy:
        if "delivered" in completed_codes:
            return DocumentStatus.delivered
        if "issued" in completed_codes:
            return DocumentStatus.approved
        if "ordered" in completed_codes:
            return DocumentStatus.in_progress

    elif process_type == DocumentProcessType.other:
        if state.completed_steps >= state.total_steps > 0:
            return DocumentStatus.completed
        if state.has_started or state.completed_steps > 0:
            return DocumentStatus.in_progress
        return DocumentStatus.requested

    # Generic fallbacks
    if state.completed_steps >= state.total_steps > 0:
        # If process-specific mapping already returned (delivered/approved/etc.) we would have exited.
        return DocumentStatus.completed
    if state.completed_steps > 0 or state.has_started:
        return DocumentStatus.in_progress
    return DocumentStatus.requested


def status_from_workflow(
    process_type: DocumentProcessType,
    workflow: Optional[Mapping[str, Any]],
) -> Optional[DocumentStatus]:
    state = evaluate_workflow(process_type, workflow)
    return _status_from_workflow_state(process_type, state)


def auto_status(
    current_status: DocumentStatus,
    *,
    process_type: DocumentProcessType,
    workflow: Optional[Mapping[str, Any]] = None,
    has_files: bool = False,
    expire_date: Optional[date] = None,
) -> DocumentStatus:
    status = current_status
    if isinstance(expire_date, datetime):
        expire_date = expire_date.date()
    if expire_date and expire_date < datetime.now(timezone.utc).date():
        return DocumentStatus.expired
    if has_files:
        status = promote_status(status, DocumentStatus.received)
    wf_state = evaluate_workflow(process_type, workflow)
    if wf_state:
        if wf_state.overdue:
            return DocumentStatus.overdue
        progress_status = _status_from_workflow_state(process_type, wf_state)
        if progress_status:
            status = promote_status(status, progress_status)
    return status


def iter_workflow_step_deadlines(
    workflow: Optional[Mapping[str, Any]],
) -> Iterable[Tuple[str, datetime]]:
    if not workflow:
        return []
    steps = workflow.get("steps")
    if not isinstance(steps, Iterable):
        return []
    results: List[Tuple[str, datetime]] = []
    for entry in steps:
        if not isinstance(entry, Mapping):
            continue
        code = str(entry.get("code") or "").strip()
        if not code:
            continue
        if entry.get("completed_at"):
            continue
        due_at = _parse_datetime(entry.get("due_at"))
        if due_at is None:
            due_in_hours = entry.get("due_in_hours")
            try:
                due_at = _iso_datetime_from_hours(int(due_in_hours))
            except Exception:
                due_at = None
        if due_at is None:
            continue
        results.append((code, due_at))
    return results


def _iso_date_from_delta(days: Optional[int]) -> Optional[str]:
    if days is None:
        return None
    base = datetime.now(timezone.utc).date()
    target = base + timedelta(days=int(days))
    return target.isoformat()


def _iso_datetime_from_hours(hours: Optional[int]) -> Optional[datetime]:
    if hours is None:
        return None
    base = datetime.now(timezone.utc)
    target = base + timedelta(hours=int(hours))
    return target


def _normalize_iso_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            parsed_dt = datetime.fromisoformat(value)
            return parsed_dt.isoformat()
        except ValueError:
            try:
                parsed_date = date.fromisoformat(value[:10])
                return parsed_date.isoformat()
            except ValueError:
                return value
    return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                parsed_date = date.fromisoformat(value[:10])
            except ValueError:
                return None
            return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
    return None


def evaluate_workflow(
    process_type: DocumentProcessType,
    workflow: Optional[Mapping[str, Any]],
) -> WorkflowState:
    definition = WORKFLOW_DEFINITIONS.get(process_type)
    steps_payload = workflow.get("steps") if isinstance(workflow, Mapping) else None
    if not isinstance(steps_payload, Iterable):
        total_defined = len(definition.steps) if definition else 0
        current_step = (
            definition.steps[0].code if definition and definition.steps else None
        )
        return WorkflowState(
            total_steps=total_defined,
            completed_steps=0,
            in_progress_steps=0,
            pending_steps=total_defined,
            overdue=False,
            has_started=False,
            final_status=definition.final_status if definition else DocumentStatus.received,
            current_step=current_step,
            completed_codes=frozenset(),
        )

    now = datetime.now(timezone.utc)
    completed = 0
    in_progress = 0
    pending = 0
    overdue = False
    has_started = False
    completed_codes: Set[str] = set()
    current_step: Optional[str] = None

    for entry in steps_payload:
        if not isinstance(entry, Mapping):
            continue
        code = str(entry.get("code") or "").strip()
        if not code:
            continue
        status_str = str(entry.get("status") or "").lower()
        completed_at = _parse_datetime(entry.get("completed_at"))
        if completed_at:
            completed += 1
            has_started = True
            completed_codes.add(code)
            continue
        if status_str in {"done", "completed"}:
            completed += 1
            has_started = True
            completed_codes.add(code)
            continue
        if status_str in {"in_progress", "active"}:
            in_progress += 1
            has_started = True
            if current_step is None:
                current_step = code
        elif status_str:
            pending += 1
            if current_step is None:
                current_step = code
        else:
            pending += 1
            if current_step is None:
                current_step = code

        due_at = _parse_datetime(entry.get("due_at"))
        if due_at is None:
            due_in_hours = entry.get("due_in_hours")
            try:
                due_at = _iso_datetime_from_hours(int(due_in_hours))
            except Exception:
                due_at = None
        if due_at and due_at < now:
            overdue = True

    total_defined = len(definition.steps) if definition else completed + in_progress + pending
    final_status = definition.final_status if definition else DocumentStatus.received
    return WorkflowState(
        total_steps=total_defined,
        completed_steps=completed,
        in_progress_steps=in_progress,
        pending_steps=pending,
        overdue=overdue,
        has_started=has_started,
        final_status=final_status,
        current_step=current_step,
        completed_codes=frozenset(completed_codes),
    )


__all__ = [
    "WORKFLOW_DEFINITIONS",
    "auto_status",
    "default_workflow",
    "evaluate_workflow",
    "iter_workflow_step_deadlines",
    "normalize_workflow",
    "promote_status",
    "status_from_workflow",
    "WorkflowState",
]
