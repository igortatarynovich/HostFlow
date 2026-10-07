"""Employment physical start — frozen contract (ESO-5).

Policy id: ``employment_started.v1``.

Employee created ≠ Started. Formalize complete ≠ Started.
Started is an explicit, audit-able, idempotent confirm of first day at
work (start date + employment context). Known date/context are reused.

LLM-OFF for start decisions.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Final, Mapping

from backend.app.reference.employment_accept_policy import (
    PACKAGE_AUTHORITATIVE_FIELD_CODES,
    assert_employment_missing_reuses_package,
)
from backend.app.reference.employment_formalize import (
    DECISION_COMPLETE as FORMALIZE_COMPLETE,
    evaluate_employment_formalize_v1,
)
from backend.app.reference.ready_for_employment import ACCEPTANCE_GATE_IDS

POLICY_ID: Final[str] = "employment_started.v1"

OPERATOR_QUESTION: Final[str] = (
    "given a handoff that may already have an employee (or ready_to_create_employee), "
    "plus employment context, has this person actually started work — and if confirming, "
    "with which start date + employment context — without treating employee create or "
    "formalization complete as started?"
)

DECISION_STARTED: Final[str] = "started"
DECISION_ALREADY_STARTED: Final[str] = "already_started"
DECISION_NOT_STARTED: Final[str] = "not_started"
DECISION_BLOCKED: Final[str] = "blocked"
DECISION_REJECTED_CONFIRM: Final[str] = "rejected_confirm"

DECISION_VALUES: Final[tuple[str, ...]] = (
    DECISION_STARTED,
    DECISION_ALREADY_STARTED,
    DECISION_NOT_STARTED,
    DECISION_BLOCKED,
    DECISION_REJECTED_CONFIRM,
)

ACTION_CONFIRM: Final[str] = "confirm_physical_start"
FACT_START_DATE: Final[str] = "start_date"
FACT_EMPLOYMENT_CONTEXT: Final[str] = "employment_context"

AUDIT_EVENT_PHYSICAL_START: Final[str] = "employee_physical_start"
PHYSICAL_START_META_KEY: Final[str] = "physical_start_v1"

ARCH_REL: Final[str] = "docs/specs/architecture/employment-started.md"
ESO_BRIEF_REL: Final[str] = "docs/specs/tasks/employment-spine-orchestrator-v1.md"
FORMALIZE_ARCH_REL: Final[str] = "docs/specs/architecture/employment-formalize.md"
EVALUATE_API: Final[str] = "evaluate_employment_started_v1"
APPLY_API: Final[str] = "apply_employment_started_v1"
RUNTIME_API: Final[str] = "confirm_employment_started_for_handoff"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm_code(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _iso_date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return None


def _context_from_package(package: Mapping[str, Any] | None) -> dict[str, Any]:
    target = _record((_record(package)).get("target_work"))
    return {
        "employment_country": _text(
            target.get("employment_country") or target.get("country")
        ),
        "employer_id": _text(target.get("employer_id")),
        "vacancy_id": _text(target.get("vacancy_id")),
        "position_category": _text(target.get("position_category")),
    }


def _start_date_from_package(package: Mapping[str, Any] | None) -> str | None:
    target = _record((_record(package)).get("target_work"))
    return (
        _iso_date(target.get("start_date"))
        or _iso_date(target.get("planned_start_date"))
        or _iso_date(target.get("first_work_date"))
    )


def merge_employment_context_v1(
    *,
    package: Mapping[str, Any] | None,
    employment_context: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reuse package target_work; overlay provided context (known facts win last)."""
    merged = _context_from_package(package)
    for src in (employment_context, extra):
        row = _record(src)
        for key in ("employment_country", "employer_id", "vacancy_id", "position_category"):
            val = _text(row.get(key) or (row.get("country") if key == "employment_country" else ""))
            if val:
                merged[key] = val
    return {k: v for k, v in merged.items() if v}


def employment_context_is_complete_v1(context: Mapping[str, Any] | None) -> bool:
    ctx = _record(context)
    country = _text(ctx.get("employment_country"))
    employer = _text(ctx.get("employer_id"))
    vacancy = _text(ctx.get("vacancy_id"))
    return bool(country) and bool(employer or vacancy)


def _prior_start(value: Any) -> dict[str, Any]:
    row = _record(value)
    nested = _record(row.get(PHYSICAL_START_META_KEY) or row.get("physical_start"))
    src = nested or row
    date = _iso_date(src.get("start_date"))
    ctx = merge_employment_context_v1(
        package=None,
        employment_context=_record(src.get("employment_context")),
    )
    event_id = _text(src.get("event_id") or src.get("audit_event_id"))
    if not date and not ctx and not event_id:
        return {}
    out: dict[str, Any] = {}
    if date:
        out["start_date"] = date
    if ctx:
        out["employment_context"] = ctx
    if event_id:
        out["event_id"] = event_id
    return out


def _confirmation(value: Any) -> dict[str, Any]:
    if value is True:
        return {"confirmed": True}
    if isinstance(value, str) and _norm_code(value) in {ACTION_CONFIRM, "true", "yes", "started"}:
        return {"confirmed": True}
    row = _record(value)
    if not row:
        return {}
    confirmed = row.get("confirmed")
    if confirmed is None:
        confirmed = bool(
            row.get(ACTION_CONFIRM)
            or row.get("confirm_start")
            or row.get("start_date")
            or row.get("employment_context")
        )
    return {
        "confirmed": bool(confirmed),
        "start_date": _iso_date(row.get("start_date")),
        "employment_context": _record(row.get("employment_context")),
    }


def _contexts_match(a: Mapping[str, Any] | None, b: Mapping[str, Any] | None) -> bool:
    left = merge_employment_context_v1(package=None, employment_context=a)
    right = merge_employment_context_v1(package=None, employment_context=b)
    keys = ("employment_country", "employer_id", "vacancy_id")
    for key in keys:
        lv, rv = _text(left.get(key)), _text(right.get(key))
        if lv and rv and lv != rv:
            return False
    return True


def evaluate_employment_started_v1(
    *,
    package: Mapping[str, Any] | None,
    handoff_status: str | None,
    employment_context: Mapping[str, Any] | None = None,
    employee_id: str | None = None,
    ready_to_create_employee: bool | None = None,
    known_start_date: str | None = None,
    prior_start: Mapping[str, Any] | None = None,
    start_confirmation: Mapping[str, Any] | bool | str | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Pure Started evaluation. Does not mint Employee. LLM-OFF."""
    missing_rows = list(employment_missing or [])
    reuse_violations = assert_employment_missing_reuses_package(missing_rows, package=package)

    if ready_to_create_employee is None:
        formalize = evaluate_employment_formalize_v1(
            package=package,
            handoff_status=handoff_status,
            employment_context=employment_context,
            employment_missing=missing_rows,
        )
        ready_create = bool(formalize.get("ready_to_create_employee"))
        formalize_decision = formalize.get("decision")
    else:
        ready_create = bool(ready_to_create_employee)
        formalize_decision = FORMALIZE_COMPLETE if ready_create else None

    employee_exists = bool(_text(employee_id))
    prior = _prior_start(prior_start)
    confirm = _confirmation(start_confirmation)

    ctx = merge_employment_context_v1(
        package=package,
        employment_context=employment_context,
        extra=confirm.get("employment_context") if confirm else None,
    )
    if prior.get("employment_context"):
        # Prior confirmed context is authoritative for display/reuse.
        ctx = merge_employment_context_v1(
            package=None,
            employment_context=prior.get("employment_context"),
            extra=ctx,
        )

    start_date = (
        _iso_date(prior.get("start_date"))
        or _iso_date(confirm.get("start_date"))
        or _iso_date(known_start_date)
        or _iso_date(_record(employment_context).get("start_date"))
        or _start_date_from_package(package)
    )
    context_complete = employment_context_is_complete_v1(ctx)
    already = bool(prior.get("start_date") and (prior.get("event_id") or prior.get("employment_context")))
    # Stored physical-start fact (even without event_id) counts as already started.
    if prior.get("start_date") and prior.get("employment_context"):
        already = True

    blockers: list[dict[str, str]] = []
    if reuse_violations:
        for code in reuse_violations:
            blockers.append(
                {
                    "code": "package_fact_reask",
                    "message": f"must not re-ask package fact {code!r} without conflict_reason",
                }
            )

    if already and confirm.get("confirmed"):
        confirm_date = _iso_date(confirm.get("start_date"))
        confirm_ctx = merge_employment_context_v1(
            package=None, employment_context=confirm.get("employment_context")
        )
        date_conflict = bool(confirm_date and prior.get("start_date") and confirm_date != prior.get("start_date"))
        ctx_conflict = bool(confirm_ctx) and not _contexts_match(
            prior.get("employment_context"), confirm_ctx
        )
        if date_conflict or ctx_conflict:
            blockers.append(
                {
                    "code": "start_fact_conflict",
                    "message": "Existing physical start must not be replaced by a second start",
                }
            )

    can_mint = (not employee_exists) and ready_create
    if not employee_exists and not ready_create:
        blockers.append(
            {
                "code": "employee_not_allowed",
                "message": "Started requires an Employee, or ready_to_create_employee from ESO-4",
            }
        )

    active_missing: list[dict[str, str]] = []
    if not already and not reuse_violations and (employee_exists or ready_create):
        if not start_date:
            active_missing.append(
                {
                    "code": FACT_START_DATE,
                    "kind": "fact",
                    "message": "Physical start date is not yet known",
                }
            )
        if not context_complete:
            active_missing.append(
                {
                    "code": FACT_EMPLOYMENT_CONTEXT,
                    "kind": "fact",
                    "message": "Employment context (country + employer/vacancy) is incomplete",
                }
            )
        if start_date and context_complete and not confirm.get("confirmed"):
            active_missing.append(
                {
                    "code": ACTION_CONFIRM,
                    "kind": "confirmation",
                    "message": "Confirm physical first day (date and context already known)",
                }
            )

    conflict = any(b.get("code") == "start_fact_conflict" for b in blockers)
    if reuse_violations or conflict or (not employee_exists and not ready_create):
        decision = DECISION_BLOCKED
        primary = {
            "code": "resolve_preconditions",
            "kind": "blocker",
            "message": "Resolve Employee allow / existing start conflict",
        }
        started = False
        emitted = False
        replay = False
    elif already:
        decision = DECISION_ALREADY_STARTED
        primary = {
            "code": ACTION_CONFIRM,
            "kind": "idempotent",
            "message": "Physical start already recorded — replay must not emit a second event",
        }
        started = True
        emitted = False
        replay = True
        active_missing = []
    elif confirm.get("confirmed") and start_date and context_complete and (employee_exists or ready_create):
        decision = DECISION_STARTED
        primary = {
            "code": ACTION_CONFIRM,
            "kind": "threshold",
            "message": "Physical start confirmed — spine Employee → Started",
        }
        started = True
        emitted = True
        replay = False
        active_missing = []
    else:
        decision = DECISION_NOT_STARTED
        if active_missing:
            primary = {
                "code": active_missing[0]["code"],
                "kind": active_missing[0].get("kind") or "fact",
                "message": active_missing[0].get("message") or active_missing[0]["code"],
            }
        else:
            primary = {
                "code": ACTION_CONFIRM,
                "kind": "confirmation",
                "message": "Employee may exist — Started still requires explicit confirm",
            }
        started = False
        emitted = False
        replay = False

    mint_employee = can_mint and decision != DECISION_BLOCKED
    employee_created = employee_exists or (
        mint_employee and decision in {DECISION_STARTED, DECISION_ALREADY_STARTED}
    )

    return {
        "policy_id": POLICY_ID,
        "decision": decision,
        "employee_id": _text(employee_id) or None,
        "employee_created": employee_created,
        "mint_employee": mint_employee,
        "ready_to_create_employee": ready_create,
        "started": started,
        "start_date": start_date,
        "employment_context": ctx,
        "active_missing": active_missing,
        "primary_item": primary,
        "start_event_emitted": emitted,
        "idempotent_replay": replay,
        "audit_event_type": AUDIT_EVENT_PHYSICAL_START,
        "formalization_complete_implies_started": False,
        "employee_created_implies_started": False,
        "llm_start": False,
        "blockers": blockers,
        "reuse_violations": reuse_violations,
        "formalize_decision": formalize_decision,
        "acceptance_gate_ids": list(ACCEPTANCE_GATE_IDS),
        "package_authoritative_field_codes": sorted(PACKAGE_AUTHORITATIVE_FIELD_CODES),
    }


def apply_employment_started_v1(
    *,
    package: Mapping[str, Any] | None,
    handoff_status: str | None,
    employment_context: Mapping[str, Any] | None = None,
    employee_id: str | None = None,
    ready_to_create_employee: bool | None = None,
    known_start_date: str | None = None,
    prior_start: Mapping[str, Any] | None = None,
    start_confirmation: Mapping[str, Any] | bool | str | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
    require_confirm_when_not_started: bool = False,
) -> dict[str, Any]:
    """Merge explicit start confirmation → re-evaluate. Idempotent. Does not auto-start."""
    confirm = _confirmation(start_confirmation)
    baseline = evaluate_employment_started_v1(
        package=package,
        handoff_status=handoff_status,
        employment_context=employment_context,
        employee_id=employee_id,
        ready_to_create_employee=ready_to_create_employee,
        known_start_date=known_start_date,
        prior_start=prior_start,
        start_confirmation=None,
        employment_missing=employment_missing,
    )

    if (
        require_confirm_when_not_started
        and baseline.get("decision") == DECISION_NOT_STARTED
        and not confirm.get("confirmed")
        and not baseline.get("started")
    ):
        return {
            **baseline,
            "decision": DECISION_REJECTED_CONFIRM,
            "started": False,
            "start_event_emitted": False,
            "idempotent_replay": False,
            "rejection_reason": "explicit_confirm_required_for_physical_start",
        }

    merged_known_date = _iso_date(confirm.get("start_date")) or known_start_date
    merged_ctx = merge_employment_context_v1(
        package=package,
        employment_context=employment_context,
        extra=confirm.get("employment_context") if confirm else None,
    )

    result = evaluate_employment_started_v1(
        package=package,
        handoff_status=handoff_status,
        employment_context=merged_ctx or employment_context,
        employee_id=employee_id,
        ready_to_create_employee=ready_to_create_employee,
        known_start_date=merged_known_date or known_start_date,
        prior_start=prior_start,
        start_confirmation=confirm if confirm else None,
        employment_missing=employment_missing,
    )
    result["rejection_reason"] = None
    result["package_merged"] = False
    if result.get("decision") == DECISION_STARTED:
        result["start_record"] = {
            PHYSICAL_START_META_KEY: {
                "start_date": result.get("start_date"),
                "employment_context": deepcopy(result.get("employment_context") or {}),
                "event_type": AUDIT_EVENT_PHYSICAL_START,
                "policy_id": POLICY_ID,
            }
        }
    elif result.get("decision") == DECISION_ALREADY_STARTED:
        result["start_record"] = {
            PHYSICAL_START_META_KEY: {
                "start_date": result.get("start_date"),
                "employment_context": deepcopy(result.get("employment_context") or {}),
                "event_type": AUDIT_EVENT_PHYSICAL_START,
                "policy_id": POLICY_ID,
                "event_id": _prior_start(prior_start).get("event_id"),
            }
        }
    else:
        result["start_record"] = None
    return result


__all__ = [
    "POLICY_ID",
    "OPERATOR_QUESTION",
    "DECISION_STARTED",
    "DECISION_ALREADY_STARTED",
    "DECISION_NOT_STARTED",
    "DECISION_BLOCKED",
    "DECISION_REJECTED_CONFIRM",
    "DECISION_VALUES",
    "ACTION_CONFIRM",
    "FACT_START_DATE",
    "FACT_EMPLOYMENT_CONTEXT",
    "AUDIT_EVENT_PHYSICAL_START",
    "PHYSICAL_START_META_KEY",
    "ARCH_REL",
    "ESO_BRIEF_REL",
    "FORMALIZE_ARCH_REL",
    "EVALUATE_API",
    "APPLY_API",
    "RUNTIME_API",
    "merge_employment_context_v1",
    "employment_context_is_complete_v1",
    "evaluate_employment_started_v1",
    "apply_employment_started_v1",
]
