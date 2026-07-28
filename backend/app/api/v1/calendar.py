from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status, Response
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.core.queue import enqueue_job
from backend.app.core.settings import settings
from backend.app.services.communications_oauth import (
    OAuthProviderError,
    exchange_oauth_code_for_tokens,
    refresh_oauth_access_token,
)
from backend.app.services.calendar_provider_push import (
    CalendarPushError,
    push_create_event,
    push_delete_event,
    push_update_event,
)
from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID, get_db, get_db_with_tenant
from backend.app.models.calendar_integration import (
    CalendarConnection,
    CalendarItem,
    CalendarItemLink,
    CalendarSyncCursor,
    CalendarSyncJob,
    IntegrationActionLog,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])


class CalendarItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    kind: str = "event"
    starts_at: datetime
    ends_at: Optional[datetime] = None
    timezone: str = "UTC"
    all_day: bool = False
    linked_entity_type: Optional[str] = None
    linked_entity_id: Optional[str] = None
    assignee_id: Optional[UUID] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CalendarItemPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    timezone: Optional[str] = None
    all_day: Optional[bool] = None
    assignee_id: Optional[UUID] = None
    status: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class CalendarRemindRequest(BaseModel):
    remind_at: Optional[datetime] = None
    channel: str = "in_app"
    note: Optional[str] = None


class CalendarAssignRequest(BaseModel):
    assignee_id: UUID
    note: Optional[str] = None


class CalendarItemOut(BaseModel):
    id: UUID
    kind: str
    status: str
    title: str
    description: Optional[str] = None
    timezone: str
    starts_at: datetime
    ends_at: Optional[datetime] = None
    all_day: bool
    linked_entity_type: Optional[str] = None
    linked_entity_id: Optional[str] = None
    owner_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, item: CalendarItem) -> "CalendarItemOut":
        return cls(
            id=UUID(item.id),
            kind=item.kind,
            status=item.status,
            title=item.title,
            description=item.description,
            timezone=item.timezone,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
            all_day=bool(item.all_day),
            linked_entity_type=item.linked_entity_type,
            linked_entity_id=item.linked_entity_id,
            owner_id=UUID(item.owner_id) if item.owner_id else None,
            assignee_id=UUID(item.assignee_id) if item.assignee_id else None,
            source=item.source,
            payload=dict(item.payload or {}),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class CalendarItemsResponse(BaseModel):
    items: list[CalendarItemOut]


class IntegrationWebhookAck(BaseModel):
    accepted: bool
    tenant_id: str
    queued_job_id: Optional[UUID] = None


class CalendarConnectionCreate(BaseModel):
    provider: str = Field(pattern="^(google|microsoft)$")
    account_ref: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    status: str = "active"


class CalendarConnectionOAuthComplete(BaseModel):
    provider: str = Field(pattern="^(google|microsoft)$")
    code: str
    client_id: str
    client_secret: Optional[str] = None
    redirect_uri: str
    account_ref: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)


class CalendarConnectionRefreshRequest(BaseModel):
    client_id: str
    client_secret: Optional[str] = None
    scope: Optional[str] = None


class CalendarConnectionOut(BaseModel):
    id: UUID
    provider: str
    account_ref: Optional[str] = None
    status: str
    user_id: Optional[UUID] = None
    scopes: list[Any] = Field(default_factory=list)
    token_meta: dict[str, Any] = Field(default_factory=dict)
    last_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @staticmethod
    def _public_token_meta(raw: dict[str, Any] | None) -> dict[str, Any]:
        """Never expose OAuth secrets / access tokens in API responses."""
        if not raw:
            return {}
        allow = {
            "expires_at",
            "expiry",
            "exp",
            "expires_in",
            "token_type",
            "scope",
            "scopes",
        }
        out: dict[str, Any] = {}
        for key, value in raw.items():
            lk = str(key).strip().lower()
            if lk in allow:
                out[key] = value
                continue
            if any(s in lk for s in ("token", "secret", "password", "authorization")):
                continue
            out[key] = value
        return out

    @classmethod
    def from_model(cls, row: CalendarConnection) -> "CalendarConnectionOut":
        return cls(
            id=UUID(row.id),
            provider=row.provider,
            account_ref=row.account_ref,
            status=row.status,
            user_id=UUID(row.user_id) if row.user_id else None,
            scopes=list(row.scopes_json or []),
            token_meta=cls._public_token_meta(dict(row.token_meta_json or {})),
            last_error=row.last_error,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class CalendarConnectionsResponse(BaseModel):
    items: list[CalendarConnectionOut]


class CalendarOAuthStartRequest(BaseModel):
    provider: str = Field(pattern="^(google|microsoft)$")


class CalendarOAuthStartResponse(BaseModel):
    provider: str
    auth_url: str
    redirect_uri: str
    state: str
    scopes: list[str] = Field(default_factory=list)


class CalendarOAuthQuickCompleteRequest(BaseModel):
    provider: str = Field(pattern="^(google|microsoft)$")
    code: str
    state: str
    account_ref: Optional[str] = None


class CalendarSyncCursorPatch(BaseModel):
    calendar_ref: Optional[str] = None
    cursor: Optional[str] = None
    cursor_meta: dict[str, Any] = Field(default_factory=dict)


class CalendarSyncCursorOut(BaseModel):
    id: UUID
    connection_id: UUID
    provider: str
    calendar_ref: Optional[str] = None
    cursor: Optional[str] = None
    cursor_meta: dict[str, Any] = Field(default_factory=dict)
    last_synced_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, row: CalendarSyncCursor) -> "CalendarSyncCursorOut":
        return cls(
            id=UUID(row.id),
            connection_id=UUID(row.connection_id),
            provider=row.provider,
            calendar_ref=row.calendar_ref,
            cursor=row.cursor,
            cursor_meta=dict(row.cursor_meta_json or {}),
            last_synced_at=row.last_synced_at,
        )


class CalendarSyncCursorListOut(BaseModel):
    items: list[CalendarSyncCursorOut]


class CalendarReconcileRequest(BaseModel):
    connection_id: Optional[UUID] = None
    provider: Optional[str] = Field(default=None, pattern="^(google|microsoft)$")


class CalendarReconcileResponse(BaseModel):
    queued: int


class CalendarSubscriptionRenewRequest(BaseModel):
    connection_id: Optional[UUID] = None
    provider: Optional[str] = Field(default=None, pattern="^(google|microsoft)$")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _provider_oauth_name(provider: str) -> str:
    p = str(provider or "").strip().lower()
    if p == "google":
        return "gmail"
    if p == "microsoft":
        return "microsoft_graph"
    raise HTTPException(status_code=422, detail=f"Unsupported provider: {provider}")


def _calendar_oauth_secret() -> str:
    return str(settings.jwt_secret or settings.meta_credentials_key or "").strip()


def _sign_state_payload(raw: str) -> str:
    secret = _calendar_oauth_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Calendar OAuth quick-connect is not configured")
    digest = hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def _make_calendar_oauth_state(*, provider: str, tenant_id: str, user_id: str) -> str:
    body = {
        "provider": provider,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "ts": int(time.time()),
    }
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=True)
    b64 = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = _sign_state_payload(raw)
    return f"{b64}.{sig}"


def _verify_calendar_oauth_state(*, state: str, provider: str, tenant_id: str, user_id: str, max_age_sec: int = 1800) -> None:
    try:
        b64, sig = str(state or "").split(".", 1)
    except Exception:
        raise HTTPException(status_code=409, detail="OAuth state is invalid")
    padded = b64 + "=" * (-len(b64) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        payload = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=409, detail="OAuth state is invalid")
    expected_sig = _sign_state_payload(raw)
    if not hmac.compare_digest(expected_sig, sig):
        raise HTTPException(status_code=409, detail="OAuth state mismatch")
    if str(payload.get("provider") or "") != provider:
        raise HTTPException(status_code=409, detail="OAuth provider mismatch")
    if str(payload.get("tenant_id") or "") != tenant_id:
        raise HTTPException(status_code=409, detail="OAuth tenant mismatch")
    if str(payload.get("user_id") or "") != user_id:
        raise HTTPException(status_code=409, detail="OAuth user mismatch")
    ts = int(payload.get("ts") or 0)
    if ts <= 0 or abs(int(time.time()) - ts) > max_age_sec:
        raise HTTPException(status_code=409, detail="OAuth state expired")


def _calendar_oauth_provider_config(provider: str) -> tuple[str, str, list[str]]:
    if provider == "google":
        client_id = str(settings.calendar_google_client_id or "").strip()
        redirect_uri = str(settings.calendar_google_redirect_uri or "").strip()
        scopes = [s for s in str(settings.calendar_google_scopes or "").split() if s.strip()]
        return client_id, redirect_uri, scopes
    if provider == "microsoft":
        client_id = str(settings.calendar_microsoft_client_id or "").strip()
        redirect_uri = str(settings.calendar_microsoft_redirect_uri or "").strip()
        scopes = [s for s in str(settings.calendar_microsoft_scopes or "").split() if s.strip()]
        return client_id, redirect_uri, scopes
    raise HTTPException(status_code=422, detail=f"Unsupported provider: {provider}")


def _calendar_oauth_provider_secret(provider: str) -> str | None:
    if provider == "google":
        return str(settings.calendar_google_client_secret or "").strip() or None
    if provider == "microsoft":
        return str(settings.calendar_microsoft_client_secret or "").strip() or None
    return None


def _build_calendar_auth_url(*, provider: str, client_id: str, redirect_uri: str, scopes: list[str], state: str) -> str:
    if provider == "google":
        qp = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "scope": " ".join(scopes),
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{httpx.QueryParams(qp)}"
    if provider == "microsoft":
        qp = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "response_mode": "query",
            "scope": " ".join(scopes),
            "state": state,
        }
        return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{httpx.QueryParams(qp)}"
    raise HTTPException(status_code=422, detail=f"Unsupported provider: {provider}")


async def _load_calendar_item_or_404(db: AsyncSession, *, tenant_id: str, item_id: str) -> CalendarItem:
    row = await db.execute(
        select(CalendarItem).where(and_(CalendarItem.id == item_id, CalendarItem.tenant_id == tenant_id)).limit(1)
    )
    item = row.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Calendar item not found")
    return item


async def _log_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    calendar_item_id: Optional[str],
    source: str,
    action: str,
    actor_user_id: Optional[str],
    idempotency_key: Optional[str],
    payload: dict[str, Any],
    outcome: dict[str, Any],
) -> None:
    db.add(
        IntegrationActionLog(
            tenant_id=tenant_id,
            calendar_item_id=calendar_item_id,
            source=source,
            action=action,
            actor_user_id=actor_user_id,
            idempotency_key=idempotency_key,
            payload=payload,
            outcome=outcome,
        )
    )


async def _active_calendar_connections(db: AsyncSession, *, tenant_id: str) -> list[CalendarConnection]:
    rows = (
        await db.execute(
            select(CalendarConnection)
            .where(
                and_(
                    CalendarConnection.tenant_id == tenant_id,
                    CalendarConnection.status == "active",
                    CalendarConnection.provider.in_(["google", "microsoft"]),
                )
            )
            .order_by(CalendarConnection.created_at.desc())
        )
    ).scalars().all()
    return rows


async def _sync_item_create_to_provider(
    db: AsyncSession,
    *,
    tenant_id: str,
    item: CalendarItem,
) -> dict[str, Any]:
    report: dict[str, Any] = {"created": [], "errors": []}
    connections = await _active_calendar_connections(db, tenant_id=tenant_id)
    for conn in connections:
        try:
            created = await push_create_event(db, connection=conn, item=item)
            provider_event_id = str(created.get("provider_event_id") or "").strip()
            if not provider_event_id:
                raise CalendarPushError("provider_event_id is missing in create response")
            link = CalendarItemLink(
                tenant_id=tenant_id,
                calendar_item_id=item.id,
                connection_id=conn.id,
                provider=str(conn.provider),
                provider_calendar_id=str(created.get("provider_calendar_id") or "").strip() or None,
                provider_event_id=provider_event_id,
                provider_version=str(created.get("provider_version") or "").strip() or None,
                sync_state="synced",
                payload={"raw": created.get("raw") or {}},
            )
            db.add(link)
            conn.last_error = None
            report["created"].append({"provider": conn.provider, "connection_id": conn.id, "event_id": provider_event_id})
        except Exception as exc:
            conn.last_error = str(exc)
            report["errors"].append({"provider": conn.provider, "connection_id": conn.id, "error": str(exc)})
    return report


async def _sync_item_update_to_provider(
    db: AsyncSession,
    *,
    tenant_id: str,
    item: CalendarItem,
) -> dict[str, Any]:
    report: dict[str, Any] = {"updated": [], "errors": []}
    links = (
        await db.execute(
            select(CalendarItemLink).where(
                and_(
                    CalendarItemLink.tenant_id == tenant_id,
                    CalendarItemLink.calendar_item_id == item.id,
                )
            )
        )
    ).scalars().all()
    if not links:
        return await _sync_item_create_to_provider(db, tenant_id=tenant_id, item=item)
    for link in links:
        conn = await db.get(CalendarConnection, str(link.connection_id)) if link.connection_id else None
        if conn is None or conn.status != "active":
            report["errors"].append(
                {
                    "provider": link.provider,
                    "connection_id": link.connection_id,
                    "error": "active connection not found",
                }
            )
            continue
        try:
            updated = await push_update_event(db, connection=conn, link=link, item=item)
            link.provider_version = str(updated.get("provider_version") or "").strip() or link.provider_version
            link.sync_state = "synced"
            link.payload = {**dict(link.payload or {}), "raw": updated.get("raw") or {}}
            conn.last_error = None
            report["updated"].append(
                {
                    "provider": conn.provider,
                    "connection_id": conn.id,
                    "event_id": link.provider_event_id,
                }
            )
        except Exception as exc:
            link.sync_state = "failed"
            link.payload = {**dict(link.payload or {}), "last_error": str(exc)}
            conn.last_error = str(exc)
            report["errors"].append({"provider": conn.provider, "connection_id": conn.id, "error": str(exc)})
    return report


async def _sync_item_cancel_to_provider(
    db: AsyncSession,
    *,
    tenant_id: str,
    item: CalendarItem,
) -> dict[str, Any]:
    report: dict[str, Any] = {"cancelled": [], "errors": []}
    links = (
        await db.execute(
            select(CalendarItemLink).where(
                and_(
                    CalendarItemLink.tenant_id == tenant_id,
                    CalendarItemLink.calendar_item_id == item.id,
                )
            )
        )
    ).scalars().all()
    for link in links:
        conn = await db.get(CalendarConnection, str(link.connection_id)) if link.connection_id else None
        if conn is None or conn.status != "active":
            report["errors"].append(
                {
                    "provider": link.provider,
                    "connection_id": link.connection_id,
                    "error": "active connection not found",
                }
            )
            continue
        try:
            await push_delete_event(db, connection=conn, link=link)
            link.sync_state = "cancelled"
            conn.last_error = None
            report["cancelled"].append(
                {
                    "provider": conn.provider,
                    "connection_id": conn.id,
                    "event_id": link.provider_event_id,
                }
            )
        except Exception as exc:
            link.sync_state = "failed"
            link.payload = {**dict(link.payload or {}), "last_error": str(exc)}
            conn.last_error = str(exc)
            report["errors"].append({"provider": conn.provider, "connection_id": conn.id, "error": str(exc)})
    return report


@router.get("/items", response_model=CalendarItemsResponse)
async def list_calendar_items(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> CalendarItemsResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    stmt = select(CalendarItem).where(CalendarItem.tenant_id == tenant_id)
    if start is not None:
        stmt = stmt.where(CalendarItem.starts_at >= start)
    if end is not None:
        stmt = stmt.where(CalendarItem.starts_at <= end)
    stmt = stmt.order_by(CalendarItem.starts_at.asc()).limit(500)
    rows = await db.execute(stmt)
    items = rows.scalars().all()
    return CalendarItemsResponse(items=[CalendarItemOut.from_model(x) for x in items])


@router.post("/items", response_model=CalendarItemOut, status_code=status.HTTP_201_CREATED)
async def create_calendar_item(
    body: CalendarItemCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarItemOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    item = CalendarItem(
        tenant_id=tenant_id,
        owner_id=str(current_user.sub),
        assignee_id=str(body.assignee_id) if body.assignee_id else None,
        kind=body.kind,
        status="scheduled",
        title=body.title,
        description=body.description,
        timezone=body.timezone,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        all_day=body.all_day,
        linked_entity_type=body.linked_entity_type,
        linked_entity_id=body.linked_entity_id,
        source="hostflow",
        payload=dict(body.payload or {}),
    )
    db.add(item)
    await db.flush()
    sync_report = await _sync_item_create_to_provider(db, tenant_id=tenant_id, item=item)
    item.payload = {**dict(item.payload or {}), "provider_sync": sync_report}
    await _log_action(
        db,
        tenant_id=tenant_id,
        calendar_item_id=item.id,
        source="hostflow",
        action="create_item",
        actor_user_id=str(current_user.sub),
        idempotency_key=idempotency_key,
        payload=body.model_dump(mode="json"),
        outcome={"status": "created"},
    )
    await db.commit()
    await db.refresh(item)
    return CalendarItemOut.from_model(item)


@router.patch("/items/{item_id}", response_model=CalendarItemOut)
async def patch_calendar_item(
    item_id: UUID,
    body: CalendarItemPatch,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarItemOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    item = await _load_calendar_item_or_404(db, tenant_id=tenant_id, item_id=str(item_id))

    updates = body.model_dump(exclude_unset=True, exclude_none=False)
    for key, value in updates.items():
        if key == "assignee_id":
            setattr(item, key, str(value) if value else None)
        elif key == "payload" and value is not None:
            current_payload = dict(item.payload or {})
            current_payload.update(value)
            item.payload = current_payload
        elif value is not None:
            setattr(item, key, value)

    sync_report = await _sync_item_update_to_provider(db, tenant_id=tenant_id, item=item)
    item.payload = {**dict(item.payload or {}), "provider_sync": sync_report}

    await _log_action(
        db,
        tenant_id=tenant_id,
        calendar_item_id=item.id,
        source="hostflow",
        action="patch_item",
        actor_user_id=str(current_user.sub),
        idempotency_key=idempotency_key,
        payload=body.model_dump(mode="json"),
        outcome={"status": "updated"},
    )
    await db.commit()
    await db.refresh(item)
    return CalendarItemOut.from_model(item)


@router.post("/items/{item_id}/cancel", response_model=CalendarItemOut)
async def cancel_calendar_item(
    item_id: UUID,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarItemOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    item = await _load_calendar_item_or_404(db, tenant_id=tenant_id, item_id=str(item_id))
    item.status = "cancelled"
    payload = dict(item.payload or {})
    payload["cancelled_at"] = _utc_now().isoformat()
    sync_report = await _sync_item_cancel_to_provider(db, tenant_id=tenant_id, item=item)
    payload["provider_sync"] = sync_report
    item.payload = payload
    await _log_action(
        db,
        tenant_id=tenant_id,
        calendar_item_id=item.id,
        source="hostflow",
        action="cancel_item",
        actor_user_id=str(current_user.sub),
        idempotency_key=idempotency_key,
        payload={"item_id": str(item_id)},
        outcome={"status": "cancelled"},
    )
    await db.commit()
    await db.refresh(item)
    return CalendarItemOut.from_model(item)


@router.post("/items/{item_id}/remind", response_model=CalendarItemOut)
async def remind_calendar_item(
    item_id: UUID,
    body: CalendarRemindRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarItemOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    item = await _load_calendar_item_or_404(db, tenant_id=tenant_id, item_id=str(item_id))
    payload = dict(item.payload or {})
    payload["remind_at"] = (body.remind_at or _utc_now()).isoformat()
    payload["remind_channel"] = body.channel
    if body.note:
        payload["remind_note"] = body.note
    item.payload = payload
    await _log_action(
        db,
        tenant_id=tenant_id,
        calendar_item_id=item.id,
        source="hostflow",
        action="remind_item",
        actor_user_id=str(current_user.sub),
        idempotency_key=idempotency_key,
        payload=body.model_dump(mode="json"),
        outcome={"status": "queued"},
    )
    await db.commit()
    await db.refresh(item)
    return CalendarItemOut.from_model(item)


@router.post("/items/{item_id}/assign", response_model=CalendarItemOut)
async def assign_calendar_item(
    item_id: UUID,
    body: CalendarAssignRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarItemOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    item = await _load_calendar_item_or_404(db, tenant_id=tenant_id, item_id=str(item_id))
    item.assignee_id = str(body.assignee_id)
    payload = dict(item.payload or {})
    payload["assignee_note"] = body.note
    item.payload = payload
    await _log_action(
        db,
        tenant_id=tenant_id,
        calendar_item_id=item.id,
        source="hostflow",
        action="assign_item",
        actor_user_id=str(current_user.sub),
        idempotency_key=idempotency_key,
        payload=body.model_dump(mode="json"),
        outcome={"status": "assigned"},
    )
    await db.commit()
    await db.refresh(item)
    return CalendarItemOut.from_model(item)


def _resolve_webhook_tenant(payload: dict[str, Any], tenant_header: Optional[str]) -> str:
    raw = (tenant_header or "").strip()
    if raw:
        return raw
    candidate = payload.get("tenant_id") or payload.get("tenantId") or payload.get("tenant")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)


async def _enqueue_webhook_job(
    db: AsyncSession,
    *,
    source_kind: str,
    payload: dict[str, Any],
    tenant_header: Optional[str],
) -> IntegrationWebhookAck:
    tenant_id = _resolve_webhook_tenant(payload, tenant_header)
    dedupe_key = str(payload.get("event_id") or payload.get("eventId") or payload.get("id") or "")
    job = CalendarSyncJob(
        tenant_id=tenant_id,
        source_kind=source_kind,
        operation="ingest",
        status="queued",
        dedupe_key=dedupe_key or None,
        payload=payload,
    )
    db.add(job)
    await db.flush()
    await db.commit()
    await enqueue_job(
        "calendar_sync_ingest",
        sync_job_id=job.id,
        job_id=f"calendar_sync_ingest:{job.id}",
    )
    return IntegrationWebhookAck(accepted=True, tenant_id=tenant_id, queued_job_id=UUID(job.id))


def _require_slack_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    timestamp_header: Optional[str],
) -> None:
    secret = str(settings.slack_signing_secret or "").strip()
    if not secret:
        return
    ts = str(timestamp_header or "").strip()
    provided = str(signature_header or "").strip()
    if not ts or not provided:
        raise HTTPException(status_code=401, detail="Missing Slack signature headers")
    try:
        # Slack replay window ~5 minutes.
        delta = abs(int(_utc_now().timestamp()) - int(ts))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Slack signature timestamp")
    if delta > 60 * 5:
        raise HTTPException(status_code=401, detail="Slack signature timestamp expired")
    raw = f"v0:{ts}:".encode("utf-8") + (raw_body or b"")
    digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")


def _require_teams_secret(secret_header: Optional[str]) -> None:
    expected = str(settings.teams_webhook_secret or "").strip()
    if not expected:
        return
    got = str(secret_header or "").strip()
    if not got or not hmac.compare_digest(expected, got):
        raise HTTPException(status_code=401, detail="Invalid Teams webhook secret")


@router.get("/integrations/connections", response_model=CalendarConnectionsResponse)
async def list_calendar_connections(
    provider: Optional[str] = Query(None),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> CalendarConnectionsResponse:
    db, tenant_uuid = db_tenant
    stmt = select(CalendarConnection).where(CalendarConnection.tenant_id == str(tenant_uuid))
    if provider:
        stmt = stmt.where(CalendarConnection.provider == provider)
    stmt = stmt.order_by(CalendarConnection.created_at.desc()).limit(200)
    rows = (await db.execute(stmt)).scalars().all()
    return CalendarConnectionsResponse(items=[CalendarConnectionOut.from_model(x) for x in rows])


@router.post("/integrations/oauth/start", response_model=CalendarOAuthStartResponse)
async def start_calendar_oauth_quick_connect(
    body: CalendarOAuthStartRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarOAuthStartResponse:
    _db, tenant_uuid = db_tenant
    provider = str(body.provider or "").strip().lower()
    client_id, redirect_uri, scopes = _calendar_oauth_provider_config(provider)
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail=f"Calendar OAuth quick-connect is not configured for provider: {provider}",
        )
    state = _make_calendar_oauth_state(
        provider=provider,
        tenant_id=str(tenant_uuid),
        user_id=str(current_user.sub),
    )
    auth_url = _build_calendar_auth_url(
        provider=provider,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        state=state,
    )
    return CalendarOAuthStartResponse(
        provider=provider,
        auth_url=auth_url,
        redirect_uri=redirect_uri,
        state=state,
        scopes=scopes,
    )


@router.post(
    "/integrations/connections/oauth/complete/quick",
    response_model=CalendarConnectionOut,
    status_code=status.HTTP_201_CREATED,
)
async def complete_calendar_connection_oauth_quick(
    body: CalendarOAuthQuickCompleteRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarConnectionOut:
    db, tenant_uuid = db_tenant
    provider = str(body.provider or "").strip().lower()
    _verify_calendar_oauth_state(
        state=body.state,
        provider=provider,
        tenant_id=str(tenant_uuid),
        user_id=str(current_user.sub),
    )
    client_id, redirect_uri, scopes = _calendar_oauth_provider_config(provider)
    client_secret = _calendar_oauth_provider_secret(provider)
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail=f"Calendar OAuth quick-connect is not configured for provider: {provider}",
        )
    provider_name = _provider_oauth_name(provider)
    try:
        token_payload = await exchange_oauth_code_for_tokens(
            provider=provider_name,
            code=body.code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )
    except OAuthProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    row = CalendarConnection(
        tenant_id=str(tenant_uuid),
        user_id=str(current_user.sub),
        provider=provider,
        account_ref=body.account_ref,
        status="active",
        scopes_json=scopes,
        token_meta_json={
            "access_token": token_payload.access_token,
            "refresh_token": token_payload.refresh_token,
            "token_type": token_payload.token_type,
            "scope": token_payload.scope,
            "expires_in": token_payload.expires_in,
            "expires_at": (_utc_now().timestamp() + int(token_payload.expires_in or 3600)),
            "id_token": token_payload.id_token,
        },
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return CalendarConnectionOut.from_model(row)


@router.post("/integrations/connections", response_model=CalendarConnectionOut, status_code=status.HTTP_201_CREATED)
async def create_calendar_connection(
    body: CalendarConnectionCreate,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarConnectionOut:
    db, tenant_uuid = db_tenant
    scopes = [x for x in body.scopes if isinstance(x, str) and x.strip()]
    token_meta: dict[str, Any] = {}
    if body.access_token:
        token_meta["access_token"] = body.access_token
    if body.refresh_token:
        token_meta["refresh_token"] = body.refresh_token
    if body.expires_in:
        token_meta["expires_in"] = body.expires_in
        token_meta["expires_at"] = (_utc_now().timestamp() + int(body.expires_in))
    row = CalendarConnection(
        tenant_id=str(tenant_uuid),
        user_id=str(current_user.sub),
        provider=body.provider,
        account_ref=body.account_ref,
        status=body.status,
        scopes_json=scopes,
        token_meta_json=token_meta,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return CalendarConnectionOut.from_model(row)


@router.post("/integrations/connections/oauth/complete", response_model=CalendarConnectionOut, status_code=status.HTTP_201_CREATED)
async def complete_calendar_connection_oauth(
    body: CalendarConnectionOAuthComplete,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CalendarConnectionOut:
    db, tenant_uuid = db_tenant
    provider_name = _provider_oauth_name(body.provider)
    try:
        token_payload = await exchange_oauth_code_for_tokens(
            provider=provider_name,
            code=body.code,
            redirect_uri=body.redirect_uri,
            client_id=body.client_id,
            client_secret=body.client_secret,
        )
    except OAuthProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    row = CalendarConnection(
        tenant_id=str(tenant_uuid),
        user_id=str(current_user.sub),
        provider=body.provider,
        account_ref=body.account_ref,
        status="active",
        scopes_json=body.scopes,
        token_meta_json={
            "access_token": token_payload.access_token,
            "refresh_token": token_payload.refresh_token,
            "token_type": token_payload.token_type,
            "scope": token_payload.scope,
            "expires_in": token_payload.expires_in,
            "expires_at": (_utc_now().timestamp() + int(token_payload.expires_in or 3600)),
            "id_token": token_payload.id_token,
        },
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return CalendarConnectionOut.from_model(row)


@router.post("/integrations/connections/{connection_id}/refresh", response_model=CalendarConnectionOut)
async def refresh_calendar_connection_oauth(
    connection_id: UUID,
    body: CalendarConnectionRefreshRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> CalendarConnectionOut:
    db, tenant_uuid = db_tenant
    row = await db.get(CalendarConnection, str(connection_id))
    if row is None or str(row.tenant_id) != str(tenant_uuid):
        raise HTTPException(status_code=404, detail="Connection not found")
    token_meta = dict(row.token_meta_json or {})
    refresh_token = str(token_meta.get("refresh_token") or "").strip()
    if not refresh_token:
        raise HTTPException(status_code=409, detail="refresh_token is missing for this connection")
    try:
        token_payload = await refresh_oauth_access_token(
            provider=_provider_oauth_name(row.provider),
            refresh_token=refresh_token,
            client_id=body.client_id,
            client_secret=body.client_secret,
            scope=body.scope,
        )
    except OAuthProviderError as exc:
        row.status = "error"
        row.last_error = str(exc)
        await db.commit()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    token_meta["access_token"] = token_payload.access_token
    if token_payload.refresh_token:
        token_meta["refresh_token"] = token_payload.refresh_token
    token_meta["token_type"] = token_payload.token_type
    token_meta["scope"] = token_payload.scope
    token_meta["expires_in"] = token_payload.expires_in
    token_meta["expires_at"] = (_utc_now().timestamp() + int(token_payload.expires_in or 3600))
    row.token_meta_json = token_meta
    row.status = "active"
    row.last_error = None
    await db.commit()
    await db.refresh(row)
    return CalendarConnectionOut.from_model(row)


@router.delete("/integrations/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_calendar_connection(
    connection_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> Response:
    db, tenant_uuid = db_tenant
    row = await db.get(CalendarConnection, str(connection_id))
    if row is None or str(row.tenant_id) != str(tenant_uuid):
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(row)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/integrations/connections/{connection_id}/cursor", response_model=CalendarSyncCursorListOut)
async def get_calendar_connection_cursors(
    connection_id: UUID,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> CalendarSyncCursorListOut:
    db, tenant_uuid = db_tenant
    conn_row = await db.get(CalendarConnection, str(connection_id))
    if conn_row is None or str(conn_row.tenant_id) != str(tenant_uuid):
        raise HTTPException(status_code=404, detail="Connection not found")
    rows = (
        await db.execute(
            select(CalendarSyncCursor)
            .where(CalendarSyncCursor.connection_id == str(connection_id))
            .order_by(CalendarSyncCursor.updated_at.desc())
        )
    ).scalars().all()
    return CalendarSyncCursorListOut(items=[CalendarSyncCursorOut.from_model(x) for x in rows])


@router.patch("/integrations/connections/{connection_id}/cursor", response_model=CalendarSyncCursorOut)
async def patch_calendar_connection_cursor(
    connection_id: UUID,
    body: CalendarSyncCursorPatch,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> CalendarSyncCursorOut:
    db, tenant_uuid = db_tenant
    conn_row = await db.get(CalendarConnection, str(connection_id))
    if conn_row is None or str(conn_row.tenant_id) != str(tenant_uuid):
        raise HTTPException(status_code=404, detail="Connection not found")
    cursor_row = (
        await db.execute(
            select(CalendarSyncCursor).where(
                and_(
                    CalendarSyncCursor.connection_id == str(connection_id),
                    CalendarSyncCursor.calendar_ref == body.calendar_ref,
                )
            )
        )
    ).scalar_one_or_none()
    if cursor_row is None:
        cursor_row = CalendarSyncCursor(
            tenant_id=str(tenant_uuid),
            connection_id=str(connection_id),
            provider=conn_row.provider,
            calendar_ref=body.calendar_ref,
            cursor=body.cursor,
            cursor_meta_json=dict(body.cursor_meta or {}),
            last_synced_at=_utc_now(),
        )
        db.add(cursor_row)
    else:
        cursor_row.cursor = body.cursor
        cursor_row.cursor_meta_json = dict(body.cursor_meta or {})
        cursor_row.last_synced_at = _utc_now()
    await db.commit()
    await db.refresh(cursor_row)
    return CalendarSyncCursorOut.from_model(cursor_row)


@router.post("/integrations/reconcile", response_model=CalendarReconcileResponse)
async def queue_calendar_reconcile(
    body: CalendarReconcileRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> CalendarReconcileResponse:
    db, tenant_uuid = db_tenant
    stmt = select(CalendarConnection).where(
        and_(
            CalendarConnection.tenant_id == str(tenant_uuid),
            CalendarConnection.status == "active",
        )
    )
    if body.connection_id is not None:
        stmt = stmt.where(CalendarConnection.id == str(body.connection_id))
    if body.provider:
        stmt = stmt.where(CalendarConnection.provider == body.provider)
    connections = (await db.execute(stmt)).scalars().all()
    queued = 0
    for conn in connections:
        cursor_row = (
            await db.execute(
                select(CalendarSyncCursor)
                .where(CalendarSyncCursor.connection_id == str(conn.id))
                .order_by(CalendarSyncCursor.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        payload = {
            "tenant_id": str(tenant_uuid),
            "connection_id": str(conn.id),
            "provider": conn.provider,
            "cursor": cursor_row.cursor if cursor_row else None,
            "cursor_meta": dict(cursor_row.cursor_meta_json or {}) if cursor_row else {},
        }
        job = CalendarSyncJob(
            tenant_id=str(tenant_uuid),
            source_kind=f"{conn.provider}_reconcile",
            operation="reconcile",
            status="queued",
            dedupe_key=f"reconcile:{conn.id}:{payload.get('cursor') or ''}",
            payload=payload,
        )
        db.add(job)
        await db.flush()
        await enqueue_job(
            "calendar_sync_ingest",
            sync_job_id=job.id,
            job_id=f"calendar_sync_ingest:{job.id}",
        )
        queued += 1
    await db.commit()
    return CalendarReconcileResponse(queued=queued)


@router.post("/integrations/subscriptions/renew", response_model=CalendarReconcileResponse)
async def queue_calendar_subscription_renew(
    body: CalendarSubscriptionRenewRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
) -> CalendarReconcileResponse:
    db, tenant_uuid = db_tenant
    stmt = select(CalendarConnection).where(
        and_(
            CalendarConnection.tenant_id == str(tenant_uuid),
            CalendarConnection.status == "active",
        )
    )
    if body.connection_id is not None:
        stmt = stmt.where(CalendarConnection.id == str(body.connection_id))
    if body.provider:
        stmt = stmt.where(CalendarConnection.provider == body.provider)
    connections = (await db.execute(stmt)).scalars().all()
    queued = 0
    for conn in connections:
        job = CalendarSyncJob(
            tenant_id=str(tenant_uuid),
            source_kind=f"{conn.provider}_subscription_renew",
            operation="renew_subscription",
            status="queued",
            dedupe_key=f"renew:{conn.id}",
            payload={
                "tenant_id": str(tenant_uuid),
                "connection_id": str(conn.id),
                "provider": conn.provider,
            },
        )
        db.add(job)
        await db.flush()
        await enqueue_job(
            "calendar_sync_ingest",
            sync_job_id=job.id,
            job_id=f"calendar_sync_ingest:{job.id}",
        )
        queued += 1
    await db.commit()
    return CalendarReconcileResponse(queued=queued)


@router.post("/integrations/google/calendar/webhook", response_model=IntegrationWebhookAck, status_code=status.HTTP_202_ACCEPTED)
async def google_calendar_webhook(
    payload: dict[str, Any],
    tenant_header: Optional[str] = Header(None, alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db),
) -> IntegrationWebhookAck:
    return await _enqueue_webhook_job(db, source_kind="google_webhook", payload=payload, tenant_header=tenant_header)


@router.post("/integrations/microsoft/calendar/webhook", response_model=IntegrationWebhookAck, status_code=status.HTTP_202_ACCEPTED)
async def microsoft_calendar_webhook(
    payload: dict[str, Any],
    tenant_header: Optional[str] = Header(None, alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db),
) -> IntegrationWebhookAck:
    return await _enqueue_webhook_job(
        db,
        source_kind="microsoft_webhook",
        payload=payload,
        tenant_header=tenant_header,
    )


@router.post("/integrations/slack/events", response_model=IntegrationWebhookAck, status_code=status.HTTP_202_ACCEPTED)
async def slack_events_webhook(
    request: Request,
    payload: dict[str, Any],
    tenant_header: Optional[str] = Header(None, alias="X-Tenant-Id"),
    slack_signature: Optional[str] = Header(None, alias="X-Slack-Signature"),
    slack_timestamp: Optional[str] = Header(None, alias="X-Slack-Request-Timestamp"),
    db: AsyncSession = Depends(get_db),
) -> IntegrationWebhookAck:
    _require_slack_signature(await request.body(), slack_signature, slack_timestamp)
    return await _enqueue_webhook_job(db, source_kind="slack_event", payload=payload, tenant_header=tenant_header)


@router.post("/integrations/teams/events", response_model=IntegrationWebhookAck, status_code=status.HTTP_202_ACCEPTED)
async def teams_events_webhook(
    payload: dict[str, Any],
    tenant_header: Optional[str] = Header(None, alias="X-Tenant-Id"),
    teams_secret: Optional[str] = Header(None, alias="X-Teams-Webhook-Secret"),
    db: AsyncSession = Depends(get_db),
) -> IntegrationWebhookAck:
    _require_teams_secret(teams_secret)
    return await _enqueue_webhook_job(db, source_kind="teams_event", payload=payload, tenant_header=tenant_header)
