"""Resolve a legalization requirement from Hub evidence.

Applicability decides what can apply. This module decides whether that
requirement is actually confirmed. It does not copy documents and it does not
choose a different basis. Readiness reads only the resolved status.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from backend.app.reference.legal_eligibility_chain import citizenship_class
from backend.app.reference.legalization_catalog import exemption_catalog, stay_catalog, work_procedure_catalog

_APPROVED = frozenset({"approved", "verified", "completed"})
_REJECTED = frozenset({"rejected", "cancelled"})
_ORDERED = frozenset({"requested", "to_prepare", "ordered"})
_RECEIVED = frozenset({"received", "issued", "registered", "delivered"})

def readiness_from_resolved(resolved: Mapping[str, Any]) -> dict[str, Any]:
    """One reading of the resolved pair. It does not look at documents again."""

    blockers: list[dict[str, Any]] = []
    for requirement in ("residence", "work"):
        status = resolved.get(requirement)
        if status == "confirmed":
            continue
        blockers.append({
            "requirement": requirement,
            "status": status,
            "missing": list(resolved.get(f"missing_{requirement}") or []),
            "detail": resolved.get(f"{requirement}_detail"),
        })
    return {"ready": not blockers, "blockers": blockers}


def apply_hub_resolution(
    reading: Mapping[str, Any],
    documents: list[Mapping[str, Any]],
    *,
    facts: Mapping[str, Any],
    employment: Mapping[str, Any] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Replace the provisional statuses with the Hub result. Applicability stays."""

    current = dict(reading)
    resolved = dict(current.get("resolved") or {})
    day = today or date.today()
    presence = facts.get("document_presence") if isinstance(facts.get("document_presence"), Mapping) else {}
    work = facts.get("work") if isinstance(facts.get("work"), Mapping) else {}
    context = employment or {}

    residence, residence_missing, residence_detail = _residence(current, documents, facts, presence, day)
    work_status, work_missing, work_detail = _work(
        current,
        documents,
        facts,
        work,
        presence,
        context,
        day,
        residence_status=residence,
    )
    resolved.update({
        "residence": residence,
        "work": work_status,
        "missing_residence": residence_missing,
        "missing_work": work_missing,
        "residence_detail": residence_detail,
        "work_detail": work_detail,
    })
    current["resolved"] = resolved
    current["readiness"] = readiness_from_resolved(resolved)
    return current


def _residence(
    reading: Mapping[str, Any],
    documents: list[Mapping[str, Any]],
    facts: Mapping[str, Any],
    presence: Mapping[str, Any],
    today: date,
) -> tuple[str, list[str], str | None]:
    if (reading.get("resolved") or {}).get("residence") == "needs_review":
        return "needs_review", [], "basis_not_applicable"
    selection = reading.get("selection") or {}
    if selection.get("stay_required") is False:
        return _execute_exemption(
            selection.get("stay_exemption") or "",
            reading,
            documents,
            facts,
            presence,
            {},
            today,
            manual=bool(selection.get("stay_manual")),
            residence_status="confirmed",
        )
    selected = reading.get("selected_stay")
    if not selected:
        return "needs_document", ["stay_basis"], None
    return _execute_evidence(selected, documents, facts, presence, today)


def _work(
    reading: Mapping[str, Any],
    documents: list[Mapping[str, Any]],
    facts: Mapping[str, Any],
    work: Mapping[str, Any],
    presence: Mapping[str, Any],
    employment: Mapping[str, Any],
    today: date,
    *,
    residence_status: str,
) -> tuple[str, list[str], str | None]:
    selection = reading.get("selection") or {}
    if residence_status == "needs_review" and selection.get("work_required") is True:
        return "needs_review", [], "basis_not_applicable"
    if selection.get("work_required") is False:
        return _execute_exemption(
            selection.get("work_exemption") or "",
            reading,
            documents,
            facts,
            presence,
            employment,
            today,
            manual=bool(selection.get("work_manual")),
            residence_status=residence_status,
        )
    procedure = _procedure(work)
    if procedure is not None:
        return _execute_procedure(procedure, documents, presence, today, employment)
    if work.get("work_authorization_basis") == "included_in_stay":
        return _execute_work_effect(reading.get("selected_stay") or {}, documents, presence, employment, today, residence_status)
    return "needs_permit", [], None


def _execute_exemption(
    code: str,
    reading: Mapping[str, Any],
    documents: list[Mapping[str, Any]],
    facts: Mapping[str, Any],
    presence: Mapping[str, Any],
    employment: Mapping[str, Any],
    today: date,
    *,
    manual: bool,
    residence_status: str,
) -> tuple[str, list[str], str | None]:
    contract = next((row for row in exemption_catalog() if row["code"] == code), {"confirm": "never"})
    mode = contract.get("confirm")
    if mode == "citizenship_class" and not manual:
        classes = {citizenship_class(item) for item in _citizenships(facts)}
        if contract.get("citizenship_class") in classes:
            return "confirmed", [], None
    if mode == "basis":
        entry = _catalog_basis(str(contract.get("basis") or ""))
        status, missing, detail = _execute_evidence(entry, documents, facts, presence, today, employment=None)
        condition = contract.get("work_condition") or entry.get("work_condition")
        if status == "confirmed" and condition and not _condition(condition, entry, documents):
            return "needs_review", [], "not_polish_status"
        return status, missing, detail
    if mode == "work_effect" and residence_status == "confirmed":
        return _execute_work_effect(reading.get("selected_stay") or {}, documents, presence, employment, today, residence_status)
    return "needs_verification", [], "override" if manual else None


def _execute_evidence(
    entry: Mapping[str, Any],
    documents: list[Mapping[str, Any]],
    facts: Mapping[str, Any],
    presence: Mapping[str, Any],
    today: date,
    employment: Mapping[str, Any] | None = None,
) -> tuple[str, list[str], str | None]:
    if entry.get("confirm") == "never" or not entry.get("evidence"):
        return "needs_verification", [], None
    missing: list[str] = []
    detail: str | None = None
    worst: str | None = None
    for group in entry.get("evidence") or []:
        metadata = tuple(group.get("metadata") or [])
        state, state_detail = _document_state(
            documents,
            presence,
            today,
            codes=tuple(group.get("codes") or []),
            require_number="number" in metadata,
            require_expiry="expire_date" in metadata,
            employment=employment,
        )
        if state != "approved":
            missing.append(str(group.get("label") or ""))
            if worst is None:
                worst = state
                detail = state_detail or state
    if missing:
        return _outcome(worst), [item for item in missing if item], detail
    for rule in entry.get("validity_rules") or []:
        failed = _validity(str(rule), entry, documents, facts, today)
        if failed is not None:
            return failed
    return "confirmed", [], None


def _execute_work_effect(
    entry: Mapping[str, Any],
    documents: list[Mapping[str, Any]],
    presence: Mapping[str, Any],
    employment: Mapping[str, Any],
    today: date,
    residence_status: str,
) -> tuple[str, list[str], str | None]:
    effect = entry.get("work_effect")
    if effect == "free_access" and residence_status == "confirmed":
        return "confirmed", [], None
    if effect == "free_access_if_polish":
        if residence_status != "confirmed":
            return "needs_verification", [], None
        if _condition(entry.get("work_condition"), entry, documents):
            return "confirmed", [], None
        return "needs_review", [], "not_polish_status"
    if effect == "conditional":
        groups = list(entry.get("evidence") or [])
        dependent = groups[-1] if len(groups) > 1 else None
        if dependent is None:
            return "needs_verification", [], "conditions"
        state, detail = _document_state(
            documents,
            presence,
            today,
            codes=tuple(dependent.get("codes") or []),
            require_number="number" in tuple(dependent.get("metadata") or []),
            require_expiry=False,
            employment=employment,
        )
        if state != "approved":
            return _outcome(state), [str(dependent.get("label") or "")], detail or state
        matched = _matching(documents, tuple(dependent.get("codes") or []))
        meta = matched.get("meta") if isinstance(matched.get("meta"), Mapping) else {}
        if meta.get("work_allowed") is False:
            return "not_confirmed", [], "work_not_granted"
        employer = _employer(meta)
        expected = str(employment.get("client_company_id") or "").strip()
        if employer and expected and employer != expected:
            return "needs_review", [], "employment_mismatch"
        if meta.get("work_allowed") is True:
            return "confirmed", [], None
        return "needs_verification", [], "conditions"
    return "needs_verification", [], None


def _execute_procedure(
    procedure: Mapping[str, Any],
    documents: list[Mapping[str, Any]],
    presence: Mapping[str, Any],
    today: date,
    employment: Mapping[str, Any],
) -> tuple[str, list[str], str | None]:
    metadata = tuple(procedure.get("metadata") or [])
    state, detail = _document_state(
        documents,
        presence,
        today,
        codes=tuple(procedure.get("documents") or []),
        require_number="number" in metadata,
        require_expiry="expire_date" in metadata,
        employment=employment if procedure.get("match_employer") else None,
    )
    label = str(procedure.get("code") or "")
    if state == "ordered":
        return "ordered", [], None
    if state == "approved":
        return "confirmed", [], None
    return _outcome(state), [label], detail or state


def _procedure(work: Mapping[str, Any]) -> dict[str, Any] | None:
    procedure_type = str(work.get("procedure_type") or "")
    for row in work_procedure_catalog():
        if procedure_type in set(row.get("procedure_types") or []):
            return row
    return None


def _catalog_basis(code: str) -> dict[str, Any]:
    for entry in stay_catalog():
        if entry["code"] == code:
            return entry
    return {"code": code, "confirm": "never", "evidence": []}


def _condition(rule: str | None, entry: Mapping[str, Any], documents: list[Mapping[str, Any]]) -> bool:
    if rule != "polish_issuing_country":
        return True
    groups = list(entry.get("evidence") or [])
    if not groups:
        return False
    matched = _matching(documents, tuple(groups[0].get("codes") or []))
    meta = matched.get("meta") if isinstance(matched.get("meta"), Mapping) else {}
    country = str(meta.get("issuing_country") or meta.get("country") or "").strip().upper()
    kind = str(meta.get("residence_permit_type") or meta.get("card_kind") or "").strip().lower()
    accepted = {str(item) for item in entry.get("accepted_meta_kinds") or []}
    return bool(accepted) and kind in accepted and country == "PL"


def _validity(
    rule: str,
    entry: Mapping[str, Any],
    documents: list[Mapping[str, Any]],
    facts: Mapping[str, Any],
    today: date,
) -> tuple[str, list[str], str | None] | None:
    if rule == "visa_type":
        if _has_visa_type(documents, facts, entry):
            return None
        label = str((entry.get("evidence") or [{"label": "visa"}])[0].get("label") or "visa")
        return "needs_verification", [label], "incomplete"
    if rule == "schengen_90_180":
        start = _as_date(facts.get("stay_valid_from"))
        end = _as_date(facts.get("stay_valid_to"))
        if start is None or end is None:
            return "needs_verification", [], "period"
        if end < today or (end - start).days > 90:
            return "not_confirmed", [], "period"
    return None


def _has_visa_type(documents: list[Mapping[str, Any]], facts: Mapping[str, Any], entry: Mapping[str, Any]) -> bool:
    if str(facts.get("stay_basis") or "") in {"visa_c", "visa_d"}:
        return True
    if str(facts.get("visa_type") or "").upper() in {"C", "D"}:
        return True
    codes = tuple((entry.get("evidence") or [{"codes": ()}])[0].get("codes") or [])
    matched = _matching(documents, codes)
    meta = matched.get("meta") if isinstance(matched.get("meta"), Mapping) else {}
    return str(meta.get("visa_type") or meta.get("type") or "").strip().upper() in {"C", "D"}


def _outcome(state: str | None) -> str:
    if state == "rejected":
        return "not_confirmed"
    if state == "expired":
        return "expired"
    if state == "mismatch":
        return "needs_review"
    if state in {"in_review", "incomplete"}:
        return "needs_verification"
    return "needs_document"


def _citizenships(facts: Mapping[str, Any]) -> list[str]:
    raw = facts.get("citizenship")
    values = raw if isinstance(raw, list) else [raw]
    return [str(item).strip().upper() for item in values if str(item or "").strip()]


def _document_state(
    documents: list[Mapping[str, Any]],
    presence: Mapping[str, Any],
    today: date,
    *,
    codes: tuple[str, ...],
    require_number: bool,
    require_expiry: bool,
    employment: Mapping[str, Any] | None = None,
) -> tuple[str, str | None]:
    if _presence_is(presence, codes, False) and _matching(documents, codes, require_file=True):
        return "missing", "stale_file"
    if _presence_is(presence, codes, True) and not _matching(documents, codes, require_file=True):
        return "missing", "presence_without_file"
    doc = _matching(documents, codes)
    if not doc:
        return "missing", None
    status = str(doc.get("status") or "").strip().lower()
    has_file = bool(doc.get("has_file"))
    if not has_file and (doc.get("ordered_at") or status in _ORDERED):
        return "ordered", None
    if not has_file and status in _RECEIVED:
        return "missing", "received_without_file"
    if not has_file:
        return "missing", None
    if status in _REJECTED:
        return "rejected", "rejected"
    if status == "expired" or _expired(doc, today):
        return "expired", "expired"
    if status not in _APPROVED:
        return "in_review", "in_review"
    if require_number and not str(doc.get("number") or "").strip():
        return "incomplete", "incomplete"
    if require_expiry and _as_date(doc.get("expire_date")) is None:
        return "incomplete", "incomplete"
    if employment is not None:
        employer = _employer(doc.get("meta") if isinstance(doc.get("meta"), Mapping) else {})
        expected = str(employment.get("client_company_id") or "").strip()
        if employer and expected and employer != expected:
            return "mismatch", "employment_mismatch"
    return "approved", None


def _matching(
    documents: list[Mapping[str, Any]],
    codes: tuple[str, ...],
    *,
    require_file: bool = False,
) -> dict[str, Any]:
    wanted = {str(code).strip().lower() for code in codes}
    found: list[Mapping[str, Any]] = []
    for doc in documents:
        code = str(doc.get("type_code") or doc.get("doc_type") or "").strip().lower()
        if code not in wanted:
            continue
        if require_file and not doc.get("has_file"):
            continue
        found.append(doc)
    approved = [doc for doc in found if str(doc.get("status") or "").lower() in _APPROVED and doc.get("has_file")]
    pool = approved or found
    return dict(pool[0]) if pool else {}


def _presence_is(presence: Mapping[str, Any], codes: tuple[str, ...], expected: bool) -> bool:
    for code in codes:
        value = presence.get(code)
        if value is expected:
            return True
    return False


def _expired(doc: Mapping[str, Any], today: date) -> bool:
    expiry = _as_date(doc.get("expire_date"))
    return expiry is not None and expiry < today


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _employer(meta: Mapping[str, Any]) -> str:
    for key in ("client_company_id", "employer_id", "company_id", "employer"):
        text = str(meta.get(key) or "").strip()
        if text:
            return text
    return ""

