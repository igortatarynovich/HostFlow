"""HR consumer of ``requirement_resolution.v1``.

One Employment's ``hr_employment_requirements`` are the policy input. The
shared resolver reads the shared facts and Candidate Evidence. This module
does not add a resolution rule, a citizenship list, or a second evidence
resolver. It writes the stored result on this Employment's row.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import (
    APPLICABILITY_APPLICABLE,
    APPLICABILITY_NOT_APPLICABLE,
    RESOLUTION_BLOCKING,
    RESOLUTION_SATISFIED,
    RESOLUTION_UNRESOLVED,
    RESOLUTION_WAIVED,
    HrEmploymentRequirement,
)
from backend.app.reference.document_policy_merge import platform_ruleset_base
from backend.app.reference.requirement_policy_consumer_parity import r5_required_set
from backend.app.reference.legal_eligibility_evidence import (
    STAY_REQUIREMENT,
    WORK_REQUIREMENT,
    stay_accepted_evidence,
    work_accepted_evidence,
)
from backend.app.reference.requirement_resolution import (
    CE_REQUIREMENT,
    CODE95_REQUIREMENT,
    resolve_requirement,
)
from backend.app.requirement_rules.requirement_definition_registry import (
    get_requirement_definition_v1,
    requirement_definitions_version,
)
from backend.app.services.operator_facts_surface import chain_reading
from backend.app.services.pre_employment_requirements_runtime import (
    RequirementDefinition,
    block_pre_employment_requirement,
    materialize_pre_employment_requirements,
    realign_pre_employment_requirement,
    satisfy_pre_employment_requirement,
)

POLICY_ID = "requirement_definitions.v1"

# Registry keys the shared resolver already accepts. Legal stay and work
# authorization pass their accepted evidence in; they are not extra rules.
_RESOLVER_CODE = {
    "driver_entitlement": CE_REQUIREMENT,
    "professional_qualification": CODE95_REQUIREMENT,
}
_LEGAL = {STAY_REQUIREMENT, WORK_REQUIREMENT}

_CLOSED = {RESOLUTION_SATISFIED, RESOLUTION_WAIVED, RESOLUTION_BLOCKING}


@dataclass(frozen=True)
class HrRequirementResolution:
    accepted: bool
    requirements: tuple[HrEmploymentRequirement, ...]
    readings: tuple[dict[str, Any], ...]
    required_set: tuple[str, ...]
    reason: str | None


def hr_policy_definitions() -> tuple[RequirementDefinition, ...]:
    """Registry requirements HR already names.

    CE, Code 95, legal stay, and work authorization. A fact that the person
    holds ADR or a tachograph card adds nothing. Identity is not a row.
    """

    version = requirement_definitions_version()
    rows: list[RequirementDefinition] = []
    for key in (
        "driver_entitlement",
        "professional_qualification",
        STAY_REQUIREMENT,
        WORK_REQUIREMENT,
    ):
        if get_requirement_definition_v1(key) is None:
            continue
        rows.append(
            RequirementDefinition(
                definition_key=key,
                policy_id=POLICY_ID,
                policy_version=version,
                applicability="applicable",
                applicability_basis=f"{POLICY_ID}:{key}",
            )
        )
    return tuple(rows)


def materialize_hr_requirements(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    definitions: Sequence[RequirementDefinition] | None = None,
):
    """Write this Employment's rows from HR policy. A later call does not rewrite them."""

    chosen = tuple(definitions) if definitions is not None else hr_policy_definitions()
    return materialize_pre_employment_requirements(
        db,
        tenant_id=tenant_id,
        employment=employment,
        definitions=list(chosen),
    )


def hr_required_set(readings: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Documents this Employment still needs, written by ``r5_required_set``.

    The candidate pack is removed. Only evidence the shared resolution still
    asks for is added back. A satisfied or in-review row adds no file.
    """

    pending: list[str] = []
    for row in readings:
        if row.get("progress") != "needs_evidence":
            continue
        for code in row.get("document_codes") or []:
            text = str(code or "").strip().lower()
            if text and text not in pending:
                pending.append(text)
    defaults = (
        ((platform_ruleset_base().get("ruleset") or {}).get("candidate") or {}).get("defaults") or {}
    )
    remove = [str(code) for code in (defaults.get("requiredTypes") or []) if str(code).strip()]
    delta: dict[str, Any] = {
        "candidate": {"overrides": [{"when": {}, "remove": remove}]},
    }
    if pending:
        delta["vacancy"] = {"additions": [{"when": {}, "require": pending}]}
    produced = r5_required_set({"process": "hr"}, delta)
    return tuple(code for code in pending if code in produced)


def apply_hr_requirement_resolution(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    facts: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    today: date | None = None,
) -> HrRequirementResolution:
    """Resolve each open row of this Employment. A closed row is not recomputed.

    Satisfaction is written on this row. It is not a copy of another
    Employment's ``satisfied``.
    """

    tenant = str(tenant_id).strip()
    rows = _stored(db, tenant, str(employment.id))
    if not rows:
        return HrRequirementResolution(
            accepted=False,
            requirements=(),
            readings=(),
            required_set=(),
            reason="undefined",
        )

    readings: list[dict[str, Any]] = []
    for row in rows:
        readings.append(_apply_row(db, tenant, employment, row, facts, evidence, today=today))
    db.flush()
    stored = _stored(db, tenant, str(employment.id))
    return HrRequirementResolution(
        accepted=True,
        requirements=stored,
        readings=tuple(readings),
        required_set=hr_required_set(readings),
        reason=None,
    )


def _apply_row(
    db: Session,
    tenant_id: str,
    employment: Employment,
    row: HrEmploymentRequirement,
    facts: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    today: date | None,
) -> dict[str, Any]:
    if row.definition_key in _LEGAL:
        return _apply_legal_row(db, tenant_id, employment, row, facts, evidence, today=today)
    if row.applicability != APPLICABILITY_APPLICABLE or row.resolution in _CLOSED or row.resolution is None:
        return _stored_reading(row)
    code = _RESOLVER_CODE.get(row.definition_key)
    if code is None:
        return _stored_reading(row)
    resolved = resolve_requirement(
        {"requirement_code": code, "level": "REQUIRED"},
        facts,
        evidence,
        today=today,
    )
    resolved = dict(resolved)
    resolved["definition_key"] = row.definition_key
    resolved["employment_id"] = str(employment.id)
    progress = resolved.get("progress")
    if progress == "satisfied" and resolved.get("evidence_id"):
        satisfy_pre_employment_requirement(
            db,
            tenant_id=tenant_id,
            employment=employment,
            definition_key=row.definition_key,
            evidence_id=str(resolved["evidence_id"]),
        )
    elif progress == "blocking":
        block_pre_employment_requirement(
            db,
            tenant_id=tenant_id,
            employment=employment,
            definition_key=row.definition_key,
            blocking_reason="requirement_resolution.v1",
        )
    return resolved


def _legal_spec(definition_key: str, facts: Mapping[str, Any], employment_id: str) -> dict[str, Any]:
    chain = chain_reading(facts, employment_id=employment_id)
    if definition_key == STAY_REQUIREMENT:
        return stay_accepted_evidence(chain.get("stay_basis"))
    work = _employment_work(facts, employment_id)
    return work_accepted_evidence(
        work_authorization_basis=chain.get("work_authorization_basis"),
        procedure_type=work.get("procedure_type"),
        valid_for_this_employment=chain.get("valid_for_this_employment"),
    )


def _employment_work(facts: Mapping[str, Any], employment_id: str) -> Mapping[str, Any]:
    employments = facts.get("employments")
    if isinstance(employments, Mapping) and isinstance(employments.get(employment_id), Mapping):
        return employments[employment_id]
    work = facts.get("work")
    return work if isinstance(work, Mapping) else {}


def _evidence_by_id(evidence: Sequence[Mapping[str, Any]], evidence_id: str | None) -> Mapping[str, Any] | None:
    if not evidence_id:
        return None
    for row in evidence:
        if str(row.get("id") or "") == evidence_id:
            return row
    return None


def _legal_still_holds(
    row: HrEmploymentRequirement,
    spec: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
) -> bool:
    outcome = spec.get("outcome")
    if row.resolution == RESOLUTION_WAIVED:
        return True
    if outcome == "not_required":
        return row.applicability == APPLICABILITY_NOT_APPLICABLE and row.resolution is None
    if outcome == "blocking":
        return row.resolution == RESOLUTION_BLOCKING
    if outcome == "needs_evidence" and row.resolution == RESOLUTION_SATISFIED:
        linked = _evidence_by_id(evidence, row.satisfaction_evidence_id)
        if linked is None:
            return False
        if str(linked.get("evidence_variant_code") or "") != str(spec.get("variant") or ""):
            return False
        covered = {str(code).strip().lower() for code in (linked.get("document_codes") or [])}
        needed = {str(code).strip().lower() for code in (spec.get("document_codes") or [])}
        return needed <= covered
    return False


def _apply_legal_row(
    db: Session,
    tenant_id: str,
    employment: Employment,
    row: HrEmploymentRequirement,
    facts: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    today: date | None,
) -> dict[str, Any]:
    spec = _legal_spec(row.definition_key, facts, str(employment.id))
    if row.resolution == RESOLUTION_WAIVED or _legal_still_holds(row, spec, evidence):
        reading = _stored_reading(row)
        reading["evidence_variant"] = spec.get("variant")
        return reading
    if row.resolution in _CLOSED or row.applicability == APPLICABILITY_NOT_APPLICABLE:
        realign_pre_employment_requirement(
            db,
            tenant_id=tenant_id,
            employment=employment,
            definition_key=row.definition_key,
            applicable=True,
        )
    resolved = resolve_requirement(
        {
            "requirement_code": row.definition_key,
            "level": "REQUIRED",
            "accepted_evidence": spec,
        },
        facts,
        evidence,
        today=today,
    )
    resolved = dict(resolved)
    resolved["definition_key"] = row.definition_key
    resolved["employment_id"] = str(employment.id)
    if resolved.get("applicable") is False:
        realign_pre_employment_requirement(
            db,
            tenant_id=tenant_id,
            employment=employment,
            definition_key=row.definition_key,
            applicable=False,
        )
        return resolved
    progress = resolved.get("progress")
    if progress == "satisfied" and resolved.get("evidence_id"):
        satisfy_pre_employment_requirement(
            db,
            tenant_id=tenant_id,
            employment=employment,
            definition_key=row.definition_key,
            evidence_id=str(resolved["evidence_id"]),
        )
    elif progress == "blocking":
        block_pre_employment_requirement(
            db,
            tenant_id=tenant_id,
            employment=employment,
            definition_key=row.definition_key,
            blocking_reason="requirement_resolution.v1",
        )
    return resolved


def _stored(db: Session, tenant_id: str, employment_id: str) -> tuple[HrEmploymentRequirement, ...]:
    rows = db.scalars(
        select(HrEmploymentRequirement)
        .where(
            HrEmploymentRequirement.tenant_id == tenant_id,
            HrEmploymentRequirement.employment_id == employment_id,
        )
        .order_by(HrEmploymentRequirement.definition_key)
    ).all()
    return tuple(rows)


def _stored_reading(row: HrEmploymentRequirement) -> dict[str, Any]:
    progress = row.resolution if row.resolution in {RESOLUTION_SATISFIED, RESOLUTION_BLOCKING} else None
    if row.resolution == RESOLUTION_UNRESOLVED:
        progress = None
    return {
        "definition_key": row.definition_key,
        "employment_id": row.employment_id,
        "progress": progress,
        "resolution": row.resolution,
        "document_codes": [],
        "evidence_id": row.satisfaction_evidence_id,
        "resolved": row.resolution in _CLOSED,
    }
