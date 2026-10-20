"""Read-only professional profile projection.

The function reads canonical facts, employment history, and legacy scalars.
It does not write candidates, employments, extra, or experience scalars.
Consumers keep their current reads until a named cutover.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable, Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.models.professional_profile import (
    CandidateAvailability,
    CandidateCompensationExpectation,
    CandidateDeclaredFact,
    CandidatePreferenceChoice,
    CandidateProfessionalConstraint,
    ProfessionalCodeMapping,
)
from backend.app.models.tenant import Tenant
from backend.app.reference.country_registry import get_country_registry_entry
from backend.app.reference.professional_profile_catalogs import (
    CREW_MODE,
    MOVEMENT_PATTERN,
    OPERATION_SCOPE,
    WORK_AREA_REGION,
    catalog_code_pairs,
)
from backend.app.services.operator_facts_surface import facts_from_personal_data

_YEAR_DAYS = Decimal(365)
_YEAR_QUANT = Decimal("0.0001")
_CALCULATED = "calculated"
_PRESENCE = "presence_only"
_INSUFFICIENT = "insufficient_history"
_AMBIGUOUS = "ambiguous_history"
_NONE = "no_evidence"

_EU_FIELD = "experience" + "_eu_years"
_CE_TOTAL_FIELD = "experience" + "_ce_total"
_YEARS_FIELD = "experience" + "_years"
_NON_EU_FIELD = "experience" + "_non_eu_years"
_INTL_FIELD = "intl" + "_experience"
_TRAILER_FIELD = "trailer" + "_types"
_ROUTE_FIELD = "route" + "_types"


class ProfessionalProfileNotFound(LookupError):
    pass


@dataclass(frozen=True)
class EmploymentFact:
    id: str
    employer_name: str
    country: str | None
    position: str | None
    start_date: date | None
    end_date: date | None
    driving_categories: tuple[str, ...]
    operation_scopes: tuple[str, ...]
    movement_patterns: tuple[str, ...]
    crew_modes: tuple[str, ...]
    work_areas: tuple[tuple[str, str], ...]
    trailer_types: tuple[str, ...]
    route_types: tuple[str, ...]
    eu_routes: bool | None


@dataclass(frozen=True)
class ConstraintFact:
    id: str
    subject: str
    code: str
    effect: str
    source: str
    valid_from: date | None
    valid_to: date | None
    note: str | None


@dataclass(frozen=True)
class ChoiceFact:
    id: str
    subject: str
    kind: str | None
    code: str


@dataclass(frozen=True)
class CompensationFact:
    amount: Decimal | None
    currency: str | None
    period: str | None


@dataclass(frozen=True)
class MappingFact:
    source_vocabulary: str
    source_code: str
    target_vocabulary: str
    target_code: str


@dataclass(frozen=True)
class DeclaredIntakeFact:
    subject: str
    code: str
    years: Decimal | None
    presence: bool | None
    provenance: str


@dataclass(frozen=True)
class ProfileInputs:
    candidate_id: str
    tenant_id: str
    timezone_name: str | None
    now: datetime
    personal_data: Mapping[str, Any]
    extra: Mapping[str, Any]
    intake_state: Mapping[str, Any]
    employments: tuple[EmploymentFact, ...]
    constraints: tuple[ConstraintFact, ...]
    choices: tuple[ChoiceFact, ...]
    compensation: CompensationFact | None
    available_from: date | None
    mappings: tuple[MappingFact, ...]
    declared_intake: tuple[DeclaredIntakeFact, ...] = ()


def resolve_professional_profile(inputs: ProfileInputs) -> dict[str, Any]:
    today = _workspace_today(inputs.timezone_name, inputs.now)
    known_categories = _known_driving_categories()
    jobs = tuple(
        sorted(
            sorted(inputs.employments, key=lambda job: job.id),
            key=lambda job: (
                job.start_date or date.min,
                job.end_date is None,
                job.end_date or date.min,
            ),
            reverse=True,
        )
    )
    provenance = _provenance(inputs.extra, inputs.intake_state)
    experience = _experience(jobs, today, known_categories, inputs.mappings)
    legacy_eu = provenance[_EU_FIELD]
    declared_ce_years = legacy_eu["declared_ce_years"]
    experience["declared"] = {
        "ce": {
            "status": "declared" if declared_ce_years is not None else _NONE,
            "years": declared_ce_years,
            "origin": "ce_written_as_eu" if declared_ce_years is not None else None,
        },
        "eu": {
            "status": _NONE,
            "years": None,
            "origin": None,
        },
        "non_eu_years": provenance[_NON_EU_FIELD],
        "legacy_total": provenance[_YEARS_FIELD],
        "international_flag": provenance[_INTL_FIELD],
        "ce_total": provenance[_CE_TOTAL_FIELD],
        "intake": _declared_intake(inputs.declared_intake, inputs.mappings),
    }
    intake_ce = experience["declared"]["intake"]["ce_years"]
    if intake_ce is not None:
        experience["declared"]["ce"] = {
            "status": "declared",
            "years": intake_ce,
            "origin": "candidate_intake",
        }
    return {
        "candidate_id": inputs.candidate_id,
        "tenant_id": inputs.tenant_id,
        "capabilities": _capabilities(inputs.personal_data),
        "experience": experience,
        "constraints": _constraints(inputs.constraints, today),
        "preferences_and_availability": _preferences(inputs),
        "provenance": provenance,
    }


def _experience(
    jobs: Sequence[EmploymentFact],
    today: date | None,
    known_categories: set[str],
    mappings: Sequence[MappingFact],
) -> dict[str, Any]:
    return {
        "employments": [_employment_row(job) for job in jobs],
        "aggregates": {
            "total_tenure": _tenure_aggregate(jobs, today),
            "ce": _single_code_aggregate(
                jobs,
                today,
                codes_of=_driving_codes,
                exact=("CE",),
                known=known_categories,
                facet="driving_categories",
            ),
            "international": _single_code_aggregate(
                jobs,
                today,
                codes_of=_scope_codes,
                exact=("international",),
                known=_known(OPERATION_SCOPE),
                facet="operation_scopes",
            ),
            "eu": _eu_aggregate(jobs, today),
            "movement_pattern": _single_value_group_aggregate(
                jobs,
                today,
                codes_of=_movement_codes,
                known=_known(MOVEMENT_PATTERN),
                facet="movement_patterns",
            ),
            "crew_mode": _single_value_group_aggregate(
                jobs,
                today,
                codes_of=_crew_codes,
                known=_known(CREW_MODE),
                facet="crew_modes",
            ),
        },
        "practical_experience": {
            "trailers": _trailer_presence(jobs, mappings),
        },
        "geography": _geography(jobs),
        "work_character": {
            "operation_scopes": _group_presence(jobs, _scope_codes, _known(OPERATION_SCOPE)),
            "movement_patterns": _group_presence(jobs, _movement_codes, _known(MOVEMENT_PATTERN)),
            "crew_modes": _group_presence(jobs, _crew_codes, _known(CREW_MODE)),
        },
    }


def _capabilities(personal_data: Mapping[str, Any]) -> dict[str, Any]:
    facts = facts_from_personal_data(dict(personal_data) if personal_data else None)
    raw = personal_data.get("operator_facts") if isinstance(personal_data, Mapping) else None
    raw_categories = raw.get("licence_categories") if isinstance(raw, Mapping) else None
    accepted = list(facts.get("licence_categories") or [])
    raw_unmapped: list[str] = []
    if isinstance(raw_categories, list):
        accepted_set = set(accepted)
        for item in raw_categories:
            code = str(item or "").strip().upper()
            if code and code not in accepted_set and code not in raw_unmapped:
                raw_unmapped.append(code)
    return {
        "source": "operator_facts",
        "licence": {
            "issuing_country": facts.get("licence_issuing_country"),
            "categories": accepted,
            "raw_unmapped": raw_unmapped,
            "valid_to": facts.get("licence_valid_to"),
        },
        "code95": {
            "presence": facts.get("code95_presence"),
            "valid_to": facts.get("code95_valid_to"),
        },
        "tachograph": {
            "presence": facts.get("tachograph_presence"),
            "issuing_country": facts.get("tachograph_issuing_country"),
            "valid_to": facts.get("tachograph_valid_to"),
        },
        "adr": {
            "presence": facts.get("adr_presence"),
            "issuing_country": facts.get("adr_issuing_country"),
            "valid_to": facts.get("adr_valid_to"),
        },
    }


def _constraints(rows: Sequence[ConstraintFact], today: date | None) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: (row.subject, row.code, row.effect, row.id))
    return [
        {
            "id": row.id,
            "subject": row.subject,
            "code": row.code,
            "effect": row.effect,
            "source": row.source,
            "valid_from": _iso(row.valid_from),
            "valid_to": _iso(row.valid_to),
            "note": row.note,
            "activity": _constraint_activity(row, today),
            "matching_key": {"subject": row.subject, "code": row.code, "effect": row.effect},
        }
        for row in ordered
    ]


def _constraint_activity(row: ConstraintFact, today: date | None) -> str:
    """Active, expired and not-yet-started use the workspace date.

    Without a readable tenant zone the validity is unknown. UTC is not used.
    """

    if today is None:
        return "unknown"
    if row.valid_to is not None and row.valid_to < today:
        return "expired"
    if row.valid_from is not None and row.valid_from > today:
        return "scheduled"
    return "active"


def _declared_intake(
    rows: Sequence[DeclaredIntakeFact],
    mappings: Sequence[MappingFact],
) -> dict[str, Any]:
    ce_years = None
    international = None
    trailers: list[dict[str, Any]] = []
    for row in rows:
        if row.provenance != "candidate_intake":
            continue
        if row.subject == "ce" and row.years is not None:
            ce_years = _number_text(row.years)
        elif row.subject == "international" and isinstance(row.presence, bool):
            international = row.presence
        elif row.subject == "trailer" and row.code:
            mapped = _mapping_for("trailer_intake", row.code, mappings)
            trailers.append(
                {
                    "code": row.code,
                    "mapping": "mapped" if mapped else "unmapped",
                    "target_vocabulary": mapped[0] if mapped else None,
                    "target_code": mapped[1] if mapped else None,
                }
            )
    trailers.sort(key=lambda item: item["code"])
    return {
        "provenance": "candidate_intake" if ce_years is not None or international is not None or trailers else None,
        "ce_years": ce_years,
        "international": international,
        "trailers": trailers,
    }


def _preferences(inputs: ProfileInputs) -> dict[str, Any]:
    choices = sorted(inputs.choices, key=lambda row: (row.subject, row.kind or "", row.code, row.id))
    compensation = None
    if inputs.compensation is not None:
        amount = inputs.compensation.amount
        compensation = {
            "amount": None if amount is None else format(amount.quantize(Decimal("0.01")), "f"),
            "currency": inputs.compensation.currency,
            "period": inputs.compensation.period,
        }
    return {
        "choices": [
            {"id": row.id, "subject": row.subject, "kind": row.kind, "code": row.code}
            for row in choices
        ],
        "compensation": compensation,
        "availability": {
            "available_from": _iso(inputs.available_from),
            "status": "recorded" if inputs.available_from is not None else _NONE,
            "source": "candidate_availability",
        },
    }


def _provenance(extra: Mapping[str, Any], intake_state: Mapping[str, Any]) -> dict[str, Any]:
    experience = intake_state.get("experience") if isinstance(intake_state, Mapping) else None
    years_ce = experience.get("years_ce") if isinstance(experience, Mapping) else None
    stored_eu = extra.get(_EU_FIELD) if isinstance(extra, Mapping) else None
    ce_number = _decimal(years_ce)
    eu_number = _decimal(stored_eu)
    years_ce_present = _present(years_ce)
    eu_present = _present(stored_eu)
    if years_ce_present and eu_present and ce_number is not None and eu_number is not None and ce_number == eu_number:
        origin = "ce_written_as_eu"
        declared_ce = _number_text(ce_number)
    elif not years_ce_present and eu_present:
        origin = "operator_eu_label"
        declared_ce = None
    elif eu_present:
        origin = "ambiguous"
        declared_ce = None
    else:
        origin = None
        declared_ce = None
    return {
        _EU_FIELD: {
            "stored_value": stored_eu if eu_present else None,
            "origin": origin,
            "declared_ce_years": declared_ce,
            "used_as_calculated_eu": False,
        },
        _CE_TOTAL_FIELD: {
            "stored_value": extra.get(_CE_TOTAL_FIELD) if isinstance(extra, Mapping) else None,
            "interpreted_as": "not_declared_ce",
        },
        _YEARS_FIELD: {
            "stored_value": extra.get(_YEARS_FIELD) if isinstance(extra, Mapping) and _present(extra.get(_YEARS_FIELD)) else None,
            "interpreted_as": "legacy_declared_total" if isinstance(extra, Mapping) and _present(extra.get(_YEARS_FIELD)) else _NONE,
        },
        _NON_EU_FIELD: {
            "stored_value": extra.get(_NON_EU_FIELD) if isinstance(extra, Mapping) and _present(extra.get(_NON_EU_FIELD)) else None,
            "interpreted_as": "declared_non_eu_years" if isinstance(extra, Mapping) and _present(extra.get(_NON_EU_FIELD)) else _NONE,
        },
        _INTL_FIELD: {
            "stored_value": extra.get(_INTL_FIELD) if isinstance(extra, Mapping) and extra.get(_INTL_FIELD) is not None else None,
            "interpreted_as": "declared_flag",
        },
        _TRAILER_FIELD: {
            "source": "extra",
            "codes": _string_list(extra.get(_TRAILER_FIELD) if isinstance(extra, Mapping) else None),
            "interpreted_as": "questionnaire_presence",
        },
        _ROUTE_FIELD: {
            "source": "extra",
            "codes": _string_list(extra.get(_ROUTE_FIELD) if isinstance(extra, Mapping) else None),
            "interpreted_as": "questionnaire_presence",
        },
    }


def _employment_row(job: EmploymentFact) -> dict[str, Any]:
    return {
        "id": job.id,
        "employer_name": job.employer_name,
        "country": job.country,
        "position": job.position,
        "start_date": _iso(job.start_date),
        "end_date": _iso(job.end_date),
        "driving_categories": list(job.driving_categories),
        "operation_scopes": list(job.operation_scopes),
        "movement_patterns": list(job.movement_patterns),
        "crew_modes": list(job.crew_modes),
        "work_areas": [{"kind": kind, "code": code} for kind, code in job.work_areas],
        "trailer_types": list(job.trailer_types),
        "route_types": list(job.route_types),
        "eu_routes": job.eu_routes,
    }


def _tenure_aggregate(jobs: Sequence[EmploymentFact], today: date | None) -> dict[str, Any]:
    intervals: list[tuple[date, date]] = []
    reasons: list[dict[str, str]] = []
    contributors: list[str] = []
    saw_job = False
    for job in jobs:
        saw_job = True
        outcome = _interval(job, today)
        if outcome[0] == "measured":
            intervals.append(outcome[1])
            contributors.append(job.id)
        elif outcome[0] == "inverted":
            reasons.append({"employment_id": job.id, "code": "inverted_interval", "facet": "total_tenure"})
        elif outcome[0] == "open_without_timezone":
            reasons.append({"employment_id": job.id, "code": "open_period_without_timezone", "facet": "total_tenure"})
        else:
            reasons.append({"employment_id": job.id, "code": "missing_start", "facet": "total_tenure"})
    return _finish_aggregate(intervals, reasons, contributors, presence=[], saw_signal=saw_job)


def _single_code_aggregate(
    jobs: Sequence[EmploymentFact],
    today: date | None,
    *,
    codes_of,
    exact: tuple[str, ...],
    known: set[str],
    facet: str,
) -> dict[str, Any]:
    intervals: list[tuple[date, date]] = []
    reasons: list[dict[str, str]] = []
    contributors: list[str] = []
    target = exact[0]
    raw: set[str] = set()
    saw = False
    for job in jobs:
        codes, unknown = _split_codes(codes_of(job), known)
        if target not in codes:
            continue
        saw = True
        raw.update(unknown)
        if tuple(codes) == exact and not unknown:
            outcome = _interval(job, today)
            if outcome[0] == "measured":
                intervals.append(outcome[1])
                contributors.append(job.id)
            elif outcome[0] == "inverted":
                reasons.append({"employment_id": job.id, "code": "inverted_interval", "facet": facet})
            elif outcome[0] == "open_without_timezone":
                reasons.append({"employment_id": job.id, "code": "open_period_without_timezone", "facet": facet})
            else:
                reasons.append({"employment_id": job.id, "code": "missing_start", "facet": facet})
        else:
            reasons.append({"employment_id": job.id, "code": "mixed_values", "facet": facet})
    return _finish_aggregate(
        intervals,
        reasons,
        contributors,
        presence=[target] if saw else [],
        raw=sorted(raw),
        saw_signal=saw,
    )


def _single_value_group_aggregate(
    jobs: Sequence[EmploymentFact],
    today: date | None,
    *,
    codes_of,
    known: set[str],
    facet: str,
) -> dict[str, Any]:
    """Years only for a job whose group is exactly one known code. Each code is its own duration."""

    by_code: dict[str, dict[str, Any]] = {}
    for code in sorted(known):
        by_code[code] = _single_code_aggregate(
            jobs,
            today,
            codes_of=codes_of,
            exact=(code,),
            known=known,
            facet=facet,
        )
    return by_code


def _eu_aggregate(jobs: Sequence[EmploymentFact], today: date | None) -> dict[str, Any]:
    intervals: list[tuple[date, date]] = []
    reasons: list[dict[str, str]] = []
    contributors: list[str] = []
    saw_eu = False
    for job in jobs:
        if not job.work_areas:
            continue
        kinds = [_area_eu_kind(kind, code) for kind, code in job.work_areas]
        if "eu" not in kinds:
            continue
        saw_eu = True
        if all(kind == "eu" for kind in kinds):
            outcome = _interval(job, today)
            if outcome[0] == "measured":
                intervals.append(outcome[1])
                contributors.append(job.id)
            elif outcome[0] == "inverted":
                reasons.append({"employment_id": job.id, "code": "inverted_interval", "facet": "work_areas"})
            elif outcome[0] == "open_without_timezone":
                reasons.append({"employment_id": job.id, "code": "open_period_without_timezone", "facet": "work_areas"})
            else:
                reasons.append({"employment_id": job.id, "code": "missing_start", "facet": "work_areas"})
        else:
            reasons.append({"employment_id": job.id, "code": "mixed_values", "facet": "work_areas"})
    return _finish_aggregate(
        intervals,
        reasons,
        contributors,
        presence=["eu"] if saw_eu else [],
        saw_signal=saw_eu,
    )


def _finish_aggregate(
    intervals: list[tuple[date, date]],
    reasons: list[dict[str, str]],
    contributors: list[str],
    *,
    presence: list[str],
    saw_signal: bool,
    raw: list[str] | None = None,
) -> dict[str, Any]:
    ordered_reasons = sorted(reasons, key=lambda item: (item["employment_id"], item["code"], item["facet"]))
    raw_presence = list(raw or [])
    if intervals:
        days = _merged_days(intervals)
        return {
            "status": _CALCULATED,
            "years": _years_text(days),
            "days": days,
            "presence": presence,
            "raw_presence": raw_presence,
            "contributing_employment_ids": sorted(contributors),
            "reasons": ordered_reasons,
        }
    if not saw_signal and not raw_presence:
        status = _NONE
    elif any(item["code"] == "inverted_interval" for item in ordered_reasons) and not any(
        item["code"] == "open_period_without_timezone" for item in ordered_reasons
    ) and not any(item["code"] == "mixed_values" for item in ordered_reasons):
        status = _AMBIGUOUS
    elif any(item["code"] in {"open_period_without_timezone", "missing_start"} for item in ordered_reasons) and not any(
        item["code"] == "mixed_values" for item in ordered_reasons
    ):
        status = _INSUFFICIENT
    elif any(item["code"] == "mixed_values" for item in ordered_reasons) or presence or raw_presence:
        status = _PRESENCE
    elif any(item["code"] == "inverted_interval" for item in ordered_reasons):
        status = _AMBIGUOUS
    else:
        status = _INSUFFICIENT if saw_signal else _NONE
    return {
        "status": status,
        "years": None,
        "days": None,
        "presence": presence,
        "raw_presence": raw_presence,
        "contributing_employment_ids": [],
        "reasons": ordered_reasons,
    }


def _interval(job: EmploymentFact, today: date | None) -> tuple[str, tuple[date, date] | None]:
    if job.start_date is None:
        return "missing_start", None
    end = job.end_date
    if end is None:
        if today is None:
            return "open_without_timezone", None
        end = today
    if end < job.start_date:
        return "inverted", None
    return "measured", (job.start_date, end)


def _merged_days(intervals: Sequence[tuple[date, date]]) -> int:
    ordered = sorted(intervals)
    merged: list[list[date]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1] + timedelta(days=1):
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return sum((end - start).days + 1 for start, end in merged)


def _trailer_presence(jobs: Sequence[EmploymentFact], mappings: Sequence[MappingFact]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for job in sorted(jobs, key=lambda row: row.id):
        for code in job.trailer_types:
            if code in seen:
                continue
            seen.add(code)
            mapped = _mapping_for("trailer_employment_raw", code, mappings)
            items.append(
                {
                    "code": code,
                    "vocabulary": "trailer_employment_raw",
                    "mapping": "mapped" if mapped else "unmapped",
                    "target_vocabulary": mapped[0] if mapped else None,
                    "target_code": mapped[1] if mapped else None,
                    "status": _PRESENCE,
                }
            )
    items.sort(key=lambda item: item["code"])
    return {
        "status": _PRESENCE if items else _NONE,
        "years": None,
        "days": None,
        "items": items,
    }


def _geography(jobs: Sequence[EmploymentFact]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for job in jobs:
        for kind, code in job.work_areas:
            grouped.setdefault((kind, code), [])
            if job.id not in grouped[(kind, code)]:
                grouped[(kind, code)].append(job.id)
    areas = []
    for kind, code in sorted(grouped):
        areas.append(
            {
                "kind": kind,
                "code": code,
                "resolution": _area_resolution(kind, code),
                "employment_ids": sorted(grouped[(kind, code)]),
            }
        )
    return {"work_areas": areas}


def _group_presence(jobs: Sequence[EmploymentFact], codes_of, known: set[str]) -> list[dict[str, Any]]:
    found: dict[str, str] = {}
    for job in jobs:
        codes, unknown = _split_codes(codes_of(job), known)
        for code in codes:
            found.setdefault(code, "catalog")
        for code in unknown:
            found.setdefault(code, "unmapped")
    return [{"code": code, "resolution": found[code], "status": _PRESENCE} for code in sorted(found)]


def _area_eu_kind(kind: str, code: str) -> str:
    if kind == "region" and code == "eu":
        return "eu"
    if kind == "country":
        entry = get_country_registry_entry(code)
        if entry is not None and entry.classifications.eu_member:
            return "eu"
        if entry is not None:
            return "non_eu"
    if kind == "region" and code in _known(WORK_AREA_REGION):
        return "non_eu"
    return "raw"


def _area_resolution(kind: str, code: str) -> str:
    if kind == "region" and code in _known(WORK_AREA_REGION):
        return "catalog"
    if kind == "country" and get_country_registry_entry(code) is not None:
        return "catalog"
    return "unmapped"


def _mapping_for(vocabulary: str, code: str, mappings: Sequence[MappingFact]) -> tuple[str, str] | None:
    for item in mappings:
        if item.source_vocabulary == vocabulary and item.source_code == code:
            return item.target_vocabulary, item.target_code
    return None


def _split_codes(codes: Sequence[str], known: set[str]) -> tuple[list[str], list[str]]:
    catalog: list[str] = []
    raw: list[str] = []
    for code in codes:
        if code in known and code not in catalog:
            catalog.append(code)
        elif code not in known and code not in raw:
            raw.append(code)
    return catalog, raw


def _driving_codes(job: EmploymentFact) -> tuple[str, ...]:
    return tuple(_unique(code.strip().upper() for code in job.driving_categories if code and code.strip()))


def _scope_codes(job: EmploymentFact) -> tuple[str, ...]:
    return tuple(_unique(code.strip().lower() for code in job.operation_scopes if code and code.strip()))


def _movement_codes(job: EmploymentFact) -> tuple[str, ...]:
    return tuple(_unique(code.strip().lower() for code in job.movement_patterns if code and code.strip()))


def _crew_codes(job: EmploymentFact) -> tuple[str, ...]:
    return tuple(_unique(code.strip().lower() for code in job.crew_modes if code and code.strip()))


def _known(vocabulary: str) -> set[str]:
    return {code for name, code in catalog_code_pairs() if name == vocabulary}


def _known_driving_categories() -> set[str]:
    from backend.app.services.operator_facts_surface import licence_category_codes

    return set(licence_category_codes())


def _workspace_today(timezone_name: str | None, now: datetime) -> date | None:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    name = str(timezone_name or "").strip()
    if not name or now.tzinfo is None:
        return None
    try:
        zone = ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return None
    return now.astimezone(zone).date()


def _years_text(days: int) -> str:
    return format((Decimal(days) / _YEAR_DAYS).quantize(_YEAR_QUANT, rounding=ROUND_HALF_UP), "f")


def _number_text(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str) and value.strip():
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return None
    return None


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _unique(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _areas(value: Any) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        return ()
    out: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        kind = str(item.get("kind") or "").strip().lower()
        raw_code = str(item.get("code") or "").strip()
        if kind not in {"country", "region"} or not raw_code:
            continue
        code = raw_code.upper() if kind == "country" else raw_code.lower()
        pair = (kind, code)
        if pair not in out:
            out.append(pair)
    return tuple(out)


def _texts(value: Any, *, upper: bool = False, lower: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        if upper:
            text = text.upper()
        elif lower:
            text = text.lower()
        if text not in out:
            out.append(text)
    return tuple(out)


def _employment_fact(row: CandidateEmployment) -> EmploymentFact:
    return EmploymentFact(
        id=str(row.id),
        employer_name=row.employer_name,
        country=(row.country or "").strip().upper() or None,
        position=row.position,
        start_date=row.start_date,
        end_date=row.end_date,
        driving_categories=_texts(row.driving_categories, upper=True),
        operation_scopes=_texts(row.operation_scopes, lower=True),
        movement_patterns=_texts(row.movement_patterns, lower=True),
        crew_modes=_texts(row.crew_modes, lower=True),
        work_areas=_areas(row.work_areas),
        trailer_types=_texts(row.trailer_types),
        route_types=_texts(row.route_types),
        eu_routes=row.eu_routes,
    )


async def load_professional_profile(
    session: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Load one tenant's candidate and project it. Performs no writes."""

    candidate = await session.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
            Candidate.deleted_at.is_(None),
        )
    )
    if candidate is None:
        raise ProfessionalProfileNotFound(candidate_id)
    employments = (
        await session.scalars(
            select(CandidateEmployment).where(
                CandidateEmployment.tenant_id == tenant_id,
                CandidateEmployment.candidate_id == candidate_id,
            )
        )
    ).all()
    constraints = (
        await session.scalars(
            select(CandidateProfessionalConstraint).where(
                CandidateProfessionalConstraint.tenant_id == tenant_id,
                CandidateProfessionalConstraint.candidate_id == candidate_id,
            )
        )
    ).all()
    choices = (
        await session.scalars(
            select(CandidatePreferenceChoice).where(
                CandidatePreferenceChoice.tenant_id == tenant_id,
                CandidatePreferenceChoice.candidate_id == candidate_id,
            )
        )
    ).all()
    declared_rows = (
        await session.scalars(
            select(CandidateDeclaredFact).where(
                CandidateDeclaredFact.tenant_id == tenant_id,
                CandidateDeclaredFact.candidate_id == candidate_id,
            )
        )
    ).all()
    availability = await session.scalar(
        select(CandidateAvailability).where(
            CandidateAvailability.tenant_id == tenant_id,
            CandidateAvailability.candidate_id == candidate_id,
        )
    )
    compensation = await session.scalar(
        select(CandidateCompensationExpectation).where(
            CandidateCompensationExpectation.tenant_id == tenant_id,
            CandidateCompensationExpectation.candidate_id == candidate_id,
        )
    )
    timezone_name = await session.scalar(select(Tenant.timezone).where(Tenant.id == tenant_id))
    mappings = (await session.scalars(select(ProfessionalCodeMapping))).all()
    extra = candidate._get_extra()
    personal = candidate._get_personal_data()
    intake = _as_dict(candidate.intake_state)
    moment = now or datetime.now(timezone.utc)
    return resolve_professional_profile(
        ProfileInputs(
            candidate_id=str(candidate.id),
            tenant_id=tenant_id,
            timezone_name=timezone_name,
            now=moment,
            personal_data=personal,
            extra=extra,
            intake_state=intake,
            employments=tuple(_employment_fact(row) for row in employments),
            constraints=tuple(
                ConstraintFact(
                    id=str(row.id),
                    subject=row.subject,
                    code=row.code,
                    effect=row.effect,
                    source=row.source,
                    valid_from=row.valid_from,
                    valid_to=row.valid_to,
                    note=row.note,
                )
                for row in constraints
            ),
            choices=tuple(
                ChoiceFact(id=str(row.id), subject=row.subject, kind=row.kind, code=row.code)
                for row in choices
            ),
            compensation=None
            if compensation is None
            else CompensationFact(
                amount=compensation.amount,
                currency=compensation.currency,
                period=compensation.period,
            ),
            available_from=None if availability is None else availability.available_from,
            declared_intake=tuple(
                DeclaredIntakeFact(
                    subject=row.subject,
                    code=row.code,
                    years=row.years,
                    presence=row.presence,
                    provenance=row.provenance,
                )
                for row in declared_rows
            ),
            mappings=tuple(
                MappingFact(
                    source_vocabulary=row.source_vocabulary,
                    source_code=row.source_code,
                    target_vocabulary=row.target_vocabulary,
                    target_code=row.target_code,
                )
                for row in mappings
            ),
        )
    )


__all__ = [
    "DeclaredIntakeFact",
    "EmploymentFact",
    "ProfessionalProfileNotFound",
    "ProfileInputs",
    "load_professional_profile",
    "resolve_professional_profile",
]
