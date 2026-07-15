"""PR17 — handoff snapshot and work-eligibility seed helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import uuid

from backend.app.services.workforce_employees import (
    _candidate_snapshot,
    _handoff_meta_from_snapshot,
    _seed_work_eligibility_from_candidate,
)


def _candidate(**kwargs):
    extra = kwargs.pop(
        "extra",
        {
            "citizenship": "UA",
            "work_country": "PL",
            "position_category": "driver",
            "legal_status": "temporary_residence",
            "license_number": "DL-1",
        },
    )
    personal = kwargs.pop("personal_data", {"citizenship": "UA", "address": "Warsaw 1"})
    contacts = kwargs.pop("contacts", {})
    base = dict(
        id="cand-1",
        tenant_id="tenant-1",
        first_name="Jan",
        last_name="Kowalski",
        email="jan@example.com",
        phone="+48111222333",
        company_id="co-1",
        vacancy_id=None,
        vacancy=None,
        stage="ready_for_handoff",
        status="active",
        note="note",
    )
    base.update(kwargs)
    return SimpleNamespace(
        _get_extra=lambda: extra,
        _get_personal_data=lambda: personal,
        _get_contacts=lambda: contacts,
        **base,
    )


def test_candidate_snapshot_includes_personal_data_extra_and_document_fields() -> None:
    cand = _candidate()
    snap = _candidate_snapshot(cand)  # type: ignore[arg-type]
    assert snap["first_name"] == "Jan"
    assert snap["last_name"] == "Kowalski"
    assert snap["citizenship"] == "UA"
    assert snap["work_country"] == "PL"
    assert snap["position_category"] == "driver"
    assert isinstance(snap.get("personal_data"), dict)
    assert isinstance(snap.get("extra"), dict)
    assert snap["document_field_values"]["license_number"] == "DL-1"


def test_handoff_meta_from_snapshot_sets_recruitment_transfer() -> None:
    cand = _candidate()
    snap = _candidate_snapshot(cand)  # type: ignore[arg-type]
    meta = _handoff_meta_from_snapshot(cand, snap, internal_hr_handoff_id="ho-1")  # type: ignore[arg-type]
    transfer = meta.get("recruitment_transfer") or {}
    assert meta["source"] == "recruitment_handoff"
    assert meta["internal_hr_handoff_id"] == "ho-1"
    assert transfer.get("candidate_id") == "cand-1"
    assert transfer.get("citizenship") == "UA"
    assert transfer.get("work_country") == "PL"
    assert transfer.get("position_category") == "driver"


@pytest.mark.anyio
async def test_seed_work_eligibility_from_candidate(db) -> None:
    from backend.app.models.company import Company
    from backend.app.models.tenant import Tenant, TenantStatus, TenantType
    from backend.app.models.workforce_employee import WorkforceEmployee
    from backend.app.services.workforce_work_eligibility import get_work_eligibility_profile

    suffix = uuid.uuid4().hex[:8]
    tenant = Tenant(
        id=f"tenant-wel-{suffix}",
        name=f"Wel Test {suffix}",
        slug=f"wel-test-{suffix}",
        api_key=f"wel-key-{suffix}",
        type=TenantType.agency,
        status=TenantStatus.active,
        settings={"modules": {"hr": True}},
    )
    company = Company(id=f"co-wel-{suffix}", tenant_id=tenant.id, name=f"Wel Co {suffix}")
    emp = WorkforceEmployee(
        id=f"emp-wel-{suffix}",
        tenant_id=tenant.id,
        candidate_id=None,
        company_id=company.id,
        display_name="Jan Kowalski",
        status="onboarding",
    )
    cand = _candidate(tenant_id=tenant.id, company_id=company.id)
    db.add_all([tenant, company, emp])
    await db.flush()

    await _seed_work_eligibility_from_candidate(db, tenant.id, emp.id, cand)  # type: ignore[arg-type]
    await db.commit()

    row = await get_work_eligibility_profile(db, tenant.id, emp.id)
    assert row is not None
    assert row.citizenship == "UA"
    assert row.work_country == "PL"
    assert row.position_category == "driver"
    assert row.residence_status == "temporary_residence"
