from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Candidate,
    Company,
    Lead,
    MetaAdsMap,
    MetaLeadCredential,
    MetaLeadSettings,
    Vacancy,
)


async def create_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    vacancy_id: Optional[str],
    payload: Dict[str, Any],
    normalized: Optional[Dict[str, Any]],
    source: str = "meta",
    ad_id: Optional[int] = None,
    last_routed_at: Optional[datetime] = None,
    external_id: Optional[str] = None,
) -> Lead:
    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
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
) -> Lead:
    lead.status = status
    lead.candidate_id = candidate_id
    if vacancy_id is not None:
        lead.vacancy_id = vacancy_id
    if normalized is not None:
        lead.normalized = normalized
    lead.error = error
    if last_routed_at is not None:
        lead.last_routed_at = last_routed_at
    await db.flush()
    return lead


async def resolve_vacancy_by_id(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
) -> Optional[Vacancy]:
    stmt = select(Vacancy).where(
        Vacancy.id == vacancy_id,
        Vacancy.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def resolve_vacancy_by_ad(
    db: AsyncSession,
    tenant_id: str,
    ad_id: Optional[int],
) -> Optional[Vacancy]:
    if not ad_id:
        return None
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
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


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
    matchers = []
    if email:
        email_lower = email.lower()
        matchers.append(func.lower(Candidate.email) == email_lower)
    if phone:
        matchers.append(Candidate.phone == phone)

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
    stmt = (
        select(MetaLeadSettings)
        .where(MetaLeadSettings.webhook_verify_token == verify_token)
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
