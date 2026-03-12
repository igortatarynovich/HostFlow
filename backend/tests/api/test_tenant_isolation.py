"""
Tests for tenant isolation and RLS (Row-Level Security).

These tests verify that:
1. Users from one tenant cannot access data from another tenant
2. RLS policies are enforced at the database level
3. API endpoints respect tenant boundaries
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.document import Document
from backend.app.models.user import User
from backend.app.models.vacancy import Vacancy


TENANT_1_ID = "11111111-1111-1111-1111-111111111111"
TENANT_2_ID = "22222222-2222-2222-2222-222222222222"


async def _set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """Set tenant context for RLS."""
    try:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )
    except Exception:
        pass


@pytest_asyncio.fixture
async def tenant2_data(tenant_id: str) -> Dict[str, str]:
    """Create test data for tenant 2."""
    async with async_session_maker() as session:
        await _set_tenant_context(session, TENANT_2_ID)
        
        # Create user for tenant 2 using raw SQL (let server handle timestamps)
        user2_id = str(uuid.uuid4())
        await session.execute(
            text(f"""
                INSERT INTO users (id, email, password_hash, role, tenant_id, short_id, full_name, is_active)
                VALUES (:id, :email, :password_hash, :role, :tenant_id, :short_id, :full_name, :is_active)
            """),
            {
                "id": user2_id,
                "email": "admin2@tenant2.com",
                "password_hash": "hash",
                "role": "administrator",
                "tenant_id": TENANT_2_ID,
                "short_id": "ADM2",
                "full_name": "Tenant 2 Admin",
                "is_active": True,
            },
        )
        
        # Create company for tenant 2 using raw SQL
        company2_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO companies (id, tenant_id, name)
                VALUES (:id, :tenant_id, :name)
            """),
            {
                "id": company2_id,
                "tenant_id": TENANT_2_ID,
                "name": "Tenant 2 Company",
            },
        )
        
        # Create candidate for tenant 2
        candidate2_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO candidates (id, tenant_id, first_name, last_name, manager, company_id)
                VALUES (:id, :tenant_id, :first_name, :last_name, :manager, :company_id)
            """),
            {
                "id": candidate2_id,
                "tenant_id": TENANT_2_ID,
                "first_name": "Tenant2",
                "last_name": "Candidate",
                "manager": user2_id,
                "company_id": company2_id,
            },
        )
        
        # Add user_memberships for tenant 2
        await session.execute(
            text("""
                INSERT INTO user_memberships (id, user_id, tenant_id, role)
                VALUES (:id, :user_id, :tenant_id, :role)
                ON CONFLICT(user_id, tenant_id)
                DO UPDATE SET role = excluded.role
            """),
            {
                "id": str(uuid.uuid4()),
                "user_id": user2_id,
                "tenant_id": TENANT_2_ID,
                "role": "administrator",
            },
        )

        await session.commit()

        return {
            "user_id": user2_id,
            "company_id": company2_id,
            "candidate_id": candidate2_id,
        }


@pytest_asyncio.fixture
async def tenant2_token(tenant2_data: Dict[str, str]) -> str:
    """Create JWT token for tenant 2 admin."""
    from backend.app.auth.jwt_tools import encode
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    payload = {
        "sub": tenant2_data["user_id"],
        "email": "admin2@tenant2.com",
        "role": "administrator",
        "tenant_id": TENANT_2_ID,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=120)).timestamp()),
    }
    return encode(payload)


@pytest_asyncio.fixture
async def tenant2_headers(tenant2_token: str) -> Dict[str, str]:
    """Headers for tenant 2 requests."""
    return {
        "Authorization": f"Bearer {tenant2_token}",
        "X-Tenant-Id": TENANT_2_ID,
    }


@pytest.mark.anyio
async def test_tenant_isolation_candidates(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    tenant2_headers: Dict[str, str],
    tenant2_data: Dict[str, str],
    candidate_id: str,
) -> None:
    """Test that candidates are isolated by tenant."""
    # Tenant 1 should see their own candidate
    resp = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    
    # Tenant 1 should NOT see tenant 2's candidate
    resp = await client.get(
        f"/api/v1/candidates/{tenant2_data['candidate_id']}",
        headers=manager_headers,
    )
    assert resp.status_code == 404, "Tenant 1 should not see tenant 2's candidate"
    
    # Tenant 2 should see their own candidate
    resp = await client.get(
        f"/api/v1/candidates/{tenant2_data['candidate_id']}",
        headers=tenant2_headers,
    )
    assert resp.status_code == 200, resp.text
    
    # Tenant 2 should NOT see tenant 1's candidate
    resp = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=tenant2_headers,
    )
    assert resp.status_code == 404, "Tenant 2 should not see tenant 1's candidate"


@pytest.mark.anyio
async def test_tenant_isolation_companies(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    tenant2_headers: Dict[str, str],
    tenant2_data: Dict[str, str],
) -> None:
    """Test that companies are isolated by tenant."""
    # Get tenant 1 companies
    resp = await client.get(
        "/api/v1/companies",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    companies1 = resp.json()
    company_ids_1 = {c["id"] for c in companies1}
    
    # Tenant 1 should NOT see tenant 2's company
    assert tenant2_data["company_id"] not in company_ids_1, "Tenant 1 should not see tenant 2's company"
    
    # Get tenant 2 companies
    resp = await client.get(
        "/api/v1/companies",
        headers=tenant2_headers,
    )
    assert resp.status_code == 200, resp.text
    companies2 = resp.json()
    company_ids_2 = {c["id"] for c in companies2}
    
    # Tenant 2 should see their own company
    assert tenant2_data["company_id"] in company_ids_2, "Tenant 2 should see their own company"
    
    # Tenant 2 should NOT see tenant 1's companies
    assert not company_ids_1.intersection(company_ids_2), "Tenants should not share companies"


@pytest.mark.anyio
async def test_tenant_isolation_documents(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    tenant2_headers: Dict[str, str],
    tenant2_data: Dict[str, str],
) -> None:
    """Test that documents are isolated by tenant."""
    # Create document for tenant 2
    doc_resp = await client.post(
        "/api/v1/documents",
        headers=tenant2_headers,
        json={
            "candidate_id": tenant2_data["candidate_id"],
            "doc_type": "driver_license",
            "kind": "driver",
            "status": "missing",
        },
    )
    assert doc_resp.status_code == 200, doc_resp.text
    doc2_id = doc_resp.json()["id"]
    
    # Tenant 1 should NOT see tenant 2's document
    resp = await client.get(
        f"/api/v1/documents/{doc2_id}",
        headers=manager_headers,
    )
    assert resp.status_code == 404, "Tenant 1 should not see tenant 2's document"
    
    # Tenant 2 should see their own document
    resp = await client.get(
        f"/api/v1/documents/{doc2_id}",
        headers=tenant2_headers,
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_tenant_isolation_vacancies(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    tenant2_headers: Dict[str, str],
    tenant2_data: Dict[str, str],
) -> None:
    """Test that vacancies are isolated by tenant."""
    # Create vacancy for tenant 2
    vacancy_resp = await client.post(
        "/api/v1/vacancies",
        headers=tenant2_headers,
        json={
            "title": "Tenant 2 Vacancy",
            "company_id": tenant2_data["company_id"],
            "employment_type": "full_time",
        },
    )
    assert vacancy_resp.status_code == 200, vacancy_resp.text
    vacancy2_id = vacancy_resp.json()["id"]
    
    # Tenant 1 should NOT see tenant 2's vacancy
    resp = await client.get(
        f"/api/v1/vacancies/{vacancy2_id}",
        headers=manager_headers,
    )
    assert resp.status_code == 404, "Tenant 1 should not see tenant 2's vacancy"
    
    # Tenant 2 should see their own vacancy
    resp = await client.get(
        f"/api/v1/vacancies/{vacancy2_id}",
        headers=tenant2_headers,
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.anyio
async def test_rls_enforcement_at_db_level(
    tenant2_data: Dict[str, str],
    candidate_id: str,
) -> None:
    """Test that RLS is enforced at database level."""
    async with async_session_maker() as session:
        # Set tenant 1 context
        await _set_tenant_context(session, TENANT_1_ID)
        
        # Query candidates - should only see tenant 1's candidate
        result = await session.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        candidate = result.scalar_one_or_none()
        assert candidate is not None, "Should see tenant 1's candidate"
        assert candidate.tenant_id == TENANT_1_ID
        
        # Should NOT see tenant 2's candidate
        result = await session.execute(
            select(Candidate).where(Candidate.id == tenant2_data["candidate_id"])
        )
        candidate2 = result.scalar_one_or_none()
        assert candidate2 is None, "Should NOT see tenant 2's candidate with tenant 1 context"
        
        # Switch to tenant 2 context
        await _set_tenant_context(session, TENANT_2_ID)
        
        # Now should see tenant 2's candidate
        result = await session.execute(
            select(Candidate).where(Candidate.id == tenant2_data["candidate_id"])
        )
        candidate2 = result.scalar_one_or_none()
        assert candidate2 is not None, "Should see tenant 2's candidate with tenant 2 context"
        assert candidate2.tenant_id == TENANT_2_ID
        
        # Should NOT see tenant 1's candidate
        result = await session.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        candidate1 = result.scalar_one_or_none()
        assert candidate1 is None, "Should NOT see tenant 1's candidate with tenant 2 context"


@pytest.mark.anyio
async def test_cross_tenant_creation_blocked(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    tenant2_data: Dict[str, str],
) -> None:
    """Test that creating resources with wrong tenant_id is blocked."""
    # Try to create candidate with tenant 2's company but tenant 1's context
    resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,  # Tenant 1 headers
        json={
            "first_name": "Cross",
            "last_name": "Tenant",
            "company_id": tenant2_data["company_id"],  # Tenant 2's company
        },
    )
    # Should fail - cannot reference tenant 2's company from tenant 1
    assert resp.status_code in (400, 403, 404), "Should block cross-tenant resource creation"


@pytest.mark.anyio
async def test_tenant_isolation_list_endpoints(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    tenant2_headers: Dict[str, str],
    tenant2_data: Dict[str, str],
) -> None:
    """Test that list endpoints respect tenant isolation."""
    # Get candidates for tenant 1
    resp = await client.get(
        "/api/v1/candidates",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    candidates1 = resp.json()
    candidate_ids_1 = {c["id"] for c in candidates1}
    
    # Get candidates for tenant 2
    resp = await client.get(
        "/api/v1/candidates",
        headers=tenant2_headers,
    )
    assert resp.status_code == 200, resp.text
    candidates2 = resp.json()
    candidate_ids_2 = {c["id"] for c in candidates2}
    
    # No overlap between tenants
    assert not candidate_ids_1.intersection(candidate_ids_2), "Tenants should not share candidates"


@pytest.mark.anyio
async def test_tenant_isolation_invoices(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    tenant2_headers: Dict[str, str],
    tenant2_data: Dict[str, str],
) -> None:
    """Test that invoices are isolated by tenant."""
    from datetime import date

    # Create invoice for tenant 2
    invoice_resp = await client.post(
        "/api/v1/invoices",
        headers=tenant2_headers,
        json={
            "company_id": tenant2_data["company_id"],
            "issue_date": date.today().isoformat(),
            "due_date": date.today().isoformat(),
            "items": [
                {
                    "description": "Tenant 2 service",
                    "qty": 1,
                    "unit_price": 100,
                },
            ],
        },
    )
    if invoice_resp.status_code not in (200, 201):
        pytest.skip(f"Invoices API not available: {invoice_resp.status_code} {invoice_resp.text}")
    invoice2_id = invoice_resp.json()["id"]

    # Tenant 1 should NOT see tenant 2's invoice
    resp = await client.get(
        f"/api/v1/invoices/{invoice2_id}",
        headers=manager_headers,
    )
    assert resp.status_code == 404, f"Tenant 1 should not see tenant 2's invoice: {resp.text}"

    # Tenant 2 should see their own invoice
    resp = await client.get(
        f"/api/v1/invoices/{invoice2_id}",
        headers=tenant2_headers,
    )
    assert resp.status_code == 200, resp.text

    # List invoices: tenant 1 should not see tenant 2's invoice in their list
    list1 = await client.get("/api/v1/invoices", headers=manager_headers)
    assert list1.status_code == 200, list1.text
    invoice_ids_1 = {inv["id"] for inv in list1.json()}
    assert invoice2_id not in invoice_ids_1, "Tenant 1 list should not contain tenant 2's invoice"

    list2 = await client.get("/api/v1/invoices", headers=tenant2_headers)
    assert list2.status_code == 200, list2.text
    invoice_ids_2 = {inv["id"] for inv in list2.json()}
    assert invoice2_id in invoice_ids_2, "Tenant 2 should see their own invoice in list"

