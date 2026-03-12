from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.crypto import decrypt_secret, encrypt_secret, generate_secret
from backend.app.core.settings import settings
from backend.app.modules.leads import crud, service
from backend.app.modules.leads.schemas import (
    LeadOut,
    MetaAdsMapCreate,
    MetaAdsMapEntry,
    MetaAdsMapUpdate,
    MetaCredentialCreate,
    MetaCredentialOut,
    MetaCredentialRotateResponse,
    MetaCredentialUpdate,
    MetaLeadResponse,
    MetaLeadRerouteRequest,
    MetaLeadRetryItem,
    MetaLeadRetryRequest,
    MetaLeadRetryResponse,
    MetaLeadSettingsOut,
    MetaLeadSettingsUpdate,
    UnmappedAdGroup,
    UnmappedLeadsResponse,
)


def _to_uuid(value: Optional[str]) -> Optional[UUID]:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _mask_tail(value: Optional[str], keep: int = 4) -> Optional[str]:
    if not value:
        return None
    text = value.strip()
    if len(text) <= keep:
        return text
    return f"{'*' * max(0, len(text) - keep)}{text[-keep:]}"


async def _ensure_settings_schema(db: AsyncSession) -> None:
    try:
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS webhook_url VARCHAR(512)"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS last_webhook_check_at TIMESTAMPTZ"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS last_signature_status VARCHAR(32)"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS webhook_verify_token VARCHAR(255)"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS pull_field_data_from_graph BOOLEAN DEFAULT true"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS field_mapping JSONB DEFAULT '[]'::jsonb"
            )
        )
        await db.flush()
    except Exception:  # pragma: no cover - best effort for legacy DBs
        try:
            await db.execute(
                text(
                    "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS webhook_url TEXT"
                )
            )
            await db.execute(
                text(
                    "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS last_webhook_check_at TEXT"
                )
            )
            await db.execute(
                text(
                    "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS last_signature_status TEXT"
                )
            )
            await db.execute(
                text(
                    "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS webhook_verify_token TEXT"
                )
            )
            await db.execute(
                text(
                    "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS field_mapping JSON DEFAULT '[]'"
                )
            )
            await db.flush()
        except Exception:
            pass


async def _ensure_settings(db: AsyncSession, tenant_id: str) -> crud.MetaLeadSettings:
    await _ensure_settings_schema(db)
    entry = await crud.get_meta_settings(db, tenant_id=tenant_id)
    if entry:
        return entry
    return await crud.create_meta_settings(
        db,
        tenant_id=tenant_id,
        auto_create_enabled=True,
        mask_pii_in_logs=True,
        pull_field_data_from_graph=settings.pull_field_data_from_graph,
    )


def _settings_to_schema(entry: crud.MetaLeadSettings) -> MetaLeadSettingsOut:
    raw_mapping = getattr(entry, "field_mapping", None) or []
    if isinstance(raw_mapping, dict):
        if isinstance(raw_mapping.get("rules"), list):
            normalized_mapping = raw_mapping.get("rules") or []
        else:
            normalized_mapping = []
    elif isinstance(raw_mapping, list):
        normalized_mapping = raw_mapping
    else:
        normalized_mapping = []

    return MetaLeadSettingsOut(
        tenant_id=_to_uuid(entry.tenant_id) or UUID(entry.tenant_id),
        default_company_id=_to_uuid(entry.default_company_id),
        fallback_recruiter_id=_to_uuid(entry.fallback_recruiter_id),
        auto_create_enabled=bool(entry.auto_create_enabled),
        reroute_after_hours=entry.reroute_after_hours,
        mask_pii_in_logs=bool(entry.mask_pii_in_logs),
        pull_field_data_from_graph=bool(getattr(entry, "pull_field_data_from_graph", True)),
        field_mapping=normalized_mapping,
        webhook_url=entry.webhook_url,
        last_webhook_check_at=entry.last_webhook_check_at,
        last_signature_status=entry.last_signature_status,
        webhook_verify_token=entry.webhook_verify_token,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


async def get_settings(db: AsyncSession, tenant_id: str) -> MetaLeadSettingsOut:
    entry = await _ensure_settings(db, tenant_id)
    return _settings_to_schema(entry)


async def update_settings(
    db: AsyncSession,
    tenant_id: str,
    payload: MetaLeadSettingsUpdate,
) -> MetaLeadSettingsOut:
    entry = await _ensure_settings(db, tenant_id)
    if hasattr(payload, "model_dump"):
        updates = payload.model_dump(exclude_unset=True)
    else:  # pragma: no cover - Pydantic v1 fallback
        updates = payload.dict(exclude_unset=True)
    if "webhook_verify_token" in updates:
        token = updates["webhook_verify_token"]
        updates["webhook_verify_token"] = token.strip() or None if token is not None else None
    if "field_mapping" in updates:
        mapping_rules = updates["field_mapping"]
        if mapping_rules is None:
            updates["field_mapping"] = []
        elif isinstance(mapping_rules, list):
            updates["field_mapping"] = mapping_rules
        else:
            updates["field_mapping"] = []
    await crud.update_meta_settings(db, entry, **updates)
    return _settings_to_schema(entry)


def _credential_to_schema(entry) -> MetaCredentialOut:
    decrypted_ad_account = decrypt_secret(entry.encrypted_ad_account_id)
    decrypted_page_id = decrypt_secret(entry.encrypted_page_id)
    return MetaCredentialOut(
        id=UUID(entry.id),
        label=entry.label,
        status=entry.status,  # type: ignore[arg-type]
        has_secret=bool(entry.encrypted_secret),
        ad_account_last4=_mask_tail(decrypted_ad_account, keep=4),
        page_id_masked=_mask_tail(decrypted_page_id, keep=4),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        last_verified_at=entry.last_verified_at,
        last_rotation_at=entry.last_rotation_at,
    )


async def list_credentials(db: AsyncSession, tenant_id: str) -> List[MetaCredentialOut]:
    rows = await crud.list_meta_credentials(db, tenant_id=tenant_id)
    return [_credential_to_schema(row) for row in rows]


async def create_credential(
    db: AsyncSession,
    tenant_id: str,
    payload: MetaCredentialCreate,
) -> MetaCredentialOut:
    entry = await crud.create_meta_credential(
        db,
        tenant_id=tenant_id,
        label=payload.label,
        status=payload.status,
        encrypted_secret=encrypt_secret(payload.secret),
        encrypted_access_token=encrypt_secret(payload.access_token),
        encrypted_ad_account_id=encrypt_secret(payload.ad_account_id),
        encrypted_page_id=encrypt_secret(payload.page_id),
    )
    return _credential_to_schema(entry)


async def update_credential(
    db: AsyncSession,
    tenant_id: str,
    credential_id: str,
    payload: MetaCredentialUpdate,
) -> MetaCredentialOut:
    entry = await crud.get_meta_credential(db, tenant_id=tenant_id, credential_id=credential_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    if hasattr(payload, "model_dump"):
        updates = payload.model_dump(exclude_unset=True)
    else:  # pragma: no cover
        updates = payload.dict(exclude_unset=True)
    secret_update = updates.pop("secret", None)
    access_update = updates.pop("access_token", None)
    ad_account_update = updates.pop("ad_account_id", None)
    page_id_update = updates.pop("page_id", None)
    now = datetime.now(timezone.utc)
    kwargs = {
        "label": updates.get("label"),
        "status": updates.get("status"),
        "encrypted_secret": encrypt_secret(secret_update) if secret_update is not None else None,
        "encrypted_access_token": encrypt_secret(access_update) if access_update is not None else None,
        "encrypted_ad_account_id": encrypt_secret(ad_account_update) if ad_account_update is not None else None,
        "encrypted_page_id": encrypt_secret(page_id_update) if page_id_update is not None else None,
    }
    if secret_update is not None:
        kwargs["last_rotation_at"] = now
    await crud.update_meta_credential(db, entry, **kwargs)
    return _credential_to_schema(entry)


async def delete_credential(
    db: AsyncSession,
    tenant_id: str,
    credential_id: str,
) -> None:
    entry = await crud.get_meta_credential(db, tenant_id=tenant_id, credential_id=credential_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    await crud.delete_meta_credential(db, entry)


async def rotate_credential(
    db: AsyncSession,
    tenant_id: str,
    credential_id: str,
) -> MetaCredentialRotateResponse:
    entry = await crud.get_meta_credential(db, tenant_id=tenant_id, credential_id=credential_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    new_secret = generate_secret()
    await crud.update_meta_credential(
        db,
        entry,
        encrypted_secret=encrypt_secret(new_secret),
        last_rotation_at=datetime.now(timezone.utc),
    )
    return MetaCredentialRotateResponse(secret=new_secret)


async def get_active_secret_candidates(
    db: AsyncSession,
    tenant_id: str,
) -> List[Tuple[Optional[str], Optional[object], str]]:
    """
    Returns list of tuples (credential_id, credential_obj, secret) for signature verification.
    credential_id is None for legacy env secret fallback.
    """
    entries = await crud.list_meta_credentials(db, tenant_id=tenant_id)
    secrets: List[Tuple[Optional[str], Optional[object], str]] = []
    for entry in entries:
        if entry.status not in {"active", "rotation_pending"}:
            continue
        secret = decrypt_secret(entry.encrypted_secret)
        if secret:
            secrets.append((entry.id, entry, secret))
    if settings.meta_webhook_secret:
        secrets.append((None, None, settings.meta_webhook_secret))
    return secrets


async def mark_credential_verified(
    db: AsyncSession,
    credential,
) -> None:
    if credential is None:
        return
    await crud.update_meta_credential(
        db,
        credential,
        last_verified_at=datetime.now(timezone.utc),
    )


async def mark_signature_status(
    db: AsyncSession,
    tenant_id: str,
    status_value: str,
) -> None:
    await crud.touch_signature_status(
        db,
        tenant_id=tenant_id,
        status=status_value,
        checked_at=datetime.now(timezone.utc),
    )


async def resolve_tenant_by_verify_token(
    db: AsyncSession,
    verify_token: Optional[str],
) -> Optional[Tuple[str, crud.MetaLeadSettings]]:
    if not verify_token:
        return None
    token = verify_token.strip()
    if not token:
        return None
    await _ensure_settings_schema(db)
    entry = await crud.get_meta_settings_by_verify_token(db, verify_token=token)
    if entry:
        return entry.tenant_id, entry
    return None


def extract_page_ids(payload: Dict[str, Any]) -> List[str]:
    entries = payload.get("entry") or []
    result: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        page_id = entry.get("id") or entry.get("page_id")
        if page_id:
            result.append(str(page_id).strip())
        changes = entry.get("changes") or []
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value") or {}
            if isinstance(value, dict):
                inner_page = value.get("page_id") or value.get("page")
                if inner_page:
                    result.append(str(inner_page).strip())
    return [pid for pid in result if pid]


async def resolve_tenant_by_page_ids(
    db: AsyncSession,
    page_ids: Iterable[str],
) -> Optional[Tuple[str, Optional[crud.MetaLeadCredential]]]:
    normalized = {str(pid).strip() for pid in page_ids if str(pid).strip()}
    if not normalized:
        return None
    rows = await crud.list_all_meta_credentials(db)
    for entry in rows:
        if entry.status not in {"active", "rotation_pending"}:
            continue
        page_id = decrypt_secret(entry.encrypted_page_id)
        if page_id and page_id.strip() in normalized:
            return entry.tenant_id, entry
    return None


async def get_page_access_token(
    db: AsyncSession,
    tenant_id: str,
    page_id: str,
) -> Optional[str]:
    entries = await crud.list_meta_credentials(db, tenant_id=tenant_id)
    for entry in entries:
        decrypted_page = decrypt_secret(entry.encrypted_page_id)
        if decrypted_page and decrypted_page.strip() == page_id:
            token = decrypt_secret(entry.encrypted_access_token)
            if token:
                return token
    return None


async def list_mapping(
    db: AsyncSession,
    tenant_id: str,
    search: Optional[str],
    limit: int,
) -> List[MetaAdsMapEntry]:
    rows = await crud.list_meta_ads_map(db, tenant_id=tenant_id, search=search, limit=limit)
    return [
        MetaAdsMapEntry(
            ad_id=str(row.ad_id),
            vacancy_id=UUID(str(row.vacancy_id)),
            note=row.note,
            created_at=row.created_at,
        )
        for row in rows
    ]


async def upsert_mapping(
    db: AsyncSession,
    tenant_id: str,
    payload: MetaAdsMapCreate | MetaAdsMapUpdate,
    *,
    ad_id: Optional[int] = None,
) -> MetaAdsMapEntry:
    if hasattr(payload, "model_dump"):
        data = payload.model_dump(exclude_unset=True)
    else:  # pragma: no cover
        data = payload.dict(exclude_unset=True)
    target_ad = ad_id or int(data["ad_id"])
    existing = await crud.get_meta_ads_entry(db, tenant_id=tenant_id, ad_id=target_ad)
    vacancy_value = data.get("vacancy_id") or (existing.vacancy_id if existing else None)
    if not vacancy_value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="vacancy_id is required")
    note = data.get("note") if "note" in data else (existing.note if existing else None)
    entry = await crud.upsert_meta_ads_map(
        db,
        tenant_id=tenant_id,
        ad_id=target_ad,
        vacancy_id=str(vacancy_value),
        note=note,
    )
    return MetaAdsMapEntry(
        ad_id=str(entry.ad_id),
        vacancy_id=UUID(str(entry.vacancy_id)),
        note=entry.note,
        created_at=entry.created_at,
    )


async def list_unmapped_leads(
    db: AsyncSession,
    tenant_id: str,
    status: str = "needs_routing",
    limit_per_ad: int = 10,
) -> UnmappedLeadsResponse:
    groups_raw = await crud.list_leads_with_unmapped_ad_ids(
        db,
        tenant_id=tenant_id,
        status=status,
        limit_per_ad=limit_per_ad,
    )
    groups: List[UnmappedAdGroup] = []
    for ad_id, leads_list in groups_raw:
        items: List[LeadOut] = []
        for lead in leads_list:
            items.append(
                LeadOut(
                    id=UUID(lead.id),
                    tenant_id=UUID(lead.tenant_id),
                    company_id=UUID(lead.company_id),
                    company_name=None,
                    vacancy_id=_to_uuid(lead.vacancy_id),
                    vacancy_title=None,
                    source=lead.source,
                    ad_id=lead.ad_id,
                    status=lead.status,  # type: ignore[arg-type]
                    candidate_id=_to_uuid(lead.candidate_id),
                    candidate_name=None,
                    recruiter_id=None,
                    error=lead.error,
                    payload=lead.payload or {},
                    normalized=lead.normalized,
                    created_at=lead.created_at,
                    last_routed_at=lead.last_routed_at,
                )
            )
        groups.append(
            UnmappedAdGroup(ad_id=str(ad_id), count=len(leads_list), leads=items)
        )
    return UnmappedLeadsResponse(groups=groups)


async def delete_mapping(db: AsyncSession, tenant_id: str, ad_id: int) -> None:
    removed = await crud.delete_meta_ads_map(db, tenant_id=tenant_id, ad_id=ad_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")


async def reroute_lead(
    db: AsyncSession,
    tenant_id: str,
    lead_id: str,
    payload: MetaLeadRerouteRequest,
) -> MetaLeadResponse:
    result = await service.reroute_lead_manual(
        db,
        tenant_id=tenant_id,
        lead_id=lead_id,
        vacancy_id=str(payload.vacancy_id) if payload.vacancy_id else None,
        company_id=str(payload.company_id) if payload.company_id else None,
        force_process=payload.force_process,
    )
    return result.to_schema()


async def retry_leads(
    db: AsyncSession,
    tenant_id: str,
    payload: MetaLeadRetryRequest,
) -> MetaLeadRetryResponse:
    lead_ids = [str(value) for value in payload.lead_ids] if payload.lead_ids else None
    statuses = [value for value in payload.statuses] if payload.statuses else None

    outcomes = await service.retry_meta_leads(
        db,
        tenant_id=tenant_id,
        lead_ids=lead_ids,
        statuses=statuses,
        limit=payload.limit,
        refresh_graph=payload.refresh_graph,
    )

    items: List[MetaLeadRetryItem] = []
    processed_count = 0
    failed_count = 0
    skipped_count = 0

    for outcome in outcomes:
        try:
            lead_uuid = UUID(outcome.lead_id)
        except ValueError:
            lead_uuid = UUID(int=0)

        candidate_uuid: Optional[UUID] = None
        if outcome.candidate_id:
            try:
                candidate_uuid = UUID(outcome.candidate_id)
            except ValueError:
                candidate_uuid = None

        item = MetaLeadRetryItem(
            lead_id=lead_uuid,
            status_before=outcome.status_before,  # type: ignore[arg-type]
            status_after=outcome.status_after,  # type: ignore[arg-type]
            candidate_id=candidate_uuid,
            error_before=outcome.error_before,
            error_after=outcome.error_after,
            processed=outcome.processed,
            message=outcome.message,
        )
        items.append(item)

        if outcome.processed:
            processed_count += 1
        elif outcome.message and "payload is empty" in outcome.message.lower():
            skipped_count += 1
        else:
            failed_count += 1

    return MetaLeadRetryResponse(
        items=items,
        processed=processed_count,
        failed=failed_count,
        skipped=skipped_count,
    )
