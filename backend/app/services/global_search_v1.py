"""
Global search v1: server-side merge + heuristic ranking for CRM core entities.

Leads, documents, and inbox threads additionally use PostgreSQL full-text search
(``hostflow_simple_tsvector`` + ``websearch_to_tsquery('simple')`` +
``ts_rank_cd``) alongside ILIKE so multi-word queries can match across
non-adjacent text (e.g. JSON fields), with optional quoted phrases / exclusions.
Leads use a JSON-only ``hostflow_simple_tsvector`` path (subset of the full
concat) for cheaper matches when only ``normalized``/``payload`` matter; GIN on
these expressions is not deployed (see migration ``202603291700`` / PG15+).

Leads are matched via normalized/payload JSON text, ids, stage/source/status, and
linked company name (same tenant / own_company scope as list endpoints).

Documents: server-side slice (tenant + own_company, same role gate as leads); document-row
``hostflow_document_search_tsv`` (GIN) plus full vector including linked candidate in-query.
Invoices, service orders, inbox threads (conversations), and reminders/tasks are searched here too.
Assignee scope for tasks matches GET /reminders (mine vs team).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlencode
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import String, Text, and_, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates import repo as cand_repo
from backend.app.api.v1.invoices import crud as invoice_crud
from backend.app.api.v1.candidates.acl import resolve_candidate_acl
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.auth.deps import Role, UserCtx
from backend.app.modules.companies.service import list_companies_service
from backend.app.api.v1.vacancies.repo import VacancyRepo
from backend.app.api.v1.vacancies.service import VacancyService
from backend.app.constants.spa_paths import (
    APP_PREFIX,
    TASKS,
    spa_candidate,
    spa_candidate_documents,
    spa_client,
    spa_lead,
    spa_vacancy,
)
from backend.app.db.deps import compute_tenant_visibility_for_tenant
from backend.app.models import Candidate, Company, Document, Lead
from backend.app.models.communication import CommunicationThread
from backend.app.models.tenant import Tenant
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.additional_services import AdditionalServicesService
from backend.app.services import reminder_tasks
from backend.app.services.tenant_visibility import get_tenant_visibility
from backend.app.services.global_search_fts import (
    BIND_GS_FTS_Q,
    as_text,
    fts_match_and_rank,
    fts_vector_from_concat,
)

logger = logging.getLogger(__name__)


@dataclass
class _SavedTenantCtx:
    tenant_id: Any
    tenant_visibility: Any


async def _push_scope_tenant_context(db: AsyncSession, scope_tenant: str) -> _SavedTenantCtx:
    """Align session.info + RLS + TenantVisibility with scope_tenant (see candidates scope_tenant_id)."""
    saved = _SavedTenantCtx(
        tenant_id=db.info.get("tenant_id"),
        tenant_visibility=db.info.get("tenant_visibility"),
    )
    tid = UUID(scope_tenant)
    db.info["tenant_id"] = tid
    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass
    db.info["tenant_visibility"] = await compute_tenant_visibility_for_tenant(db, tid)
    return saved


async def _pop_scope_tenant_context(db: AsyncSession, saved: _SavedTenantCtx) -> None:
    db.info["tenant_id"] = saved.tenant_id
    db.info["tenant_visibility"] = saved.tenant_visibility
    try:
        if saved.tenant_id is not None:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(saved.tenant_id)},
            )
    except Exception:
        pass

MAX_CONSECUTIVE_SAME_TYPE = 2


def _normalize_for_match(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _match_quality_score(q_norm: str, title: str, subtitle: str | None) -> int:
    if not q_norm:
        return 0
    t = _normalize_for_match(title)
    sub = _normalize_for_match(subtitle) if subtitle else ""
    hay = f"{t} {sub}".strip() if sub else t
    if t == q_norm:
        return 100
    if hay == q_norm:
        return 95
    if t.startswith(q_norm):
        return 85
    if hay.startswith(q_norm):
        return 80
    idx = hay.find(q_norm)
    if idx >= 0:
        at_word = idx == 0 or hay[idx - 1] == " "
        return 55 if at_word else 35
    # Multi-token: all words present somewhere in title+subtitle (IA v1 relevance heuristic).
    words = [w for w in q_norm.split() if len(w) >= 2]
    if len(words) > 1 and all(w in hay for w in words):
        return 48
    return 0


def _spa_invoice(invoice_id: str) -> str:
    return f"{APP_PREFIX}/invoices/{quote(str(invoice_id).strip(), safe='')}"


def _spa_service_order(order_id: str) -> str:
    return f"{APP_PREFIX}/orders?{urlencode({'order_id': str(order_id).strip()})}"


def _spa_task_link(*, reminder_id: str, raw_q: str, assignee_scope: str) -> str:
    pairs = [("t_q", raw_q.strip()), ("t_id", str(reminder_id).strip())]
    if str(assignee_scope or "").strip().lower() == "team":
        pairs.append(("t_assignee", "team"))
    return f"{TASKS}?{urlencode(pairs)}"


def _spa_inbox_thread(
    thread_id: str,
    *,
    channel: str | None,
    linked_candidate_id: str | None,
) -> str:
    tid = quote(str(thread_id).strip(), safe="")
    path = f"{APP_PREFIX}/inbox/threads/{tid}"
    pairs: list[tuple[str, str]] = []
    ch = str(channel or "").strip().lower()
    if ch == "email":
        pairs.append(("channel", "email"))
    elif ch:
        pairs.append(("channel", "messages"))
    cid = str(linked_candidate_id or "").strip()
    if cid:
        pairs.append(("candidateId", cid))
    if pairs:
        return f"{path}?{urlencode(pairs)}"
    return path


def merge_and_rank_items(
    items: list[dict[str, Any]],
    raw_query: str,
    *,
    max_out: int = 24,
) -> list[dict[str, Any]]:
    """Interleave by match quality (ported from frontend mergeSearchResultsHeuristic)."""
    if len(items) <= 1:
        return items[:max_out]
    q_norm = _normalize_for_match(raw_query)
    scored = [(it, _match_quality_score(q_norm, str(it.get("title") or ""), it.get("subtitle"))) for it in items]
    scored.sort(
        key=lambda x: (-x[1], str(x[0].get("title") or "").casefold()),
    )
    pool = [x[0] for x in scored]
    out: list[dict[str, Any]] = []
    last_type: str | None = None
    streak = 0
    while len(out) < max_out and pool:
        idx = next(
            (i for i, item in enumerate(pool) if not (item.get("type") == last_type and streak >= MAX_CONSECUTIVE_SAME_TYPE)),
            0,
        )
        next_item = pool.pop(idx)
        out.append(next_item)
        nt = str(next_item.get("type") or "")
        if nt == last_type:
            streak += 1
        else:
            last_type = nt
            streak = 1
    return out


def _candidate_row_to_model(row: Any) -> Any:
    return row[0] if isinstance(row, (list, tuple)) and row else row


def _candidate_to_mask_dict(c: Any) -> dict[str, Any]:
    extra = getattr(c, "extra", None)
    if not isinstance(extra, dict):
        extra = {}
    return {
        "id": str(c.id),
        "tenant_id": str(getattr(c, "tenant_id", "") or "") or None,
        "short_id": getattr(c, "short_id", None),
        "first_name": getattr(c, "first_name", None),
        "last_name": getattr(c, "last_name", None),
        "email": getattr(c, "email", None),
        "phone": getattr(c, "phone", None),
        "phone_country_code": getattr(c, "phone_country_code", None),
        "stage": getattr(c, "stage", None),
        "extra": extra,
    }


async def _search_candidates_slice(
    db: AsyncSession,
    *,
    scope_tenant: str,
    current_user: UserCtx,
    own_company_id: str | None,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    from backend.app.api.v1.candidates.router import ACL_RESTRICTED_ROLES, _apply_client_view_mask

    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass

    visibility = get_tenant_visibility(db, scope_tenant)
    filters: dict[str, object] = {}
    client_tenant = await is_client_tenant_for_list(db, scope_tenant)
    if own_company_id and not client_tenant:
        filters["own_company_id"] = own_company_id
    filters["is_client_tenant"] = client_tenant

    user_role_lower = (current_user.role or "").lower()
    is_platform_superadmin = user_role_lower == Role.superadmin.value and not client_tenant
    apply_client_view = client_tenant and not is_platform_superadmin

    qs = q.strip()
    if not qs:
        return []
    filters["q"] = qs

    if current_user.role in ACL_RESTRICTED_ROLES:
        acl = await resolve_candidate_acl(db, scope_tenant, current_user)
        if not client_tenant and acl.is_empty():
            return []
        if not client_tenant:
            filters["allowed_company_ids"] = list(acl.company_ids)
            filters["allowed_vacancy_ids"] = list(acl.vacancy_ids)
            filters["allowed_manager_ids"] = list(acl.manager_ids)

    raw_rows: list[Any]
    if client_tenant:
        cands = await cand_repo.list_candidates(
            db,
            scope_tenant,
            filters,
            "created_at",
            True,
            limit,
            0,
            visibility,
        )
        raw_rows = list(cands)
    else:
        rows = await cand_repo.fetch_candidates_with_labels(
            db,
            tenant_id=scope_tenant,
            filters=filters,
            limit=limit,
            offset=0,
            order_by="created_at",
            desc=True,
            visibility=visibility,
        )
        raw_rows = list(rows)

    out: list[dict[str, Any]] = []
    for row in raw_rows:
        c = _candidate_row_to_model(row)
        if c is None:
            continue
        item = _candidate_to_mask_dict(c)
        cid = str(item["id"])
        if apply_client_view:
            item = await _apply_client_view_mask(db, item, cid, scope_tenant)
        fn = str(item.get("first_name") or "").strip()
        ln = str(item.get("last_name") or "").strip()
        title = f"{fn} {ln}".strip() or (str(item.get("email") or "").strip()) or (str(item.get("short_id") or "").strip()) or "Candidate"
        email = item.get("email")
        stage = item.get("stage")
        subtitle = str(stage) if stage else (str(email) if email else None)
        out.append(
            {
                "type": "candidate",
                "id": cid,
                "title": title,
                "subtitle": subtitle,
                "link": spa_candidate(cid),
            }
        )
    return out


async def _search_companies_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    try:
        acl = await resolve_restricted_acl(db, tenant_id, current_user)
        allowed_company_ids = None if acl is None else set(acl.company_ids)
        companies = await list_companies_service(
            db=db,
            q=q.strip() or None,
            include_archived=False,
            allowed_company_ids=allowed_company_ids,
        )
        sliced = companies[:limit]
        results: list[dict[str, Any]] = []
        for c in sliced:
            cid = str(c.id)
            name = (getattr(c, "name", None) or getattr(c, "legal_name", None) or "Company") or "Company"
            city = getattr(c, "city", None)
            cc = getattr(c, "country_code", None)
            subtitle = " · ".join(x for x in [str(city) if city else None, str(cc) if cc else None] if x) or None
            results.append(
                {
                    "type": "company",
                    "id": cid,
                    "title": str(name),
                    "subtitle": subtitle,
                    "link": spa_client(cid),
                }
            )
        return results
    except Exception:
        logger.exception("global_search companies slice failed")
        return []


def _user_can_global_search_leads(user: UserCtx) -> bool:
    """Align with GET /leads list roles (no client handoff roles)."""
    r = (user.role or "").strip().lower()
    return r not in (Role.client_manager.value, Role.client_processor.value)


async def _search_leads_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    current_user: UserCtx,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    if not _user_can_global_search_leads(current_user):
        return []
    raw_q = q.strip()
    qs = raw_q.lower()
    if len(qs) < 2:
        return []
    like = f"%{qs}%"
    try:
        text_norm = cast(Lead.normalized, Text)
        text_payload = cast(Lead.payload, Text)
        company_l = func.lower(func.coalesce(Company.name, ""))
        ilike_clause = or_(
            func.lower(text_norm).like(like),
            func.lower(text_payload).like(like),
            func.lower(Lead.id).like(like),
            func.lower(Lead.source).like(like),
            func.lower(func.coalesce(Lead.stage, "")).like(like),
            func.lower(func.coalesce(Lead.status, "")).like(like),
            func.lower(func.coalesce(Lead.lead_type, "")).like(like),
            company_l.like(like),
        )
        # JSON: prefer trigger-maintained tsvector (GIN); coalesce fallback before backfill / old rows.
        lead_json_vec = func.coalesce(
            Lead.hostflow_lead_json_tsv,
            fts_vector_from_concat(
                func.coalesce(as_text(Lead.normalized), ""),
                func.coalesce(as_text(Lead.payload), ""),
            ),
        )
        lead_vec = fts_vector_from_concat(
            as_text(Lead.normalized),
            as_text(Lead.payload),
            func.coalesce(Company.name, ""),
            as_text(Lead.id),
            func.coalesce(Lead.source, ""),
            func.coalesce(Lead.stage, ""),
            func.coalesce(Lead.status, ""),
            func.coalesce(Lead.lead_type, ""),
        )
        fts_match_json, fts_rank_json = fts_match_and_rank(lead_json_vec)
        fts_match_full, fts_rank_full = fts_match_and_rank(lead_vec)
        fts_rank_best = func.greatest(
            func.coalesce(fts_rank_json, 0.0),
            func.coalesce(fts_rank_full, 0.0),
        )
        search_clause = or_(ilike_clause, fts_match_json, fts_match_full)
        filters: list[Any] = [Lead.tenant_id == tenant_id, search_clause]
        if own_company_id:
            filters.append(Lead.own_company_id == own_company_id)
        stmt = (
            select(Lead)
            .outerjoin(Company, Company.id == Lead.company_id)
            .where(*filters)
            .order_by(fts_rank_best.desc(), Lead.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt, {BIND_GS_FTS_Q: raw_q})).scalars().all()
    except Exception:
        logger.exception("global_search leads slice failed")
        return []

    out: list[dict[str, Any]] = []
    for lead in rows:
        lid = str(lead.id)
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        fn = str(norm.get("first_name") or norm.get("name") or "").strip()
        ln = str(norm.get("last_name") or "").strip()
        title = (
            f"{fn} {ln}".strip()
            or str(norm.get("email") or "").strip()
            or str(norm.get("phone") or "").strip()
            or f"Lead {lid[:8]}…"
        )
        parts = [lead.stage, lead.source, lead.status]
        subtitle = " · ".join(str(p) for p in parts if p) or None
        out.append(
            {
                "type": "lead",
                "id": lid,
                "title": title,
                "subtitle": subtitle,
                "link": spa_lead(lid),
            }
        )
    return out


async def _search_documents_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    current_user: UserCtx,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Match documents by metadata + linked candidate name/email (same client-role gate as leads)."""
    if not _user_can_global_search_leads(current_user):
        return []
    raw_q = q.strip()
    qs = raw_q.lower()
    if len(qs) < 2:
        return []
    like = f"%{qs}%"
    try:
        status_txt = cast(Document.status, Text)
        ilike_clause = or_(
            func.lower(Document.doc_type).like(like),
            func.lower(func.coalesce(Document.custom_name, "")).like(like),
            func.lower(func.coalesce(Document.filename, "")).like(like),
            func.lower(func.coalesce(Document.number, "")).like(like),
            func.lower(func.coalesce(Document.external_id, "")).like(like),
            func.lower(func.coalesce(Document.user_comment, "")).like(like),
            func.lower(func.coalesce(Document.source, "")).like(like),
            func.lower(Document.id).like(like),
            func.lower(Document.candidate_id).like(like),
            func.lower(status_txt).like(like),
            func.lower(func.coalesce(Candidate.first_name, "")).like(like),
            func.lower(func.coalesce(Candidate.last_name, "")).like(like),
            func.lower(func.coalesce(Candidate.email, "")).like(like),
        )
        doc_parts = [
            func.coalesce(Document.doc_type, ""),
            func.coalesce(Document.custom_name, ""),
            func.coalesce(Document.filename, ""),
            func.coalesce(Document.number, ""),
            func.coalesce(Document.external_id, ""),
            func.coalesce(Document.user_comment, ""),
            func.coalesce(Document.source, ""),
            as_text(Document.id),
            as_text(Document.candidate_id),
            status_txt,
        ]
        doc_stored = func.coalesce(
            Document.hostflow_document_search_tsv,
            fts_vector_from_concat(*doc_parts),
        )
        full_vec = fts_vector_from_concat(
            *doc_parts,
            func.coalesce(Candidate.first_name, ""),
            func.coalesce(Candidate.last_name, ""),
            func.coalesce(Candidate.email, ""),
        )
        fts_match_doc, fts_rank_doc = fts_match_and_rank(doc_stored)
        fts_match_full, fts_rank_full = fts_match_and_rank(full_vec)
        fts_match = or_(fts_match_doc, fts_match_full)
        fts_rank_best = func.greatest(
            func.coalesce(fts_rank_doc, 0.0),
            func.coalesce(fts_rank_full, 0.0),
        )
        search_clause = or_(ilike_clause, fts_match)
        filters = [
            Document.tenant_id == tenant_id,
            Document.deleted_at.is_(None),
            search_clause,
        ]
        if own_company_id:
            filters.append(Document.own_company_id == own_company_id)
        stmt = (
            select(Document, Candidate, fts_rank_best.label("fts_rank"))
            .outerjoin(Candidate, Candidate.id == Document.candidate_id)
            .where(and_(*filters))
            .order_by(fts_rank_best.desc().nulls_last(), Document.updated_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt, {BIND_GS_FTS_Q: raw_q})).all()
    except Exception:
        logger.exception("global_search documents slice failed")
        return []

    out: list[dict[str, Any]] = []
    for doc, cand, *_ in rows:
        did = str(doc.id)
        title = (str(doc.custom_name).strip() if doc.custom_name else "") or str(doc.doc_type or "").strip() or "Document"
        st = getattr(doc.status, "value", None) or (str(doc.status) if doc.status is not None else "")
        fn = str(getattr(cand, "first_name", None) or "").strip() if cand else ""
        ln = str(getattr(cand, "last_name", None) or "").strip() if cand else ""
        cand_label = f"{fn} {ln}".strip()
        subtitle = " · ".join(x for x in (cand_label or None, st) if x) or None
        cid = str(doc.candidate_id or "").strip()
        link = spa_candidate_documents(cid) if cid else f"{APP_PREFIX}/documents"
        out.append(
            {
                "type": "document",
                "id": did,
                "title": title,
                "subtitle": subtitle,
                "link": link,
            }
        )
    return out


async def _search_invoices_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    qs = q.strip()
    if len(qs) < 2:
        return []
    try:
        rows = await invoice_crud.list_invoices(
            db,
            tenant_id,
            own_company_id=own_company_id,
            q=qs,
            limit=limit,
            offset=0,
        )
    except Exception:
        logger.exception("global_search invoices slice failed")
        return []

    out: list[dict[str, Any]] = []
    for inv in rows:
        iid = str(inv.id)
        title = str(inv.invoice_number or "").strip() or "Invoice"
        st = str(getattr(inv.status, "value", None) or inv.status or "").strip()
        amt = inv.total_amount
        cur = str(inv.currency or "").strip()
        money: str | None = None
        if amt is not None:
            money = f"{amt} {cur}".strip() if cur else str(amt)
        subtitle = " · ".join(x for x in (st, money) if x) or None
        out.append(
            {
                "type": "invoice",
                "id": iid,
                "title": title,
                "subtitle": subtitle,
                "link": _spa_invoice(iid),
            }
        )
    return out


async def _search_service_orders_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    qs = q.strip()
    if len(qs) < 2:
        return []
    try:
        svc = AdditionalServicesService(db, tenant_id)
        rows = await svc.list_orders(
            q=qs,
            limit=limit,
            own_company_scope=own_company_id,
        )
    except Exception:
        logger.exception("global_search service_orders slice failed")
        return []

    out: list[dict[str, Any]] = []
    for order in rows:
        oid = str(order.id)
        short = f"{oid[:8]}…" if len(oid) > 12 else oid
        st = str(getattr(order.status, "value", None) or order.status or "").strip()
        amt = getattr(order, "total_amount", None)
        cur = str(getattr(order, "currency", None) or "").strip()
        money: str | None = None
        if amt is not None:
            money = f"{amt} {cur}".strip() if cur else str(amt)
        subtitle = " · ".join(x for x in (st, money) if x) or None
        out.append(
            {
                "type": "service_order",
                "id": oid,
                "title": short,
                "subtitle": subtitle,
                "link": _spa_service_order(oid),
            }
        )
    return out


async def _search_conversations_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    current_user: UserCtx,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    qs = q.strip()
    if len(qs) < 2:
        return []
    try:
        tenant_row = await db.scalar(select(Tenant).where(Tenant.id == tenant_id).limit(1))
        if tenant_row is None:
            return []
        allowed = False
        for feat in ("messages", "email"):
            try:
                assert_comm_feature_access(
                    tenant=tenant_row,
                    current_user=current_user,
                    feature=feat,  # type: ignore[arg-type]
                    tenant_id=tenant_id,
                )
                allowed = True
                break
            except HTTPException:
                continue
        if not allowed:
            return []

        like = f"%{qs.lower()}%"
        ilike_clause = or_(
            func.lower(func.coalesce(CommunicationThread.subject, "")).like(like),
            func.lower(func.coalesce(CommunicationThread.last_message_preview, "")).like(like),
            func.lower(cast(func.coalesce(CommunicationThread.channel_thread_ref, ""), String)).like(like),
        )
        conv_tsv = func.coalesce(
            CommunicationThread.hostflow_search_tsv,
            fts_vector_from_concat(
                func.coalesce(CommunicationThread.subject, ""),
                func.coalesce(CommunicationThread.last_message_preview, ""),
                cast(func.coalesce(CommunicationThread.channel_thread_ref, ""), String),
            ),
        )
        fts_match, fts_rank = fts_match_and_rank(conv_tsv)
        filters = [
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.is_archived.is_(False),
            or_(ilike_clause, fts_match),
        ]
        if own_company_id:
            filters.append(CommunicationThread.own_company_id == own_company_id)
        last_at = func.coalesce(CommunicationThread.last_message_at, CommunicationThread.updated_at)
        stmt = (
            select(CommunicationThread)
            .where(and_(*filters))
            .order_by(
                fts_rank.desc().nulls_last(),
                last_at.desc(),
                CommunicationThread.updated_at.desc(),
            )
            .limit(limit)
        )
        rows = (await db.execute(stmt, {BIND_GS_FTS_Q: qs})).scalars().all()
    except Exception:
        logger.exception("global_search conversations slice failed")
        return []

    out: list[dict[str, Any]] = []
    for t in rows:
        tid = str(t.id)
        subj = str(t.subject or "").strip()
        prev = str(t.last_message_preview or "").strip()
        title = subj or (prev[:80] if prev else "") or tid
        ch = str(t.channel or "").strip()
        preview = prev[:120] if prev else ""
        subtitle = " · ".join(x for x in (ch, preview) if x) or None
        cand = str(t.linked_candidate_id or "").strip() or None
        out.append(
            {
                "type": "conversation",
                "id": tid,
                "title": title,
                "subtitle": subtitle,
                "link": _spa_inbox_thread(tid, channel=ch or None, linked_candidate_id=cand),
            }
        )
    return out


def _format_task_due_subtitle(due_at: datetime | None) -> str:
    if due_at is None:
        return ""
    s = due_at.isoformat()
    return s[:16].replace("T", " ") if s else ""


async def _search_tasks_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
    q: str,
    limit: int,
    assignee_scope: str,
) -> list[dict[str, Any]]:
    qs = q.strip()
    if len(qs) < 2:
        return []
    try:
        aid = reminder_tasks.resolve_assignee_for_reminder_list(
            explicit_assignee_id=None,
            assignee_scope=assignee_scope,
            viewer_id=str(getattr(current_user, "sub", "") or "").strip(),
            viewer_role=str(getattr(current_user, "role", "") or ""),
        )
        rows = await reminder_tasks.list_reminders(
            db,
            tenant_id=tenant_id,
            assignee_id=aid,
            q=qs,
            limit=limit,
        )
    except Exception:
        logger.exception("global_search tasks slice failed")
        return []

    scope = str(assignee_scope or "mine").strip().lower()
    out: list[dict[str, Any]] = []
    for rem in rows:
        rid = str(rem.id)
        title = str(rem.title or "").strip() or str(rem.type or "").strip() or "Task"
        st = str(rem.status or "").strip()
        due_txt = _format_task_due_subtitle(rem.due_at)
        subtitle = " · ".join(x for x in (st, due_txt) if x) or None
        out.append(
            {
                "type": "task",
                "id": rid,
                "title": title,
                "subtitle": subtitle,
                "link": _spa_task_link(reminder_id=rid, raw_q=qs, assignee_scope=scope),
            }
        )
    return out


async def _search_vacancies_slice(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    current_user: UserCtx,
    own_company_id: str | None,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    try:
        tid = str(tenant_id)
        visibility = get_tenant_visibility(db, tid)
        svc = VacancyService(VacancyRepo(db, tid, own_company_id=own_company_id, visibility=visibility))
        acl = await resolve_restricted_acl(db, tid, current_user)
        rows = await svc.list(
            company_id=None,
            status=None,
            search=q.strip() or None,
            candidate_profile_id=None,
            limit=limit,
            offset=0,
            order_by="created_at",
            descending=True,
            acl=acl,
            include_archived=False,
        )
        results: list[dict[str, Any]] = []
        for v in rows:
            vid = str(v.id)
            parts = [v.company_name, v.status]
            subtitle = " · ".join(str(p) for p in parts if p) or None
            results.append(
                {
                    "type": "vacancy",
                    "id": vid,
                    "title": str(v.title or "Vacancy"),
                    "subtitle": subtitle,
                    "link": spa_vacancy(vid),
                }
            )
        return results
    except Exception:
        logger.exception("global_search vacancies slice failed")
        return []


async def run_global_search_v1(
    db: AsyncSession,
    *,
    header_tenant_id: UUID,
    scope_tenant_id: UUID | None,
    current_user: UserCtx,
    own_company_id: str | None,
    q: str,
    limit_per_type: int,
    max_results: int,
    assignee_scope: str,
) -> dict[str, Any]:
    scope_tenant = str(scope_tenant_id).strip() if scope_tenant_id else str(header_tenant_id).strip()
    header_str = str(header_tenant_id).strip()
    scope_override = scope_tenant != header_str

    saved: _SavedTenantCtx | None = None
    if scope_override:
        saved = await _push_scope_tenant_context(db, scope_tenant)

    candidates: list[dict[str, Any]] = []
    companies: list[dict[str, Any]] = []
    vacancies: list[dict[str, Any]] = []
    leads: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    invoices: list[dict[str, Any]] = []
    service_orders: list[dict[str, Any]] = []
    conversations: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []

    try:
        # One session: run sequentially (avoid concurrent set_config / session mutation).
        candidates = await _search_candidates_slice(
            db,
            scope_tenant=scope_tenant,
            current_user=current_user,
            own_company_id=own_company_id,
            q=q,
            limit=limit_per_type,
        )
        companies = await _search_companies_slice(
            db,
            tenant_id=scope_tenant,
            current_user=current_user,
            q=q,
            limit=limit_per_type,
        )
        vacancies = await _search_vacancies_slice(
            db,
            tenant_id=UUID(scope_tenant),
            current_user=current_user,
            own_company_id=own_company_id,
            q=q,
            limit=limit_per_type,
        )
        leads = await _search_leads_slice(
            db,
            tenant_id=scope_tenant,
            own_company_id=own_company_id,
            current_user=current_user,
            q=q,
            limit=limit_per_type,
        )
        documents = await _search_documents_slice(
            db,
            tenant_id=scope_tenant,
            own_company_id=own_company_id,
            current_user=current_user,
            q=q,
            limit=limit_per_type,
        )
        invoices = await _search_invoices_slice(
            db,
            tenant_id=scope_tenant,
            own_company_id=own_company_id,
            q=q,
            limit=limit_per_type,
        )
        service_orders = await _search_service_orders_slice(
            db,
            tenant_id=scope_tenant,
            own_company_id=own_company_id,
            q=q,
            limit=limit_per_type,
        )
        conversations = await _search_conversations_slice(
            db,
            tenant_id=scope_tenant,
            own_company_id=own_company_id,
            current_user=current_user,
            q=q,
            limit=limit_per_type,
        )
        tasks = await _search_tasks_slice(
            db,
            tenant_id=scope_tenant,
            current_user=current_user,
            q=q,
            limit=limit_per_type,
            assignee_scope=assignee_scope,
        )
    finally:
        if saved is not None:
            await _pop_scope_tenant_context(db, saved)

    merged = [
        *candidates,
        *companies,
        *vacancies,
        *leads,
        *documents,
        *invoices,
        *service_orders,
        *conversations,
        *tasks,
    ]
    ranked = merge_and_rank_items(merged, q.strip(), max_out=max_results)
    return {"q": q.strip(), "items": ranked}
