"""HR Documents Hub read-model (GET /api/v1/hr/documents/hub)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from backend.app.db.session import async_session_maker
from backend.app.models.document import Document
from backend.app.models.workforce_compliance_state import WorkforceComplianceState
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_document_context import WorkforceHrDocumentContext
from backend.tests.conftest import _init_data
from backend.tests.api.test_hr_documents_queue import (
    _ensure_tenant_link_internal_hr,
    _internal_hr_handoff_accepted,
)


async def _set_rls_tenant(session, tenant_id: str) -> None:
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
        {"tenant_id": tenant_id},
    )


@pytest.mark.anyio
async def test_hr_documents_hub_row_from_context(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    mod = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    assert mod.status_code == 200, mod.text

    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    candidate_id, hid, _ = await _internal_hr_handoff_accepted(
        client,
        manager_headers=manager_headers,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        tenant_id=tenant_id,
        company_id=company_id,
    )

    lst = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert lst.status_code == 200, lst.text
    emp_row = next(
        (e for e in lst.json() if str(e.get("candidate_id") or "") == str(candidate_id)),
        None,
    )
    assert emp_row is not None
    emp_id = str(emp_row["id"])

    doc_id: str | None = None
    async with async_session_maker() as session:
        await _set_rls_tenant(session, tenant_id)
        r = await session.execute(
            select(Document)
            .where(
                Document.tenant_id == tenant_id,
                Document.candidate_id == str(candidate_id),
                Document.deleted_at.is_(None),
            )
            .limit(1)
        )
        doc = r.scalar_one_or_none()
        assert doc is not None
        doc_id = str(doc.id)
        cs_row = (
            await session.execute(
                select(WorkforceComplianceState).where(
                    WorkforceComplianceState.tenant_id == tenant_id,
                    WorkforceComplianceState.employee_id == emp_id,
                )
            )
        ).scalar_one_or_none()
        if cs_row:
            cs_row.status = "attention_required"
            cs_row.cannot_work = False
        else:
            session.add(
                WorkforceComplianceState(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    employee_id=emp_id,
                    status="attention_required",
                    cannot_work=False,
                )
            )
        session.add(
            WorkforceHrDocumentContext(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                employee_id=emp_id,
                document_id=doc_id,
                context_type="hr_workspace_link",
                legal_category="right_to_work",
                document_group="core",
                required=True,
                verified=False,
                verification_status=None,
                source="test_seed",
            )
        )
        await session.commit()

    hub = await client.get(
        "/api/v1/hr/documents/hub",
        headers=hr_officer_headers,
        params={"employee_id_substr": emp_id[:8], "horizon_days": 30},
    )
    assert hub.status_code == 200, hub.text
    body = hub.json()
    assert body["total"] >= 1
    row = next((i for i in body["items"] if i["document_id"] == doc_id), None)
    assert row is not None
    assert row["employee_id"] == emp_id
    assert row["handoff_id"] == hid
    assert row["legal_category"] == "right_to_work"
    assert row["document_group"] == "core"
    assert row["context_type"] == "hr_workspace_link"
    assert row["required"] is True
    assert row["compliance_status"] == "attention_required"
    assert row["compliance_cannot_work"] is False
    assert "missing" in row and "expired" in row and "expiring" in row


@pytest.mark.anyio
async def test_hr_documents_hub_recruiter_forbidden(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    mod = await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    assert mod.status_code == 200, mod.text

    denied = await client.get("/api/v1/hr/documents/hub", headers=recruiter_headers)
    assert denied.status_code == 403, denied.text
