"""Early employability — frozen contract (ESO-2).

Policy id: ``early_employability.v1``.

Employment evaluates whether a transferred person can be employed **now** in a
given employment context, using accepted-handoff preconditions and canonical
``ready_for_employment.v1`` facts. Deterministic. LLM-OFF for eligibility.

Does not create Employee. Does not force operator legal-pathway selection when
the pathway is uniquely determined. Requirements are contextual, not a
universal checklist.
"""

from __future__ import annotations

from typing import Any, Final, Mapping

from backend.app.reference.employment_accept_policy import (
    PACKAGE_AUTHORITATIVE_FIELD_CODES,
    assert_employment_missing_reuses_package,
)
from backend.app.reference.ready_for_employment import (
    ACCEPTANCE_GATE_IDS,
    CONTRACT_ID as RFE_CONTRACT_ID,
    validate_ready_for_employment_package_v1,
)

POLICY_ID: Final[str] = "early_employability.v1"

OPERATOR_QUESTION: Final[str] = (
    "after Employment has accepted a handoff (employment_started), can this "
    "transferred person be employed now in this employment context — and if "
    "not, what concrete blockers or missing facts prevent the next decision — "
    "without creating an Employee and without requiring the operator to know "
    "the internal legal model?"
)

DECISION_EMPLOYABLE: Final[str] = "employable"
DECISION_BLOCKED: Final[str] = "blocked"
DECISION_INSUFFICIENT_FACTS: Final[str] = "insufficient_facts"

DECISION_VALUES: Final[tuple[str, ...]] = (
    DECISION_EMPLOYABLE,
    DECISION_BLOCKED,
    DECISION_INSUFFICIENT_FACTS,
)

# EU + EEA + CH — free-movement group for thin PL pathway uniqueness.
EU_EEA_CH_ALPHA2: Final[frozenset[str]] = frozenset(
    "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE "
    "IS LI NO CH".split()
)

PATHWAY_PL_EU_EEA: Final[str] = "pl_eu_eea_free_movement"
PATHWAY_PL_THIRD_COUNTRY: Final[str] = "pl_third_country_work_authorization"

ACCEPTED_HANDOFF_STATUSES: Final[frozenset[str]] = frozenset({"accepted"})

ARCH_REL: Final[str] = "docs/specs/architecture/early-employability.md"
ESO_BRIEF_REL: Final[str] = "docs/specs/tasks/employment-spine-orchestrator-v1.md"
ACCEPT_ARCH_REL: Final[str] = "docs/specs/architecture/employment-accept-policy.md"
EVALUATE_API: Final[str] = "evaluate_early_employability_v1"
APPLY_API: Final[str] = "evaluate_early_employability_for_handoff"

# Evidence / fact codes that unlock third-country work authorization (thin).
WORK_AUTHORIZATION_EVIDENCE_CODES: Final[frozenset[str]] = frozenset(
    {
        "work_permit",
        "work_authorization",
        "zezwolenie",
        "oswiadczenie",
        "work_permit_document_id",
        "work_authorization_document_id",
    }
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm_code(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _upper_alpha2(value: Any) -> str:
    code = _text(value).upper()
    return code if len(code) == 2 and code.isalpha() else ""


def citizenship_from_canonical_facts(
    package: Mapping[str, Any] | None,
    *,
    canonical_facts: Mapping[str, Any] | None = None,
) -> str:
    """Single path: canonical_facts.citizenship or package identity_facts.citizenship.

    Does not accept ``nationality`` / ``country`` as citizenship twins.
    """
    from backend.app.field_registry.canonical_facts import read_citizenship_alpha2

    if isinstance(canonical_facts, Mapping):
        code = read_citizenship_alpha2(canonical_facts)
        if code:
            return code
    return read_citizenship_alpha2(package)


def citizenship_group(citizenship: str) -> str:
    code = _upper_alpha2(citizenship)
    if not code:
        return "unknown"
    if code in EU_EEA_CH_ALPHA2:
        return "eu_eea_ch"
    return "third_country"


def resolve_employment_country(
    employment_context: Mapping[str, Any] | None,
    *,
    package: Mapping[str, Any] | None = None,
) -> str:
    if isinstance(employment_context, Mapping):
        country = _upper_alpha2(
            employment_context.get("employment_country")
            or employment_context.get("country")
            or employment_context.get("country_code")
        )
        if country:
            return country
    if isinstance(package, Mapping):
        target = package.get("target_work")
        if isinstance(target, Mapping):
            country = _upper_alpha2(
                target.get("employment_country")
                or target.get("country")
                or target.get("country_code")
            )
            if country:
                return country
    # Thin default for HostFlow v1 employment spine (PL-first).
    return "PL"


def evidence_has_work_authorization(package: Mapping[str, Any] | None) -> bool:
    if not isinstance(package, Mapping):
        return False
    evidence = package.get("evidence")
    if not isinstance(evidence, Mapping):
        return False
    for key, value in evidence.items():
        code = _norm_code(key)
        if code in WORK_AUTHORIZATION_EVIDENCE_CODES:
            if value in (None, "", [], {}, False):
                continue
            return True
        if code.endswith("_document_ids") and isinstance(value, list) and value:
            # e.g. work_permit_document_ids
            if "work_permit" in code or "work_authorization" in code or "zezwolenie" in code:
                return True
    # Nested document_ids tagged via typed keys already covered; also accept
    # explicit boolean flags.
    if evidence.get("has_work_authorization") is True:
        return True
    return False


def _next_step(code: str, label: str) -> dict[str, str]:
    return {"code": code, "label": label}


def _pathway(pathway_id: str) -> dict[str, Any]:
    return {
        "pathway_id": pathway_id,
        "selection_required": False,
        "uniquely_determined": True,
    }


def derive_unique_legal_pathway(
    *,
    employment_country: str,
    citizenship: str,
) -> dict[str, Any] | None:
    """Return pathway object when uniquely determined; else None."""
    country = _upper_alpha2(employment_country) or "PL"
    group = citizenship_group(citizenship)
    if group == "unknown":
        return None
    if country != "PL":
        # Thin ESO-2: non-PL uniqueness not frozen — ask discriminating context.
        return None
    if group == "eu_eea_ch":
        return _pathway(PATHWAY_PL_EU_EEA)
    return _pathway(PATHWAY_PL_THIRD_COUNTRY)


def evaluate_early_employability_v1(
    *,
    package: Mapping[str, Any] | None,
    handoff_status: str | None,
    employment_context: Mapping[str, Any] | None = None,
    canonical_facts: Mapping[str, Any] | None = None,
    employment_missing: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Pure policy evaluation. Does not persist. Does not create Employee.

    LLM must not call this as an eligibility oracle with invented decisions —
    callers pass facts; this function alone decides employable/blocked/insufficient.
    """
    package_errors = validate_ready_for_employment_package_v1(package)
    missing = list(employment_missing or [])
    reuse_violations = assert_employment_missing_reuses_package(missing, package=package)

    status = _text(handoff_status).lower()
    country = resolve_employment_country(employment_context, package=package)
    position = ""
    if isinstance(employment_context, Mapping):
        position = _norm_code(employment_context.get("position_category"))

    citizenship = citizenship_from_canonical_facts(package, canonical_facts=canonical_facts)
    group = citizenship_group(citizenship)
    pathway = derive_unique_legal_pathway(
        employment_country=country,
        citizenship=citizenship,
    )

    blockers: list[dict[str, str]] = []
    requirements: list[dict[str, str]] = []

    if package_errors:
        for err in package_errors:
            blockers.append({"code": "invalid_package", "message": err})
    if status not in ACCEPTED_HANDOFF_STATUSES:
        blockers.append(
            {
                "code": "handoff_not_accepted",
                "message": (
                    f"Handoff status is {status!r}; early employability requires "
                    "accepted (after employment_started)"
                ),
            }
        )
    for code in reuse_violations:
        blockers.append(
            {
                "code": "package_fact_reask",
                "message": (
                    f"employment_missing must not re-ask package fact {code!r} "
                    "without conflict_reason"
                ),
            }
        )
    for row in missing:
        if isinstance(row, Mapping):
            blockers.append(
                {
                    "code": _norm_code(row.get("field_code") or row.get("code"))
                    or "employment_missing",
                    "message": _text(row.get("label") or row.get("message"))
                    or "Employment missing",
                }
            )

    # --- Decision path (after structural blockers) ---
    decision = DECISION_BLOCKED
    next_step = _next_step("resolve_blockers", "Resolve employment blockers")

    if package_errors:
        decision = DECISION_BLOCKED
        next_step = _next_step("fix_package", "Fix ready_for_employment.v1 package")
    elif status not in ACCEPTED_HANDOFF_STATUSES:
        decision = DECISION_BLOCKED
        next_step = _next_step(
            "accept_handoff_first",
            "Accept handoff via employment_accept_policy.v1 before employability",
        )
    elif reuse_violations or missing:
        decision = DECISION_BLOCKED
        next_step = _next_step("resolve_blockers", "Resolve employment blockers")
    elif group == "unknown":
        decision = DECISION_INSUFFICIENT_FACTS
        requirements.append(
            {
                "code": "citizenship",
                "message": "Citizenship (ISO alpha-2) is required to determine legal pathway",
            }
        )
        next_step = _next_step(
            "provide_citizenship",
            "Provide citizenship (ISO alpha-2) — minimal fact for pathway",
        )
        # Do not set pathway; selection still not offered as a menu.
    elif country != "PL":
        decision = DECISION_INSUFFICIENT_FACTS
        requirements.append(
            {
                "code": "employment_country",
                "message": (
                    f"Employment country {country!r} is outside thin ESO-2 PL "
                    "pathway table; provide supported employment context"
                ),
            }
        )
        next_step = _next_step(
            "provide_employment_country",
            "Confirm employment country supported by employability policy",
        )
    elif pathway and pathway["pathway_id"] == PATHWAY_PL_EU_EEA:
        decision = DECISION_EMPLOYABLE
        next_step = _next_step(
            "proceed_to_formalize",
            "Proceed to Formalize (Employee still downstream)",
        )
    elif pathway and pathway["pathway_id"] == PATHWAY_PL_THIRD_COUNTRY:
        has_auth = evidence_has_work_authorization(package)
        # Contextual requirement — only for this pathway (+ driver hint).
        req = {
            "code": "work_authorization_evidence",
            "message": "Work authorization evidence required for third-country employment in PL",
        }
        if has_auth:
            decision = DECISION_EMPLOYABLE
            # Requirement satisfied — do not list as outstanding.
            next_step = _next_step(
                "proceed_to_formalize",
                "Proceed to Formalize (Employee still downstream)",
            )
        else:
            requirements.append(req)
            blockers.append(
                {
                    "code": "work_authorization_evidence",
                    "message": req["message"],
                }
            )
            # Prefer insufficient_facts when the only gap is missing evidence.
            decision = DECISION_INSUFFICIENT_FACTS
            next_step = _next_step(
                "provide_work_authorization_evidence",
                "Provide work authorization evidence (permit / oświadczenie)",
            )
            if position == "driver":
                # Still contextual — same requirement, clearer label.
                next_step = _next_step(
                    "provide_work_authorization_evidence",
                    "Provide work authorization evidence for driver employment",
                )
    else:
        decision = DECISION_INSUFFICIENT_FACTS
        next_step = _next_step(
            "provide_discriminating_fact",
            "Provide the minimal fact needed to determine legal pathway",
        )

    return {
        "policy_id": POLICY_ID,
        "decision": decision,
        "package_contract_id": RFE_CONTRACT_ID,
        "package_valid": not package_errors,
        "package_errors": package_errors,
        "handoff_accepted": status in ACCEPTED_HANDOFF_STATUSES,
        "employment_country": country,
        "citizenship": citizenship or None,
        "citizenship_group": group,
        "legal_pathway": pathway,
        # ESO-2: never force operator pathway menu — ask discriminating fact instead.
        "pathway_selection_required": False,
        "blockers": blockers,
        "requirements": requirements,
        "reuse_violations": reuse_violations,
        "next_step": next_step,
        "employee_created": False,
        "llm_eligibility": False,
        "acceptance_gate_ids": list(ACCEPTANCE_GATE_IDS),
        "package_authoritative_field_codes": sorted(PACKAGE_AUTHORITATIVE_FIELD_CODES),
    }


__all__ = [
    "POLICY_ID",
    "OPERATOR_QUESTION",
    "DECISION_EMPLOYABLE",
    "DECISION_BLOCKED",
    "DECISION_INSUFFICIENT_FACTS",
    "DECISION_VALUES",
    "EU_EEA_CH_ALPHA2",
    "PATHWAY_PL_EU_EEA",
    "PATHWAY_PL_THIRD_COUNTRY",
    "ACCEPTED_HANDOFF_STATUSES",
    "ARCH_REL",
    "ESO_BRIEF_REL",
    "ACCEPT_ARCH_REL",
    "EVALUATE_API",
    "APPLY_API",
    "WORK_AUTHORIZATION_EVIDENCE_CODES",
    "citizenship_from_canonical_facts",
    "citizenship_group",
    "resolve_employment_country",
    "evidence_has_work_authorization",
    "derive_unique_legal_pathway",
    "evaluate_early_employability_v1",
]
