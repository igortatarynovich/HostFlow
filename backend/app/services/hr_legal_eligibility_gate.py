"""HR checkpoint on one Employment(preparing).

Reads a legal_eligibility.v1 chain. It does not derive that chain, it does
not copy evidence, and it does not move Employment.state.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_terms import HrEmploymentTerms
from backend.app.models.hr_legal_eligibility_gate import HrLegalEligibilityGateDecision

POLICY_ID = "legal_eligibility.v1"

_CITIZENSHIP = frozenset({"pl", "eu_eea_ch", "third_country"})
_STAY = frozenset(
    {
        "not_required",
        "visa_d",
        "visa_c",
        "karta_pobytu",
        "visa_free",
        "waiting_for_trc",
        "special_protection",
        "other",
        "none",
    }
)
_WORK = frozenset({"not_required", "included_in_stay", "separate_required"})
_VALID = frozenset({"yes", "no", "operator_verification"})

_CHAIN_KEYS = (
    "citizenship_class",
    "stay_basis",
    "work_authorization_basis",
    "valid_for_this_employment",
)


@dataclass(frozen=True)
class HrLegalEligibilityGateResult:
    outcome: str
    applies: bool
    continues_existing_workflow: bool
    fingerprint: str
    chain: dict[str, str | None]
    employment_context: dict[str, str | None]
    policy_id: str = POLICY_ID


def _token(reading: Mapping[str, Any], key: str) -> str | None:
    raw = reading.get(key)
    text = str(raw or "").strip()
    return text or None


def chain_from_reading(reading: Mapping[str, Any]) -> dict[str, str | None]:
    return {key: _token(reading, key) for key in _CHAIN_KEYS}


def _context(
    *,
    client_company_id: str | None,
    vacancy_id: str | None,
    planned_start: date | None,
) -> dict[str, str | None]:
    return {
        "client_company_id": str(client_company_id).strip() if client_company_id else None,
        "vacancy_id": str(vacancy_id).strip() if vacancy_id else None,
        "planned_start": planned_start.isoformat() if planned_start else None,
    }


def reading_fingerprint(
    chain: Mapping[str, str | None],
    employment_context: Mapping[str, str | None],
) -> str:
    payload = {
        "policy_id": POLICY_ID,
        "citizenship_class": chain.get("citizenship_class") or "",
        "stay_basis": chain.get("stay_basis") or "",
        "work_authorization_basis": chain.get("work_authorization_basis") or "",
        "valid_for_this_employment": chain.get("valid_for_this_employment") or "",
        "client_company_id": employment_context.get("client_company_id") or "",
        "vacancy_id": employment_context.get("vacancy_id") or "",
        "planned_start": employment_context.get("planned_start") or "",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _chain_determined(chain: Mapping[str, str | None]) -> bool:
    return (
        chain.get("citizenship_class") in _CITIZENSHIP
        and chain.get("stay_basis") in _STAY
        and chain.get("work_authorization_basis") in _WORK
        and chain.get("valid_for_this_employment") in _VALID
    )


def _context_complete(employment_context: Mapping[str, str | None]) -> bool:
    return all(employment_context.get(key) for key in ("client_company_id", "vacancy_id", "planned_start"))


def evaluate_hr_legal_eligibility_gate(
    *,
    employment_state: str,
    reading: Mapping[str, Any],
    client_company_id: str | None,
    vacancy_id: str | None,
    planned_start: date | None,
) -> HrLegalEligibilityGateResult:
    """Checkpoint for this Employment. Does not write Employment.state."""

    chain = chain_from_reading(reading)
    context = _context(
        client_company_id=client_company_id,
        vacancy_id=vacancy_id,
        planned_start=planned_start,
    )
    fingerprint = reading_fingerprint(chain, context)
    if str(employment_state or "").strip().lower() != "preparing":
        return HrLegalEligibilityGateResult(
            outcome="not_preparing",
            applies=False,
            continues_existing_workflow=False,
            fingerprint=fingerprint,
            chain=chain,
            employment_context=context,
        )
    if not _chain_determined(chain) or not _context_complete(context):
        return HrLegalEligibilityGateResult(
            outcome="blocked",
            applies=True,
            continues_existing_workflow=True,
            fingerprint=fingerprint,
            chain=chain,
            employment_context=context,
        )
    if chain["valid_for_this_employment"] == "operator_verification":
        return HrLegalEligibilityGateResult(
            outcome="blocked",
            applies=True,
            continues_existing_workflow=True,
            fingerprint=fingerprint,
            chain=chain,
            employment_context=context,
        )
    if chain["valid_for_this_employment"] == "no":
        return HrLegalEligibilityGateResult(
            outcome="fail",
            applies=True,
            continues_existing_workflow=False,
            fingerprint=fingerprint,
            chain=chain,
            employment_context=context,
        )
    return HrLegalEligibilityGateResult(
        outcome="pass",
        applies=True,
        continues_existing_workflow=False,
        fingerprint=fingerprint,
        chain=chain,
        employment_context=context,
    )


def checkpoint_planned_start(employment: Employment, intended_start: date | None) -> date | None:
    """The plan while preparing. ``started_on`` is the actual start and stays empty until then."""

    if employment.started_on is not None:
        return employment.started_on
    return intended_start


def decision_is_current(
    decision: HrLegalEligibilityGateDecision,
    *,
    reading: Mapping[str, Any],
    client_company_id: str | None,
    vacancy_id: str | None,
    planned_start: date | None,
) -> bool:
    """A recorded PASS is current only while the chain and this Employment context match."""

    chain = chain_from_reading(reading)
    context = _context(
        client_company_id=client_company_id,
        vacancy_id=vacancy_id,
        planned_start=planned_start,
    )
    return decision.fingerprint == reading_fingerprint(chain, context)


async def latest_hr_legal_eligibility_decision(
    db: AsyncSession,
    *,
    tenant_id: str,
    employment_id: str,
) -> HrLegalEligibilityGateDecision | None:
    res = await db.execute(
        select(HrLegalEligibilityGateDecision)
        .where(
            HrLegalEligibilityGateDecision.tenant_id == tenant_id,
            HrLegalEligibilityGateDecision.employment_id == employment_id,
        )
        .order_by(HrLegalEligibilityGateDecision.decided_at.desc())
    )
    return res.scalars().first()


async def record_hr_legal_eligibility_gate(
    db: AsyncSession,
    *,
    tenant_id: str,
    employment: Employment,
    reading: Mapping[str, Any],
    actor_user_id: str,
    decided_at: datetime | None = None,
) -> HrLegalEligibilityGateResult:
    """Append the HR checkpoint. Employment.state is not written."""

    actor = str(actor_user_id or "").strip()
    if not actor:
        raise ValueError("actor_user_id is required")
    current_terms = (
        await db.scalars(
            select(HrEmploymentTerms).where(
                HrEmploymentTerms.tenant_id == str(tenant_id).strip(),
                HrEmploymentTerms.employment_id == str(employment.id),
                HrEmploymentTerms.is_current.is_(True),
            )
        )
    ).one_or_none()
    planned = checkpoint_planned_start(
        employment,
        current_terms.intended_start_date if current_terms is not None else None,
    )
    state_before = employment.state
    result = evaluate_hr_legal_eligibility_gate(
        employment_state=state_before,
        reading=reading,
        client_company_id=employment.client_company_id,
        vacancy_id=employment.vacancy_id,
        planned_start=planned,
    )
    if employment.state != state_before:
        raise RuntimeError("HR Legal Eligibility Gate must not change Employment.state")
    if not result.applies:
        return result
    when = decided_at or datetime.now(timezone.utc)
    db.add(
        HrLegalEligibilityGateDecision(
            tenant_id=str(tenant_id).strip(),
            employment_id=str(employment.id),
            outcome=result.outcome,
            policy_id=POLICY_ID,
            citizenship_class=result.chain["citizenship_class"],
            stay_basis=result.chain["stay_basis"],
            work_authorization_basis=result.chain["work_authorization_basis"],
            valid_for_this_employment=result.chain["valid_for_this_employment"],
            client_company_id=result.employment_context["client_company_id"],
            vacancy_id=result.employment_context["vacancy_id"],
            planned_start=planned if result.employment_context["planned_start"] else None,
            fingerprint=result.fingerprint,
            actor_user_id=actor,
            decided_at=when,
        )
    )
    await db.flush()
    if employment.state != state_before:
        raise RuntimeError("HR Legal Eligibility Gate must not change Employment.state")
    return result
