"""HR host read-model: live authorities + manifest Why Ready.

Operational currents come from live Person / Vacancy / Employer / Hub.
Manifest supplies Why Ready (fits / verdicts / evidence refs / as-of) only.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.recruitment.public.models import Candidate
from backend.app.modules.boundary.public.models import CandidateHandoff
from backend.app.modules.boundary.public.ready import is_ready_for_employment_manifest
from backend.app.services.hr_recruitment_transfer import flatten_recruitment_candidate_fields


def live_person_flat(candidate: Candidate | None) -> dict[str, Any]:
    """Current identity/contacts from live Person (= Candidate)."""
    if candidate is None:
        return {}
    flat = flatten_recruitment_candidate_fields(candidate)
    contacts_data = getattr(candidate, "contacts", None)
    if isinstance(contacts_data, dict):
        for key in ("email", "phone", "phone_country_code"):
            if contacts_data.get(key) and not flat.get(key):
                flat[key] = contacts_data.get(key)
    first = str(getattr(candidate, "first_name", None) or "").strip()
    last = str(getattr(candidate, "last_name", None) or "").strip()
    if first:
        flat["first_name"] = first
    if last:
        flat["last_name"] = last
    if first or last:
        flat["full_name"] = f"{first} {last}".strip()
    return flat


def display_name_from_live_person(flat: Mapping[str, Any] | None) -> str | None:
    if not isinstance(flat, Mapping):
        return None
    full = str(flat.get("full_name") or "").strip()
    if full:
        return full
    parts = [
        str(flat.get("first_name") or "").strip(),
        str(flat.get("last_name") or "").strip(),
    ]
    name = " ".join(p for p in parts if p).strip()
    if name:
        return name
    email = str(flat.get("email") or "").strip()
    return email or None


def build_why_ready_from_manifest(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Backend Why Ready read model from ready_for_employment.v1.

    FE must display this object — not re-aggregate from raw snapshot keys.
    """
    if not is_ready_for_employment_manifest(payload):
        return None
    m = dict(payload)
    person = m.get("person") if isinstance(m.get("person"), Mapping) else {}
    identity = person.get("identity_facts") if isinstance(person.get("identity_facts"), Mapping) else {}
    contacts = person.get("contacts") if isinstance(person.get("contacts"), Mapping) else {}
    target = m.get("target_work") if isinstance(m.get("target_work"), Mapping) else {}
    refs = m.get("context_refs") if isinstance(m.get("context_refs"), Mapping) else {}
    rf = m.get("recruitment_facts") if isinstance(m.get("recruitment_facts"), Mapping) else {}
    evidence = m.get("evidence") if isinstance(m.get("evidence"), Mapping) else {}
    fits = m.get("fits_decision") if isinstance(m.get("fits_decision"), Mapping) else {}

    document_refs = [
        dict(r)
        for r in (evidence.get("document_refs") or [])
        if isinstance(r, Mapping)
    ]
    verdicts = [
        dict(v)
        for v in (rf.get("requirement_verdicts_as_of") or [])
        if isinstance(v, Mapping)
    ]

    return {
        "contract_id": str(m.get("contract_id") or ""),
        "fits_decision": dict(fits) if fits else None,
        "requirement_verdicts_as_of": verdicts,
        "evidence_refs": document_refs,
        "target_work_as_of": {
            "vacancy_id": target.get("vacancy_id"),
            "employer_id": target.get("employer_id"),
            "vacancy_title_as_of": target.get("vacancy_title_as_of"),
        },
        "context_refs": {
            "application_id": refs.get("application_id"),
            "handoff_id": refs.get("handoff_id"),
            "recruiter_id": refs.get("recruiter_id"),
            "emitted_at": refs.get("emitted_at"),
        },
        "as_of": {
            "identity": {
                "first_name": identity.get("first_name"),
                "last_name": identity.get("last_name"),
                "citizenship": identity.get("citizenship"),
                "birth_date": identity.get("birth_date"),
                "work_country": identity.get("work_country"),
                "country_code": identity.get("country_code"),
            },
            "contacts": {
                "email": contacts.get("email"),
                "phone": contacts.get("phone"),
                "phone_country_code": contacts.get("phone_country_code"),
            },
            "candidate_stage": rf.get("candidate_stage_as_of"),
        },
    }


async def load_live_target_work(
    db: AsyncSession,
    *,
    candidate: Candidate | None,
    handoff: CandidateHandoff | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Current vacancy/employer labels from live entities; fall back to as-of title only if needed."""
    from backend.app.models.company import Company
    from backend.app.modules.recruitment.public.models import Vacancy

    vac_id: str | None = None
    employer_id: str | None = None
    if candidate is not None:
        vac_id = str(getattr(candidate, "vacancy_id", None) or "").strip() or None
        employer_id = str(getattr(candidate, "company_id", None) or "").strip() or None
    if handoff is not None:
        if not employer_id:
            employer_id = (
                str(getattr(handoff, "client_company_id", None) or "").strip()
                or str(getattr(handoff, "to_company_id", None) or "").strip()
                or None
            )
    if is_ready_for_employment_manifest(manifest):
        target = manifest.get("target_work") if isinstance(manifest.get("target_work"), Mapping) else {}
        if not vac_id:
            vac_id = str(target.get("vacancy_id") or "").strip() or None
        if not employer_id:
            employer_id = str(target.get("employer_id") or "").strip() or None

    vacancy_title: str | None = None
    employer_name: str | None = None
    if vac_id:
        vac = await db.get(Vacancy, vac_id)
        if vac:
            vacancy_title = str(getattr(vac, "title", None) or "").strip() or None
            if not employer_id:
                employer_id = str(getattr(vac, "company_id", None) or "").strip() or None
    if employer_id:
        company = await db.get(Company, employer_id)
        if company:
            employer_name = str(getattr(company, "name", None) or "").strip() or None

    # As-of title only when live vacancy title missing (explicit historical fallback).
    if not vacancy_title and is_ready_for_employment_manifest(manifest):
        target = manifest.get("target_work") if isinstance(manifest.get("target_work"), Mapping) else {}
        as_of = str(target.get("vacancy_title_as_of") or "").strip() or None
        if as_of:
            vacancy_title = as_of

    out: dict[str, Any] = {}
    if vac_id:
        out["vacancy_id"] = vac_id
    if vacancy_title:
        out["vacancy_title"] = vacancy_title
    if employer_id:
        out["employer_id"] = employer_id
    if employer_name:
        out["employer_name"] = employer_name
    return out


def build_transfer_summary_live(
    *,
    live_person: Mapping[str, Any] | None,
    live_target: Mapping[str, Any] | None = None,
    documents_count: int | None = None,
) -> dict[str, Any] | None:
    """Operational transfer chips from live Person + live target work."""
    person = dict(live_person) if isinstance(live_person, Mapping) else {}
    target = dict(live_target) if isinstance(live_target, Mapping) else {}
    out = {
        "first_name": person.get("first_name"),
        "last_name": person.get("last_name"),
        "email": person.get("email"),
        "phone": person.get("phone"),
        "citizenship": person.get("citizenship"),
        "work_country": person.get("work_country"),
        "vacancy_title": target.get("vacancy_title"),
        "employer_name": target.get("employer_name"),
        "documents_count": documents_count,
    }
    cleaned = {k: v for k, v in out.items() if v not in (None, "")}
    return cleaned or None


def live_candidate_summary(candidate: Candidate | None) -> dict[str, Any]:
    """Queue/hub name chip from live Person (not shim)."""
    flat = live_person_flat(candidate)
    return {
        "candidate_id": str(candidate.id) if candidate is not None else None,
        "first_name": flat.get("first_name"),
        "last_name": flat.get("last_name"),
        "display_name": display_name_from_live_person(flat),
    }


def manifest_doc_status_as_of(payload: Mapping[str, Any] | None, doc_type: str) -> str | None:
    """Historical/as-of document status from RFE evidence refs only.

    Not an operational Hub status — callers must prefer Hub for current.
    """
    from backend.app.modules.documents.public.types import normalize_doc_type

    if not is_ready_for_employment_manifest(payload):
        return None
    canon = normalize_doc_type(doc_type)
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), Mapping) else {}
    for ref in evidence.get("document_refs") or []:
        if not isinstance(ref, Mapping):
            continue
        t = normalize_doc_type(str(ref.get("canonical_code") or ref.get("doc_type") or ""))
        if t == canon:
            return str(ref.get("status") or "").strip() or None
    return None


def apply_live_person_to_profile_namespace(
    namespace: dict[str, Any] | None,
    flat: Mapping[str, Any] | None,
    *,
    as_of: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Overwrite current candidate fields with live Person; attach as-of separately."""
    out = dict(namespace) if namespace else {}
    cand = dict(out.get("candidate") or {})
    for key, value in (flat or {}).items():
        if value in (None, ""):
            continue
        cand[key] = value
    if as_of:
        cand["as_of"] = dict(as_of)
    out["candidate"] = cand
    return out


def profile_application_from_manifest_and_live(
    *,
    live_target: Mapping[str, Any] | None,
    why_ready: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    target = dict(live_target) if isinstance(live_target, Mapping) else {}
    why = dict(why_ready) if isinstance(why_ready, Mapping) else {}
    refs = why.get("context_refs") if isinstance(why.get("context_refs"), Mapping) else {}
    app: dict[str, Any] = {}
    if refs.get("application_id"):
        app["application_id"] = refs.get("application_id")
    if target.get("vacancy_id"):
        app["vacancy_id"] = target.get("vacancy_id")
    if target.get("vacancy_title"):
        app["vacancy_title"] = target.get("vacancy_title")
    return app or None
