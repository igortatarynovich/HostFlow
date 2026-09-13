"""Temporary read-shim: ready_for_employment.v1 → legacy snapshot-shaped namespace (RSO-2A/B).

Deprecated. Removal = RSO-2E.

Locks:
- May reproduce legacy *shape*.
- MUST NOT reproduce legacy *authority*: current person/doc/vacancy values come from
  live authorities when provided; manifest supplies as-of / historical only.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from backend.app.reference.ready_for_employment import CONTRACT_ID

COMPAT_MARKER = "_rso2_compat_projection"
COMPAT_DEPRECATED = True


def is_ready_for_employment_manifest(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload, Mapping):
        return False
    if payload.get(COMPAT_MARKER):
        return False
    return str(payload.get("contract_id") or "").strip() == CONTRACT_ID


def project_manifest_to_legacy_snapshot_shape(
    manifest: Mapping[str, Any] | None,
    *,
    live_person: Mapping[str, Any] | None = None,
    live_documents: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a legacy-shaped dict for temporary consumers.

    Current identity/contacts prefer ``live_person`` over manifest identity_facts.
    Manifest values are retained under ``as_of`` for explicit historical reads.
    """
    if not is_ready_for_employment_manifest(manifest):
        return dict(manifest) if isinstance(manifest, Mapping) else {}

    m = dict(manifest)
    person = m.get("person") if isinstance(m.get("person"), Mapping) else {}
    identity = person.get("identity_facts") if isinstance(person.get("identity_facts"), Mapping) else {}
    contacts_m = person.get("contacts") if isinstance(person.get("contacts"), Mapping) else {}
    live = dict(live_person) if isinstance(live_person, Mapping) else {}

    def _live_or_as_of(key: str, *as_of_keys: str) -> Any:
        if live.get(key) not in (None, ""):
            return live.get(key)
        for k in as_of_keys or (key,):
            if identity.get(k) not in (None, ""):
                return identity.get(k)
            if contacts_m.get(k) not in (None, ""):
                return contacts_m.get(k)
        return None

    first = _live_or_as_of("first_name")
    last = _live_or_as_of("last_name")
    candidate_block: dict[str, Any] = {
        "id": str(person.get("candidate_id") or person.get("person_id") or ""),
        "first_name": first,
        "last_name": last,
        "name": {"first_name": first or "", "last_name": last or ""},
        "contacts": {
            "email": _live_or_as_of("email"),
            "phone": _live_or_as_of("phone"),
            "phone_country_code": _live_or_as_of("phone_country_code"),
        },
        "email": _live_or_as_of("email"),
        "phone": _live_or_as_of("phone"),
        "citizenship": _live_or_as_of("citizenship"),
        "birth_date": _live_or_as_of("birth_date"),
        "work_country": _live_or_as_of("work_country"),
        "country_code": _live_or_as_of("country_code"),
        "as_of": {
            "citizenship": identity.get("citizenship"),
            "birth_date": identity.get("birth_date"),
            "work_country": identity.get("work_country"),
            "first_name": identity.get("first_name"),
            "last_name": identity.get("last_name"),
            "contacts": dict(contacts_m),
        },
    }

    target = m.get("target_work") if isinstance(m.get("target_work"), Mapping) else {}
    refs = m.get("context_refs") if isinstance(m.get("context_refs"), Mapping) else {}
    application_block = {
        "application_id": refs.get("application_id"),
        "vacancy_id": target.get("vacancy_id"),
        "vacancy_title": target.get("vacancy_title_as_of"),
        "recruiter": {"id": refs.get("recruiter_id"), "name": None},
    }

    docs_out: list[dict[str, Any]] = []
    if live_documents:
        for d in live_documents:
            if not isinstance(d, Mapping):
                continue
            docs_out.append(dict(d))
    else:
        evidence = m.get("evidence") if isinstance(m.get("evidence"), Mapping) else {}
        for ref in evidence.get("document_refs") or []:
            if not isinstance(ref, Mapping):
                continue
            docs_out.append(
                {
                    "type": ref.get("doc_type") or "",
                    "status": ref.get("status") or "",
                    "document_id": ref.get("document_id"),
                    "canonical": {
                        "code": ref.get("canonical_code"),
                        "category": None,
                        "criticality": None,
                        "fallback_used": False,
                    },
                    # metadata only — not a file copy
                }
            )

    fits = m.get("fits_decision") if isinstance(m.get("fits_decision"), Mapping) else {}
    rf = m.get("recruitment_facts") if isinstance(m.get("recruitment_facts"), Mapping) else {}

    return {
        COMPAT_MARKER: True,
        "compat_deprecated": COMPAT_DEPRECATED,
        "contract_id": CONTRACT_ID,
        "candidate": candidate_block,
        "application": application_block,
        "vacancy": {"title": target.get("vacancy_title_as_of"), "id": target.get("vacancy_id")},
        "vacancy_title": target.get("vacancy_title_as_of"),
        "documents": docs_out,
        "documents_count": len(docs_out),
        "expected_documents": [],
        "requirement_fulfillments": list(rf.get("requirement_verdicts_as_of") or []),
        "notes_summary": None,
        "source": {"lead_id": None, "source": None, "campaign": None},
        "handoff": {
            "handoff_id": refs.get("handoff_id"),
            "created_at": refs.get("emitted_at"),
            "requested_by": {"user_id": fits.get("actor_id"), "name": None},
        },
        "integrity": {
            "snapshot_version": "ready_for_employment.v1",
            "created_at": refs.get("emitted_at"),
        },
        "fits_decision": dict(fits),
        "citizenship": candidate_block.get("citizenship"),
        "work_country": candidate_block.get("work_country"),
    }


def coerce_snapshot_payload_for_legacy_readers(
    payload: Mapping[str, Any] | None,
    *,
    live_person: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """If RFE manifest → compat projection; else pass through legacy payload."""
    if is_ready_for_employment_manifest(payload):
        return project_manifest_to_legacy_snapshot_shape(payload, live_person=live_person)
    return dict(payload) if isinstance(payload, Mapping) else {}
