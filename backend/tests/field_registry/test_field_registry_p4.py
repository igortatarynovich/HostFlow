"""Field Registry P4 — Process Engine field requirements via registry populated checks."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from backend.app.field_registry.populated_check import (
    candidate_field_is_populated,
    read_candidate_storage_value,
)
from backend.app.field_registry.requirement_evaluator import evaluate_field_requirements_for_candidate
from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults
from backend.app.process_engine.seed import ensure_recruitment_process_engine_defaults


def _candidate(**kwargs):
    defaults = {
        "phone": "",
        "email": "",
        "address": None,
        "_get_contacts": lambda: {},
        "_get_personal_data": lambda: {},
        "_get_extra": lambda: {},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_p4_populated_check_reads_phone_email_address() -> None:
    empty = _candidate()
    assert candidate_field_is_populated(empty, {"kind": "column", "path": "phone"}) is False  # type: ignore[arg-type]
    assert candidate_field_is_populated(empty, {"kind": "column", "path": "email"}) is False  # type: ignore[arg-type]
    assert candidate_field_is_populated(empty, {"kind": "json_path", "path": "personal_data.address"}) is False  # type: ignore[arg-type]

    complete = _candidate(
        phone="+48111222333",
        email="a@b.c",
        _get_personal_data=lambda: {"address": "Street 1"},
    )
    assert candidate_field_is_populated(complete, {"kind": "column", "path": "phone"}) is True  # type: ignore[arg-type]
    assert read_candidate_storage_value(complete, {"kind": "json_path", "path": "personal_data.address"}) == "Street 1"  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_p4_evaluator_emits_field_requirements_blocking_reasons(db) -> None:
    tenant_id = f"fr-p4-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM pe_field_requirements LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Process Engine / Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await ensure_recruitment_process_engine_defaults(db, tenant_id)
    await db.commit()

    candidate = _candidate()
    candidate.id = str(uuid.uuid4())  # type: ignore[attr-defined]
    result = await evaluate_field_requirements_for_candidate(
        db,
        tenant_id=tenant_id,
        candidate=candidate,  # type: ignore[arg-type]
        context="transition",
        system_stage="ready_for_handoff",
    )
    missing_codes = {row["field_code"] for row in result["missing_fields"]}
    assert {"phone", "email", "address"}.issubset(missing_codes)
    assert result["blocking_reasons"]
    assert all(row["source_layer"] == "field_requirements" for row in result["blocking_reasons"])
    assert any(row.get("qualified_code") == "recruitment.candidate.contacts.phone" for row in result["missing_fields"])


@pytest.mark.anyio
async def test_p4_evaluator_passes_when_contact_fields_complete(db) -> None:
    tenant_id = f"fr-p4-ok-{uuid.uuid4().hex[:10]}"
    try:
        await db.execute(text("SELECT 1 FROM pe_field_requirements LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Process Engine / Field Registry tables not available: {exc}")

    await ensure_tenant_field_registry_defaults(db, tenant_id)
    await ensure_recruitment_process_engine_defaults(db, tenant_id)
    await db.commit()

    candidate = _candidate(
        phone="+48111222333",
        email="a@b.c",
        _get_personal_data=lambda: {"address": {"line1": "Street 1"}},
    )
    candidate.id = str(uuid.uuid4())  # type: ignore[attr-defined]
    result = await evaluate_field_requirements_for_candidate(
        db,
        tenant_id=tenant_id,
        candidate=candidate,  # type: ignore[arg-type]
    )
    assert result["missing_fields"] == []
