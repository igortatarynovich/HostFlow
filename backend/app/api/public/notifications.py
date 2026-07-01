"""
Public API for candidate notifications
Allows candidates to subscribe to email/push notifications about their application status
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.services import user_notifications
from backend.app.services.notifications import notify

router = APIRouter(prefix="/public/notifications", tags=["public-notifications"])


class NotificationSubscriptionRequest(BaseModel):
    token: str = Field(..., description="Candidate intake token")
    email: Optional[EmailStr] = Field(None, description="Email for notifications")
    phone: Optional[str] = Field(None, description="Phone for SMS notifications")
    subscribe_document_status: bool = Field(True, description="Subscribe to document status changes")
    subscribe_stage_changes: bool = Field(True, description="Subscribe to stage changes")
    subscribe_reminders: bool = Field(True, description="Subscribe to reminders")


class NotificationSubscriptionResponse(BaseModel):
    subscribed: bool
    channels: list[str] = Field(default_factory=list)
    message: str


class NotificationUnsubscribeRequest(BaseModel):
    token: str = Field(..., description="Candidate intake token")
    channel: Optional[str] = Field(None, description="Channel to unsubscribe from (email/phone/push/all)")


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(..., description="P256DH public key")
    auth: str = Field(..., description="Auth secret")


class PushSubscriptionRequest(BaseModel):
    token: str = Field(..., description="Candidate intake token")
    endpoint: str = Field(..., description="Push subscription endpoint")
    keys: PushSubscriptionKeys = Field(..., description="Push subscription keys")


async def _load_candidate_by_token(
    db: AsyncSession, tenant_id: UUID, token: str
) -> Candidate:
    """Load candidate by intake token"""
    from sqlalchemy import select
    stmt = select(Candidate).where(
        Candidate.intake_token == token,
        Candidate.tenant_id == str(tenant_id),
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid token or candidate not found",
        )
    return candidate


@router.post("/subscribe", response_model=NotificationSubscriptionResponse)
async def subscribe_to_notifications(
    payload: NotificationSubscriptionRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> NotificationSubscriptionResponse:
    """
    Subscribe candidate to notifications about their application status.
    Supports email and phone (SMS) channels.
    """
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, payload.token)

    # Update candidate's notification preferences
    if not candidate.intake_state:
        candidate.intake_state = {}

    notification_prefs = candidate.intake_state.get("notifications", {})
    
    channels = []
    if payload.email:
        notification_prefs["email"] = payload.email
        notification_prefs["email_subscribed"] = True
        channels.append("email")
        # Update candidate email if not set
        if not candidate.email:
            candidate.email = payload.email

    if payload.phone:
        notification_prefs["phone"] = payload.phone
        notification_prefs["phone_subscribed"] = True
        channels.append("phone")
        # Update candidate phone if not set
        if not candidate.phone:
            candidate.phone = payload.phone

    notification_prefs["subscribe_document_status"] = payload.subscribe_document_status
    notification_prefs["subscribe_stage_changes"] = payload.subscribe_stage_changes
    notification_prefs["subscribe_reminders"] = payload.subscribe_reminders
    notification_prefs["subscribed_at"] = datetime.now(timezone.utc).isoformat()

    candidate.intake_state["notifications"] = notification_prefs
    await db.commit()

    return NotificationSubscriptionResponse(
        subscribed=True,
        channels=channels,
        message="Successfully subscribed to notifications",
    )


@router.post("/unsubscribe", response_model=NotificationSubscriptionResponse)
async def unsubscribe_from_notifications(
    payload: NotificationUnsubscribeRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> NotificationSubscriptionResponse:
    """
    Unsubscribe candidate from notifications.
    """
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, payload.token)

    if not candidate.intake_state:
        candidate.intake_state = {}

    notification_prefs = candidate.intake_state.get("notifications", {})

    if payload.channel == "all" or not payload.channel:
        notification_prefs["email_subscribed"] = False
        notification_prefs["phone_subscribed"] = False
        notification_prefs["push_subscribed"] = False
        notification_prefs["push_subscription"] = None
        notification_prefs["subscribe_document_status"] = False
        notification_prefs["subscribe_stage_changes"] = False
        notification_prefs["subscribe_reminders"] = False
    elif payload.channel == "email":
        notification_prefs["email_subscribed"] = False
    elif payload.channel == "phone":
        notification_prefs["phone_subscribed"] = False
    elif payload.channel == "push":
        notification_prefs["push_subscribed"] = False
        notification_prefs["push_subscription"] = None

    candidate.intake_state["notifications"] = notification_prefs
    await db.commit()

    return NotificationSubscriptionResponse(
        subscribed=False,
        channels=[],
        message="Successfully unsubscribed from notifications",
    )


@router.post("/push/subscribe", response_model=NotificationSubscriptionResponse)
async def subscribe_to_push_notifications(
    payload: PushSubscriptionRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> NotificationSubscriptionResponse:
    """
    Subscribe candidate to push notifications.
    Stores push subscription data for sending notifications later.
    """
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, payload.token)

    if not candidate.intake_state:
        candidate.intake_state = {}

    notification_prefs = candidate.intake_state.get("notifications", {})
    
    # Store push subscription
    notification_prefs["push_subscribed"] = True
    notification_prefs["push_subscription"] = {
        "endpoint": payload.endpoint,
        "keys": {
            "p256dh": payload.keys.p256dh,
            "auth": payload.keys.auth,
        },
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
    }

    candidate.intake_state["notifications"] = notification_prefs
    await db.commit()

    return NotificationSubscriptionResponse(
        subscribed=True,
        channels=["push"],
        message="Successfully subscribed to push notifications",
    )


@router.post("/push/unsubscribe", response_model=NotificationSubscriptionResponse)
async def unsubscribe_from_push_notifications(
    payload: NotificationUnsubscribeRequest,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> NotificationSubscriptionResponse:
    """
    Unsubscribe candidate from push notifications.
    """
    db, tenant_id = db_tenant
    candidate = await _load_candidate_by_token(db, tenant_id, payload.token)

    if not candidate.intake_state:
        candidate.intake_state = {}

    notification_prefs = candidate.intake_state.get("notifications", {})
    notification_prefs["push_subscribed"] = False
    notification_prefs["push_subscription"] = None

    candidate.intake_state["notifications"] = notification_prefs
    await db.commit()

    return NotificationSubscriptionResponse(
        subscribed=False,
        channels=[],
        message="Successfully unsubscribed from push notifications",
    )


@router.get("/push/vapid-key")
async def get_vapid_public_key() -> dict:
    """
    Get VAPID public key for push notification subscription.
    The frontend needs this to subscribe to push notifications.
    """
    # Get VAPID public key from environment or config
    # For now, return a placeholder - should be configured in production
    vapid_public_key = os.getenv("VAPID_PUBLIC_KEY", "")
    
    if not vapid_public_key:
        # Return empty key - push notifications will be disabled
        return {"publicKey": ""}
    
    return {"publicKey": vapid_public_key}


# Export function for use in other modules
async def send_push_notification(
    db: AsyncSession,
    candidate: Candidate,
    title: str,
    body: str,
    *,
    url: Optional[str] = None,
    data: Optional[dict] = None,
) -> bool:
    """
    Send push notification to candidate.
    Returns True if sent successfully, False otherwise.
    
    Note: Currently sends via webhook. In production, implement direct Web Push Protocol
    using libraries like pywebpush or py-vapid with VAPID keys.
    """
    if not candidate.intake_state:
        return False

    notification_prefs = candidate.intake_state.get("notifications", {})
    push_subscription_data = notification_prefs.get("push_subscription")

    if not push_subscription_data or not notification_prefs.get("push_subscribed"):
        return False

    # Send push notification via webhook
    # The webhook service should handle Web Push Protocol delivery
    try:
        await notify(
            to=push_subscription_data.get("endpoint", ""),
            subject=title,
            text=body,
            template_key="push.notification",
            template_context={
                "title": title,
                "body": body,
                "url": url or "/public",
                "data": data or {},
                "subscription": push_subscription_data,  # Include full subscription for webhook
            },
            channels=["webhook"],  # Webhook will handle push delivery
        )
        return True
    except Exception:
        return False


async def send_candidate_notification(
    db: AsyncSession,
    candidate: Candidate,
    event_type: str,
    subject: str,
    message: str,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """
    Send notification to candidate via their preferred channels.
    This function is called from other parts of the system when events occur.
    """
    if not candidate.intake_state:
        return

    notification_prefs = candidate.intake_state.get("notifications", {})
    
    # Check if candidate is subscribed to any channel
    if (
        not notification_prefs.get("email_subscribed")
        and not notification_prefs.get("phone_subscribed")
        and not notification_prefs.get("push_subscribed")
    ):
        return

    # Determine which events candidate wants to receive
    if event_type.startswith("document.") and not notification_prefs.get("subscribe_document_status", True):
        return
    if event_type.startswith("stage.") and not notification_prefs.get("subscribe_stage_changes", True):
        return
    if event_type.startswith("reminder.") and not notification_prefs.get("subscribe_reminders", True):
        return

    channels = []
    email = notification_prefs.get("email") or candidate.email
    phone = notification_prefs.get("phone") or candidate.phone

    if email and notification_prefs.get("email_subscribed"):
        channels.append("email")
        try:
            await notify(
                to=email,
                subject=subject,
                text=message,
                template_key=f"candidate.{event_type}",
                template_context={
                    "candidate_name": candidate.full_name or "Candidate",
                    "candidate_id": str(candidate.id),
                    **(payload or {}),
                },
                channels=["email"],
            )
        except Exception:
            # Log error but don't fail
            pass

    if phone and notification_prefs.get("phone_subscribed"):
        channels.append("phone")
        try:
            await notify(
                to=phone,
                subject=subject,
                text=message,
                template_key=f"candidate.{event_type}",
                template_context={
                    "candidate_name": candidate.full_name or "Candidate",
                    "candidate_id": str(candidate.id),
                    **(payload or {}),
                },
                channels=["phone"],
            )
        except Exception:
            # Log error but don't fail
            pass

    # Send push notification if subscribed
    if notification_prefs.get("push_subscribed"):
        try:
            # Build notification URL
            notification_url = None
            if entity_type and entity_id:
                if entity_type == "document":
                    # Link to status page with document highlight
                    notification_url = f"/public/status/{candidate.status_share_token or candidate.intake_token}?highlight={entity_id}"
                else:
                    notification_url = f"/public/status/{candidate.status_share_token or candidate.intake_token}"

            await send_push_notification(
                db,
                candidate,
                subject,
                message,
                url=notification_url,
                data={
                    "event_type": event_type,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    **(payload or {}),
                },
            )
        except Exception:
            # Log error but don't fail
            pass

    # Also create in-app notification if candidate has user account
    # (for future use when candidates can log in)
    if entity_type and entity_id:
        try:
            await user_notifications.create_notification(
                db,
                tenant_id=candidate.tenant_id,
                user_id=str(candidate.id),  # Using candidate_id as user_id for now
                event_type=event_type,
                payload=payload or {},
                entity_type=entity_type,
                entity_id=entity_id,
                channel="in_app",
            )
        except Exception:
            # Ignore errors for in-app notifications
            pass

