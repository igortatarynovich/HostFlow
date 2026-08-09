"""Dossier zones: recruitment vs internal HR vs client, plus per-user shares."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from backend.app.auth.deps import Role, UserCtx
from backend.app.auth.trust_roles import (
    TrustRole,
    is_hr_workspace_actor,
    is_portal_actor,
    is_team_lead_org_actor,
    normalize_trust_role,
)
from backend.app.models.document import Document
from backend.app.models.document_dossier_share import DocumentDossierShare

# Product-level visibility (dossier zone + optional share). Not a transport or numeric error code.
DOSSIER_VISIBILITY_ERROR_CODE = "DOSSIER_ZONE_OR_SHARE_REQUIRED"


def dossier_visibility_denied_detail() -> Dict[str, Any]:
    """Structured 403 body: machine reason + human-readable copy in UI locales (en/ru/pl)."""
    messages = {
        "en": (
            "You cannot open this document under the current account. "
            "It may be stored in another dossier zone (for example internal HR or client-only files), "
            "or a colleague must grant you access via a dossier share."
        ),
        "ru": (
            "У вас нет доступа к этому документу с текущей учётной записью. "
            "Он может находиться в другой зоне досье (например, внутренний кадровый контур или зона клиента), "
            "либо коллега должен выдать вам доступ через общий доступ к досье (dossier share)."
        ),
        "pl": (
            "Nie masz dostępu do tego dokumentu na tym koncie. "
            "Może on znajdować się w innej strefie akt (np. HR wewnętrzny lub pliki tylko dla klienta), "
            "albo współpracownik musi udzielić Ci dostępu przez udostępnienie akt (dossier share)."
        ),
    }
    return {
        "code": DOSSIER_VISIBILITY_ERROR_CODE,
        "constraint": "dossier_visibility",
        "message": messages["en"],
        "messages": messages,
    }

ZONE_RECRUITMENT = "recruitment"
ZONE_INTERNAL_HR = "internal_hr"
ZONE_CLIENT = "client"

ALL_ZONES: tuple[str, ...] = (ZONE_RECRUITMENT, ZONE_INTERNAL_HR, ZONE_CLIENT)


def normalize_dossier_zone(value: Optional[str]) -> str:
    v = (value or "").strip() or ZONE_RECRUITMENT
    if v not in ALL_ZONES:
        raise ValueError(f"Invalid dossier_zone: {value!r}")
    return v


def allowed_zones_for_role(role: str, *, access_context: str | None = None) -> Set[str]:
    """Which zones a user may see when listing/downloading documents."""
    r = (role or "").strip().lower()
    trust = normalize_trust_role(r)
    if trust in {TrustRole.administrator.value, TrustRole.superadmin.value} or is_team_lead_org_actor(r):
        return set(ALL_ZONES)
    if is_hr_workspace_actor(r):
        return {ZONE_RECRUITMENT, ZONE_INTERNAL_HR}
    if is_portal_actor(r, access_context):
        return {ZONE_CLIENT}
    if trust == TrustRole.employee.value or r in {
        Role.recruiter.value,
        Role.compliance_officer.value,
    }:
        return {ZONE_RECRUITMENT}
    return {ZONE_RECRUITMENT}


def default_zone_for_creator(role: str, *, client_tenant: bool) -> str:
    if client_tenant:
        return ZONE_CLIENT
    r = (role or "").strip().lower()
    if is_hr_workspace_actor(r):
        return ZONE_INTERNAL_HR
    return ZONE_RECRUITMENT


def can_assign_zone_on_create(role: str, zone: str, *, client_tenant: bool) -> bool:
    if client_tenant:
        return zone == ZONE_CLIENT
    r = (role or "").strip().lower()
    allowed = allowed_zones_for_role(r)
    return zone in allowed


def can_assign_zone_on_patch(role: str, new_zone: str, *, client_tenant: bool) -> bool:
    return can_assign_zone_on_create(role, new_zone, client_tenant=client_tenant)


def dossier_list_condition(user: UserCtx) -> ColumnElement[bool]:
    """SQL: document visible by zone membership or active share to this user."""
    zones = allowed_zones_for_role(
        user.role,
        access_context=getattr(user, "access_context", None),
    )
    now = datetime.now(timezone.utc)
    share_sq = (
        select(1)
        .select_from(DocumentDossierShare)
        .where(
            DocumentDossierShare.document_id == Document.id,
            DocumentDossierShare.tenant_id == Document.tenant_id,
            DocumentDossierShare.grantee_user_id == user.sub,
            or_(
                DocumentDossierShare.expires_at.is_(None),
                DocumentDossierShare.expires_at > now,
            ),
        )
        .exists()
    )
    return or_(Document.dossier_zone.in_(list(zones)), share_sq)


async def user_can_view_document(
    db: AsyncSession,
    user: UserCtx,
    doc: Document,
) -> bool:
    zone = getattr(doc, "dossier_zone", None) or ZONE_RECRUITMENT
    if zone in allowed_zones_for_role(
        user.role,
        access_context=getattr(user, "access_context", None),
    ):
        return True
    now = datetime.now(timezone.utc)
    row = await db.scalar(
        select(DocumentDossierShare.id).where(
            DocumentDossierShare.document_id == doc.id,
            DocumentDossierShare.tenant_id == doc.tenant_id,
            DocumentDossierShare.grantee_user_id == user.sub,
            or_(
                DocumentDossierShare.expires_at.is_(None),
                DocumentDossierShare.expires_at > now,
            ),
        )
    )
    return row is not None
