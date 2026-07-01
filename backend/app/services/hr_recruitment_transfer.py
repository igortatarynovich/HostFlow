"""Shared recruitment → HR field flattening (handoff snapshot, employee snapshot, verification)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.services.hr_profile_address import promote_address_fields
from backend.app.services.candidate_employments import list_employments


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed:
                return trimmed
            continue
        return value
    return None


def _iso_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if text else None


def _employment_row_dict(row: CandidateEmployment) -> dict[str, Any]:
    return {
        "employer_name": row.employer_name,
        "country": row.country,
        "position": row.position,
        "date_from": _iso_date(row.start_date),
        "date_to": _iso_date(row.end_date),
        "start_date": _iso_date(row.start_date),
        "end_date": _iso_date(row.end_date),
    }


def _format_employment_line(item: dict[str, Any]) -> str:
    chunks = [
        str(item.get("position") or "").strip(),
        str(item.get("employer_name") or item.get("company") or "").strip(),
        str(item.get("country") or "").strip(),
    ]
    period = " – ".join(
        p
        for p in (
            str(item.get("date_from") or item.get("start_date") or "").strip(),
            str(item.get("date_to") or item.get("end_date") or "").strip(),
        )
        if p
    )
    if period:
        chunks.append(period)
    return " · ".join(c for c in chunks if c)


def _experience_from_extra(extra: dict[str, Any]) -> tuple[list[dict[str, Any]], Optional[str], Optional[str]]:
    raw = extra.get("employment_history") or extra.get("employments") or extra.get("experience")
    rows: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                rows.append(dict(item))
    summary = _first_non_empty(extra.get("experience_summary"), extra.get("experience"))
    if isinstance(summary, (list, dict)):
        summary = None
    last_position = _first_non_empty(extra.get("last_position"))
    if not summary and rows:
        summary = "\n".join(_format_employment_line(r) for r in rows if _format_employment_line(r))
    if not last_position and rows:
        last_position = _first_non_empty(rows[0].get("position"), rows[0].get("employer_name"))
    return rows, str(summary).strip() if summary else None, str(last_position).strip() if last_position else None


def flatten_recruitment_candidate_fields(candidate: Candidate) -> dict[str, Any]:
    """Identity + contacts + address + country fields used across HR transfer paths."""
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    contacts = candidate._get_contacts() if hasattr(candidate, "_get_contacts") else {}
    if not isinstance(personal, dict):
        personal = {}
    if not isinstance(extra, dict):
        extra = {}
    if not isinstance(contacts, dict):
        contacts = {}

    first = str(candidate.first_name or "").strip()
    last = str(candidate.last_name or "").strip()
    full_name = " ".join(p for p in (first, last) if p).strip() or None

    phone_country_code = _first_non_empty(
        getattr(candidate, "phone_country_code", None),
        contacts.get("phone_country_code"),
        extra.get("phone_country_code"),
        extra.get("phone_prefix"),
    )
    country_code = _first_non_empty(
        personal.get("country_code"),
        extra.get("country_code"),
    )
    citizenship = _first_non_empty(
        personal.get("citizenship"),
        extra.get("citizenship"),
        personal.get("nationality"),
        extra.get("nationality"),
    )
    work_country = _first_non_empty(
        personal.get("work_country"),
        extra.get("work_country"),
        personal.get("country_of_work"),
        extra.get("country_of_work"),
    )
    birth_date = _iso_date(
        _first_non_empty(
            personal.get("birth_date"),
            extra.get("birth_date"),
            getattr(candidate, "birth_date", None),
        )
    )

    out: dict[str, Any] = {
        "first_name": first or None,
        "last_name": last or None,
        "full_name": full_name,
        "email": _first_non_empty(contacts.get("email"), candidate.email, personal.get("email"), extra.get("email")),
        "phone": _first_non_empty(contacts.get("phone"), candidate.phone, personal.get("phone"), extra.get("phone")),
        "phone_country_code": phone_country_code,
        "citizenship": citizenship,
        "work_country": work_country,
        "country_code": country_code,
        "birth_date": birth_date,
        "experience_eu_years": extra.get("experience_eu_years"),
    }

    address_raw = _first_non_empty(
        personal.get("address"),
        extra.get("address"),
        getattr(candidate, "address", None),
    )
    if address_raw is not None:
        out["address"] = address_raw

    promote_address_fields(
        out,
        personal.get("address"),
        extra.get("address"),
        contacts.get("address"),
        address_raw,
    )
    return out


async def enrich_snapshot_experience(
    db: AsyncSession,
    tenant_id: str,
    candidate: Candidate,
    target: dict[str, Any],
) -> None:
    """Attach employment history rows + summary fields to a snapshot dict."""
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    if not isinstance(extra, dict):
        extra = {}

    rows = [
        _employment_row_dict(r)
        for r in await list_employments(db, tenant_id, str(candidate.id))
    ]
    extra_rows, extra_summary, extra_last = _experience_from_extra(extra)

    if rows:
        target["employments"] = rows
        target["experience_summary"] = "\n".join(
            _format_employment_line(r) for r in rows if _format_employment_line(r)
        )
        target["last_position"] = _first_non_empty(
            rows[0].get("position"),
            rows[0].get("employer_name"),
        )
    elif extra_rows:
        target["employments"] = extra_rows
        if extra_summary:
            target["experience_summary"] = extra_summary
        if extra_last:
            target["last_position"] = extra_last
    elif extra_summary:
        target["experience_summary"] = extra_summary
    if extra_last and not target.get("last_position"):
        target["last_position"] = extra_last
    if extra.get("experience_eu_years") is not None and target.get("experience_eu_years") is None:
        target["experience_eu_years"] = extra.get("experience_eu_years")


def merge_flat_into_handoff_candidate(namespace: dict[str, Any], flat: dict[str, Any]) -> dict[str, Any]:
    """Merge flattened recruitment fields into handoff.candidate namespace."""
    out = dict(namespace) if namespace else {}
    cand = dict(out.get("candidate") or {})
    for key, value in flat.items():
        if value is None or value == "":
            continue
        if key == "address":
            if isinstance(value, dict):
                promote_address_fields(cand, value)
                cand.setdefault("address", value)
            elif isinstance(value, str) and value.strip():
                cand.setdefault("address", value.strip())
            continue
        cand.setdefault(key, value)
    out["candidate"] = cand
    return out
