"""TikTok ad-account connection: verify Instant Forms and expose them as intake sources."""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.ensure_tiktok_intake_source import ensure_tiktok_form_intake_source
from backend.app.core.crypto import decrypt_secret, encrypt_secret
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead import TikTokLeadConnection
from backend.app.modules.leads.tenant_business_type import load_tenant_business_type

logger = logging.getLogger(__name__)

TIKTOK_API = "https://business-api.tiktok.com/open_api/v1.3"


class TikTokConnectionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class TikTokForm:
    page_id: str
    name: str


def parse_instant_forms(payload: dict[str, Any]) -> list[TikTokForm]:
    """Read Instant Forms from a TikTok ``/page/get/`` body. Raises on a TikTok error code."""
    if not isinstance(payload, dict):
        raise TikTokConnectionError("TikTok returned an unexpected response")
    code = payload.get("code")
    if code not in (0, "0", None):
        raise TikTokConnectionError(str(payload.get("message") or "TikTok rejected the request"))
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    raw = data.get("list") or data.get("pages") or data.get("page_list") or []
    forms: list[TikTokForm] = []
    if not isinstance(raw, list):
        return forms
    for item in raw:
        if not isinstance(item, dict):
            continue
        page_id = str(item.get("page_id") or item.get("id") or "").strip()
        if not page_id:
            continue
        name = str(item.get("title") or item.get("page_name") or item.get("name") or "").strip()
        forms.append(TikTokForm(page_id=page_id, name=name or f"TikTok form {page_id}"))
    return forms


def csv_text_to_tiktok_bodies(csv_text: str, *, page_id: str) -> list[dict[str, Any]]:
    """Turn a TikTok lead-download CSV into webhook bodies the lead pipeline already accepts."""
    sample = (csv_text or "").lstrip("\ufeff")
    if not sample.strip() or sample.lstrip().startswith("{"):
        return []
    reader = csv.DictReader(io.StringIO(sample))
    bodies: list[dict[str, Any]] = []
    reserved = {
        "lead_id",
        "lead id",
        "id",
        "created_time",
        "create_time",
        "ad_id",
        "ad_name",
        "adgroup_id",
        "adgroup_name",
        "campaign_id",
        "campaign_name",
        "form_id",
        "form_name",
        "page_id",
    }
    for row in reader:
        if not isinstance(row, dict):
            continue
        normalized = {
            str(key or "").strip().lower(): str(value or "").strip()
            for key, value in row.items()
            if key
        }
        lead_id = normalized.get("lead_id") or normalized.get("lead id") or normalized.get("id")
        if not lead_id:
            continue
        form_id = normalized.get("form_id") or normalized.get("page_id") or page_id
        changes = [
            {"field": key, "value": value}
            for key, value in normalized.items()
            if key not in reserved and value
        ]
        bodies.append(
            {
                "object": 1,
                "entry": [
                    {
                        "id": lead_id,
                        "page_id": form_id,
                        "page_name": normalized.get("form_name") or "",
                        "ad_id": normalized.get("ad_id") or "",
                        "advertiser_id": "",
                        "changes": changes,
                    }
                ],
            }
        )
    return bodies


async def _tiktok_get_forms(access_token: str, advertiser_id: str) -> list[TikTokForm]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{TIKTOK_API}/page/get/",
            headers={"Access-Token": access_token},
            params={
                "advertiser_id": advertiser_id,
                "business_type": "LEAD_GEN",
                "page": "1",
                "page_size": "100",
            },
        )
    try:
        payload = response.json()
    except Exception as exc:
        raise TikTokConnectionError("TikTok returned an unexpected response") from exc
    if response.status_code >= 400 and not isinstance(payload, dict):
        raise TikTokConnectionError("TikTok rejected the request")
    return parse_instant_forms(payload if isinstance(payload, dict) else {})


def _route_intent(business_type: str) -> str:
    if str(business_type or "").strip().lower() == "services":
        return "sales_inquiry"
    return "candidate_application"


async def _load_connection(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
) -> Optional[TikTokLeadConnection]:
    return (
        await db.execute(
            select(TikTokLeadConnection).where(
                TikTokLeadConnection.tenant_id == tenant_id,
                TikTokLeadConnection.own_company_id == own_company_id,
            )
        )
    ).scalar_one_or_none()


async def _form_rows(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
) -> list[dict[str, str]]:
    rows = (
        await db.execute(
            select(IntakeSourceProfile).where(
                IntakeSourceProfile.tenant_id == tenant_id,
                IntakeSourceProfile.own_company_id == own_company_id,
                IntakeSourceProfile.provider == "tiktok",
                IntakeSourceProfile.is_active.is_(True),
            ).order_by(IntakeSourceProfile.name.asc())
        )
    ).scalars().all()
    out: list[dict[str, str]] = []
    for row in rows:
        code = str(row.code or "")
        page_id = code[len("tiktok-form-") :] if code.startswith("tiktok-form-") else ""
        out.append(
            {
                "page_id": page_id,
                "name": str(row.name or page_id),
                "intake_source_profile_id": str(row.id),
            }
        )
    return out


async def connection_status(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
) -> dict[str, Any]:
    row = await _load_connection(db, tenant_id=tenant_id, own_company_id=own_company_id)
    forms = await _form_rows(db, tenant_id=tenant_id, own_company_id=own_company_id)
    if row is None or str(row.status or "") != "connected":
        return {
            "connected": False,
            "status": "not_connected",
            "advertiser_id": None,
            "last_verified_at": None,
            "last_error": None,
            "forms": [],
        }
    return {
        "connected": True,
        "status": "connected",
        "advertiser_id": row.advertiser_id,
        "last_verified_at": row.last_verified_at,
        "last_error": row.last_error,
        "forms": forms,
    }


async def connect_tiktok_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    advertiser_id: str,
    access_token: str,
) -> dict[str, Any]:
    advertiser = str(advertiser_id or "").strip()
    token = str(access_token or "").strip()
    if not advertiser or not token:
        raise TikTokConnectionError("Advertiser ID and access token are required")
    forms = await _tiktok_get_forms(token, advertiser)
    business_type = await load_tenant_business_type(db, tenant_id, own_company_id)
    intent = _route_intent(business_type)
    for form in forms:
        await ensure_tiktok_form_intake_source(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            form_id=form.page_id,
            route_intent=intent,
            display_name=form.name,
        )
    now = datetime.now(timezone.utc)
    row = await _load_connection(db, tenant_id=tenant_id, own_company_id=own_company_id)
    if row is None:
        row = TikTokLeadConnection(
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            advertiser_id=advertiser,
            encrypted_access_token=encrypt_secret(token) or "",
            status="connected",
            last_verified_at=now,
            last_error=None,
        )
        db.add(row)
    else:
        row.advertiser_id = advertiser
        row.encrypted_access_token = encrypt_secret(token) or ""
        row.status = "connected"
        row.last_verified_at = now
        row.last_error = None
    await db.flush()
    return await connection_status(db, tenant_id=tenant_id, own_company_id=own_company_id)


async def disconnect_tiktok_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
) -> dict[str, Any]:
    row = await _load_connection(db, tenant_id=tenant_id, own_company_id=own_company_id)
    if row is not None:
        await db.delete(row)
        await db.flush()
    return await connection_status(db, tenant_id=tenant_id, own_company_id=own_company_id)


async def _download_lead_csv(
    client: httpx.AsyncClient,
    *,
    token: str,
    advertiser_id: str,
    page_id: str,
) -> str:
    headers = {"Access-Token": token, "x-lead-region": "eu"}
    created = await client.post(
        f"{TIKTOK_API}/page/lead/task/",
        headers=headers,
        params={"advertiser_id": advertiser_id, "page_id": page_id},
    )
    try:
        payload = created.json()
    except Exception as exc:
        raise TikTokConnectionError("TikTok returned an unexpected response") from exc
    if not isinstance(payload, dict) or payload.get("code") not in (0, "0"):
        raise TikTokConnectionError(str((payload or {}).get("message") if isinstance(payload, dict) else "TikTok rejected the lead download"))
    task_id = str((payload.get("data") or {}).get("task_id") or "").strip()
    if not task_id:
        raise TikTokConnectionError("TikTok did not return a lead download task")
    for _ in range(5):
        downloaded = await client.get(
            f"{TIKTOK_API}/page/lead/task/download/",
            headers=headers,
            params={"advertiser_id": advertiser_id, "task_id": task_id},
        )
        content_type = downloaded.headers.get("content-type", "")
        if "json" in content_type:
            try:
                body = downloaded.json()
            except Exception:
                body = {}
            status = str((body.get("data") or {}).get("status") or "") if isinstance(body, dict) else ""
            if isinstance(body, dict) and body.get("code") not in (0, "0", None) and status != "SUCCEED":
                message = str(body.get("message") or "")
                if "region" in message.lower():
                    break
            continue
        return downloaded.text
    return ""


async def import_tiktok_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
) -> dict[str, Any]:
    """Pull current Instant Form leads into the same pipeline as a TikTok webhook."""
    from backend.app.modules.leads.service import process_generic_inbound_webhook_lead

    row = await _load_connection(db, tenant_id=tenant_id, own_company_id=own_company_id)
    if row is None or str(row.status or "") != "connected":
        raise TikTokConnectionError("TikTok is not connected")
    token = decrypt_secret(row.encrypted_access_token) or ""
    if not token:
        raise TikTokConnectionError("TikTok access token is missing. Connect the account again.")
    forms = await _form_rows(db, tenant_id=tenant_id, own_company_id=own_company_id)
    imported = 0
    async with httpx.AsyncClient(timeout=25.0) as client:
        for form in forms:
            page_id = form["page_id"]
            if not page_id:
                continue
            csv_text = await _download_lead_csv(
                client,
                token=token,
                advertiser_id=row.advertiser_id,
                page_id=page_id,
            )
            for body in csv_text_to_tiktok_bodies(csv_text, page_id=page_id):
                await process_generic_inbound_webhook_lead(
                    db,
                    tenant_id=tenant_id,
                    own_company_id=own_company_id,
                    body=body,
                )
                imported += 1
    row.last_verified_at = datetime.now(timezone.utc)
    row.last_error = None
    await db.flush()
    status = await connection_status(db, tenant_id=tenant_id, own_company_id=own_company_id)
    status["imported"] = imported
    return status
