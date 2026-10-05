"""Materialize pre_employment_requirements.v1 for one Employment.

The materialized set is stable. A later policy does not add, delete, or
rewrite a row. Resolution is an explicit act on that row. This module
does not move ``hr_employments.state``, does not insert a contract card
or an onboarding task, and does not open Ready to Start.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.document import Document
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

_APPLICABILITY = {APPLICABILITY_APPLICABLE, APPLICABILITY_NOT_APPLICABLE}
_OPEN = {RESOLUTION_UNRESOLVED, RESOLUTION_BLOCKING}


@dataclass(frozen=True)
class RequirementDefinition:
    """One policy reading. Not a stored instance until materialize writes it."""

    definition_key: str
    policy_id: str
    policy_version: str
    applicability: str
    applicability_basis: str


@dataclass(frozen=True)
class MaterializeResult:
    accepted: bool
    requirements: tuple[HrEmploymentRequirement, ...]
    reason: str | None


@dataclass(frozen=True)
class ResolutionResult:
    accepted: bool
    requirement: HrEmploymentRequirement | None
    reason: str | None


def _text(value: object) -> str | None:
    raw = str(value or "").strip()
    return raw or None


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


def _preparing(employment: Employment, tenant_id: str) -> str | None:
    if str(employment.tenant_id) != tenant_id:
        return "tenant"
    if employment.state != "preparing":
        return "not_preparing"
    return None


def _definition_rows(
    tenant_id: str,
    employment_id: str,
    definitions: tuple[RequirementDefinition, ...] | list[RequirementDefinition],
) -> tuple[list[HrEmploymentRequirement] | None, str | None]:
    if not definitions:
        return None, "undefined"
    seen: set[str] = set()
    rows: list[HrEmploymentRequirement] = []
    for definition in definitions:
        key = _text(definition.definition_key)
        policy_id = _text(definition.policy_id)
        policy_version = _text(definition.policy_version)
        basis = _text(definition.applicability_basis)
        if (
            key is None
            or policy_id is None
            or policy_version is None
            or basis is None
            or definition.applicability not in _APPLICABILITY
            or key in seen
        ):
            return None, "invalid"
        seen.add(key)
        applicable = definition.applicability == APPLICABILITY_APPLICABLE
        rows.append(
            HrEmploymentRequirement(
                id=str(uuid4()),
                tenant_id=tenant_id,
                employment_id=employment_id,
                definition_key=key,
                policy_id=policy_id,
                policy_version=policy_version,
                applicability=definition.applicability,
                applicability_basis=basis,
                resolution=RESOLUTION_UNRESOLVED if applicable else None,
            )
        )
    return rows, None


def materialize_pre_employment_requirements(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    definitions: tuple[RequirementDefinition, ...] | list[RequirementDefinition],
) -> MaterializeResult:
    """Write the set once. A later call returns the stored rows unchanged."""

    tenant = str(tenant_id).strip()
    refusal = _preparing(employment, tenant)
    if refusal is not None:
        return MaterializeResult(accepted=False, requirements=(), reason=refusal)

    employment_id = str(employment.id)
    existing = _stored(db, tenant, employment_id)
    if existing:
        return MaterializeResult(accepted=True, requirements=existing, reason=None)

    rows, reason = _definition_rows(tenant, employment_id, definitions)
    if rows is None:
        return MaterializeResult(accepted=False, requirements=(), reason=reason)
    for row in rows:
        db.add(row)
    db.flush()
    return MaterializeResult(
        accepted=True,
        requirements=_stored(db, tenant, employment_id),
        reason=None,
    )


def _instance(
    db: Session,
    tenant_id: str,
    employment: Employment,
    definition_key: str,
) -> tuple[HrEmploymentRequirement | None, str | None]:
    tenant = str(tenant_id).strip()
    refusal = _preparing(employment, tenant)
    if refusal is not None:
        return None, refusal
    key = _text(definition_key)
    if key is None:
        return None, "missing"
    row = db.scalars(
        select(HrEmploymentRequirement).where(
            HrEmploymentRequirement.tenant_id == tenant,
            HrEmploymentRequirement.employment_id == str(employment.id),
            HrEmploymentRequirement.definition_key == key,
        )
    ).one_or_none()
    if row is None:
        return None, "missing"
    if row.applicability != APPLICABILITY_APPLICABLE or row.resolution is None:
        return None, "not_applicable"
    return row, None


def _same_link(row: HrEmploymentRequirement, evidence_id: str | None, document_id: str | None) -> bool:
    return row.satisfaction_evidence_id == evidence_id and row.satisfaction_document_id == document_id


def _evidence_exists(db: Session, tenant_id: str, evidence_id: str) -> bool:
    found = db.scalar(
        select(CandidateEvidence.id).where(
            CandidateEvidence.id == evidence_id,
            CandidateEvidence.tenant_id == tenant_id,
        )
    )
    return found is not None


def _document_exists(db: Session, tenant_id: str, document_id: str) -> bool:
    found = db.scalar(
        select(Document.id).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
        )
    )
    return found is not None


def satisfy_pre_employment_requirement(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    definition_key: str,
    evidence_id: str | None = None,
    document_id: str | None = None,
) -> ResolutionResult:
    """Link this instance to evidence or a document the caller names.

    An existing row on the Employee is not consulted. The ids are the
    whole match.
    """

    row, reason = _instance(db, tenant_id, employment, definition_key)
    if row is None:
        return ResolutionResult(accepted=False, requirement=None, reason=reason)
    evidence = _text(evidence_id)
    document = _text(document_id)
    if evidence is None and document is None:
        return ResolutionResult(accepted=False, requirement=row, reason="missing_link")
    tenant = str(tenant_id).strip()
    if evidence is not None and not _evidence_exists(db, tenant, evidence):
        return ResolutionResult(accepted=False, requirement=row, reason="missing_evidence")
    if document is not None and not _document_exists(db, tenant, document):
        return ResolutionResult(accepted=False, requirement=row, reason="missing_document")
    if row.resolution == RESOLUTION_SATISFIED and _same_link(row, evidence, document):
        return ResolutionResult(accepted=True, requirement=row, reason=None)
    if row.resolution not in _OPEN:
        return ResolutionResult(accepted=False, requirement=row, reason="closed")
    row.resolution = RESOLUTION_SATISFIED
    row.satisfaction_evidence_id = evidence
    row.satisfaction_document_id = document
    row.waiver_actor_id = None
    row.waiver_at = None
    row.waiver_reason = None
    row.blocking_reason = None
    db.flush()
    return ResolutionResult(accepted=True, requirement=row, reason=None)


def waive_pre_employment_requirement(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    definition_key: str,
    actor_id: str,
    waiver_at: datetime,
    reason: str,
) -> ResolutionResult:
    """Record an explicit waiver. A second, different waiver does not rewrite the first."""

    row, refusal = _instance(db, tenant_id, employment, definition_key)
    if row is None:
        return ResolutionResult(accepted=False, requirement=None, reason=refusal)
    actor = _text(actor_id)
    waiver_reason = _text(reason)
    if actor is None or waiver_at is None or waiver_reason is None:
        return ResolutionResult(accepted=False, requirement=row, reason="waiver")
    if (
        row.resolution == RESOLUTION_WAIVED
        and row.waiver_actor_id == actor
        and row.waiver_reason == waiver_reason
    ):
        return ResolutionResult(accepted=True, requirement=row, reason=None)
    if row.resolution not in _OPEN:
        return ResolutionResult(accepted=False, requirement=row, reason="closed")
    row.resolution = RESOLUTION_WAIVED
    row.waiver_actor_id = actor
    row.waiver_at = waiver_at
    row.waiver_reason = waiver_reason
    row.satisfaction_evidence_id = None
    row.satisfaction_document_id = None
    row.blocking_reason = None
    db.flush()
    return ResolutionResult(accepted=True, requirement=row, reason=None)


def block_pre_employment_requirement(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    definition_key: str,
    blocking_reason: str,
) -> ResolutionResult:
    """Record a found problem. ``unresolved`` is not this act."""

    row, refusal = _instance(db, tenant_id, employment, definition_key)
    if row is None:
        return ResolutionResult(accepted=False, requirement=None, reason=refusal)
    found = _text(blocking_reason)
    if found is None:
        return ResolutionResult(accepted=False, requirement=row, reason="blocking")
    if row.resolution == RESOLUTION_BLOCKING and row.blocking_reason == found:
        return ResolutionResult(accepted=True, requirement=row, reason=None)
    if row.resolution != RESOLUTION_UNRESOLVED:
        return ResolutionResult(accepted=False, requirement=row, reason="closed")
    row.resolution = RESOLUTION_BLOCKING
    row.blocking_reason = found
    row.satisfaction_evidence_id = None
    row.satisfaction_document_id = None
    row.waiver_actor_id = None
    row.waiver_at = None
    row.waiver_reason = None
    db.flush()
    return ResolutionResult(accepted=True, requirement=row, reason=None)


def realign_pre_employment_requirement(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    definition_key: str,
    applicable: bool,
) -> ResolutionResult:
    """Open this row again, or mark it not applicable. Evidence rows stay stored.

    A waiver is left as recorded. Any other resolution is cleared so the
    shared resolver can write this Employment's row again.
    """

    tenant = str(tenant_id).strip()
    refusal = _preparing(employment, tenant)
    if refusal is not None:
        return ResolutionResult(accepted=False, requirement=None, reason=refusal)
    key = _text(definition_key)
    if key is None:
        return ResolutionResult(accepted=False, requirement=None, reason="missing")
    row = db.scalars(
        select(HrEmploymentRequirement).where(
            HrEmploymentRequirement.tenant_id == tenant,
            HrEmploymentRequirement.employment_id == str(employment.id),
            HrEmploymentRequirement.definition_key == key,
        )
    ).one_or_none()
    if row is None:
        return ResolutionResult(accepted=False, requirement=None, reason="missing")
    if row.resolution == RESOLUTION_WAIVED:
        return ResolutionResult(accepted=False, requirement=row, reason="closed")
    if applicable:
        if row.applicability == APPLICABILITY_APPLICABLE and row.resolution == RESOLUTION_UNRESOLVED:
            return ResolutionResult(accepted=True, requirement=row, reason=None)
        row.applicability = APPLICABILITY_APPLICABLE
        row.resolution = RESOLUTION_UNRESOLVED
    else:
        if row.applicability == APPLICABILITY_NOT_APPLICABLE and row.resolution is None:
            return ResolutionResult(accepted=True, requirement=row, reason=None)
        row.applicability = APPLICABILITY_NOT_APPLICABLE
        row.resolution = None
    row.satisfaction_evidence_id = None
    row.satisfaction_document_id = None
    row.waiver_actor_id = None
    row.waiver_at = None
    row.waiver_reason = None
    row.blocking_reason = None
    db.flush()
    return ResolutionResult(accepted=True, requirement=row, reason=None)


def evaluate_pre_employment_requirements(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
) -> bool:
    """True when the set is defined and every applicable row is satisfied or waived.

    ``not_applicable`` is outside the check. ``unresolved`` and ``blocking``
    are both false and stay different readings on the row. The bool does
    not write ``hr_employments.state``.
    """

    tenant = str(tenant_id).strip()
    if _preparing(employment, tenant) is not None:
        return False
    rows = _stored(db, tenant, str(employment.id))
    if not rows:
        return False
    applicable = [row for row in rows if row.applicability == APPLICABILITY_APPLICABLE]
    return all(row.resolution in {RESOLUTION_SATISFIED, RESOLUTION_WAIVED} for row in applicable)
