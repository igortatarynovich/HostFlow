from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.user import Role as UserRole
from backend.app.models.user import User

SEARCH_URL = "/api/v1/search"


def _utc_naive_now() -> datetime:
    """Candidate.created_at/updated_at are naive UTC columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_global_search_lead_fts_matches_tokens_across_json_keys(
    client: AsyncClient,
    db,
    manager_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    """Multi-word query: tokens in different normalized JSON keys match via FTS (not one ILIKE substring).

    Uses manager (administrator) like own-company scope tests: recruiters often have an active
    own_company_id that would hide leads unless Lead.own_company_id matches preferences.
    """
    own_id = await db.scalar(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id)
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    assert own_id is not None
    lid = str(uuid4())
    token_a = f"FtsSplitA{uuid4().hex[:6]}"
    token_b = f"FtsSplitB{uuid4().hex[:6]}"
    db.add(
        Lead(
            id=lid,
            tenant_id=tenant_id,
            own_company_id=str(own_id),
            payload={},
            normalized={"first_name": token_a, "city": token_b},
            source="meta",
            status="new",
        )
    )
    await db.commit()

    r = await client.get(
        SEARCH_URL,
        headers=manager_headers,
        params={"q": f"{token_a} {token_b}", "limit": 8, "max_results": 40},
    )
    assert r.status_code == 200, r.text
    leads = [i for i in r.json().get("items") or [] if i.get("type") == "lead"]
    assert any(i.get("id") == lid for i in leads), r.json()


@pytest.mark.asyncio
async def test_global_search_document_fts_matches_tokens_across_fields(
    client: AsyncClient,
    db,
    manager_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    """Multi-word query across document metadata fields (stored tsvector + full vector path)."""
    own_id = await db.scalar(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id)
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    assert own_id is not None
    company_id = await db.scalar(select(Company.id).where(Company.tenant_id == tenant_id).limit(1))
    admin_id = await db.scalar(
        select(User.id)
        .where(User.tenant_id == tenant_id, User.role == UserRole.administrator.value)
        .limit(1)
    )
    assert admin_id is not None

    cid = str(uuid4())
    did = str(uuid4())
    token_a = f"DocFtsA{uuid4().hex[:6]}"
    token_b = f"DocFtsB{uuid4().hex[:6]}"
    now = _utc_naive_now()
    db.add(
        Candidate(
            id=cid,
            tenant_id=tenant_id,
            own_company_id=str(own_id),
            first_name="Doc",
            last_name="Holder",
            email=f"{cid[:8]}@example.com",
            stage="new",
            manager=str(admin_id),
            company_id=str(company_id) if company_id else None,
            created_at=now,
            updated_at=now,
        )
    )
    db.add(
        Document(
            id=did,
            tenant_id=tenant_id,
            own_company_id=str(own_id),
            candidate_id=cid,
            doc_type=token_a,
            custom_name=None,
            status=DocumentStatus.requested,
            user_comment=token_b,
        )
    )
    await db.commit()

    r = await client.get(
        SEARCH_URL,
        headers=manager_headers,
        params={"q": f"{token_a} {token_b}", "limit": 12, "max_results": 48},
    )
    assert r.status_code == 200, r.text
    docs = [i for i in r.json().get("items") or [] if i.get("type") == "document"]
    assert any(i.get("id") == did for i in docs), r.json()


@pytest.mark.asyncio
async def test_global_search_q_too_short_returns_422(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
) -> None:
    r = await client.get(
        SEARCH_URL,
        headers=recruiter_headers,
        params={"q": "a", "limit": 4, "max_results": 24},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_global_search_finds_candidate_with_own_company_scope(
    client: AsyncClient,
    db,
    manager_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    """GET /search applies active own_company_id like list endpoints; bootstrap rows may be NULL and hidden."""
    own_id = await db.scalar(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id)
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    company_id = await db.scalar(select(Company.id).where(Company.tenant_id == tenant_id).limit(1))
    admin_id = await db.scalar(
        select(User.id)
        .where(User.tenant_id == tenant_id, User.role == UserRole.administrator.value)
        .limit(1)
    )
    assert admin_id is not None

    cid = str(uuid4())
    token = f"GlobCandTok{uuid4().hex[:8]}"
    now = _utc_naive_now()
    db.add(
        Candidate(
            id=cid,
            tenant_id=tenant_id,
            own_company_id=str(own_id) if own_id else None,
            first_name=token,
            last_name="SearchTest",
            email=f"{token.lower()}@example.com",
            stage="new",
            manager=str(admin_id),
            company_id=str(company_id) if company_id else None,
            created_at=now,
            updated_at=now,
        )
    )
    await db.commit()

    r = await client.get(
        SEARCH_URL,
        headers=manager_headers,
        params={"q": token[:12], "limit": 8, "max_results": 40},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("q") == token[:12]
    cands = [i for i in body.get("items") or [] if i.get("type") == "candidate"]
    assert any(i.get("id") == cid for i in cands), body
    hit = next(i for i in cands if i.get("id") == cid)
    assert token in (hit.get("title") or "")


@pytest.mark.asyncio
async def test_global_search_task_slice_mine_matches_reminder(
    client: AsyncClient,
    db,
    manager_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    admin = await db.scalar(
        select(User).where(func.lower(User.email) == "biuro@work-host.com".lower())
    )
    assert admin is not None
    rid = str(uuid4())
    token = f"GlobSearchTaskTok{rid[:8]}"
    now = datetime.now(timezone.utc)
    db.add(
        Reminder(
            id=rid,
            tenant_id=tenant_id,
            type="custom",
            entity_type="custom",
            entity_id="search-test",
            title=f"{token} follow up",
            assignee_id=admin.id,
            due_at=now,
            status=ReminderStatus.pending,
            channel="internal",
        )
    )
    await db.commit()

    r = await client.get(
        SEARCH_URL,
        headers=manager_headers,
        params={"q": token[:12], "limit": 8, "max_results": 40},
    )
    assert r.status_code == 200, r.text
    tasks = [i for i in r.json().get("items") or [] if i.get("type") == "task"]
    hit = next((i for i in tasks if i.get("id") == rid), None)
    assert hit is not None
    assert token in (hit.get("title") or "")
    link = hit.get("link") or ""
    assert link.startswith("/app/tasks?")
    assert rid in link
    assert "t_q=" in link
    assert "t_assignee=team" not in link


@pytest.mark.asyncio
async def test_global_search_task_team_scope_supervisor_sees_recruiter_reminder(
    client: AsyncClient,
    db,
    supervisor_headers: Dict[str, str],
    tenant_id: str,
) -> None:
    rec = await db.scalar(
        select(User).where(func.lower(User.email) == "recruiter@work-host.com".lower())
    )
    assert rec is not None
    rid = str(uuid4())
    token = f"GlobTeamScope{rid[:8]}"
    now = datetime.now(timezone.utc)
    db.add(
        Reminder(
            id=rid,
            tenant_id=tenant_id,
            type="custom",
            entity_type="custom",
            entity_id="search-test-team",
            title=f"{token} review",
            assignee_id=rec.id,
            due_at=now,
            status=ReminderStatus.pending,
            channel="internal",
        )
    )
    await db.commit()

    r = await client.get(
        SEARCH_URL,
        headers=supervisor_headers,
        params={
            # Full token: team scope returns many assignees' rows; due_at ASC + low limit can
            # exclude a brand-new reminder. Unique string keeps a single ILIKE match.
            "q": token,
            "limit": 20,
            "max_results": 50,
            "assignee_scope": "team",
        },
    )
    assert r.status_code == 200, r.text
    tasks = [i for i in r.json().get("items") or [] if i.get("type") == "task"]
    hit = next((i for i in tasks if i.get("id") == rid), None)
    assert hit is not None
    assert "t_assignee=team" in (hit.get("link") or "")
