"""Write new intake answers onto canonical professional facts.

Does not create employments and does not write legacy experience scalars.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.entity_profile.professional_requirement_identity import TRAILER_HIRING_CODES
from backend.app.models.candidate import Candidate
from backend.app.models.professional_profile import CandidateAvailability, CandidateDeclaredFact
from backend.app.services.operator_facts_surface import (
    apply_operator_facts_patch,
    facts_from_personal_data,
    licence_category_codes,
    personal_data_with_facts,
)

INTAKE_PROVENANCE = "candidate_intake"

LICENCE_CATEGORIES = "recruitment.candidate.professional.licence_categories"
CODE95 = "recruitment.candidate.professional.code95"
ADR = "recruitment.candidate.professional.adr"
CE_YEARS = "recruitment.candidate.professional.ce_years"
INTERNATIONAL = "recruitment.candidate.professional.international"
TRAILER_CODES = "recruitment.candidate.professional.trailer_codes"
AVAILABLE_FROM = "recruitment.candidate.professional.available_from"

PROFESSIONAL_INTAKE_FIELDS = {
    LICENCE_CATEGORIES: "licence_categories",
    CODE95: "code95_presence",
    ADR: "adr_presence",
    CE_YEARS: "ce_years",
    INTERNATIONAL: "international",
    TRAILER_CODES: "trailer_codes",
    AVAILABLE_FROM: "available_from",
}

_TRUE = {"1", "true", "yes", "y", "da", "да", "tak", "есть"}
_FALSE = {"0", "false", "no", "n", "net", "нет", "nie"}
_TRAILER_ALIASES = {"tent": "curtain", "frigo": "reefer"}
_HIRING = set(TRAILER_HIRING_CODES)


def professional_bucket(qualified_code: str) -> str | None:
    return PROFESSIONAL_INTAKE_FIELDS.get(str(qualified_code or "").strip())


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    return None


def _years(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Decimal):
        number = value
    else:
        text = str(value).strip().replace(",", ".")
        if not text or any(mark in text for mark in ("-", "–", "/")):
            return None
        try:
            number = Decimal(text)
        except InvalidOperation:
            return None
    if number < 0 or number > 60:
        return None
    return number.quantize(Decimal("0.0001"))


def _categories(value: Any) -> list[str]:
    known = set(licence_category_codes())
    items = value if isinstance(value, (list, tuple)) else str(value or "").replace(";", ",").split(",")
    out: list[str] = []
    for item in items:
        code = str(item or "").strip().upper()
        if code in known and code not in out:
            out.append(code)
    return out


def _trailers(value: Any) -> list[str]:
    items = value if isinstance(value, (list, tuple)) else str(value or "").replace(";", ",").split(",")
    out: list[str] = []
    for item in items:
        raw = str(item or "").strip().lower()
        code = _TRAILER_ALIASES.get(raw, raw)
        if code in _HIRING and code not in out:
            out.append(code)
    return out


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def normalize_intake_professional_facts(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Keep only answers that have a canonical type. Drop everything else."""

    source = dict(raw or {})
    out: dict[str, Any] = {}
    if "licence_categories" in source:
        categories = _categories(source.get("licence_categories"))
        if categories:
            out["licence_categories"] = categories
    if "code95_presence" in source:
        presence = _bool(source.get("code95_presence"))
        if presence is not None:
            out["code95_presence"] = presence
    if "adr_presence" in source:
        presence = _bool(source.get("adr_presence"))
        if presence is not None:
            out["adr_presence"] = presence
    if "ce_years" in source:
        years = _years(source.get("ce_years"))
        if years is not None:
            out["ce_years"] = years
    if "international" in source:
        presence = _bool(source.get("international"))
        if presence is not None:
            out["international"] = presence
    if "trailer_codes" in source:
        codes = _trailers(source.get("trailer_codes"))
        if codes:
            out["trailer_codes"] = codes
    if "available_from" in source:
        parsed = _date(source.get("available_from"))
        if parsed is not None:
            out["available_from"] = parsed
    return out


def facts_from_qualified_values(values: Mapping[str, Any] | None) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for code, value in dict(values or {}).items():
        bucket = professional_bucket(str(code))
        if bucket is None or value in (None, ""):
            continue
        raw[bucket] = value
    return normalize_intake_professional_facts(raw)


async def _replace_subject(
    session: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    subject: str,
    rows: list[CandidateDeclaredFact],
) -> None:
    await session.execute(
        delete(CandidateDeclaredFact).where(
            CandidateDeclaredFact.tenant_id == tenant_id,
            CandidateDeclaredFact.candidate_id == candidate_id,
            CandidateDeclaredFact.subject == subject,
        )
    )
    for row in rows:
        session.add(row)


async def record_intake_professional_facts(
    session: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    facts: Mapping[str, Any] | None,
) -> bool:
    """Persist one intake declaration. Returns True when a canonical row changed.

    Missing keys are left alone. Legacy experience fields are not written.
    No employment row is created.
    """

    normalized = normalize_intake_professional_facts(facts)
    if not normalized:
        return False
    candidate_id = str(candidate.id)
    changed = False

    operator_patch = {
        key: normalized[key]
        for key in ("licence_categories", "code95_presence", "adr_presence")
        if key in normalized
    }
    if operator_patch:
        personal = candidate.personal_data if isinstance(candidate.personal_data, dict) else {}
        current = facts_from_personal_data(personal)
        stored = apply_operator_facts_patch(current, operator_patch)
        candidate.personal_data = personal_data_with_facts(personal, stored)
        flag_modified(candidate, "personal_data")
        changed = True

    if "ce_years" in normalized:
        await _replace_subject(
            session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            subject="ce",
            rows=[
                CandidateDeclaredFact(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    subject="ce",
                    code="ce",
                    years=normalized["ce_years"],
                    presence=None,
                    provenance=INTAKE_PROVENANCE,
                )
            ],
        )
        changed = True

    if "international" in normalized:
        await _replace_subject(
            session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            subject="international",
            rows=[
                CandidateDeclaredFact(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    subject="international",
                    code="international",
                    years=None,
                    presence=normalized["international"],
                    provenance=INTAKE_PROVENANCE,
                )
            ],
        )
        changed = True

    if "trailer_codes" in normalized:
        await _replace_subject(
            session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            subject="trailer",
            rows=[
                CandidateDeclaredFact(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    subject="trailer",
                    code=code,
                    years=None,
                    presence=True,
                    provenance=INTAKE_PROVENANCE,
                )
                for code in normalized["trailer_codes"]
            ],
        )
        changed = True

    if "available_from" in normalized:
        await set_candidate_available_from(
            session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            available_from=normalized["available_from"],
        )
        changed = True

    if changed:
        await session.flush()
    return changed


async def set_candidate_available_from(
    session: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    available_from: date | None,
) -> None:
    """Upsert the one availability row. This is the recruiter and intake writer."""
    existing = await session.scalar(
        select(CandidateAvailability).where(
            CandidateAvailability.tenant_id == tenant_id,
            CandidateAvailability.candidate_id == candidate_id,
        )
    )
    if existing is None:
        if available_from is None:
            return
        session.add(
            CandidateAvailability(
                id=str(uuid4()),
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                available_from=available_from,
            )
        )
    else:
        existing.available_from = available_from
    await session.flush()


async def record_intake_professional_facts_from_values(
    session: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    values: Mapping[str, Any] | None,
) -> bool:
    return await record_intake_professional_facts(
        session,
        tenant_id=tenant_id,
        candidate=candidate,
        facts=facts_from_qualified_values(values),
    )
