"""HR employee canonical fields and default card layout."""

from __future__ import annotations

from typing import Any

from backend.app.field_registry.constants import (
    DEFAULT_HR_EMPLOYEE_LAYOUT_CODE,
    ENTITY_HR_EMPLOYEE,
    HR_MODULE,
)


def _employee_field(
    field_code: str,
    *,
    field_type: str,
    name: str,
    storage: dict[str, Any],
    section: str,
    pii_class: str | None = None,
    reference_domain: str | None = None,
) -> dict[str, Any]:
    qualified = f"hr.employee.{field_code}"
    return {
        "qualified_code": qualified,
        "code": field_code,
        "entity_type": ENTITY_HR_EMPLOYEE,
        "field_type": field_type,
        "name": name,
        "label_key": f"fields.hr_employee_{field_code}",
        "ownership": HR_MODULE,
        "pii_class": pii_class,
        "reference_domain": reference_domain,
        "storage": storage,
        "legacy_aliases": [field_code],
        "default_section": section,
    }


def hr_employee_fields() -> list[dict[str, Any]]:
    return [
        _employee_field(
            "display_name",
            field_type="text",
            name="Display name",
            storage={"kind": "column", "path": "display_name"},
            section="identity",
            pii_class="identity",
        ),
        _employee_field(
            "status",
            field_type="code",
            name="Employee status",
            storage={"kind": "column", "path": "status"},
            section="employment",
            reference_domain="workforce_employee_statuses",
        ),
        _employee_field(
            "hire_date",
            field_type="date",
            name="Hire date",
            storage={"kind": "column", "path": "hire_date"},
            section="employment",
        ),
        _employee_field(
            "probation_end",
            field_type="date",
            name="Probation end",
            storage={"kind": "column", "path": "probation_end"},
            section="employment",
        ),
        _employee_field(
            "termination_date",
            field_type="date",
            name="Termination date",
            storage={"kind": "column", "path": "termination_date"},
            section="employment",
        ),
        _employee_field(
            "company_id",
            field_type="code",
            name="Company",
            storage={"kind": "column", "path": "company_id"},
            section="assignment",
        ),
        _employee_field(
            "vacancy_id",
            field_type="code",
            name="Source vacancy",
            storage={"kind": "column", "path": "vacancy_id"},
            section="assignment",
        ),
        _employee_field(
            "notes",
            field_type="textarea",
            name="Notes",
            storage={"kind": "column", "path": "notes"},
            section="notes",
        ),
    ]


def _layout_field(qualified_code: str, *, section: str, order: int, required: bool = False) -> dict[str, Any]:
    return {
        "qualified_code": qualified_code,
        "section_code": section,
        "sort_order": order,
        "visible": True,
        "required": required,
    }


def hr_card_layouts() -> list[dict[str, Any]]:
    fields = []
    order = 10
    for row in hr_employee_fields():
        fields.append(
            _layout_field(
                row["qualified_code"],
                section=str(row.get("default_section") or "general"),
                order=order,
                required=row["qualified_code"] == "hr.employee.display_name",
            )
        )
        order += 10
    return [
        {
            "code": DEFAULT_HR_EMPLOYEE_LAYOUT_CODE,
            "name": "HR employee default card",
            "entity_type": ENTITY_HR_EMPLOYEE,
            "is_default": True,
            "fields": fields,
        }
    ]


def hr_module_manifest() -> dict[str, Any]:
    return {
        "module": HR_MODULE,
        "registry_version": "field_registry_v1",
        "canonical_fields": hr_employee_fields(),
        "card_layouts": hr_card_layouts(),
    }
