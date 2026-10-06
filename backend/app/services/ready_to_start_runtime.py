"""Aggregate ready_to_start.v1 and activate one Employment.

The four inputs are the canonical readings. This module does not decide
legal eligibility, person facts, agreed terms, or requirement resolution.
A decision is appended. Activation re-reads those inputs and writes
``preparing → active`` in the same transaction, or it writes nothing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import (
    APPLICABILITY_APPLICABLE,
    RESOLUTION_BLOCKING,
    RESOLUTION_UNRESOLVED,
    HrEmploymentRequirement,
)
from backend.app.models.hr_employment_terms import HrEmploymentTerms
from backend.app.models.hr_legal_eligibility_gate import HrLegalEligibilityGateDecision
from backend.app.models.hr_ready_to_start import (
    OUTCOME_BLOCKED,
    OUTCOME_PASS,
    HrReadyToStartDecision,
)
from backend.app.services.employee_data_reading import read_employee_data_set
from backend.app.services.employment_terms_runtime import TERMS_COMPLETE, evaluate_employment_terms
from backend.app.services.hr_legal_eligibility_gate import checkpoint_planned_start, decision_is_current
from backend.app.services.pre_employment_requirements_runtime import evaluate_pre_employment_requirements

_PASS = "pass"
_BLOCKED = "blocked"


@dataclass(frozen=True)
class InputReading:
    result: str
    fingerprint: str | None
    reasons: tuple[str, ...]
    ref_id: str | None = None


@dataclass(frozen=True)
class ReadyToStartReadings:
    legal: InputReading
    employee_data: InputReading
    terms: InputReading
    requirements: InputReading


@dataclass(frozen=True)
class ReadyToStartRecordResult:
    accepted: bool
    decision: HrReadyToStartDecision | None
    reason: str | None


@dataclass(frozen=True)
class ActivationResult:
    activated: bool
    reason: str | None


def _hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _text(value: object) -> str | None:
    raw = str(value or "").strip()
    return raw or None


def _latest_legal(db: Session, tenant_id: str, employment_id: str) -> HrLegalEligibilityGateDecision | None:
    return db.scalars(
        select(HrLegalEligibilityGateDecision)
        .where(
            HrLegalEligibilityGateDecision.tenant_id == tenant_id,
            HrLegalEligibilityGateDecision.employment_id == employment_id,
        )
        .order_by(HrLegalEligibilityGateDecision.decided_at.desc(), HrLegalEligibilityGateDecision.id.desc())
    ).first()


def _current_terms(db: Session, tenant_id: str, employment_id: str) -> HrEmploymentTerms | None:
    return db.scalars(
        select(HrEmploymentTerms).where(
            HrEmploymentTerms.tenant_id == tenant_id,
            HrEmploymentTerms.employment_id == employment_id,
            HrEmploymentTerms.is_current.is_(True),
        )
    ).one_or_none()


def _requirement_rows(db: Session, tenant_id: str, employment_id: str) -> tuple[HrEmploymentRequirement, ...]:
    rows = db.scalars(
        select(HrEmploymentRequirement)
        .where(
            HrEmploymentRequirement.tenant_id == tenant_id,
            HrEmploymentRequirement.employment_id == employment_id,
        )
        .order_by(HrEmploymentRequirement.definition_key)
    ).all()
    return tuple(rows)


def _terms_fingerprint(row: HrEmploymentTerms | None) -> str:
    if row is None:
        return _hash({"missing": True})
    return _hash(
        {
            "id": row.id,
            "is_current": row.is_current,
            "position": row.position,
            "contract_basis": row.contract_basis,
            "work_time_value": format(Decimal(row.work_time_value), "f"),
            "work_time_unit": row.work_time_unit,
            "work_system": row.work_system,
            "workplace": row.workplace,
            "compensation_amount": format(Decimal(row.compensation_amount), "f"),
            "compensation_currency": row.compensation_currency,
            "compensation_unit": row.compensation_unit,
            "duration": row.duration,
            "fixed_term_end": row.fixed_term_end.isoformat() if row.fixed_term_end else None,
            "probation_status": row.probation_status,
            "probation_end": row.probation_end.isoformat() if row.probation_end else None,
            "intended_start_date": row.intended_start_date.isoformat() if row.intended_start_date else None,
            "default_vacancy_id": row.default_vacancy_id,
        }
    )


def _requirements_fingerprint(rows: tuple[HrEmploymentRequirement, ...]) -> str:
    return _hash(
        [
            {
                "definition_key": row.definition_key,
                "policy_id": row.policy_id,
                "policy_version": row.policy_version,
                "applicability": row.applicability,
                "applicability_basis": row.applicability_basis,
                "resolution": row.resolution,
                "satisfaction_evidence_id": row.satisfaction_evidence_id,
                "satisfaction_document_id": row.satisfaction_document_id,
                "waiver_actor_id": row.waiver_actor_id,
                "waiver_at": row.waiver_at.isoformat() if row.waiver_at else None,
                "waiver_reason": row.waiver_reason,
                "blocking_reason": row.blocking_reason,
            }
            for row in rows
        ]
    )


def _legal_reading(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    legal_reading: Mapping[str, Any],
) -> InputReading:
    decision = _latest_legal(db, tenant_id, str(employment.id))
    if decision is None:
        return InputReading(result=_BLOCKED, fingerprint=None, reasons=("legal_missing",), ref_id=None)
    terms = _current_terms(db, tenant_id, str(employment.id))
    current = decision_is_current(
        decision,
        reading=legal_reading,
        client_company_id=employment.client_company_id,
        vacancy_id=employment.vacancy_id,
        planned_start=checkpoint_planned_start(
            employment,
            terms.intended_start_date if terms is not None else None,
        ),
    )
    if decision.outcome == "pass" and current:
        return InputReading(
            result=_PASS,
            fingerprint=decision.fingerprint,
            reasons=(),
            ref_id=decision.id,
        )
    if decision.outcome == "fail":
        reason = "legal_fail"
    elif decision.outcome == "blocked":
        reason = "legal_blocked"
    elif decision.outcome == "pass":
        reason = "legal_stale"
    else:
        reason = "legal_blocked"
    return InputReading(
        result=_BLOCKED,
        fingerprint=decision.fingerprint,
        reasons=(reason,),
        ref_id=decision.id,
    )


def _terms_reading(db: Session, tenant_id: str, employment_id: str) -> InputReading:
    row = _current_terms(db, tenant_id, employment_id)
    fingerprint = _terms_fingerprint(row)
    if row is None:
        return InputReading(result=_BLOCKED, fingerprint=fingerprint, reasons=("terms_missing",), ref_id=None)
    if evaluate_employment_terms(row) != TERMS_COMPLETE:
        return InputReading(result=_BLOCKED, fingerprint=fingerprint, reasons=("terms_incomplete",), ref_id=row.id)
    return InputReading(result=_PASS, fingerprint=fingerprint, reasons=(), ref_id=row.id)


def _requirements_reading(db: Session, tenant_id: str, employment: Employment) -> InputReading:
    rows = _requirement_rows(db, tenant_id, str(employment.id))
    fingerprint = _requirements_fingerprint(rows)
    if evaluate_pre_employment_requirements(db, tenant_id=tenant_id, employment=employment):
        return InputReading(result=_PASS, fingerprint=fingerprint, reasons=())
    if not rows:
        return InputReading(result=_BLOCKED, fingerprint=fingerprint, reasons=("requirements_undefined",))
    reasons: list[str] = []
    for row in rows:
        if row.applicability != APPLICABILITY_APPLICABLE:
            continue
        if row.resolution == RESOLUTION_UNRESOLVED:
            reasons.append(f"requirements_unresolved:{row.definition_key}")
        elif row.resolution == RESOLUTION_BLOCKING:
            reasons.append(f"requirements_blocking:{row.definition_key}")
    if not reasons:
        reasons.append("requirements_not_ready")
    return InputReading(result=_BLOCKED, fingerprint=fingerprint, reasons=tuple(reasons))


def read_ready_to_start_inputs(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    legal_reading: Mapping[str, Any],
    employee_facts: Mapping[str, Any] | None,
    employee_data_complete: bool,
) -> ReadyToStartReadings:
    """Call the four readings. Person-fact keys are not interpreted here."""

    tenant = str(tenant_id).strip()
    data = read_employee_data_set(employee_facts, complete=employee_data_complete)
    employee = InputReading(
        result=_PASS if data.complete else _BLOCKED,
        fingerprint=data.fingerprint,
        reasons=() if data.complete else ("employee_data_incomplete",),
    )
    return ReadyToStartReadings(
        legal=_legal_reading(db, tenant_id=tenant, employment=employment, legal_reading=legal_reading),
        employee_data=employee,
        terms=_terms_reading(db, tenant, str(employment.id)),
        requirements=_requirements_reading(db, tenant, employment),
    )


def _reasons(readings: ReadyToStartReadings) -> tuple[str, ...]:
    return (
        readings.legal.reasons
        + readings.employee_data.reasons
        + readings.terms.reasons
        + readings.requirements.reasons
    )


def ready_to_start_is_current(
    decision: HrReadyToStartDecision,
    readings: ReadyToStartReadings,
) -> bool:
    """A stored pass is current only while the four captured readings still match."""

    if decision.outcome != OUTCOME_PASS:
        return False
    stamps = (
        (decision.legal_result, decision.legal_fingerprint, readings.legal),
        (decision.employee_data_result, decision.employee_data_fingerprint, readings.employee_data),
        (decision.terms_result, decision.terms_fingerprint, readings.terms),
        (decision.requirements_result, decision.requirements_fingerprint, readings.requirements),
    )
    for stored_result, stored_fingerprint, fresh in stamps:
        if stored_result != _PASS or fresh.result != _PASS:
            return False
        if stored_fingerprint != fresh.fingerprint:
            return False
    return not _reasons(readings)


def latest_ready_to_start_decision(
    db: Session,
    *,
    tenant_id: str,
    employment_id: str,
) -> HrReadyToStartDecision | None:
    return db.scalars(
        select(HrReadyToStartDecision)
        .where(
            HrReadyToStartDecision.tenant_id == str(tenant_id).strip(),
            HrReadyToStartDecision.employment_id == str(employment_id),
        )
        .order_by(HrReadyToStartDecision.decided_at.desc(), HrReadyToStartDecision.id.desc())
    ).first()


def _lock_employment(db: Session, employment_id: str) -> Employment | None:
    stmt = select(Employment).where(Employment.id == str(employment_id))
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    return db.scalars(stmt).one_or_none()


def record_ready_to_start(
    db: Session,
    *,
    tenant_id: str,
    employment: Employment,
    actor_user_id: str,
    legal_reading: Mapping[str, Any],
    employee_facts: Mapping[str, Any] | None,
    employee_data_complete: bool,
    decided_at: datetime | None = None,
) -> ReadyToStartRecordResult:
    """Append one decision. An earlier row is left as it was."""

    tenant = str(tenant_id).strip()
    actor = _text(actor_user_id)
    if employment.state != "preparing" or str(employment.tenant_id) != tenant:
        return ReadyToStartRecordResult(accepted=False, decision=None, reason="not_preparing")
    if actor is None:
        return ReadyToStartRecordResult(accepted=False, decision=None, reason="actor")
    readings = read_ready_to_start_inputs(
        db,
        tenant_id=tenant,
        employment=employment,
        legal_reading=legal_reading,
        employee_facts=employee_facts,
        employee_data_complete=employee_data_complete,
    )
    reasons = _reasons(readings)
    outcome = OUTCOME_PASS if not reasons else OUTCOME_BLOCKED
    row = HrReadyToStartDecision(
        tenant_id=tenant,
        employment_id=str(employment.id),
        outcome=outcome,
        actor_user_id=actor,
        decided_at=decided_at or datetime.now(timezone.utc),
        legal_result=readings.legal.result,
        legal_decision_id=readings.legal.ref_id,
        legal_fingerprint=readings.legal.fingerprint,
        employee_data_result=readings.employee_data.result,
        employee_data_fingerprint=readings.employee_data.fingerprint or "",
        terms_result=readings.terms.result,
        terms_id=readings.terms.ref_id,
        terms_fingerprint=readings.terms.fingerprint or "",
        requirements_result=readings.requirements.result,
        requirements_fingerprint=readings.requirements.fingerprint or "",
        blocked_reasons=json.dumps(list(reasons), separators=(",", ":")),
    )
    db.add(row)
    db.flush()
    if employment.state != "preparing":
        raise RuntimeError("Ready to Start must not change Employment.state")
    return ReadyToStartRecordResult(accepted=True, decision=row, reason=None)


def activate_employment(
    db: Session,
    *,
    tenant_id: str,
    employment_id: str,
    legal_reading: Mapping[str, Any],
    employee_facts: Mapping[str, Any] | None,
    employee_data_complete: bool,
) -> ActivationResult:
    """Move preparing to active only when the latest pass is still current.

    The freshness check and the state write share this session. Nothing is
    committed here, and no upstream gate is filled in.
    """

    tenant = str(tenant_id).strip()
    employment = _lock_employment(db, employment_id)
    if employment is None or employment.state != "preparing" or str(employment.tenant_id) != tenant:
        return ActivationResult(activated=False, reason="not_preparing")
    decision = latest_ready_to_start_decision(db, tenant_id=tenant, employment_id=str(employment.id))
    if decision is None:
        return ActivationResult(activated=False, reason="missing")
    readings = read_ready_to_start_inputs(
        db,
        tenant_id=tenant,
        employment=employment,
        legal_reading=legal_reading,
        employee_facts=employee_facts,
        employee_data_complete=employee_data_complete,
    )
    if decision.outcome != OUTCOME_PASS:
        return ActivationResult(activated=False, reason="blocked")
    if not ready_to_start_is_current(decision, readings):
        return ActivationResult(activated=False, reason="stale")
    employment.state = "active"
    db.flush()
    return ActivationResult(activated=True, reason=None)
