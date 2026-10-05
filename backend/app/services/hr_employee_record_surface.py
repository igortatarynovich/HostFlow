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
from backend.app.models.hr_employment import Employment
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_zus_workspace_task import WorkforceZusWorkspaceTask
from backend.app.services.hr_driver_operator_surface import (
    build_hr_driver_operator_surface,
    canonical_fact_key,
)

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


def apply_citizenship(personal: dict[str, Any] | None, value: str) -> dict[str, Any]:
    """Write the person fact. Other keys on the same object stay."""

    merged = dict(personal or {})
    merged["citizenship"] = value.strip()
    return merged


def project_employee_record(
    *,
    identity: dict[str, Any],
    personal: dict[str, Any] | None,
    phone: str | None,
    email: str | None,
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
) -> dict[str, Any]:
    person = personal or {}
    rows: list[dict[str, Any]] = []
    rows.extend(_person_rows(identity, person, phone, email))
    rows.extend(_legal_rows(legal_stay, work_eligibility, legal_pass))
    rows.extend(_fact_rows(professional_facts, professional_defined))
    rows.extend(_employment_rows(terms, employer, client_name, actual_start))
    rows.extend(_formality_rows(zus_status))
    rows.append(
        _row(
            "dokumenty.access",
            "Dokumenty",
            None,
            "canonical",
            "document objects",
        )
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
    return {
        "groups": groups,
        "current_process": {
            "next_action": next_action,
            "target_row_id": _target_row_id(next_action, by_id),
        },
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


def _person_rows(
    identity: dict[str, Any],
    personal: dict[str, Any],
    phone: str | None,
    email: str | None,
) -> list[dict[str, Any]]:
    name = " ".join(
        part
        for part in (identity.get("first_name"), identity.get("last_name"))
        if part
    ).strip()
    citizenship = personal.get("citizenship")
    if citizenship is None:
        citizenship = identity.get("citizenship")
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
            actions=["edit"],
        ),
        _row("dane_osobowe.phone", "Telefon", _text(phone), _presence(phone)),
        _row("dane_osobowe.email", "Email", _text(email), _presence(email)),
        _row(
            "dane_osobowe.address",
            "Adres",
            _text(personal.get("address")),
            _presence(personal.get("address")),
        ),
        _row("dane_osobowe.pesel", "PESEL", _text(personal.get("pesel")), _presence(personal.get("pesel"))),
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
    ]


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
        if not applicable:
            status = "not_applicable"
            value = None
        else:
            status = str(fact.get("resolution") or "unresolved")
            value = status
        evidence = "linked" if fact.get("evidence_linked") else None
        projected.append(
            _row(
                f"{group}.{key}",
                str(fact.get("label") or key),
                value,
                status,
                evidence,
            )
        )
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
    projected = project_employee_record(
        identity=driver.get("identity") or {},
        personal=personal,
        phone=candidate.phone if candidate is not None else None,
        email=candidate.email if candidate is not None else None,
        legal_stay=driver.get("legal_stay") or {},
        work_eligibility=driver.get("work_eligibility") or {},
        legal_pass=legal_pass,
        professional_facts=list(professional.get("facts") or []),
        professional_defined=bool(professional.get("defined")),
        terms=driver.get("terms"),
        employer=(driver.get("header") or {}).get("employer"),
        client_name=client_name,
        actual_start=actual_start,
        zus_status=zus_status,
        next_action=driver.get("next_action"),
    )
    return {
        "employee_id": str(employee.id),
        "employment_id": driver.get("employment_id"),
        "state": driver.get("state"),
        "header": driver.get("header") or {},
        "current_process": projected["current_process"],
        "groups": projected["groups"],
    }


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
