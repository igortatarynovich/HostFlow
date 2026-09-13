"""Employment start_allowed — frozen contract machine (PEM-1 foundation).

Policy id: ``employment_start_allowed.v1``.

Derived admit-to-work decision from normalized evidence views + allowlisted
typed exceptions. Does not mint Employee. Does not set Started.
Does not own Contract/Medical/BHP persistence.

LLM-OFF.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Final, Mapping, Sequence

POLICY_ID: Final[str] = "employment_start_allowed.v1"

OPERATOR_QUESTION: Final[str] = (
    "given an Employee already created after ESO-4 allow-create, for a PEM-1 "
    "employment context, may this person be admitted to work — i.e. is "
    "start_allowed=true — based only on proven Contract + applicable Medical* + "
    "applicable BHP* (or a policy-listed typed exception), before any human "
    "Confirm physical start?"
)

DECISION_START_ALLOWED: Final[str] = "start_allowed"
DECISION_MISSING: Final[str] = "missing"
DECISION_BLOCKED: Final[str] = "blocked"
DECISION_UNSUPPORTED: Final[str] = "unsupported_context"
DECISION_REJECTED_PATCH: Final[str] = "rejected_patch"

DECISION_VALUES: Final[tuple[str, ...]] = (
    DECISION_START_ALLOWED,
    DECISION_MISSING,
    DECISION_BLOCKED,
    DECISION_UNSUPPORTED,
    DECISION_REJECTED_PATCH,
)

REQ_CONTRACT: Final[str] = "written_employment_contract_or_confirmation"
REQ_MEDICAL: Final[str] = "occupational_medical_fit_for_post"
REQ_BHP: Final[str] = "introductory_bhp_before_admit"

EXCEPTION_BHP_SUCCESSIVE: Final[str] = "bhp_successive_same_employer_same_post"

PEM1_EXCEPTION_ALLOWLIST: Final[dict[str, str]] = {
    EXCEPTION_BHP_SUCCESSIVE: REQ_BHP,
}

FACT_PLANNED_START: Final[str] = "planned_start_date"

CONTEXT_PEM1: Final[str] = "PEM-1"

ARCH_REL: Final[str] = "docs/specs/architecture/employment-start-allowed.md"
ADAPT_REL: Final[str] = "docs/analysis/employment-start-allowed-adaptation-design.md"
FOUNDATION_REL: Final[str] = "docs/specs/tasks/employment-start-allowed-runtime-foundation.md"
EVALUATE_API: Final[str] = "evaluate_employment_start_allowed_v1"
APPLY_API: Final[str] = "apply_employment_start_allowed_v1"

FORBIDDEN_REQUIREMENT_CODES: Final[frozenset[str]] = frozenset(
    {
        "zus_registration",
        "insurance",
        "a1",
        "delegation",
        "zgloszenie_delegacji",
        "legalization",
        "work_permit",
    }
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def is_pem1_context(employment_context: Mapping[str, Any] | None) -> bool:
    """Deterministic PEM-1 applicability (domestic PL EU/EEA, no posting)."""
    ctx = _record(employment_context)
    country = _norm(ctx.get("employment_country") or ctx.get("country") or "pl")
    if country not in {"pl", "pol", "poland"}:
        return False
    if ctx.get("posting") or ctx.get("international_posting") or ctx.get("delegation"):
        return False
    pathway = _norm(ctx.get("pathway_id") or ctx.get("legal_pathway") or "")
    if pathway and pathway not in {
        "pl_eu_eea_free_movement",
        "eu_eea",
        "pl_citizen",
        "eu_citizen",
    }:
        # Explicit non-PEM-1 pathway
        if pathway in {
            "pl_third_country_work_authorization",
            "third_country",
            "non_eu",
        }:
            return False
    contract_type = _norm(ctx.get("contract_type") or ctx.get("employment_type") or "employment_contract")
    if contract_type and contract_type not in {
        "employment_contract",
        "umowa_o_prace",
        "umowa_o_prace_na_czas_nieokreslony",
        "umowa_o_prace_na_czas_okreslony",
    }:
        return False
    # Default: treat as PEM-1 when country PL and not posting / not third-country
    return True


def resolve_planned_start_date(
    *,
    planned_start_date: Any = None,
    employment_context: Mapping[str, Any] | None = None,
) -> date | None:
    if planned_start_date is not None:
        return _parse_date(planned_start_date)
    ctx = _record(employment_context)
    for key in ("planned_start_date", "start_date", "first_work_date"):
        parsed = _parse_date(ctx.get(key))
        if parsed:
            return parsed
    return None


def _contract_satisfied(view: Mapping[str, Any] | None) -> bool:
    v = _record(view)
    return bool(v.get("written_instrument_confirmed") is True)


def _medical_satisfied(
    view: Mapping[str, Any] | None,
    *,
    planned_start: date | None,
    post_key: str,
) -> tuple[bool, str | None]:
    """Return (satisfied, missing_code_if_any)."""
    if planned_start is None:
        return False, FACT_PLANNED_START
    v = _record(view)
    if not v:
        return False, REQ_MEDICAL
    valid_until = _parse_date(v.get("medical_valid_until") or v.get("expires_at"))
    if valid_until is None or valid_until < planned_start:
        return False, REQ_MEDICAL
    fit = v.get("fit_for_work")
    if fit is not True and _norm(fit) not in {"true", "fit", "1", "yes"}:
        return False, REQ_MEDICAL
    applies = _norm(v.get("applies_to_post") or v.get("post_key") or "")
    if post_key and applies and applies != _norm(post_key):
        return False, REQ_MEDICAL
    if post_key and not applies:
        return False, REQ_MEDICAL
    conditions_ok = v.get("conditions_match") is True or bool(_text(v.get("working_conditions_ref")))
    if not conditions_ok:
        return False, REQ_MEDICAL
    return True, None


def _bhp_evidence_satisfied(
    view: Mapping[str, Any] | None,
    *,
    planned_start: date | None,
    employer_id: str,
    post_key: str,
) -> tuple[bool, str | None]:
    if planned_start is None:
        return False, FACT_PLANNED_START
    v = _record(view)
    if not v:
        return False, REQ_BHP
    if not _parse_date(v.get("training_date")):
        return False, REQ_BHP
    kind = _norm(v.get("training_kind") or v.get("bhp_stage") or "")
    if kind not in {"introductory", "intro", "wstepne", "wstępne"}:
        return False, REQ_BHP
    if employer_id and _norm(v.get("employer_id")) not in {"", _norm(employer_id)}:
        if _text(v.get("employer_id")) and _norm(v.get("employer_id")) != _norm(employer_id):
            return False, REQ_BHP
    applies = _norm(v.get("applies_to_post") or v.get("post_key") or "")
    if post_key and (not applies or applies != _norm(post_key)):
        return False, REQ_BHP
    expires = _parse_date(v.get("expires_at"))
    if expires is not None and expires < planned_start:
        return False, REQ_BHP
    return True, None


def prove_bhp_successive_exception(facts: Mapping[str, Any] | None) -> list[str]:
    """Return list of violation codes; empty means succession proven."""
    f = _record(facts)
    violations: list[str] = []
    if not _text(f.get("employer_id")):
        violations.append("missing_employer_id")
    if not _text(f.get("post_key") or f.get("post")):
        violations.append("missing_post_key")
    if not _text(f.get("prior_contract_ref")):
        violations.append("missing_prior_contract_ref")
    prior_end = _parse_date(f.get("prior_contract_end_date"))
    current_start = _parse_date(f.get("current_contract_start_date"))
    if prior_end is None:
        violations.append("missing_prior_contract_end_date")
    if current_start is None:
        violations.append("missing_current_contract_start_date")
    if f.get("successive") is not True and _norm(f.get("successive")) not in {"true", "1", "yes"}:
        violations.append("successive_flag_required")
    # Do not trust successive=True alone — prove immediate succession.
    if prior_end and current_start:
        # Same-day or next-calendar-day contiguous succession only.
        if current_start < prior_end:
            violations.append("current_starts_before_prior_ends")
        elif current_start - prior_end > timedelta(days=1):
            violations.append("succession_gap_too_large")
    return violations


def _active_exceptions(
    exceptions: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in exceptions or []:
        r = _record(row)
        if r.get("revoked_at"):
            continue
        out.append(r)
    return out


def _exception_satisfies(
    requirement_code: str,
    *,
    exceptions: Sequence[Mapping[str, Any]] | None,
    employment_context: Mapping[str, Any] | None,
) -> bool:
    ctx = _record(employment_context)
    employer_id = _text(ctx.get("employer_id"))
    post_key = _text(ctx.get("post_key") or ctx.get("position") or ctx.get("post"))
    for row in _active_exceptions(exceptions):
        code = _norm(row.get("exception_code"))
        req = _norm(row.get("requirement_code"))
        if PEM1_EXCEPTION_ALLOWLIST.get(code) != requirement_code:
            continue
        if req and req != _norm(requirement_code):
            continue
        if code == EXCEPTION_BHP_SUCCESSIVE:
            facts = _record(row.get("facts_json") or row.get("facts"))
            violations = prove_bhp_successive_exception(facts)
            if violations:
                continue
            if employer_id and _norm(facts.get("employer_id")) != _norm(employer_id):
                continue
            fact_post = _norm(facts.get("post_key") or facts.get("post"))
            if post_key and fact_post != _norm(post_key):
                continue
            return True
    return False


def evaluate_employment_start_allowed_v1(
    *,
    employee_id: str | None,
    employment_context: Mapping[str, Any] | None = None,
    contract_view: Mapping[str, Any] | None = None,
    medical_view: Mapping[str, Any] | None = None,
    bhp_view: Mapping[str, Any] | None = None,
    exceptions: Sequence[Mapping[str, Any]] | None = None,
    planned_start_date: Any = None,
) -> dict[str, Any]:
    """Pure evaluate. Does not write. Does not mint. LLM-OFF."""
    emp = _text(employee_id)
    ctx = _record(employment_context)

    base = {
        "policy_id": POLICY_ID,
        "employee_id": emp or None,
        "employee_minted_by_this_policy": False,
        "started": False,
        "zus_required_for_start": False,
        "manual_override": False,
        "llm_start_allowed": False,
        "context_policy": None,
        "decision_snapshot_is_authority": False,
    }

    if not emp:
        return {
            **base,
            "decision": DECISION_BLOCKED,
            "start_allowed": False,
            "required_actions": [],
            "active_missing": [],
            "primary_item": {
                "code": "employee_required",
                "kind": "blocker",
                "message": "start_allowed requires an existing employee_id",
            },
            "blockers": [{"code": "employee_required", "message": "Employee must exist before start_allowed"}],
        }

    if not is_pem1_context(ctx):
        return {
            **base,
            "decision": DECISION_UNSUPPORTED,
            "start_allowed": False,
            "context_policy": None,
            "required_actions": [],
            "active_missing": [],
            "primary_item": {
                "code": "unsupported_context",
                "kind": "policy_routing",
                "message": "employment_start_allowed.v1 has no authority for this employment context",
            },
            "blockers": [],
        }

    planned = resolve_planned_start_date(
        planned_start_date=planned_start_date,
        employment_context=ctx,
    )
    employer_id = _text(ctx.get("employer_id"))
    post_key = _text(ctx.get("post_key") or ctx.get("position") or ctx.get("post"))

    required = [
        {"code": REQ_CONTRACT, "kind": "evidence", "message": "Written employment contract or confirmation of terms"},
        {"code": REQ_MEDICAL, "kind": "evidence", "message": "Valid occupational medical fit for post/conditions"},
        {"code": REQ_BHP, "kind": "evidence", "message": "Introductory BHP before admit (or allowlisted exception)"},
    ]
    for code in FORBIDDEN_REQUIREMENT_CODES:
        assert code not in {r["code"] for r in required}

    active_missing: list[dict[str, str]] = []

    if not _contract_satisfied(contract_view):
        active_missing.append(dict(required[0]))

    med_ok, med_miss = _medical_satisfied(medical_view, planned_start=planned, post_key=post_key)
    if not med_ok:
        if med_miss == FACT_PLANNED_START:
            active_missing.append(
                {
                    "code": FACT_PLANNED_START,
                    "kind": "fact",
                    "message": "Canonical planned_start_date required for medical validity",
                }
            )
        else:
            active_missing.append(dict(required[1]))

    bhp_ok = False
    if _exception_satisfies(REQ_BHP, exceptions=exceptions, employment_context=ctx):
        bhp_ok = True
    else:
        bhp_ok, bhp_miss = _bhp_evidence_satisfied(
            bhp_view,
            planned_start=planned,
            employer_id=employer_id,
            post_key=post_key,
        )
        if not bhp_ok:
            if bhp_miss == FACT_PLANNED_START and not any(
                m.get("code") == FACT_PLANNED_START for m in active_missing
            ):
                active_missing.append(
                    {
                        "code": FACT_PLANNED_START,
                        "kind": "fact",
                        "message": "Canonical planned_start_date required for BHP validity",
                    }
                )
            elif bhp_miss != FACT_PLANNED_START:
                active_missing.append(dict(required[2]))

    # Deduplicate by code preserving order
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in active_missing:
        c = row["code"]
        if c in seen:
            continue
        seen.add(c)
        deduped.append(row)
    active_missing = deduped

    if active_missing:
        primary = active_missing[0]
        return {
            **base,
            "decision": DECISION_MISSING,
            "start_allowed": False,
            "context_policy": CONTEXT_PEM1,
            "required_actions": required,
            "active_missing": active_missing,
            "primary_item": {
                "code": primary["code"],
                "kind": primary.get("kind") or "formal_action",
                "message": primary.get("message") or primary["code"],
            },
            "planned_start_date": planned.isoformat() if planned else None,
            "blockers": [],
        }

    return {
        **base,
        "decision": DECISION_START_ALLOWED,
        "start_allowed": True,
        "context_policy": CONTEXT_PEM1,
        "required_actions": required,
        "active_missing": [],
        "primary_item": {
            "code": DECISION_START_ALLOWED,
            "kind": "threshold",
            "message": "Admit-to-work allowed — physical start still requires ESO-5 confirm",
        },
        "planned_start_date": planned.isoformat() if planned else None,
        "blockers": [],
    }


def apply_employment_start_allowed_v1(
    *,
    employee_id: str | None,
    employment_context: Mapping[str, Any] | None = None,
    contract_view: Mapping[str, Any] | None = None,
    medical_view: Mapping[str, Any] | None = None,
    bhp_view: Mapping[str, Any] | None = None,
    exceptions: Sequence[Mapping[str, Any]] | None = None,
    planned_start_date: Any = None,
    resolution_patch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply narrow resolution then re-evaluate.

    Write scope (slice 1): typed exception create/revoke payloads only.
    Does not upload Contract/Medical/BHP evidence. Does not set start_allowed.
    """
    patch = _record(resolution_patch)
    working_exceptions = [dict(r) for r in _active_exceptions(exceptions)]

    # Revoke
    revoke_id = _text(patch.get("revoke_exception_id") or patch.get("revoke_id"))
    if revoke_id:
        for row in working_exceptions:
            if _text(row.get("id")) == revoke_id:
                row["revoked_at"] = _text(patch.get("revoked_at")) or "revoked"
                row["revoked_by"] = patch.get("actor_user_id")

    # Create exception
    new_exc = _record(patch.get("exception") or patch.get("create_exception"))
    if new_exc:
        code = _norm(new_exc.get("exception_code"))
        req = _norm(new_exc.get("requirement_code")) or PEM1_EXCEPTION_ALLOWLIST.get(code, "")
        if code not in PEM1_EXCEPTION_ALLOWLIST:
            baseline = evaluate_employment_start_allowed_v1(
                employee_id=employee_id,
                employment_context=employment_context,
                contract_view=contract_view,
                medical_view=medical_view,
                bhp_view=bhp_view,
                exceptions=working_exceptions,
                planned_start_date=planned_start_date,
            )
            return {
                **baseline,
                "decision": DECISION_REJECTED_PATCH,
                "start_allowed": False,
                "rejection_reason": "exception_code_not_allowlisted",
                "exceptions": working_exceptions,
            }
        if PEM1_EXCEPTION_ALLOWLIST[code] != req and req:
            # force canonical requirement for allowlisted code
            req = PEM1_EXCEPTION_ALLOWLIST[code]
        facts = _record(new_exc.get("facts_json") or new_exc.get("facts"))
        if code == EXCEPTION_BHP_SUCCESSIVE:
            violations = prove_bhp_successive_exception(facts)
            if violations:
                baseline = evaluate_employment_start_allowed_v1(
                    employee_id=employee_id,
                    employment_context=employment_context,
                    contract_view=contract_view,
                    medical_view=medical_view,
                    bhp_view=bhp_view,
                    exceptions=working_exceptions,
                    planned_start_date=planned_start_date,
                )
                return {
                    **baseline,
                    "decision": DECISION_REJECTED_PATCH,
                    "start_allowed": False,
                    "rejection_reason": "exception_succession_not_proven",
                    "succession_violations": violations,
                    "exceptions": working_exceptions,
                }
        # Optional existing evidence ref bind only (no new evidence write)
        evidence_refs = list(new_exc.get("evidence_refs") or [])
        working_exceptions.append(
            {
                "id": _text(new_exc.get("id")) or f"exc-{code}",
                "requirement_code": req or PEM1_EXCEPTION_ALLOWLIST[code],
                "exception_code": code,
                "facts_json": facts,
                "evidence_refs": evidence_refs,
                "actor_user_id": new_exc.get("actor_user_id") or patch.get("actor_user_id"),
                "created_at": new_exc.get("created_at") or "now",
            }
        )

    # Reject force / override patches
    if patch.get("start_allowed") is True or patch.get("force_start_allowed") or patch.get("allow_anyway"):
        baseline = evaluate_employment_start_allowed_v1(
            employee_id=employee_id,
            employment_context=employment_context,
            contract_view=contract_view,
            medical_view=medical_view,
            bhp_view=bhp_view,
            exceptions=working_exceptions,
            planned_start_date=planned_start_date,
        )
        return {
            **baseline,
            "decision": DECISION_REJECTED_PATCH,
            "start_allowed": False,
            "rejection_reason": "manual_override_forbidden",
            "exceptions": working_exceptions,
        }

    result = evaluate_employment_start_allowed_v1(
        employee_id=employee_id,
        employment_context=employment_context,
        contract_view=contract_view,
        medical_view=medical_view,
        bhp_view=bhp_view,
        exceptions=working_exceptions,
        planned_start_date=planned_start_date,
    )
    result["exceptions"] = working_exceptions
    result["rejection_reason"] = None
    return result


__all__ = [
    "POLICY_ID",
    "OPERATOR_QUESTION",
    "DECISION_START_ALLOWED",
    "DECISION_MISSING",
    "DECISION_BLOCKED",
    "DECISION_UNSUPPORTED",
    "DECISION_REJECTED_PATCH",
    "DECISION_VALUES",
    "REQ_CONTRACT",
    "REQ_MEDICAL",
    "REQ_BHP",
    "EXCEPTION_BHP_SUCCESSIVE",
    "PEM1_EXCEPTION_ALLOWLIST",
    "FACT_PLANNED_START",
    "CONTEXT_PEM1",
    "ARCH_REL",
    "ADAPT_REL",
    "FOUNDATION_REL",
    "EVALUATE_API",
    "APPLY_API",
    "FORBIDDEN_REQUIREMENT_CODES",
    "is_pem1_context",
    "resolve_planned_start_date",
    "prove_bhp_successive_exception",
    "evaluate_employment_start_allowed_v1",
    "apply_employment_start_allowed_v1",
]
