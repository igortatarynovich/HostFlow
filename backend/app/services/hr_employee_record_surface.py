"""Employee Record is a read of the owners that already exist.

Current Process is the driver next action. Neither layer stores a fact.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus
from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import HrEmploymentRequirement
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services.candidate_workforce_lock import recruitment_holds_returned_case
from backend.app.models.workforce_zus_workspace_task import WorkforceZusWorkspaceTask
from backend.app.services.document_hub_delivery_contract import (
    E4_LINKED_ENTITY_TYPE,
    E4_RELATION_TYPE,
    hub_status_needs_attention,
    list_entity_link_documents_via_contract,
)
from backend.app.services.hr_driver_operator_surface import (
    build_hr_driver_operator_surface,
    canonical_fact_key,
)
from backend.app.services.hr_verification_plan import VERIFICATION_SLOT_DEFS
from backend.app.services.requirement_document_data import fact_fields_from_document

GROUP_ORDER = (
    "dane_osobowe",
    "legalizacja",
    "kwalifikacje",
    "badania",
    "zatrudnienie",
    "formalnosci",
    "dokumenty",
    "historia",
)

_GROUP_LABELS = {
    "dane_osobowe": "Dane osobowe",
    "legalizacja": "Legalizacja / Prawo do pracy",
    "kwalifikacje": "Kwalifikacje i uprawnienia",
    "badania": "Badania i zdolność do pracy",
    "zatrudnienie": "Zatrudnienie",
    "formalnosci": "Formalności",
    "dokumenty": "Dokumenty",
    "historia": "Historia",
}

_QUALIFICATION_KEYS = frozenset({"driving_licence", "code_95", "tachograph_card"})
_MEDICAL_KEYS = frozenset({"medical", "psychological", "occupational_medicine"})
_DOCUMENT_KEYS = frozenset({"passport"})
_CONFIRMED_DOCUMENT = frozenset({DocumentStatus.approved.value, DocumentStatus.verified.value})
_ZUS_DONE = frozenset({"done", "completed"})
_ZUS_CLOSED = frozenset({"done", "completed", "cancelled", "canceled"})


def _slot_types(document_key: str) -> frozenset[str]:
    for slot in VERIFICATION_SLOT_DEFS:
        if slot.document_key == document_key:
            return slot.catalog_types
    return frozenset()


def project_employment_path(
    *,
    phase: str,
    identity_complete: bool,
    facts: list[dict[str, Any]],
    legal_pass: bool,
    zus_status: str | None,
    terms_complete: bool,
    ready_status: str | None,
) -> list[dict[str, Any]]:
    """Marks for processes that already have a reading. Parallel marks are allowed."""

    applicable = [
        fact
        for fact in facts
        if fact.get("applicability") == "applicable" and not fact.get("not_applicable")
    ]
    blocking = any(fact.get("resolution") == "blocking" for fact in applicable)
    unresolved = any(fact.get("resolution") == "unresolved" for fact in applicable)
    if blocking:
        verification = "blocked"
    elif not identity_complete or unresolved:
        verification = "current"
    else:
        verification = "completed"

    legal = "completed" if legal_pass else "current"
    if zus_status is None:
        formalities = "not_applicable"
    elif str(zus_status).lower() in _ZUS_DONE:
        formalities = "completed"
    elif str(zus_status).lower() in _ZUS_CLOSED:
        formalities = "not_applicable"
    else:
        formalities = "current"
    terms = "completed" if terms_complete else "current"
    ready = "completed" if ready_status in {"pass", "active"} else "pending"
    start = "completed" if phase == "active" or ready_status == "active" else "pending"
    if ready_status == "pass" and phase == "preparing":
        start = "current"
    if phase == "ended":
        start = "completed"

    if phase == "returned":
        return [
            _path_step("handoff", "current", "recruitment"),
            _path_step("verification", "pending", "dane_osobowe"),
            _path_step("legal", "pending", "legalizacja"),
            _path_step("formalities", formalities if formalities == "not_applicable" else "pending", "formalnosci"),
            _path_step("terms", "pending", "zatrudnienie"),
            _path_step("ready", "pending", "ready"),
            _path_step("start", "pending", "start"),
        ]

    if phase == "active" and verification == "current":
        verification = "blocked"
    if phase == "active" and legal == "current":
        legal = "blocked"
    if phase == "active" and terms == "current":
        terms = "blocked"

    return [
        _path_step("handoff", "completed", None),
        _path_step("verification", verification, "dane_osobowe" if not identity_complete else "kwalifikacje"),
        _path_step("legal", legal, "legalizacja"),
        _path_step("formalities", formalities, "formalnosci"),
        _path_step("terms", terms, "zatrudnienie"),
        _path_step("ready", ready, "ready"),
        _path_step("start", start, "start"),
    ]


def _path_step(step_id: str, mark: str, target: str | None) -> dict[str, Any]:
    labels = {
        "handoff": "Handoff",
        "verification": _GROUP_LABELS["dane_osobowe"] if target == "dane_osobowe" else _GROUP_LABELS["kwalifikacje"],
        "legal": _GROUP_LABELS["legalizacja"],
        "formalities": _GROUP_LABELS["formalnosci"],
        "terms": _GROUP_LABELS["zatrudnienie"],
        "ready": "Ready to Start",
        "start": "Start employment",
    }
    return {"id": step_id, "mark": mark, "target": target, "label": labels[step_id]}


def _earliest(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    dated = [item for item in items if item.get("on")]
    if not dated:
        return None
    return sorted(dated, key=lambda item: str(item["on"])[:10])[0]


def project_record_overview(
    *,
    phase: str,
    citizenship: str | None,
    stay_basis: str | None,
    work_basis: str | None,
    work_status: str | None,
    terms: dict[str, Any] | None,
    start_on: str | None,
    documents: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    path: list[dict[str, Any]],
) -> dict[str, Any]:
    """One reading of the dates and marks that already exist."""

    stay_types = _slot_types("Legal stay")
    work_types = _slot_types("Work permit")
    stay_until = _earliest(
        [
            {"on": str(view.get("expires_at") or "")[:10], "label": view.get("title")}
            for view in documents
            if str(view.get("doc_type") or "") in stay_types and view.get("expires_at")
        ]
    )
    work_until = _earliest(
        [
            {"on": str(view.get("expires_at") or "")[:10], "label": view.get("title")}
            for view in documents
            if str(view.get("doc_type") or "") in work_types and view.get("expires_at")
        ]
    )
    agreed = terms or {}
    dates: list[dict[str, Any]] = []
    if agreed.get("duration") == "fixed" and agreed.get("fixed_term_end"):
        dates.append({"label": agreed.get("contract_basis") or "Umowa", "on": agreed.get("fixed_term_end"), "target": "zatrudnienie"})
    for view in documents:
        if view.get("expires_at"):
            dates.append({"label": view.get("title") or view.get("doc_type"), "on": str(view.get("expires_at"))[:10], "target": "dokumenty"})
    for fact in facts:
        until = fact.get("valid_until")
        if until:
            key = canonical_fact_key(str(fact.get("key") or ""))
            target = "dokumenty" if key in _DOCUMENT_KEYS else "kwalifikacje"
            dates.append({"label": fact.get("label") or key, "on": str(until)[:10], "target": target})
    nearest = _earliest(dates)
    attention = [step for step in path if step["mark"] in {"current", "blocked"}]
    if phase == "returned":
        notice = "returned"
    elif phase == "ended":
        notice = "ended"
    elif attention:
        notice = "attention"
    elif phase == "active":
        notice = "healthy"
    else:
        notice = "attention"
    return {
        "phase": phase,
        "citizenship": citizenship,
        "stay_basis": stay_basis,
        "stay_until": None if stay_until is None else stay_until.get("on"),
        "work_basis": work_basis,
        "work_until": None if work_until is None else work_until.get("on"),
        "work_status": work_status,
        "contract_basis": agreed.get("contract_basis"),
        "contract_until": agreed.get("fixed_term_end") if agreed.get("duration") == "fixed" else None,
        "contract_duration": agreed.get("duration"),
        "start_on": start_on,
        "attention_count": len(attention),
        "notice": notice,
        "notice_target": attention[0]["target"] if attention else None,
        "nearest_label": None if nearest is None else nearest.get("label"),
        "nearest_on": None if nearest is None else nearest.get("on"),
        "nearest_target": None if nearest is None else nearest.get("target"),
    }


def apply_citizenship(personal: dict[str, Any] | None, value: str) -> dict[str, Any]:
    """Write the person fact. Other keys on the same object stay."""

    merged = dict(personal or {})
    merged["citizenship"] = value.strip()
    return merged


def apply_person(personal: dict[str, Any] | None, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Write Dane osobowe onto the candidate columns and personal_data that already own them."""

    merged = dict(personal or {})
    citizenship = str(payload.get("citizenship") or "").strip()
    if citizenship:
        merged = apply_citizenship(merged, citizenship)
    birth = str(payload.get("birth_date") or "").strip()
    merged["birth_date"] = birth or None
    pesel = str(payload.get("pesel") or "").strip()
    merged["pesel"] = pesel or None
    merged["phone_country"] = str(payload.get("phone_country") or "").strip() or None
    merged["preferred_contact"] = str(payload.get("preferred_contact") or "").strip() or None
    merged["address"] = _stored_address(payload.get("address"), merged.get("address"))
    merged["reg_address_diff"] = bool(payload.get("reg_address_diff"))
    if merged["reg_address_diff"]:
        merged["reg_address"] = _stored_address(payload.get("reg_address"), merged.get("reg_address"))
    else:
        merged.pop("reg_address", None)
    languages = [
        part.strip()
        for part in str(payload.get("languages") or "").split(",")
        if part.strip()
    ]
    columns = {
        "first_name": str(payload.get("first_name") or "").strip(),
        "last_name": str(payload.get("last_name") or "").strip(),
        "phone": str(payload.get("phone") or "").strip() or None,
        "email": str(payload.get("email") or "").strip() or None,
        "languages": languages,
    }
    return merged, columns


_RETURNED = frozenset({"returned_to_recruitment", "returned"})


def project_employee_record(
    *,
    identity: dict[str, Any],
    personal: dict[str, Any] | None,
    phone: str | None,
    email: str | None,
    languages: list[Any] | None = None,
    legal_stay: dict[str, Any],
    work_eligibility: dict[str, Any],
    legal_pass: bool,
    professional_facts: list[dict[str, Any]],
    professional_defined: bool,
    terms: dict[str, Any] | None,
    employer: str | None,
    client_name: str | None,
    actual_start: str | None,
    zus_status: str | None,
    next_action: dict[str, Any] | None,
    employee_status: str | None = None,
    employment_state: str | None = None,
) -> dict[str, Any]:
    person = personal or {}
    rows: list[dict[str, Any]] = []
    rows.extend(_person_rows(identity, person, phone, email, languages))
    rows.extend(_legal_rows(legal_stay, work_eligibility, legal_pass))
    rows.extend(_fact_rows(professional_facts, professional_defined))
    rows.extend(_employment_rows(terms, employer, client_name, actual_start))
    rows.extend(_formality_rows(zus_status))
    rows.append(
        _row("dokumenty.access", "Dokumenty", None, "missing")
    )
    by_id = {row["id"]: row for row in rows}
    groups = []
    for group_id in GROUP_ORDER:
        group_rows = [row for row in rows if row["group"] == group_id]
        groups.append(
            {
                "id": group_id,
                "label": _GROUP_LABELS[group_id],
                "rows": group_rows,
                "empty": _empty_reason(group_id, group_rows, professional_defined, zus_status),
            }
        )
    process = _current_process(
        next_action,
        by_id,
        employee_status=employee_status,
        employment_state=employment_state,
    )
    action = process.get("next_action") or {}
    process["missing"] = _missing_terms(terms) if action.get("code") == "confirm_terms" else []
    return {
        "groups": groups,
        "current_process": process,
    }


def _current_process(
    next_action: dict[str, Any] | None,
    rows: dict[str, dict[str, Any]],
    *,
    employee_status: str | None,
    employment_state: str | None,
) -> dict[str, Any]:
    status = str(employee_status or "").strip().lower()
    if status in _RETURNED:
        return {
            "next_action": {
                "code": "returned_to_recruitment",
                "focus": "recruitment",
                "fact_key": "",
                "title": "Returned to recruitment",
                "reason": "Waiting for Recruitment update",
            },
            "target_row_id": None,
            "destination": "recruitment",
        }
    if str(employment_state or "").strip().lower() == "ended":
        return {"next_action": None, "target_row_id": None, "destination": None}
    return {
        "next_action": next_action,
        "target_row_id": _target_row_id(next_action, rows),
        "destination": None,
    }


def _empty_reason(
    group_id: str,
    group_rows: list[dict[str, Any]],
    professional_defined: bool,
    zus_status: str | None,
) -> str | None:
    if group_rows:
        return None
    if group_id in {"kwalifikacje", "badania"} and not professional_defined:
        return "not_materialized"
    if group_id == "formalnosci" and zus_status is None:
        return "no_applicable_element"
    if group_id == "historia":
        return "timeline"
    return None


def _missing_terms(terms: dict[str, Any] | None) -> list[str]:
    agreed = terms or {}
    missing: list[str] = []
    checks = (
        ("position", "position"),
        ("intended_start_date", "planned start"),
        ("compensation_amount", "compensation"),
        ("work_system", "work system"),
        ("contract_basis", "contract basis"),
        ("workplace", "workplace"),
    )
    for key, label in checks:
        if not _text(agreed.get(key)):
            missing.append(label)
    return missing


def _person_rows(
    identity: dict[str, Any],
    personal: dict[str, Any],
    phone: str | None,
    email: str | None,
    languages: list[Any] | None,
) -> list[dict[str, Any]]:
    name = " ".join(
        part
        for part in (identity.get("first_name"), identity.get("last_name"))
        if part
    ).strip()
    citizenship = personal.get("citizenship")
    if citizenship is None:
        citizenship = identity.get("citizenship")
    language_text = ", ".join(str(item).strip() for item in (languages or []) if str(item).strip()) or None
    return [
        _row("dane_osobowe.name", "Imię i nazwisko", name or None, _presence(name)),
        _row(
            "dane_osobowe.birth_date",
            "Data urodzenia",
            _text(identity.get("birth_date")),
            _presence(identity.get("birth_date")),
        ),
        _row(
            "dane_osobowe.citizenship",
            "Obywatelstwo",
            _text(citizenship),
            _presence(citizenship),
        ),
        _row("dane_osobowe.phone", "Telefon", _text(phone), _presence(phone)),
        _row("dane_osobowe.email", "Email", _text(email), _presence(email)),
        _row(
            "dane_osobowe.address",
            "Adres",
            _address_text(personal.get("address")),
            _presence(_address_text(personal.get("address"))),
        ),
        _row("dane_osobowe.pesel", "PESEL", _text(personal.get("pesel")), _presence(personal.get("pesel"))),
        _row("dane_osobowe.languages", "Języki", language_text, _presence(language_text)),
    ]


def _legal_rows(
    legal_stay: dict[str, Any],
    work: dict[str, Any],
    legal_pass: bool,
) -> list[dict[str, Any]]:
    stay = _text(legal_stay.get("basis"))
    basis = _text(work.get("basis"))
    valid = _text(work.get("valid_for_this_employment"))
    if valid == "yes" and legal_pass:
        valid_status = "current"
    elif valid:
        valid_status = "pending"
    else:
        valid_status = "missing"
    return [
        _row("legalizacja.stay_basis", "Podstawa pobytu", stay, _presence(stay)),
        _row("legalizacja.work_basis", "Prawo do pracy", basis, _presence(basis)),
        _row("legalizacja.valid_for_this_employment", "To Employment", valid, valid_status),
        _row(
            "legalizacja.status",
            "Status",
            "pass" if legal_pass else None,
            "current" if legal_pass else "pending",
        ),
    ]


def evidence_coverage(
    *,
    applicability: str | None,
    linked: bool,
    document_status: str | None,
    valid_until: date | None = None,
    today: date | None = None,
) -> str:
    """Coverage of one fact by the evidence already linked to it.

    The code is an existing document status. It is not a new vocabulary.
    """

    if applicability == "not_applicable":
        return DocumentStatus.not_required.value
    if not linked:
        return DocumentStatus.missing.value
    status = str(document_status or "").strip().lower()
    current = today or date.today()
    if status == DocumentStatus.expired.value or (valid_until is not None and valid_until < current):
        return DocumentStatus.expired.value
    if status == DocumentStatus.rejected.value:
        return DocumentStatus.rejected.value
    if status in _CONFIRMED_DOCUMENT:
        return DocumentStatus.approved.value
    return DocumentStatus.in_progress.value


def _with_recorded_professional_facts(
    facts: list[dict[str, Any]],
    personal: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Show the operator fact on the qualification row when the document field is empty."""

    from backend.app.services.operator_facts_surface import (
        facts_from_personal_data,
        recorded_professional_fields,
    )

    recorded = facts_from_personal_data(personal if isinstance(personal, dict) else {})
    painted: list[dict[str, Any]] = []
    for fact in facts:
        reading = dict(fact)
        extra = recorded_professional_fields(str(reading.get("key") or ""), recorded)
        if extra.get("valid_until") and not reading.get("valid_until"):
            reading["valid_until"] = extra["valid_until"]
        if extra.get("categories") and not reading.get("categories"):
            reading["categories"] = extra["categories"]
        if extra.get("issuing_country") and not reading.get("issuing_country"):
            reading["issuing_country"] = extra["issuing_country"]
        painted.append(reading)
    return painted


def _fact_rows(facts: list[dict[str, Any]], defined: bool) -> list[dict[str, Any]]:
    if not defined:
        return []
    projected: list[dict[str, Any]] = []
    for fact in facts:
        key = canonical_fact_key(str(fact.get("key") or ""))
        group = _fact_group(key)
        if group is None:
            continue
        applicable = fact.get("applicability") != "not_applicable" and not fact.get("not_applicable")
        status = "not_applicable" if not applicable else str(fact.get("resolution") or "unresolved")
        categories = _categories_text(fact.get("categories"))
        valid_until = _as_date(fact.get("valid_until"))
        details = []
        country = _text(fact.get("issuing_country"))
        if country:
            details.append({"label": "Kraj wydania", "value": country})
        if categories:
            details.append({"label": "Kategorie", "value": categories})
        if valid_until is not None:
            details.append({"label": "Ważne do", "value": valid_until.isoformat()})
        row = _row(
            f"{group}.{key}",
            str(fact.get("label") or key),
            categories,
            status,
            evidence_coverage(
                applicability="not_applicable" if not applicable else "applicable",
                linked=bool(fact.get("evidence_linked")),
                document_status=_text(fact.get("document_status")),
                valid_until=valid_until,
            ),
        )
        if details:
            row["details"] = details
        projected.append(row)
    return projected


def _fact_group(key: str) -> str | None:
    if key in _QUALIFICATION_KEYS:
        return "kwalifikacje"
    if key in _MEDICAL_KEYS:
        return "badania"
    if key in _DOCUMENT_KEYS:
        return "dokumenty"
    return None


def _employment_rows(
    terms: dict[str, Any] | None,
    employer: str | None,
    client_name: str | None,
    actual_start: str | None,
) -> list[dict[str, Any]]:
    agreed = terms or {}
    compensation = " ".join(
        part
        for part in (
            _text(agreed.get("compensation_amount")),
            _text(agreed.get("compensation_currency")),
            _text(agreed.get("compensation_unit")),
        )
        if part
    )
    work_time = " ".join(
        part
        for part in (_text(agreed.get("work_time_value")), _text(agreed.get("work_time_unit")))
        if part
    )
    workplace_employer = client_name or employer
    fields = (
        ("zatrudnienie.employer", "Pracodawca", workplace_employer),
        ("zatrudnienie.position", "Stanowisko", agreed.get("position")),
        ("zatrudnienie.planned_start", "Planned start", agreed.get("intended_start_date")),
        ("zatrudnienie.actual_start", "Actual start", actual_start),
        ("zatrudnienie.contract_basis", "Umowa", agreed.get("contract_basis")),
        ("zatrudnienie.work_time", "Czas pracy", work_time or None),
        ("zatrudnienie.work_system", "System pracy", agreed.get("work_system")),
        ("zatrudnienie.workplace", "Miejsce pracy", agreed.get("workplace")),
        ("zatrudnienie.compensation", "Stawka", compensation or None),
        ("zatrudnienie.duration", "Okres", agreed.get("duration")),
        ("zatrudnienie.probation", "Probation", agreed.get("probation_status")),
    )
    return [_row(row_id, label, _text(value), _presence(value)) for row_id, label, value in fields]


def _formality_rows(zus_status: str | None) -> list[dict[str, Any]]:
    if zus_status is None:
        return []
    return [_row("formalnosci.zus", "ZUS", zus_status, "process")]


def _target_row_id(next_action: dict[str, Any] | None, rows: dict[str, dict[str, Any]]) -> str | None:
    if not next_action:
        return None
    fact_key = canonical_fact_key(str(next_action.get("fact_key") or ""))
    if fact_key:
        group = _fact_group(fact_key)
        if group is not None:
            row_id = f"{group}.{fact_key}"
            if row_id in rows:
                return row_id
    code = str(next_action.get("code") or "")
    if code == "confirm_terms":
        return "zatrudnienie.position"
    if code == "register_zus":
        return "formalnosci.zus" if "formalnosci.zus" in rows else "group:formalnosci"
    if code in {"start_work_authorization", "confirm_legal"}:
        return "legalizacja.stay_basis"
    if code in {"start_employment", "record_ready"}:
        return "zatrudnienie.planned_start"
    return None


def _row(
    row_id: str,
    label: str,
    value: str | None,
    status: str,
    evidence: str | None = None,
    actions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": row_id,
        "group": row_id.split(".", 1)[0],
        "label": label,
        "value": value,
        "status": status,
        "evidence": evidence,
        "actions": list(actions or []),
    }


def _presence(value: Any) -> str:
    return "recorded" if _text(value) else "missing"


def _categories_text(value: Any) -> str | None:
    if isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(parts) or None
    return _text(value)


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        parts = [str(part).strip() for part in value.values() if part]
        text = ", ".join(parts)
        return text or None
    text = str(value).strip()
    return text or None


def _iso(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


async def build_hr_employee_record_surface(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee: WorkforceEmployee,
) -> dict[str, Any]:
    driver = await build_hr_driver_operator_surface(db, tenant_id=tenant_id, employee=employee)
    candidate = None
    if employee.candidate_id:
        candidate = await db.get(Candidate, str(employee.candidate_id))
    personal = candidate.personal_data if candidate is not None and isinstance(candidate.personal_data, dict) else {}
    employment = None
    if driver.get("employment_id"):
        employment = await db.get(Employment, str(driver["employment_id"]))
    client_name = None
    actual_start = None
    if employment is not None:
        actual_start = _iso(employment.started_on)
        if employment.client_company_id:
            client = await db.get(Company, str(employment.client_company_id))
            client_name = client.name if client is not None else None
    zus_tasks = (
        await db.scalars(
            select(WorkforceZusWorkspaceTask).where(
                WorkforceZusWorkspaceTask.tenant_id == str(tenant_id),
                WorkforceZusWorkspaceTask.employee_id == str(employee.id),
                WorkforceZusWorkspaceTask.task_kind == "registration",
            )
        )
    ).all()
    zus_status = zus_tasks[0].status if zus_tasks else None
    legal_pass = bool(
        driver.get("work_eligibility", {}).get("status") == "eligible"
    )
    professional = driver.get("professional") or {}
    facts = _with_recorded_professional_facts(
        await _facts_with_evidence(
            db,
            tenant_id=str(tenant_id),
            employment_id=str(driver.get("employment_id") or ""),
            facts=list(professional.get("facts") or []),
        ),
        personal,
    )
    document_views = await _linked_documents(db, tenant_id=str(tenant_id), candidate_id=str(employee.candidate_id or ""))
    documents = {
        "total": len(document_views),
        "attention": sum(1 for view in document_views if hub_status_needs_attention(str(view.get("status") or ""))),
    }
    phase = _phase(employee.status, driver.get("state"))
    path = project_employment_path(
        phase=phase,
        identity_complete=bool((driver.get("identity") or {}).get("complete")),
        facts=facts,
        legal_pass=legal_pass,
        zus_status=zus_status,
        terms_complete=bool((driver.get("terms") or {}).get("complete")),
        ready_status=(driver.get("ready_to_start") or {}).get("status"),
    )
    overview = project_record_overview(
        phase=phase,
        citizenship=_text(personal.get("citizenship")) or _text((driver.get("identity") or {}).get("citizenship")),
        stay_basis=(driver.get("legal_stay") or {}).get("basis"),
        work_basis=(driver.get("work_eligibility") or {}).get("basis"),
        work_status=(driver.get("work_eligibility") or {}).get("status"),
        terms=driver.get("terms"),
        start_on=actual_start or (driver.get("header") or {}).get("planned_start"),
        documents=document_views,
        facts=facts,
        path=path,
    )
    projected = project_employee_record(
        identity=driver.get("identity") or {},
        personal=personal,
        phone=candidate.phone if candidate is not None else None,
        email=candidate.email if candidate is not None else None,
        languages=list(candidate.languages or []) if candidate is not None else None,
        legal_stay=driver.get("legal_stay") or {},
        work_eligibility=driver.get("work_eligibility") or {},
        legal_pass=legal_pass,
        professional_facts=facts,
        professional_defined=bool(professional.get("defined")),
        terms=driver.get("terms"),
        employer=(driver.get("header") or {}).get("employer"),
        client_name=client_name,
        actual_start=actual_start,
        zus_status=zus_status,
        next_action=driver.get("next_action"),
        employee_status=employee.status,
        employment_state=driver.get("state"),
    )
    header = dict(driver.get("header") or {})
    if employment is not None:
        header["ended_on"] = _iso(employment.ended_on)
    return {
        "employee_id": str(employee.id),
        "candidate_id": str(employee.candidate_id) if employee.candidate_id else None,
        "employment_id": driver.get("employment_id"),
        "state": driver.get("state"),
        "header": header,
        "current_process": projected["current_process"],
        "groups": projected["groups"],
        "person": _person_editor(candidate, personal),
        "legal": {
            "citizenship_class": (driver.get("work_eligibility") or {}).get("citizenship_class"),
            "stay_basis": (driver.get("legal_stay") or {}).get("basis"),
            "work_authorization_basis": (driver.get("work_eligibility") or {}).get("basis"),
            "valid_for_this_employment": (driver.get("work_eligibility") or {}).get("valid_for_this_employment"),
        },
        "terms": driver.get("terms"),
        "documents": documents,
        "overview": overview,
        "path": path,
    }


def _phase(employee_status: str | None, employment_state: str | None) -> str:
    if recruitment_holds_returned_case(employee_status):
        return "returned"
    state = str(employment_state or "").strip().lower()
    if state in {"preparing", "active", "ended"}:
        return state
    return "preparing"


async def _facts_with_evidence(
    db: AsyncSession,
    *,
    tenant_id: str,
    employment_id: str,
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not employment_id or not facts:
        return facts
    rows = (
        await db.scalars(
            select(HrEmploymentRequirement).where(
                HrEmploymentRequirement.tenant_id == tenant_id,
                HrEmploymentRequirement.employment_id == employment_id,
            )
        )
    ).all()
    by_key = {canonical_fact_key(row.definition_key): row for row in rows}
    document_ids = [str(row.satisfaction_document_id) for row in rows if row.satisfaction_document_id]
    documents: dict[str, Document] = {}
    if document_ids:
        loaded = (
            await db.scalars(
                select(Document).where(
                    Document.tenant_id == tenant_id,
                    Document.id.in_(document_ids),
                    Document.deleted_at.is_(None),
                )
            )
        ).all()
        documents = {str(doc.id): doc for doc in loaded}
    enriched: list[dict[str, Any]] = []
    for fact in facts:
        key = canonical_fact_key(str(fact.get("key") or ""))
        row = by_key.get(key)
        reading = dict(fact)
        if row is not None and row.satisfaction_document_id:
            document = documents.get(str(row.satisfaction_document_id))
            if document is not None:
                fields = fact_fields_from_document(meta=document.meta, expire_date=document.expire_date)
                reading["categories"] = fields.get("categories")
                reading["valid_until"] = fields.get("valid_until")
                reading["document_status"] = getattr(document.status, "value", document.status)
                reading["evidence_linked"] = True
        enriched.append(reading)
    return enriched


async def _linked_documents(db: AsyncSession, *, tenant_id: str, candidate_id: str) -> list[dict[str, Any]]:
    if not candidate_id:
        return []
    views = await list_entity_link_documents_via_contract(
        db,
        tenant_id=tenant_id,
        linked_entity_type=E4_LINKED_ENTITY_TYPE,
        linked_entity_id=candidate_id,
        relation_type=E4_RELATION_TYPE,
    )
    return [view for view in views if isinstance(view, dict)]


_ADDRESS_KEYS = ("country", "city", "street", "house", "apt", "zip")


def _stored_address(incoming: Any, current: Any) -> dict[str, str] | None:
    """Keep the candidate address object. A single string is not an address."""

    base = dict(current) if isinstance(current, dict) else {}
    base.pop("address", None)
    source = incoming if isinstance(incoming, dict) else {}
    if isinstance(incoming, str) and incoming.strip() and not any(str(source.get(key) or "").strip() for key in _ADDRESS_KEYS):
        source = {"street": incoming.strip()}
    for key in _ADDRESS_KEYS:
        text = str(source.get(key) or "").strip()
        if text:
            base[key] = text
        else:
            base.pop(key, None)
    cleaned = {key: value for key, value in base.items() if str(value or "").strip()}
    return cleaned or None


def _address_text(value: Any) -> str | None:
    if isinstance(value, dict):
        ordered = [str(value.get(key) or "").strip() for key in _ADDRESS_KEYS]
        text = ", ".join(part for part in ordered if part)
        return text or None
    return _text(value)


def _address_editor(value: Any) -> dict[str, str]:
    parts = {key: "" for key in _ADDRESS_KEYS}
    if isinstance(value, dict):
        for key in _ADDRESS_KEYS:
            parts[key] = str(value.get(key) or "").strip()
        if not parts["street"]:
            parts["street"] = str(value.get("address") or "").strip()
    elif isinstance(value, str):
        parts["street"] = value.strip()
    return parts


def _person_editor(candidate: Candidate | None, personal: dict[str, Any]) -> dict[str, Any]:
    languages = candidate.languages if candidate is not None else None
    return {
        "first_name": candidate.first_name if candidate is not None else "",
        "last_name": candidate.last_name if candidate is not None else "",
        "birth_date": _text(personal.get("birth_date")) or "",
        "citizenship": _text(personal.get("citizenship")) or "",
        "short_id": candidate.short_id if candidate is not None and candidate.short_id else "",
        "phone": candidate.phone if candidate is not None and candidate.phone else "",
        "phone_country": _text(personal.get("phone_country")) or "",
        "email": candidate.email if candidate is not None and candidate.email else "",
        "preferred_contact": _text(personal.get("preferred_contact")) or "",
        "address": _address_editor(personal.get("address")),
        "reg_address_diff": bool(personal.get("reg_address_diff")),
        "reg_address": _address_editor(personal.get("reg_address")),
        "pesel": _text(personal.get("pesel")) or "",
        "languages": ", ".join(str(item).strip() for item in (languages or []) if str(item).strip()),
    }


async def update_record_person(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    employee = await db.get(WorkforceEmployee, employee_id)
    if employee is None or str(employee.tenant_id) != str(tenant_id):
        return {"accepted": False, "reason": "not_found"}
    if recruitment_holds_returned_case(employee.status):
        return {"accepted": False, "reason": "returned_to_recruitment"}
    if not employee.candidate_id:
        return {"accepted": False, "reason": "no_candidate"}
    candidate = await db.get(Candidate, str(employee.candidate_id))
    if candidate is None or str(candidate.tenant_id) != str(tenant_id):
        return {"accepted": False, "reason": "no_candidate"}
    personal, columns = apply_person(
        candidate.personal_data if isinstance(candidate.personal_data, dict) else {},
        payload,
    )
    if not columns["first_name"] or not columns["last_name"]:
        return {"accepted": False, "reason": "name_required"}
    candidate.personal_data = personal
    flag_modified(candidate, "personal_data")
    candidate.first_name = columns["first_name"]
    candidate.last_name = columns["last_name"]
    candidate.phone = columns["phone"]
    candidate.email = columns["email"]
    candidate.languages = columns["languages"]
    return {"accepted": True}


async def update_record_citizenship(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    citizenship: str,
) -> dict[str, Any]:
    value = citizenship.strip()
    if not value or len(value) > 64:
        return {"accepted": False, "reason": "invalid_citizenship"}
    employee = await db.get(WorkforceEmployee, employee_id)
    if employee is None or str(employee.tenant_id) != str(tenant_id):
        return {"accepted": False, "reason": "not_found"}
    if recruitment_holds_returned_case(employee.status):
        return {"accepted": False, "reason": "returned_to_recruitment"}
    if not employee.candidate_id:
        return {"accepted": False, "reason": "no_candidate"}
    candidate = await db.get(Candidate, str(employee.candidate_id))
    if candidate is None or str(candidate.tenant_id) != str(tenant_id):
        return {"accepted": False, "reason": "no_candidate"}
    candidate.personal_data = apply_citizenship(
        candidate.personal_data if isinstance(candidate.personal_data, dict) else {},
        value,
    )
    flag_modified(candidate, "personal_data")
    return {"accepted": True, "citizenship": value}
