from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import get_db
from backend.app.modules.leads import admin_service, normalizer, pipeline, service


logger = logging.getLogger("backend.app.modules.leads.webhook")

router = APIRouter()

def _signature_matches(secret: str, body: bytes, signature: str | None) -> bool:
    if not secret:
        return True
    if not signature:
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _extract_verify_token(request: Request) -> Optional[str]:
    params = request.query_params
    for key in ("hub_verify_token", "hub.verify_token", "verify_token", "token"):
        if params.get(key):
            return params[key]
    return request.headers.get("X-Meta-Verify-Token")


def _extract_mode(request: Request) -> str:
    params = request.query_params
    for key in ("mode", "hub.mode", "hub_mode"):
        value = params.get(key)
        if value:
            return value
    return ""


def _extract_challenge(request: Request) -> str:
    params = request.query_params
    for key in ("hub.challenge", "hub_challenge", "challenge"):
        value = params.get(key)
        if value:
            return value
    return ""


async def _apply_tenant_context(db: AsyncSession, tenant_id: str) -> None:
    db.info["tenant_id"] = UUID(tenant_id)
    try:
        await db.execute(text("SELECT set_config('app.tenant_id', :tenant_id, false)"), {"tenant_id": tenant_id})
    except Exception:
        pass


@router.get("/webhook", response_class=PlainTextResponse)
async def verify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    actual_mode = _extract_mode(request).strip()
    challenge = _extract_challenge(request).strip()
    verify_token = _extract_verify_token(request)

    if actual_mode != "subscribe" or not challenge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad verify request")

    tenant_resolution = await admin_service.resolve_tenant_by_verify_token(db, verify_token)
    if tenant_resolution:
        tenant_id, _settings = tenant_resolution
        await admin_service.mark_signature_status(db, tenant_id, "verified")
        await db.commit()
        return PlainTextResponse(challenge)

    logger.warning("Meta webhook verify failed: unknown token %s", verify_token)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bad verify token")


@router.post("/webhook")
async def receive(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    verify_token = _extract_verify_token(request)

    tenant_id: Optional[str] = None
    signature_owner: Optional[object] = None
    parsed_payload: Optional[dict] = None

    try:
        parsed_payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    # Page-bound credentials first: Graph token + app secret live on the credential row's tenant.
    # Shared verify_token across tenants would otherwise pick the wrong tenant (e.g. Focus) and yield GRAPH_NO_TOKEN.
    page_resolution = await admin_service.resolve_tenant_by_page_ids(
        db, admin_service.extract_page_ids(parsed_payload)
    )
    if page_resolution:
        tenant_id, signature_owner = page_resolution
    else:
        token_resolution = await admin_service.resolve_tenant_by_verify_token(db, verify_token)
        if token_resolution:
            tenant_id, _settings = token_resolution
        else:
            tenant_hint = request.headers.get("X-Tenant-Id") or request.query_params.get("tenant_id")
            if tenant_hint:
                tenant_id = tenant_hint.strip()

    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant not resolved")

    await _apply_tenant_context(db, tenant_id)

    header_signature = request.headers.get("X-Hub-Signature-256")
    signatures = await admin_service.get_active_secret_candidates(db, tenant_id)
    signature_status = "not_configured"

    matched_secret = None
    matched_credential = signature_owner

    if signatures:
        if not header_signature:
            await admin_service.mark_signature_status(db, tenant_id, "missing_header")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature header")

        for credential_id, credential_obj, secret in signatures:
            if _signature_matches(secret, raw_body, header_signature):
                matched_secret = secret
                matched_credential = credential_obj
                break

        if not matched_secret:
            await admin_service.mark_signature_status(db, tenant_id, "mismatch")
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature mismatch")

        signature_status = "ok"
        await admin_service.mark_credential_verified(db, matched_credential)
    else:
        signature_status = "not_configured"

    try:
        payload = await pipeline.hydrate_webhook_payload(
            db,
            tenant_id,
            parsed_payload,
            existing_leads=None,
            refresh_graph=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        result = await service.process_meta_lead(
            db=db,
            tenant_id=tenant_id,
            payload=payload,
        )
    except service.LeadProcessingError as exc:
        raise service.lead_processing_error_as_http(exc) from exc

    preview = normalizer.normalize_meta_payload(payload)
    logger.info(
        "[meta] normalized: phone=%s email=%s decided=%s",
        _mask_contact(preview.get("phone")),
        _mask_contact(preview.get("email")),
        result.status,
    )

    await admin_service.mark_signature_status(db, tenant_id, signature_status)
    await db.commit()

    return result.to_schema()


def _mask_contact(value: Optional[str]) -> str:
    if not value:
        return "-"
    if "@" in value:
        local, _, domain = value.partition("@")
        masked_local = local[:2] + "***" if len(local) > 2 else "***"
        return f"{masked_local}@{domain}"
    digits = value.replace(" ", "")
    if len(digits) <= 4:
        return "***"
    return f"{digits[:3]}***{digits[-2:]}"
