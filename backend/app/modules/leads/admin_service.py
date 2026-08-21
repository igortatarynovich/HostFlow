from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.crypto import decrypt_secret, encrypt_secret, generate_secret
from backend.app.core.settings import settings
from backend.app.modules.leads import crud, service
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.app.modules.leads import meta_oauth_service as meta_oauth
from backend.app.services.plan_feature_gates import (
    count_tenant_lead_sources,
    ensure_lead_source_limit,
    ensure_leads_generic_inbound_webhook_allowed,
    ensure_meta_lead_credential_create_allowed,
    ensure_meta_lead_field_mapping_rows_allowed,
    ensure_meta_leads_oauth_allowed,
    lead_meta_credentials_cap,
    lead_meta_field_mapping_rules_cap,
    plan_allows_meta_leads_oauth,
    resolve_tenant_plan_code,
)
from backend.app.modules.leads.schemas import (
    LeadOut,
    lead_vacancy_routing_aux,
    MetaAdsMapCreate,
    MetaAdsMapEntry,
    MetaAdsMapUpdate,
    MetaCredentialCreate,
    MetaCredentialOut,
    MetaCredentialRotateResponse,
    MetaCredentialUpdate,
    GenericInboundWebhookRotateResponse,
    MetaGraphFieldDataPreviewField,
    MetaGraphFieldDataPreviewRequest,
    MetaGraphFieldDataPreviewResponse,
    MetaIncomingLeadPreviewItem,
    MetaIncomingLeadsPreviewResponse,
    MetaLeadResponse,
    MetaLeadRerouteRequest,
    MetaLeadRetryItem,
    MetaLeadRetryRequest,
    MetaLeadFieldMappingRule,
    MetaLeadFormListResponse,
    MetaLeadFormMappingOut,
    MetaLeadFormMappingUpdate,
    MetaLeadFormSummaryOut,
    MetaFormRouteOut,
    MetaFormRouteUpdate,
    MetaLeadRetryResponse,
    MetaLeadSelfServeOnboardingOut,
    MetaLeadSettingsOut,
    MetaLeadSettingsUpdate,
    MetaOAuthCompleteIn,
    MetaOAuthCompleteOut,
    MetaOAuthFinalizeIn,
    MetaOAuthFinalizeOut,
    MetaOAuthPageOptionOut,
    MetaOAuthStartOut,
    UnmappedAdGroup,
    UnmappedLeadsResponse,
    LeadMessageTemplateOut,
    LeadMessageTemplateCreateUpdate,
)

META_LEADS_GRAPH_PERMISSIONS = [
    "pages_read_engagement",
    "pages_manage_metadata",
    "pages_show_list",
    "leads_retrieval",
    "business_management",
]


def _to_uuid(value: Optional[str]) -> Optional[UUID]:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _meta_leads_processing_mode_v1_out(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("manual", "assisted", "automatic"):
        return s
    return "assisted"


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
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS leads_processing_mode_v1 VARCHAR(24)"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS generic_inbound_webhook_secret VARCHAR(128)"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS leads_auto_convert_on_fit_v1 BOOLEAN DEFAULT true"
            )
        )
        await db.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_meta_lead_settings_generic_inbound_wh_secret
                ON meta_lead_settings (generic_inbound_webhook_secret)
                WHERE generic_inbound_webhook_secret IS NOT NULL
                """
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
            await db.execute(
                text(
                    "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS leads_processing_mode_v1 TEXT"
                )
            )
            await db.execute(
                text(
                    "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS generic_inbound_webhook_secret TEXT"
                )
            )
            await db.execute(
                text(
                    "ALTER TABLE meta_lead_settings ADD COLUMN IF NOT EXISTS leads_auto_convert_on_fit_v1 INTEGER DEFAULT 1"
                )
            )
            await db.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_meta_lead_settings_generic_inbound_wh_secret
                    ON meta_lead_settings (generic_inbound_webhook_secret)
                    WHERE generic_inbound_webhook_secret IS NOT NULL
                    """
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
    # Coerce legacy {from,to} rows and drop unparseable rules so GET never 500s.
    normalized_mapping = _coerce_mapping_rules_for_api(getattr(entry, "field_mapping", None))

    gsec = getattr(entry, "generic_inbound_webhook_secret", None)
    generic_wh_on = bool(str(gsec).strip()) if gsec is not None else False

    return MetaLeadSettingsOut(
        tenant_id=_to_uuid(entry.tenant_id) or UUID(entry.tenant_id),
        default_company_id=_to_uuid(entry.default_company_id),
        fallback_recruiter_id=_to_uuid(entry.fallback_recruiter_id),
        auto_create_enabled=bool(entry.auto_create_enabled),
        leads_auto_convert_on_fit_v1=bool(getattr(entry, "leads_auto_convert_on_fit_v1", True)),
        leads_processing_mode_v1=_meta_leads_processing_mode_v1_out(
            getattr(entry, "leads_processing_mode_v1", None)
        ),
        reroute_after_hours=entry.reroute_after_hours,
        mask_pii_in_logs=bool(entry.mask_pii_in_logs),
        pull_field_data_from_graph=bool(getattr(entry, "pull_field_data_from_graph", True)),
        field_mapping=normalized_mapping,
        plan_field_mapping_rules_limit=None,
        plan_meta_credentials_limit=None,
        generic_inbound_webhook_enabled=generic_wh_on,
        webhook_url=entry.webhook_url,
        last_webhook_check_at=entry.last_webhook_check_at,
        last_signature_status=entry.last_signature_status,
        webhook_verify_token=entry.webhook_verify_token,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        lead_fit_ordered_vacancy_ids=[],
    )


async def _tenant_lead_fit_ordered_vacancy_ids(db: AsyncSession, tenant_id: str) -> List[UUID]:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or not isinstance(tenant.settings, dict):
        return []
    raw = tenant.settings.get("lead_fit_routing_v1")
    if not isinstance(raw, dict):
        return []
    ids = raw.get("ordered_vacancy_ids")
    if not isinstance(ids, list):
        return []
    out: List[UUID] = []
    for x in ids:
        s = str(x or "").strip()
        if not s:
            continue
        try:
            out.append(UUID(s))
        except ValueError:
            continue
    return out


async def _persist_lead_fit_ordered_vacancy_ids(
    db: AsyncSession, tenant_id: str, ids: Optional[List[UUID]]
) -> None:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    st = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    lfr: Dict[str, Any] = {}
    if isinstance(st.get("lead_fit_routing_v1"), dict):
        lfr = dict(st["lead_fit_routing_v1"])
    order: List[str] = []
    for u in ids or []:
        if u is None:
            continue
        s = str(u).strip()
        if s:
            order.append(s)
    lfr["ordered_vacancy_ids"] = order
    st["lead_fit_routing_v1"] = lfr
    tenant.settings = st
    await db.flush()


async def _enrich_meta_settings_plan_limits(
    db: AsyncSession, tenant_id: str, out: MetaLeadSettingsOut
) -> MetaLeadSettingsOut:
    plan = await resolve_tenant_plan_code(db, tenant_id)
    return out.model_copy(
        update={
            "plan_field_mapping_rules_limit": lead_meta_field_mapping_rules_cap(
                plan, tenant_id=tenant_id
            ),
            "plan_meta_credentials_limit": lead_meta_credentials_cap(plan, tenant_id=tenant_id),
        }
    )


async def enrich_meta_leads_tenant_context(
    db: AsyncSession,
    header_tid: str,
    effective_tid: str,
    out: MetaLeadSettingsOut | MetaLeadSelfServeOnboardingOut,
) -> MetaLeadSettingsOut | MetaLeadSelfServeOnboardingOut:
    if (header_tid or "").strip() == (effective_tid or "").strip():
        return out
    eff = UUID(str(effective_tid))
    row = await db.get(Tenant, str(eff))
    return out.model_copy(
        update={
            "meta_leads_context_redirected": True,
            "meta_leads_data_tenant_id": eff,
            "meta_leads_data_tenant_name": row.name if row else None,
        }
    )


async def get_settings(db: AsyncSession, tenant_id: str) -> MetaLeadSettingsOut:
    from backend.app.services.lead_communication_settings import (
        get_lead_communication_settings,
        lead_communication_settings_to_api_dict,
    )
    from backend.app.services.lead_rodo_settings import get_lead_rodo_settings, lead_rodo_settings_to_api_dict

    entry = await _ensure_settings(db, tenant_id)
    base = _settings_to_schema(entry)
    ordered = await _tenant_lead_fit_ordered_vacancy_ids(db, tenant_id)
    rodo = await get_lead_rodo_settings(db, tenant_id)
    comm = await get_lead_communication_settings(db, tenant_id)
    base = base.model_copy(
        update={
            "lead_fit_ordered_vacancy_ids": ordered,
            **lead_rodo_settings_to_api_dict(rodo),
            **lead_communication_settings_to_api_dict(comm),
        }
    )
    return await _enrich_meta_settings_plan_limits(db, tenant_id, base)


async def get_meta_self_serve_onboarding(
    db: AsyncSession,
    tenant_id: str,
    *,
    include_shared_app_secret: bool,
) -> MetaLeadSelfServeOnboardingOut:
    from urllib.parse import quote

    entry = await _ensure_settings(db, tenant_id)
    token_raw = (entry.webhook_verify_token or "").strip()
    base = (settings.public_api_base_url or settings.frontend_url or "").strip().rstrip("/")
    public_configured = bool(base)
    callback = None
    if base and token_raw:
        callback = f"{base}/api/v1/leads/meta/webhook?verify_token={quote(token_raw, safe='')}"
    app_id = (settings.meta_leads_app_id or "").strip() or None
    secret = None
    if include_shared_app_secret:
        s = (settings.meta_leads_shared_app_secret or "").strip()
        secret = s or None
    dash_url = f"https://developers.facebook.com/apps/{app_id}/dashboard/" if app_id else None
    disp = (settings.meta_leads_app_display_name or "HostFlow Leads").strip() or "HostFlow Leads"
    doc = (settings.meta_leads_docs_url or "").strip() or None
    gv = (settings.meta_graph_api_version or "v24.0").strip() or "v24.0"
    plan = await resolve_tenant_plan_code(db, tenant_id)
    oauth_uri = meta_oauth.meta_leads_oauth_redirect_uri()
    oauth_ready = meta_oauth.oauth_configuration_ready()
    plan_ok = plan_allows_meta_leads_oauth(plan)
    oauth_qc = bool(plan_ok and oauth_ready)
    return MetaLeadSelfServeOnboardingOut(
        meta_app_id=app_id,
        meta_app_display_name=disp,
        documentation_url=doc,
        graph_api_version=gv,
        graph_permission_names=list(META_LEADS_GRAPH_PERMISSIONS),
        public_api_base_url=base or None,
        public_api_base_configured=public_configured,
        webhook_verify_token_configured=bool(token_raw),
        webhook_callback_url=callback,
        shared_meta_app_secret=secret,
        developers_console_app_url=dash_url,
        graph_api_explorer_url="https://developers.facebook.com/tools/explorer/",
        oauth_quick_connect_enabled=oauth_qc,
        meta_oauth_plan_allowed=plan_ok,
        meta_oauth_server_ready=oauth_ready,
        oauth_redirect_uri=oauth_uri,
    )


async def meta_oauth_start(db: AsyncSession, tenant_id: str, user_sub: str) -> MetaOAuthStartOut:
    await ensure_meta_leads_oauth_allowed(db, tenant_id)
    if not meta_oauth.oauth_configuration_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "meta_oauth_not_configured",
                "message": "Server is missing META_LEADS_APP_ID, META_LEADS_SHARED_APP_SECRET, or frontend URL for OAuth redirect.",
            },
        )
    state = meta_oauth.sign_oauth_state(tenant_id=tenant_id, user_sub=user_sub)
    try:
        url = meta_oauth.build_facebook_authorize_url(state=state)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "meta_oauth_not_configured", "message": "OAuth redirect URI could not be built."},
        )
    return MetaOAuthStartOut(authorize_url=url, state=state)


async def meta_oauth_complete(
    db: AsyncSession,
    tenant_id: str,
    user_sub: str,
    payload: MetaOAuthCompleteIn,
) -> MetaOAuthCompleteOut:
    await ensure_meta_leads_oauth_allowed(db, tenant_id)
    if not meta_oauth.oauth_configuration_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "meta_oauth_not_configured", "message": "Meta OAuth is not configured on the server."},
        )
    try:
        st = meta_oauth.verify_oauth_state(payload.state.strip())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_oauth_state")
    if st.get("t") != tenant_id or st.get("s") != user_sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="oauth_state_mismatch")
    redirect_uri = meta_oauth.meta_leads_oauth_redirect_uri()
    if not redirect_uri:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="meta_oauth_not_configured")
    code = (payload.code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing_oauth_code")
    try:
        short_tok = await meta_oauth.exchange_code_for_short_lived_user_token(
            code=code, redirect_uri=redirect_uri
        )
        long_tok = await meta_oauth.exchange_for_long_lived_user_token(short_lived_user_token=short_tok)
        pages_raw = await meta_oauth.fetch_pages_with_tokens(user_access_token=long_tok)
    except meta_oauth.MetaOAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "meta_oauth_graph_error", "message": str(exc)},
        ) from exc
    if not pages_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "meta_oauth_no_pages", "message": "No Facebook Pages returned for this account."},
        )
    await crud.delete_expired_meta_oauth_pending(db)
    enc = encrypt_secret(json.dumps(pages_raw))
    if not enc:
        raise HTTPException(status_code=500, detail="encrypt_failed")
    exp = datetime.now(timezone.utc) + timedelta(seconds=meta_oauth.PENDING_TTL_SECONDS)
    row = await crud.create_meta_oauth_pending(
        db,
        tenant_id=tenant_id,
        user_sub=user_sub,
        encrypted_payload=enc,
        expires_at=exp,
    )
    return MetaOAuthCompleteOut(
        pending_id=row.id,
        pages=[MetaOAuthPageOptionOut(id=p["id"], name=p["name"]) for p in pages_raw],
    )


async def meta_oauth_finalize(
    db: AsyncSession,
    tenant_id: str,
    user_sub: str,
    payload: MetaOAuthFinalizeIn,
) -> MetaOAuthFinalizeOut:
    await ensure_meta_leads_oauth_allowed(db, tenant_id)
    row = await crud.get_meta_oauth_pending(
        db, pending_id=(payload.pending_id or "").strip(), tenant_id=tenant_id
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="oauth_pending_not_found")
    if row.user_sub != user_sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="oauth_pending_forbidden")
    if row.expires_at < datetime.now(timezone.utc):
        await crud.delete_meta_oauth_pending(db, row)
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="oauth_pending_expired")
    raw = decrypt_secret(row.encrypted_payload)
    if not raw:
        await crud.delete_meta_oauth_pending(db, row)
        raise HTTPException(status_code=500, detail="oauth_pending_corrupt")
    try:
        pages_list = json.loads(raw)
    except json.JSONDecodeError:
        await crud.delete_meta_oauth_pending(db, row)
        raise HTTPException(status_code=500, detail="oauth_pending_corrupt")
    page_id_want = (payload.page_id or "").strip()
    match = next((p for p in pages_list if isinstance(p, dict) and str(p.get("id") or "") == page_id_want), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="oauth_page_not_in_session")
    access_token = str(match.get("access_token") or "").strip()
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="oauth_page_token_missing")
    label = (payload.label or "").strip()
    if not label:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="credential_label_required")
    app_secret = (settings.meta_leads_shared_app_secret or "").strip()
    if not app_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="meta_oauth_not_configured")
    cred_in = MetaCredentialCreate(
        label=label,
        status="active",
        secret=app_secret,
        access_token=access_token,
        page_id=page_id_want,
        ad_account_id=None,
    )
    cred_out = await create_credential(db, tenant_id, cred_in)
    subscribed = False
    warning: Optional[str] = None
    if payload.subscribe_leadgen:
        try:
            await meta_oauth.subscribe_page_leadgen(page_id=page_id_want, page_access_token=access_token)
            subscribed = True
        except meta_oauth.MetaOAuthError as exc:
            warning = str(exc)
    await crud.delete_meta_oauth_pending(db, row)
    return MetaOAuthFinalizeOut(credential=cred_out, subscribed_leadgen=subscribed, warning=warning)


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
    fields_set = getattr(payload, "model_fields_set", None) or set()
    fit_ordered = updates.pop("lead_fit_ordered_vacancy_ids", None)
    rodo_mode = updates.pop("lead_rodo_send_mode", None)
    rodo_channels = updates.pop("lead_rodo_channels", None)
    rodo_template = updates.pop("lead_rodo_template_id", None)
    rodo_message_template = updates.pop("lead_rodo_message_template_id", None)
    rodo_settings_touched = any(
        k in fields_set
        for k in ("lead_rodo_send_mode", "lead_rodo_channels", "lead_rodo_template_id", "lead_rodo_message_template_id")
    )
    comm_enabled = updates.pop("lead_communication_enabled", None)
    comm_app_recv = updates.pop("send_application_received", None)
    comm_reject = updates.pop("send_rejection_notice", None)
    comm_moving = updates.pop("send_moving_forward_notice", None)
    comm_app_recv_subject = updates.pop("application_received_subject", None)
    comm_app_recv_body = updates.pop("application_received_body", None)
    comm_reject_subject = updates.pop("rejection_notice_subject", None)
    comm_reject_body = updates.pop("rejection_notice_body", None)
    comm_moving_subject = updates.pop("moving_forward_subject", None)
    comm_moving_body = updates.pop("moving_forward_body", None)
    comm_app_recv_template = updates.pop("application_received_template_id", None)
    comm_reject_template = updates.pop("rejection_notice_template_id", None)
    comm_moving_template = updates.pop("moving_forward_template_id", None)
    comm_settings_touched = any(
        k in fields_set
        for k in (
            "lead_communication_enabled",
            "send_application_received",
            "send_rejection_notice",
            "send_moving_forward_notice",
            "application_received_subject",
            "application_received_body",
            "rejection_notice_subject",
            "rejection_notice_body",
            "moving_forward_subject",
            "moving_forward_body",
            "application_received_template_id",
            "rejection_notice_template_id",
            "moving_forward_template_id",
        )
    )
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
        await ensure_meta_lead_field_mapping_rows_allowed(
            db, tenant_id, len(updates["field_mapping"])
        )
    await crud.update_meta_settings(db, entry, **updates)
    if fit_ordered is not None:
        await _persist_lead_fit_ordered_vacancy_ids(db, tenant_id, fit_ordered)
    if rodo_settings_touched:
        from backend.app.services.lead_rodo_settings import persist_lead_rodo_settings

        await persist_lead_rodo_settings(
            db,
            tenant_id,
            send_mode=rodo_mode,
            channels=rodo_channels,
            template_id=rodo_template if "lead_rodo_template_id" in fields_set else None,
            clear_template_id="lead_rodo_template_id" in fields_set and rodo_template is None,
            message_template_id=rodo_message_template if "lead_rodo_message_template_id" in fields_set else None,
            clear_message_template_id="lead_rodo_message_template_id" in fields_set and rodo_message_template is None,
        )
    if comm_settings_touched:
        from backend.app.services.lead_communication_settings import persist_lead_communication_settings

        await persist_lead_communication_settings(
            db,
            tenant_id,
            enabled=comm_enabled if "lead_communication_enabled" in fields_set else None,
            send_application_received=comm_app_recv if "send_application_received" in fields_set else None,
            send_rejection_notice=comm_reject if "send_rejection_notice" in fields_set else None,
            send_moving_forward_notice=comm_moving if "send_moving_forward_notice" in fields_set else None,
            application_received_subject=comm_app_recv_subject if "application_received_subject" in fields_set else None,
            application_received_body=comm_app_recv_body if "application_received_body" in fields_set else None,
            rejection_notice_subject=comm_reject_subject if "rejection_notice_subject" in fields_set else None,
            rejection_notice_body=comm_reject_body if "rejection_notice_body" in fields_set else None,
            moving_forward_subject=comm_moving_subject if "moving_forward_subject" in fields_set else None,
            moving_forward_body=comm_moving_body if "moving_forward_body" in fields_set else None,
            application_received_template_id=comm_app_recv_template if "application_received_template_id" in fields_set else None,
            rejection_notice_template_id=comm_reject_template if "rejection_notice_template_id" in fields_set else None,
            moving_forward_template_id=comm_moving_template if "moving_forward_template_id" in fields_set else None,
        )
    base = _settings_to_schema(entry)
    ordered = await _tenant_lead_fit_ordered_vacancy_ids(db, tenant_id)
    from backend.app.services.lead_communication_settings import (
        get_lead_communication_settings,
        lead_communication_settings_to_api_dict,
    )
    from backend.app.services.lead_rodo_settings import get_lead_rodo_settings, lead_rodo_settings_to_api_dict

    rodo = await get_lead_rodo_settings(db, tenant_id)
    comm = await get_lead_communication_settings(db, tenant_id)
    base = base.model_copy(
        update={
            "lead_fit_ordered_vacancy_ids": ordered,
            **lead_rodo_settings_to_api_dict(rodo),
            **lead_communication_settings_to_api_dict(comm),
        }
    )
    return await _enrich_meta_settings_plan_limits(db, tenant_id, base)


async def rotate_generic_inbound_webhook_secret(
    db: AsyncSession,
    tenant_id: str,
) -> GenericInboundWebhookRotateResponse:
    """Issue a new path secret for POST /api/v1/public/leads/inbound/{secret} (Team+)."""
    await ensure_leads_generic_inbound_webhook_allowed(db, tenant_id)
    await _ensure_settings_schema(db)
    entry = await _ensure_settings(db, tenant_id)
    existing_secret = str(getattr(entry, "generic_inbound_webhook_secret", None) or "").strip()
    if not existing_secret:
        current_sources = await count_tenant_lead_sources(db, tenant_id)
        await ensure_lead_source_limit(db, tenant_id, current_count=current_sources, extra_sources=1)
    secret = secrets.token_urlsafe(32)
    await crud.update_meta_settings(db, entry, generic_inbound_webhook_secret=secret)
    base = (getattr(settings, "public_api_base_url", None) or "").strip().rstrip("/")
    path = f"/api/v1/public/leads/inbound/{secret}"
    ingest_url = f"{base}{path}" if base else path
    return GenericInboundWebhookRotateResponse(secret=secret, ingest_url=ingest_url)


async def list_lead_message_templates(db: AsyncSession, tenant_id: str) -> list[LeadMessageTemplateOut]:
    from backend.app.services.lead_message_templates import list_lead_message_templates as _list

    rows = await _list(db, tenant_id)
    return [
        LeadMessageTemplateOut(
            id=row.id,
            name=row.name,
            subject=row.subject,
            body=row.body,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


async def create_lead_message_template(
    db: AsyncSession, tenant_id: str, payload: LeadMessageTemplateCreateUpdate
) -> LeadMessageTemplateOut:
    from backend.app.services.lead_message_templates import upsert_lead_message_template

    row = await upsert_lead_message_template(
        db,
        tenant_id,
        template_id=None,
        name=payload.name,
        subject=payload.subject,
        body=payload.body,
        is_active=payload.is_active,
    )
    return LeadMessageTemplateOut(
        id=row.id,
        name=row.name,
        subject=row.subject,
        body=row.body,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def update_lead_message_template(
    db: AsyncSession, tenant_id: str, template_id: str, payload: LeadMessageTemplateCreateUpdate
) -> LeadMessageTemplateOut:
    from backend.app.services.lead_message_templates import upsert_lead_message_template

    row = await upsert_lead_message_template(
        db,
        tenant_id,
        template_id=template_id,
        name=payload.name,
        subject=payload.subject,
        body=payload.body,
        is_active=payload.is_active,
    )
    return LeadMessageTemplateOut(
        id=row.id,
        name=row.name,
        subject=row.subject,
        body=row.body,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def delete_lead_message_template(db: AsyncSession, tenant_id: str, template_id: str) -> bool:
    from backend.app.services.lead_message_templates import delete_lead_message_template as _delete

    return await _delete(db, tenant_id, template_id)


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
    await ensure_meta_lead_credential_create_allowed(db, tenant_id)
    current_sources = await count_tenant_lead_sources(db, tenant_id)
    await ensure_lead_source_limit(db, tenant_id, current_count=current_sources, extra_sources=1)
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


def _meta_graph_value_preview(values: Any, *, max_len: int = 96) -> Optional[str]:
    if not isinstance(values, list) or not values:
        return None
    first = values[0]
    if first is None:
        return None
    s = str(first).strip()
    if not s:
        return None
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def _extract_leadgen_id_from_stored_meta_payload(payload: Dict[str, Any]) -> Optional[str]:
    from backend.app.modules.leads.pipeline import collect_leadgen_ids

    ids = list(collect_leadgen_ids(payload))
    return ids[0] if ids else None


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
    from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID

    normalized = {str(pid).strip() for pid in page_ids if str(pid).strip()}
    if not normalized:
        return None
    legacy = str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
    rows = await crud.list_all_meta_credentials(db)
    matches: List[Tuple[str, crud.MetaLeadCredential]] = []
    for entry in rows:
        if entry.status not in {"active", "rotation_pending"}:
            continue
        page_id = decrypt_secret(entry.encrypted_page_id)
        if page_id and page_id.strip() in normalized:
            matches.append((entry.tenant_id, entry))
    if not matches:
        return None
    # Prefer real client tenants if the same page_id was mistakenly stored twice (e.g. superadmin + Focus).
    matches.sort(key=lambda m: (0 if m[0] != legacy else 1, m[0]))
    chosen = matches[0]
    return chosen[0], chosen[1]


async def get_page_access_token(
    db: AsyncSession,
    tenant_id: str,
    page_id: str,
) -> Optional[str]:
    """Return the newest **active** page token (skips inactive duplicates for the same page_id)."""
    entries = await crud.list_meta_credentials(db, tenant_id=tenant_id)
    for entry in entries:
        if str(getattr(entry, "status", "") or "").strip().lower() != "active":
            continue
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
    business_type = await service._load_tenant_business_type(db, tenant_id)
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
            outcome_entity_type, outcome_entity_id, outcome_entity_name = service._build_lead_outcome(
                business_type=business_type,
                company_id=lead.company_id,
                company_name=None,
                candidate_id=lead.candidate_id,
                candidate_name=None,
            )
            _, vrc = lead_vacancy_routing_aux(
                lead.normalized if isinstance(lead.normalized, dict) else {},
                lead.vacancy_id,
            )
            items.append(
                LeadOut(
                    id=UUID(lead.id),
                    tenant_id=UUID(lead.tenant_id),
                    business_type=business_type,
                    lead_type=(getattr(lead, "lead_type", None) or "candidate"),  # type: ignore[arg-type]
                    company_id=_to_uuid(lead.company_id),
                    company_name=None,
                    vacancy_id=_to_uuid(lead.vacancy_id),
                    vacancy_title=None,
                    source=lead.source,
                    ad_id=lead.ad_id,
                    external_id=getattr(lead, "external_id", None),
                    status=lead.status,  # type: ignore[arg-type]
                    candidate_id=_to_uuid(lead.candidate_id),
                    candidate_name=None,
                    outcome_entity_type=outcome_entity_type,
                    outcome_entity_id=_to_uuid(outcome_entity_id),
                    outcome_entity_name=outcome_entity_name,
                    recruiter_id=None,
                    error=lead.error,
                    payload=lead.payload or {},
                    normalized=lead.normalized,
                    created_at=lead.created_at,
                    last_routed_at=lead.last_routed_at,
                    vacancy_routing_confirmed=vrc,
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
    own_company_id: Optional[str],
    payload: MetaLeadRetryRequest,
) -> MetaLeadRetryResponse:
    lead_ids = [str(value) for value in payload.lead_ids] if payload.lead_ids else None
    statuses = [value for value in payload.statuses] if payload.statuses else None

    outcomes = await service.retry_meta_leads(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
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


_MAX_PAYLOAD_PREVIEW = 16_384
_MAX_NORMALIZED_PREVIEW = 8_192


async def fetch_meta_graph_field_preview(
    db: AsyncSession,
    tenant_id: str,
    body: MetaGraphFieldDataPreviewRequest,
) -> MetaGraphFieldDataPreviewResponse:
    """
    Pull field_data for a Meta lead from Graph using the tenant's Page token (real form field names).
    """
    from backend.app.modules.leads import pipeline as meta_pipeline

    leadgen_id: Optional[str] = None
    page_id: Optional[str] = None

    if body.hostflow_lead_id is not None:
        row = await db.get(Lead, str(body.hostflow_lead_id))
        if not row or row.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        if (row.source or "").strip().lower() != "meta":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "lead_not_meta",
                    "message": "Only Meta-source leads can resolve Graph field preview.",
                },
            )
        raw = row.payload if isinstance(row.payload, dict) else {}
        pids = extract_page_ids(raw)
        page_id = (body.page_id or "").strip() or (pids[0] if pids else "")
        leadgen_id = (body.leadgen_id or "").strip() or (row.external_id or "").strip() or None
        if not leadgen_id:
            leadgen_id = _extract_leadgen_id_from_stored_meta_payload(raw)
    else:
        leadgen_id = (body.leadgen_id or "").strip() or None
        page_id = (body.page_id or "").strip() or None

    if not leadgen_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "leadgen_id_required",
                "message": "Provide leadgen_id or hostflow_lead_id whose payload contains leadgen_id.",
            },
        )
    if not page_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "page_id_required",
                "message": "Provide page_id or use hostflow_lead_id with page_id in stored webhook payload.",
            },
        )

    token = await get_page_access_token(db, tenant_id, page_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "meta_no_page_token",
                "message": "No Page access token for this page_id. Check Meta credentials.",
            },
        )

    try:
        graph_payload = await meta_pipeline.fetch_meta_lead_field_data_from_graph(leadgen_id, token)
    except meta_pipeline.GraphAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "meta_graph_error",
                "message": str(exc),
                "graph_code": exc.code,
            },
        ) from exc

    field_data = graph_payload.get("field_data") if isinstance(graph_payload, dict) else None
    if not isinstance(field_data, list):
        field_data = []

    fields_out: List[MetaGraphFieldDataPreviewField] = []
    seen: set[str] = set()
    for item in field_data:
        if not isinstance(item, dict):
            continue
        raw_name = str(item.get("name") or "").strip()
        if not raw_name:
            continue
        nl = raw_name.lower()
        if nl in seen:
            continue
        seen.add(nl)
        fields_out.append(
            MetaGraphFieldDataPreviewField(
                name=nl,
                value_preview=_meta_graph_value_preview(item.get("values")),
            )
        )

    fields_out.sort(key=lambda f: f.name)
    ad_raw = graph_payload.get("ad_id") if isinstance(graph_payload, dict) else None
    form_raw = graph_payload.get("form_id") if isinstance(graph_payload, dict) else None

    return MetaGraphFieldDataPreviewResponse(
        field_names=[f.name for f in fields_out],
        fields=fields_out,
        leadgen_id=leadgen_id,
        page_id=page_id,
        ad_id=str(ad_raw) if ad_raw is not None and str(ad_raw).strip() else None,
        form_id=str(form_raw) if form_raw is not None and str(form_raw).strip() else None,
    )


async def list_meta_incoming_preview(
    db: AsyncSession,
    tenant_id: str,
    *,
    limit: int = 25,
    source: str = "meta",
) -> MetaIncomingLeadsPreviewResponse:
    lim = min(max(1, limit), 50)
    src = (source or "meta").strip().lower()
    if src not in ("meta", "webhook"):
        src = "meta"
    stmt = (
        select(Lead)
        .where(Lead.tenant_id == tenant_id, Lead.source == src)
        .order_by(desc(Lead.created_at))
        .limit(lim)
    )
    rows = (await db.execute(stmt)).scalars().all()
    items: List[MetaIncomingLeadPreviewItem] = []
    for row in rows:
        raw = row.payload if isinstance(row.payload, dict) else {}
        try:
            js = json.dumps(raw, ensure_ascii=False, default=str)
        except Exception:
            js = "{}"
        p_trunc = len(js) > _MAX_PAYLOAD_PREVIEW
        p_preview = js[:_MAX_PAYLOAD_PREVIEW] if p_trunc else js

        n_preview: Optional[str] = None
        n_trunc = False
        norm = row.normalized if isinstance(row.normalized, dict) else None
        if norm:
            try:
                nj = json.dumps(norm, ensure_ascii=False, default=str)
                n_trunc = len(nj) > _MAX_NORMALIZED_PREVIEW
                n_preview = nj[:_MAX_NORMALIZED_PREVIEW] if n_trunc else nj
            except Exception:
                n_preview = None
                n_trunc = False

        items.append(
            MetaIncomingLeadPreviewItem(
                lead_id=str(row.id),
                created_at=row.created_at,
                external_id=row.external_id,
                ad_id=int(row.ad_id) if row.ad_id is not None else None,
                status=str(row.status or ""),
                stage=row.stage,
                payload_json_preview=p_preview,
                payload_truncated=p_trunc,
                normalized_json_preview=n_preview,
                normalized_truncated=n_trunc,
            )
        )
    return MetaIncomingLeadsPreviewResponse(items=items)


def _coerce_mapping_rules_for_api(raw: Any) -> List[MetaLeadFieldMappingRule]:
    if not raw:
        return []
    items: List[Any]
    if isinstance(raw, dict) and isinstance(raw.get("rules"), list):
        items = raw.get("rules") or []
    elif isinstance(raw, list):
        items = raw
    else:
        return []
    out: List[MetaLeadFieldMappingRule] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            out.append(MetaLeadFieldMappingRule.model_validate(item))
        except Exception:
            continue
    return out


async def _tenant_mapping_rules(db: AsyncSession, tenant_id: str) -> List[MetaLeadFieldMappingRule]:
    entry = await _ensure_settings(db, tenant_id)
    return _coerce_mapping_rules_for_api(getattr(entry, "field_mapping", None))


async def list_meta_lead_forms(
    db: AsyncSession,
    tenant_id: str,
    *,
    source: str = "meta",
) -> MetaLeadFormListResponse:
    src = (source or "meta").strip().lower() or "meta"
    tenant_rules = await _tenant_mapping_rules(db, tenant_id)
    saved = await crud.list_meta_form_mapping_rows(db, tenant_id=tenant_id, source=src)
    saved_routes = await crud.list_meta_form_routes(db, tenant_id=tenant_id, source=src)
    discovered = await crud.list_discovered_meta_forms_from_leads(db, tenant_id=tenant_id, source=src)

    routes_by_key: Dict[Tuple[str, str], Any] = {}

    def route_key(form_id: str, page_id: Optional[str]) -> Tuple[str, str]:
        return form_id, (page_id or "").strip()

    for row in saved_routes:
        fid = str(row.form_id).strip()
        if not fid:
            continue
        pid = str(row.page_id or "").strip() or None
        routes_by_key[route_key(fid, pid)] = row

    by_key: Dict[Tuple[str, str], MetaLeadFormSummaryOut] = {}

    def key(form_id: str, page_id: Optional[str]) -> Tuple[str, str]:
        return form_id, (page_id or "").strip()

    def apply_route_fields(summary: MetaLeadFormSummaryOut, form_id: str, page_id: Optional[str]) -> MetaLeadFormSummaryOut:
        rk = route_key(form_id, page_id)
        route = routes_by_key.get(rk)
        if route is None and page_id:
            route = routes_by_key.get(route_key(form_id, ""))
        if route is None:
            return summary
        return summary.model_copy(
            update={
                "has_intake_route": True,
                "intake_route_active": bool(getattr(route, "is_active", True)),
                "intake_own_company_id": str(route.own_company_id),
                "intake_lead_target_type": getattr(route, "lead_target_type", None),
            }
        )

    for row in saved:
        fid = str(row.form_id).strip()
        if not fid:
            continue
        pid = str(row.page_id or "").strip() or None
        rules = _coerce_mapping_rules_for_api(row.mapping_rules)
        by_key[key(fid, pid)] = apply_route_fields(
            MetaLeadFormSummaryOut(
            form_id=fid,
            page_id=pid,
            source=src,
            form_name=row.form_name,
            has_form_mapping=bool(rules),
            mapping_rules_count=len(rules),
            inherits_tenant_fallback=not rules,
            last_sample_lead_id=row.last_sample_lead_id,
            updated_at=row.updated_at,
            ),
            fid,
            pid,
        )

    for disc in discovered:
        fid = str(disc.get("form_id") or "").strip()
        if not fid:
            continue
        pid = str(disc.get("page_id") or "").strip() or None
        k = key(fid, pid)
        if k in by_key:
            continue
        by_key[k] = apply_route_fields(
            MetaLeadFormSummaryOut(
            form_id=fid,
            page_id=pid,
            source=src,
            has_form_mapping=False,
            mapping_rules_count=0,
            inherits_tenant_fallback=True,
            ),
            fid,
            pid,
        )

    items = sorted(by_key.values(), key=lambda x: (x.form_name or x.form_id, x.page_id or ""))
    return MetaLeadFormListResponse(
        items=items,
        tenant_fallback_rules_count=len(tenant_rules),
    )


async def get_meta_lead_form_mapping(
    db: AsyncSession,
    tenant_id: str,
    form_id: str,
    *,
    page_id: Optional[str] = None,
    source: str = "meta",
) -> MetaLeadFormMappingOut:
    fid = str(form_id or "").strip()
    if not fid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="form_id is required")
    pid = str(page_id or "").strip() or None
    src = (source or "meta").strip().lower() or "meta"
    tenant_rules = await _tenant_mapping_rules(db, tenant_id)
    row = await crud.get_meta_form_mapping(db, tenant_id=tenant_id, form_id=fid, page_id=pid, source=src)
    if row is None and pid:
        row = await crud.get_meta_form_mapping(
            db, tenant_id=tenant_id, form_id=fid, page_id="", source=src
        )
    if row is None:
        return MetaLeadFormMappingOut(
            form_id=fid,
            page_id=pid,
            source=src,
            mapping_rules=list(tenant_rules),
            inherits_tenant_fallback=True,
            tenant_fallback_rules=list(tenant_rules),
        )
    rules = _coerce_mapping_rules_for_api(row.mapping_rules)
    inherits = not rules
    effective = list(tenant_rules) if inherits else rules
    return MetaLeadFormMappingOut(
        form_id=fid,
        page_id=pid or (str(row.page_id).strip() or None),
        source=src,
        form_name=row.form_name,
        mapping_rules=effective,
        inherits_tenant_fallback=inherits,
        tenant_fallback_rules=list(tenant_rules),
        last_sample_lead_id=row.last_sample_lead_id,
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


async def upsert_meta_lead_form_mapping(
    db: AsyncSession,
    tenant_id: str,
    form_id: str,
    payload: MetaLeadFormMappingUpdate,
    *,
    user_sub: Optional[str] = None,
) -> MetaLeadFormMappingOut:
    fid = str(form_id or "").strip()
    if not fid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="form_id is required")
    rules = payload.mapping_rules or []
    await ensure_meta_lead_field_mapping_rows_allowed(db, tenant_id, len(rules))
    src = (payload.source or "meta").strip().lower() or "meta"
    pid = str(payload.page_id or "").strip() or None
    await crud.upsert_meta_form_mapping(
        db,
        tenant_id=tenant_id,
        form_id=fid,
        page_id=pid,
        source=src,
        mapping_rules=[r.model_dump() for r in rules],
        form_name=payload.form_name,
        last_sample_lead_id=str(payload.last_sample_lead_id).strip() if payload.last_sample_lead_id else None,
        updated_by=user_sub,
    )
    return await get_meta_lead_form_mapping(db, tenant_id, fid, page_id=pid, source=src)


async def _validate_own_company_for_tenant(
    db: AsyncSession, tenant_id: str, own_company_id: str
) -> OwnCompany:
    oc = str(own_company_id or "").strip()
    if not oc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="own_company_id is required")
    row = (
        await db.execute(
            select(OwnCompany).where(
                OwnCompany.id == oc,
                OwnCompany.tenant_id == tenant_id,
                OwnCompany.is_archived.is_(False),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid own_company_id")
    return row


async def get_meta_form_route(
    db: AsyncSession,
    tenant_id: str,
    form_id: str,
    *,
    page_id: Optional[str] = None,
    source: str = "meta",
) -> MetaFormRouteOut:
    fid = str(form_id or "").strip()
    if not fid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="form_id is required")
    pid = str(page_id or "").strip() or None
    src = (source or "meta").strip().lower() or "meta"
    row = await crud.get_meta_form_route(db, tenant_id=tenant_id, form_id=fid, page_id=pid, source=src)
    if row is None and pid:
        row = await crud.get_meta_form_route(db, tenant_id=tenant_id, form_id=fid, page_id="", source=src)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake route not configured for this form")
    oc = await db.get(OwnCompany, row.own_company_id)
    return MetaFormRouteOut(
        form_id=fid,
        page_id=pid or (str(row.page_id).strip() or None),
        source=src,
        own_company_id=UUID(row.own_company_id),
        own_company_name=getattr(oc, "name", None) if oc else None,
        lead_target_type=row.lead_target_type,  # type: ignore[arg-type]
        pipeline_preset=row.pipeline_preset,
        default_assignee_id=UUID(row.default_assignee_id) if row.default_assignee_id else None,
        is_active=bool(row.is_active),
        updated_at=row.updated_at,
        updated_by=row.updated_by,
    )


async def upsert_meta_form_route(
    db: AsyncSession,
    tenant_id: str,
    form_id: str,
    payload: MetaFormRouteUpdate,
    *,
    user_sub: Optional[str] = None,
) -> MetaFormRouteOut:
    fid = str(form_id or "").strip()
    if not fid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="form_id is required")
    src = (payload.source or "meta").strip().lower() or "meta"
    pid = str(payload.page_id or "").strip() or None
    await _validate_own_company_for_tenant(db, tenant_id, str(payload.own_company_id))
    await crud.upsert_meta_form_route(
        db,
        tenant_id=tenant_id,
        form_id=fid,
        own_company_id=str(payload.own_company_id),
        lead_target_type=payload.lead_target_type,
        page_id=pid,
        source=src,
        pipeline_preset=payload.pipeline_preset,
        default_assignee_id=str(payload.default_assignee_id) if payload.default_assignee_id else None,
        is_active=payload.is_active,
        updated_by=user_sub,
    )
    return await get_meta_form_route(db, tenant_id, fid, page_id=pid, source=src)
