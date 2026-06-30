from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import String, and_, case, cast, delete, func, or_, select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Candidate,
    Company,
    Lead,
    MetaAdsMap,
    MetaFormRoute,
    MetaLeadCredential,
    MetaLeadFormMapping,
    MetaLeadSettings,
    MetaOAuthPending,
    Vacancy,
)
from backend.app.services.lead_quota import ensure_monthly_lead_creation_allowed


async def create_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    company_id: Optional[str],
    vacancy_id: Optional[str],
    payload: Dict[str, Any],
    normalized: Optional[Dict[str, Any]],
    source: str = "meta",
    ad_id: Optional[int] = None,
    last_routed_at: Optional[datetime] = None,
    external_id: Optional[str] = None,
    lead_type: str = "candidate",
    lead_target_type: str = "candidate",
) -> Lead:
    lt = str(lead_type or "candidate").strip().lower()
    if lt not in {"candidate", "client"}:
        lt = "candidate"
    ltt = str(lead_target_type or lt).strip().lower()
    if ltt not in {"candidate", "client_lead", "service_order_lead", "partner_lead"}:
        ltt = "candidate" if lt == "candidate" else "client_lead"
    if ltt == "client_lead":
        lt = "client"
        if not str(own_company_id or "").strip():
            raise ValueError("own_company_id is required for client leads")
        if company_id:
            raise ValueError("company_id must be empty for client leads")
        if vacancy_id:
            raise ValueError("vacancy_id must be empty for client leads")
    if lt == "candidate" and ltt == "candidate" and not company_id:
        raise ValueError("company_id is required for candidate leads")
    await ensure_monthly_lead_creation_allowed(db, tenant_id)
    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        lead_type=lt,
        lead_target_type=ltt,
        company_id=company_id,
        vacancy_id=vacancy_id,
        source=source,
        ad_id=ad_id,
        payload=payload,
        normalized=normalized,
        last_routed_at=last_routed_at,
        external_id=external_id,
    )
    db.add(lead)
    await db.flush()
    if lt == "candidate" and company_id:
        from backend.app.services.recruitment_funnel_resolver import (
            RecruitmentFunnelNotFoundError,
            RecruitmentModuleNotEnabledError,
            resolve_recruitment_funnel,
        )

        try:
            resolved = await resolve_recruitment_funnel(
                db,
                tenant_id=tenant_id,
                company_id=str(company_id),
                pipeline_type="lead",
            )
            lead.funnel_id = resolved.funnel.id
            await db.flush()
        except RecruitmentModuleNotEnabledError as exc:
            raise ValueError(str(exc)) from exc
        except RecruitmentFunnelNotFoundError as exc:
            raise ValueError(str(exc)) from exc
    return lead


async def update_lead(
    db: AsyncSession,
    lead: Lead,
    *,
    status: str,
    candidate_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
    normalized: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    last_routed_at: Optional[datetime] = None,
    stage: Optional[str] = None,
) -> Lead:
    lead.status = status
    lead.candidate_id = candidate_id
    if stage is not None:
        lead.stage = stage
    if vacancy_id is not None:
        lead.vacancy_id = vacancy_id
    if normalized is not None:
        from backend.app.services.lead_communications import normalized_merging_lead_persisted_blocks

        lead.normalized = normalized_merging_lead_persisted_blocks(lead, normalized)
    lead.error = error
    if last_routed_at is not None:
        lead.last_routed_at = last_routed_at
    await db.flush()
    return lead


async def resolve_vacancy_by_id(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
    *,
    scoped_own_company_id: Optional[str] = None,
) -> Optional[Vacancy]:
    oc = str(scoped_own_company_id or "").strip() or None
    stmt = select(Vacancy).where(
        Vacancy.id == vacancy_id,
        Vacancy.tenant_id == tenant_id,
    )
    if oc:
        stmt = stmt.where(
            or_(Vacancy.own_company_id.is_(None), Vacancy.own_company_id == oc)
        )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def resolve_vacancy_by_ad(
    db: AsyncSession,
    tenant_id: str,
    ad_id: Optional[int],
    *,
    scoped_own_company_id: Optional[str] = None,
) -> Optional[Vacancy]:
    if not ad_id:
        return None
    oc = str(scoped_own_company_id or "").strip() or None
    stmt = (
        select(Vacancy)
        .join(MetaAdsMap, MetaAdsMap.vacancy_id == Vacancy.id)
        .where(
            MetaAdsMap.ad_id == ad_id,
            MetaAdsMap.tenant_id == tenant_id,
            Vacancy.tenant_id == tenant_id,
        )
        .limit(1)
    )
    if oc:
        stmt = stmt.where(
            or_(Vacancy.own_company_id.is_(None), Vacancy.own_company_id == oc)
        )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def last_resort_first_open_vacancy_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: str,
    scoped_own_company_id: Optional[str] = None,
) -> Optional[Vacancy]:
    """
    When ad_map / rules / ordered routing find nothing, pick the oldest active open vacancy
    so ingest can still attach company + create a candidate (audited via ``vacancy_routing_fallback_v1``).
    """
    oc = str(scoped_own_company_id or "").strip() or None
    base = (
        select(Vacancy)
        .where(
            Vacancy.tenant_id == tenant_id,
            Vacancy.is_archived.is_(False),
            Vacancy.is_active.is_(True),
            Vacancy.status == "open",
        )
        .order_by(Vacancy.created_at.asc())
        .limit(1)
    )
    if oc:
        stmt = base.where(
            or_(Vacancy.own_company_id.is_(None), Vacancy.own_company_id == oc)
        )
        hit = (await db.execute(stmt)).scalar_one_or_none()
        if hit is not None:
            return hit
    stmt_all = (
        select(Vacancy)
        .where(
            Vacancy.tenant_id == tenant_id,
            Vacancy.is_archived.is_(False),
            Vacancy.is_active.is_(True),
            Vacancy.status == "open",
        )
        .order_by(Vacancy.created_at.asc())
        .limit(1)
    )
    return (await db.execute(stmt_all)).scalar_one_or_none()


async def get_default_company_id(db: AsyncSession, tenant_id: str) -> Optional[str]:
    stmt = (
        select(Company.id)
        .where(Company.tenant_id == tenant_id)
        .order_by(Company.created_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def resolve_company_by_name(
    db: AsyncSession,
    tenant_id: str,
    name_hint: Optional[str],
) -> Optional[str]:
    if not name_hint:
        return None
    needle = str(name_hint).strip()
    if not needle:
        return None
    needle_lower = needle.lower()

    exact_stmt = (
        select(Company.id)
        .where(
            Company.tenant_id == tenant_id,
            func.lower(Company.name) == needle_lower,
        )
        .order_by(Company.created_at.asc())
        .limit(1)
    )
    result = await db.execute(exact_stmt)
    match = result.scalar_one_or_none()
    if match:
        return match

    like_pattern = f"%{needle_lower}%"
    fuzzy_stmt = (
        select(Company.id)
        .where(
            Company.tenant_id == tenant_id,
            func.lower(Company.name).like(like_pattern),
        )
        .order_by(func.length(Company.name))
        .limit(1)
    )
    result = await db.execute(fuzzy_stmt)
    return result.scalar_one_or_none()


async def find_duplicate_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    email: Optional[str],
    phone: Optional[str],
) -> Optional[Candidate]:
    import re
    
    matchers = []
    if email:
        email_lower = email.lower()
        matchers.append(func.lower(Candidate.email) == email_lower)
    if phone:
        # Normalize phone: extract only digits for comparison
        # This handles cases where phone might be stored in different formats:
        # - "664319903" vs "+48664319903" vs "48664319903"
        # - With/without country code, with/without + prefix, with spaces/dashes
        phone_digits = re.sub(r"\D", "", phone.strip())
        
        if phone_digits:
            # Build phone matchers: exact match and variations
            phone_matchers = []
            
            # 1. Exact match with original phone (as stored)
            phone_matchers.append(Candidate.phone == phone.strip())
            
            # 2. Match by digits only (normalize both sides)
            # Use regexp_replace to extract digits from stored phone and compare
            stored_phone_digits = func.regexp_replace(
                func.coalesce(Candidate.phone, ""),
                r"[^0-9]",
                "",
                "g"
            )
            phone_matchers.append(stored_phone_digits == phone_digits)
            
            # 3. Handle cases where one number has country code and other doesn't
            # For Polish numbers: "664319903" (9 digits) should match "+48664319903" (12 digits = 48 + 664319903)
            # We compare the last 9-10 digits (typical mobile number length)
            if len(phone_digits) >= 9:
                # If input is short (9-10 digits), check if stored number ends with these digits
                # If input is long (11+ digits), check if stored number ends with last 9-10 digits
                compare_length = min(9, len(phone_digits))
                last_digits = phone_digits[-compare_length:]
                phone_matchers.append(stored_phone_digits.like(f"%{last_digits}"))
            
            if phone_matchers:
                matchers.append(or_(*phone_matchers))

    if not matchers:
        return None

    filters = [Candidate.tenant_id == tenant_id, Candidate.deleted_at.is_(None)]
    if company_id:
        filters.append(
            or_(Candidate.company_id == company_id, Candidate.company_id.is_(None))
        )

    stmt = (
        select(Candidate)
        .where(and_(*filters, or_(*matchers)))
        .order_by(Candidate.created_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> Optional[Lead]:
    stmt = select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> bool:
    """Hard-delete a lead row. Returns True if a row was removed."""
    stmt = delete(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id)
    res = await db.execute(stmt)
    await db.flush()
    rc = getattr(res, "rowcount", None)
    return bool(rc is not None and rc > 0)


async def get_lead_by_external_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    source: str,
    external_id: str,
) -> Optional[Lead]:
    stmt = (
        select(Lead)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.source == source,
            Lead.external_id == external_id,
        )
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_leads_for_retry(
    db: AsyncSession,
    *,
    tenant_id: str,
    statuses: Optional[list[str]] = None,
    lead_ids: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> list[Lead]:
    stmt = select(Lead).where(Lead.tenant_id == tenant_id)
    if statuses:
        stmt = stmt.where(Lead.status.in_(list(statuses)))
    if lead_ids:
        stmt = stmt.where(Lead.id.in_(list(lead_ids)))
    stmt = stmt.order_by(Lead.created_at.asc())
    if limit:
        stmt = stmt.limit(limit)
    rows = await db.execute(stmt)
    return list(rows.scalars())


async def list_leads_with_unmapped_ad_ids(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str = "needs_routing",
    limit_per_ad: int = 10,
) -> list[tuple[int, list[Lead]]]:
    """Return leads grouped by ad_id where ad_id is not in meta_ads_map."""
    mapped_stmt = select(MetaAdsMap.ad_id).where(MetaAdsMap.tenant_id == tenant_id)
    mapped_result = await db.execute(mapped_stmt)
    mapped_ad_ids = {int(row.ad_id) for row in mapped_result.fetchall()}

    stmt = (
        select(Lead)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.status == status,
            Lead.ad_id.isnot(None),
        )
        .order_by(Lead.created_at.desc())
    )
    result = await db.execute(stmt)
    all_leads = list(result.scalars().all())

    grouped: dict[int, list[Lead]] = {}
    for lead in all_leads:
        if lead.ad_id is None or lead.ad_id in mapped_ad_ids:
            continue
        if lead.ad_id not in grouped:
            grouped[lead.ad_id] = []
        if len(grouped[lead.ad_id]) < limit_per_ad:
            grouped[lead.ad_id].append(lead)

    return [(ad_id, leads) for ad_id, leads in sorted(grouped.items(), key=lambda x: -len(x[1]))]


async def update_lead_stage(
    db: AsyncSession,
    lead: Lead,
    *,
    stage: Optional[str],
) -> Lead:
    lead.stage = stage
    await db.flush()
    return lead


async def bulk_update_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_ids: list[str],
    stage: Optional[str] = None,
    status: Optional[str] = None,
) -> int:
    if not lead_ids:
        return 0
    values: Dict[str, Any] = {}
    if stage is not None:
        values["stage"] = stage
    if status is not None:
        values["status"] = status
    if not values:
        return 0
    stmt = (
        update(Lead)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.id.in_(lead_ids),
        )
        .values(**values)
    )
    res = await db.execute(stmt)
    await db.flush()
    return int(getattr(res, "rowcount", 0) or 0)


async def list_meta_ads_map(
    db: AsyncSession,
    *,
    tenant_id: str,
    search: Optional[str] = None,
    limit: int = 200,
) -> list[MetaAdsMap]:
    stmt = (
        select(MetaAdsMap)
        .where(MetaAdsMap.tenant_id == tenant_id)
        .order_by(MetaAdsMap.created_at.desc())
        .limit(limit)
    )
    if search:
        clauses = []
        if search.isdigit():
            clauses.append(MetaAdsMap.ad_id == int(search))
        clauses.append(cast(MetaAdsMap.ad_id, String).ilike(f"%{search}%"))
        stmt = stmt.where(or_(*clauses))
    rows = await db.execute(stmt)
    return list(rows.scalars())


async def upsert_meta_ads_map(
    db: AsyncSession,
    *,
    tenant_id: str,
    ad_id: int,
    vacancy_id: str,
    note: Optional[str],
) -> MetaAdsMap:
    stmt = select(MetaAdsMap).where(
        MetaAdsMap.ad_id == ad_id,
        MetaAdsMap.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry:
        entry.vacancy_id = vacancy_id
        entry.note = note
    else:
        entry = MetaAdsMap(
            ad_id=ad_id,
            tenant_id=tenant_id,
            vacancy_id=vacancy_id,
            note=note,
        )
        db.add(entry)
    await db.flush()
    return entry


async def get_meta_ads_entry(
    db: AsyncSession,
    *,
    tenant_id: str,
    ad_id: int,
) -> Optional[MetaAdsMap]:
    stmt = select(MetaAdsMap).where(
        MetaAdsMap.tenant_id == tenant_id,
        MetaAdsMap.ad_id == ad_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_meta_ads_map(
    db: AsyncSession,
    *,
    tenant_id: str,
    ad_id: int,
) -> int:
    stmt = (
        select(MetaAdsMap)
        .where(MetaAdsMap.ad_id == ad_id, MetaAdsMap.tenant_id == tenant_id)
        .limit(1)
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        return 0
    await db.delete(entry)
    await db.flush()
    return 1


async def list_meta_credentials(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> list[MetaLeadCredential]:
    stmt = (
        select(MetaLeadCredential)
        .where(MetaLeadCredential.tenant_id == tenant_id)
        .order_by(MetaLeadCredential.created_at.desc())
    )
    rows = await db.execute(stmt)
    return list(rows.scalars())


async def list_all_meta_credentials(db: AsyncSession) -> list[MetaLeadCredential]:
    rows = await db.execute(select(MetaLeadCredential))
    return list(rows.scalars())


async def get_meta_credential(
    db: AsyncSession,
    *,
    tenant_id: str,
    credential_id: str,
) -> Optional[MetaLeadCredential]:
    stmt = select(MetaLeadCredential).where(
        MetaLeadCredential.id == credential_id,
        MetaLeadCredential.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_meta_credential(
    db: AsyncSession,
    *,
    tenant_id: str,
    label: str,
    status: str,
    encrypted_secret: Optional[str],
    encrypted_access_token: Optional[str],
    encrypted_ad_account_id: Optional[str],
    encrypted_page_id: Optional[str],
) -> MetaLeadCredential:
    entry = MetaLeadCredential(
        tenant_id=tenant_id,
        label=label,
        status=status,
        encrypted_secret=encrypted_secret,
        encrypted_access_token=encrypted_access_token,
        encrypted_ad_account_id=encrypted_ad_account_id,
        encrypted_page_id=encrypted_page_id,
    )
    db.add(entry)
    await db.flush()
    return entry


async def update_meta_credential(
    db: AsyncSession,
    entry: MetaLeadCredential,
    *,
    label: Optional[str] = None,
    status: Optional[str] = None,
    encrypted_secret: Optional[str] = None,
    encrypted_access_token: Optional[str] = None,
    encrypted_ad_account_id: Optional[str] = None,
    encrypted_page_id: Optional[str] = None,
    last_verified_at: Optional[datetime] = None,
    last_rotation_at: Optional[datetime] = None,
) -> MetaLeadCredential:
    if label is not None:
        entry.label = label
    if status is not None:
        entry.status = status
    if encrypted_secret is not None:
        entry.encrypted_secret = encrypted_secret
    if encrypted_access_token is not None:
        entry.encrypted_access_token = encrypted_access_token
    if encrypted_ad_account_id is not None:
        entry.encrypted_ad_account_id = encrypted_ad_account_id
    if encrypted_page_id is not None:
        entry.encrypted_page_id = encrypted_page_id
    if last_verified_at is not None:
        entry.last_verified_at = last_verified_at
    if last_rotation_at is not None:
        entry.last_rotation_at = last_rotation_at
    await db.flush()
    return entry


async def delete_meta_credential(
    db: AsyncSession,
    entry: MetaLeadCredential,
) -> None:
    await db.delete(entry)
    await db.flush()


async def get_meta_settings(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> Optional[MetaLeadSettings]:
    stmt = select(MetaLeadSettings).where(MetaLeadSettings.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_meta_settings(
    db: AsyncSession,
    *,
    tenant_id: str,
    default_company_id: Optional[str] = None,
    fallback_recruiter_id: Optional[str] = None,
    auto_create_enabled: bool = True,
    reroute_after_hours: Optional[int] = None,
    mask_pii_in_logs: bool = True,
    pull_field_data_from_graph: bool = True,
    field_mapping: Optional[Any] = None,
    webhook_url: Optional[str] = None,
    last_webhook_check_at: Optional[datetime] = None,
    last_signature_status: Optional[str] = None,
    webhook_verify_token: Optional[str] = None,
) -> MetaLeadSettings:
    entry = MetaLeadSettings(
        tenant_id=tenant_id,
        default_company_id=default_company_id,
        fallback_recruiter_id=fallback_recruiter_id,
        auto_create_enabled=auto_create_enabled,
        reroute_after_hours=reroute_after_hours,
        mask_pii_in_logs=mask_pii_in_logs,
        pull_field_data_from_graph=pull_field_data_from_graph,
        field_mapping=field_mapping or [],
        webhook_url=webhook_url,
        last_webhook_check_at=last_webhook_check_at,
        last_signature_status=last_signature_status,
        webhook_verify_token=webhook_verify_token,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_meta_settings_by_verify_token(
    db: AsyncSession,
    *,
    verify_token: str,
) -> Optional[MetaLeadSettings]:
    from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID

    legacy = str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
    # Shared Meta callback URL often reuses one verify_token; deprioritize bootstrap superadmin if duplicated.
    legacy_last = case((MetaLeadSettings.tenant_id == legacy, 1), else_=0)
    stmt = (
        select(MetaLeadSettings)
        .where(MetaLeadSettings.webhook_verify_token == verify_token)
        .order_by(legacy_last, MetaLeadSettings.tenant_id)
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_meta_settings_by_generic_inbound_webhook_secret(
    db: AsyncSession,
    *,
    secret: str,
) -> Optional[MetaLeadSettings]:
    s = (secret or "").strip()
    if not s:
        return None
    stmt = (
        select(MetaLeadSettings)
        .where(MetaLeadSettings.generic_inbound_webhook_secret == s)
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_meta_settings(
    db: AsyncSession,
    entry: MetaLeadSettings,
    **updates: Any,
) -> MetaLeadSettings:
    for key, value in updates.items():
        # FastAPI/Pydantic может передавать UUID как тип данных, но в БД
        # поля settings сейчас хранятся строками (VARCHAR(36)).
        # Поэтому приводим к строке, чтобы asyncpg не падал с DataError.
        if value is not None and isinstance(value, uuid.UUID):
            value = str(value)
        if hasattr(entry, key) and value is not None:
            setattr(entry, key, value)
        elif hasattr(entry, key) and value is None:
            setattr(entry, key, None)
    await db.flush()
    return entry


async def touch_signature_status(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: str,
    checked_at: datetime,
) -> None:
    entry = await get_meta_settings(db, tenant_id=tenant_id)
    if not entry:
        entry = await create_meta_settings(
            db,
            tenant_id=tenant_id,
            auto_create_enabled=True,
            mask_pii_in_logs=True,
        )
    entry.last_signature_status = status
    entry.last_webhook_check_at = checked_at
    await db.flush()


async def delete_expired_meta_oauth_pending(db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(delete(MetaOAuthPending).where(MetaOAuthPending.expires_at < now))
    await db.flush()


async def create_meta_oauth_pending(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_sub: str,
    encrypted_payload: str,
    expires_at: datetime,
) -> MetaOAuthPending:
    entry = MetaOAuthPending(
        tenant_id=tenant_id,
        user_sub=user_sub,
        encrypted_payload=encrypted_payload,
        expires_at=expires_at,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_meta_oauth_pending(
    db: AsyncSession,
    *,
    pending_id: str,
    tenant_id: str,
) -> Optional[MetaOAuthPending]:
    stmt = select(MetaOAuthPending).where(
        MetaOAuthPending.id == pending_id,
        MetaOAuthPending.tenant_id == tenant_id,
    )
    row = await db.execute(stmt)
    return row.scalar_one_or_none()


async def delete_meta_oauth_pending(db: AsyncSession, entry: MetaOAuthPending) -> None:
    await db.delete(entry)
    await db.flush()


def _normalize_form_page_id(page_id: Optional[str]) -> str:
    return str(page_id or "").strip()


def _normalize_form_source(source: Optional[str]) -> str:
    s = (source or "meta").strip().lower()
    return s or "meta"


async def get_meta_form_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    page_id: Optional[str] = None,
    source: str = "meta",
) -> Optional[MetaLeadFormMapping]:
    fid = str(form_id or "").strip()
    if not fid:
        return None
    pid = _normalize_form_page_id(page_id)
    src = _normalize_form_source(source)
    stmt = select(MetaLeadFormMapping).where(
        MetaLeadFormMapping.tenant_id == tenant_id,
        MetaLeadFormMapping.source == src,
        MetaLeadFormMapping.form_id == fid,
        MetaLeadFormMapping.page_id == pid,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def upsert_meta_form_mapping(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    page_id: Optional[str] = None,
    source: str = "meta",
    mapping_rules: Optional[Any] = None,
    form_name: Optional[str] = None,
    last_sample_lead_id: Optional[str] = None,
    updated_by: Optional[str] = None,
) -> MetaLeadFormMapping:
    fid = str(form_id or "").strip()
    if not fid:
        raise ValueError("form_id is required")
    pid = _normalize_form_page_id(page_id)
    src = _normalize_form_source(source)
    existing = await get_meta_form_mapping(
        db, tenant_id=tenant_id, form_id=fid, page_id=pid, source=src
    )
    rules = mapping_rules if isinstance(mapping_rules, list) else []
    if existing:
        existing.mapping_rules = rules
        if form_name is not None:
            existing.form_name = form_name.strip() or None
        if last_sample_lead_id is not None:
            existing.last_sample_lead_id = last_sample_lead_id.strip() or None
        if updated_by is not None:
            existing.updated_by = updated_by.strip() or None
        await db.flush()
        return existing
    entry = MetaLeadFormMapping(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        source=src,
        page_id=pid,
        form_id=fid,
        form_name=form_name.strip() if form_name else None,
        mapping_rules=rules,
        last_sample_lead_id=last_sample_lead_id.strip() if last_sample_lead_id else None,
        updated_by=updated_by.strip() if updated_by else None,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_meta_form_mapping_rows(
    db: AsyncSession,
    *,
    tenant_id: str,
    source: Optional[str] = None,
) -> list[MetaLeadFormMapping]:
    src = _normalize_form_source(source) if source is not None else None
    stmt = select(MetaLeadFormMapping).where(MetaLeadFormMapping.tenant_id == tenant_id)
    if src is not None:
        stmt = stmt.where(MetaLeadFormMapping.source == src)
    stmt = stmt.order_by(MetaLeadFormMapping.updated_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def list_discovered_meta_forms_from_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    source: str = "meta",
    limit: int = 50,
) -> list[dict[str, Optional[str]]]:
    """Distinct form_id / page_id pairs seen on recent leads (normalized JSON)."""
    src = _normalize_form_source(source)
    lim = min(max(1, limit), 200)
    stmt = (
        select(Lead.normalized, Lead.payload)
        .where(Lead.tenant_id == tenant_id, Lead.source == src)
        .order_by(Lead.created_at.desc())
        .limit(lim * 4)
    )
    rows = (await db.execute(stmt)).all()
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Optional[str]]] = []
    for normalized, payload in rows:
        form_id: Optional[str] = None
        page_id: Optional[str] = None
        if isinstance(normalized, dict):
            raw_fid = normalized.get("form_id")
            if raw_fid is not None and str(raw_fid).strip():
                form_id = str(raw_fid).strip()
        if isinstance(payload, dict):
            from backend.app.modules.leads import normalizer

            ctx = normalizer.extract_meta_lead_form_context(payload, source=src)
            form_id = form_id or ctx.get("form_id")
            page_id = ctx.get("page_id")
        if not form_id:
            continue
        pid = _normalize_form_page_id(page_id)
        key = (form_id, pid)
        if key in seen:
            continue
        seen.add(key)
        out.append({"form_id": form_id, "page_id": pid or None, "source": src})
        if len(out) >= lim:
            break
    return out


async def get_meta_form_route(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    page_id: Optional[str] = None,
    source: str = "meta",
) -> Optional[MetaFormRoute]:
    fid = str(form_id or "").strip()
    if not fid:
        return None
    pid = _normalize_form_page_id(page_id)
    src = _normalize_form_source(source)
    stmt = select(MetaFormRoute).where(
        MetaFormRoute.tenant_id == tenant_id,
        MetaFormRoute.source == src,
        MetaFormRoute.form_id == fid,
        MetaFormRoute.page_id == pid,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def upsert_meta_form_route(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    own_company_id: str,
    lead_target_type: str,
    page_id: Optional[str] = None,
    source: str = "meta",
    pipeline_preset: Optional[str] = None,
    default_assignee_id: Optional[str] = None,
    is_active: bool = True,
    updated_by: Optional[str] = None,
) -> MetaFormRoute:
    from backend.app.modules.leads.intake_route import normalize_lead_target_type

    fid = str(form_id or "").strip()
    if not fid:
        raise ValueError("form_id is required")
    oc = str(own_company_id or "").strip()
    if not oc:
        raise ValueError("own_company_id is required")
    pid = _normalize_form_page_id(page_id)
    src = _normalize_form_source(source)
    ltt = normalize_lead_target_type(lead_target_type)
    existing = await get_meta_form_route(
        db, tenant_id=tenant_id, form_id=fid, page_id=pid, source=src
    )
    if existing:
        existing.own_company_id = oc
        existing.lead_target_type = ltt
        existing.pipeline_preset = str(pipeline_preset or "").strip() or None
        existing.default_assignee_id = str(default_assignee_id or "").strip() or None
        existing.is_active = bool(is_active)
        if updated_by is not None:
            existing.updated_by = updated_by.strip() or None
        await db.flush()
        from backend.app.modules.intake_routing.meta_bridge import sync_meta_form_route_to_intake_foundation

        await sync_meta_form_route_to_intake_foundation(db, route=existing)
        return existing
    entry = MetaFormRoute(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        source=src,
        page_id=pid,
        form_id=fid,
        own_company_id=oc,
        lead_target_type=ltt,
        pipeline_preset=str(pipeline_preset or "").strip() or None,
        default_assignee_id=str(default_assignee_id or "").strip() or None,
        is_active=bool(is_active),
        updated_by=updated_by.strip() if updated_by else None,
    )
    db.add(entry)
    await db.flush()
    from backend.app.modules.intake_routing.meta_bridge import sync_meta_form_route_to_intake_foundation

    await sync_meta_form_route_to_intake_foundation(db, route=entry)
    return entry


async def list_meta_form_routes(
    db: AsyncSession,
    *,
    tenant_id: str,
    source: str = "meta",
) -> list[MetaFormRoute]:
    src = _normalize_form_source(source)
    stmt = (
        select(MetaFormRoute)
        .where(MetaFormRoute.tenant_id == tenant_id, MetaFormRoute.source == src)
        .order_by(MetaFormRoute.updated_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())
