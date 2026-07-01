"""Resolve which tenant owns Meta Leads rows (credentials, settings, mapping) for API requests."""

from __future__ import annotations

from backend.app.auth.deps import Role, UserCtx
from backend.app.constants.hostflow_canonical_tenants import FOCUS_PERSONNEL_TENANT_ID
from backend.app.core.settings import settings
from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID

_META_LEADS_OPS_DISABLE = frozenset({"off", "disable", "none", "false", "0"})


def resolve_meta_leads_effective_tenant_id(ctx: UserCtx, header_tenant_id: str) -> str:
    """
    Platform superadmin often stays on the bootstrap tenant (legacy default UUID) for global UI.
    Meta for HostFlow ops is stored on Focus Personnel by default (canonical UUID in code).

    - Unset ``META_LEADS_OPERATIONAL_TENANT_ID`` → use ``FOCUS_PERSONNEL_TENANT_ID``.
    - Set to another UUID → use that tenant instead.
    - Set to ``off`` / ``disable`` / ``none`` / ``false`` / ``0`` → no remap (for forks).
    """
    raw = (header_tenant_id or "").strip() or str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
    raw_setting = getattr(settings, "meta_leads_operational_tenant_id", None)
    configured = "" if raw_setting is None else str(raw_setting).strip()
    if configured.lower() in _META_LEADS_OPS_DISABLE:
        return raw
    operational = configured or FOCUS_PERSONNEL_TENANT_ID
    role = str(ctx.role or "").strip().lower()
    if role != Role.superadmin.value:
        return raw
    if raw != str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID):
        return raw
    return operational
