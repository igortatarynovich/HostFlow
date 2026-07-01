"""
Optional hourly risk digest email (Phase D) — tenant opt-in via Tenant.settings.risk_model_v1.digest_email.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import OVERVIEW, spa_candidate
from backend.app.core.settings import settings
from backend.app.models.audit import ActivityLog
from backend.app.models.tenant import user_memberships
from backend.app.models.user import User
from backend.app.services.audit import log_activity
from backend.app.services.risk_intel_v1 import list_latest_shadow_snapshot, resolve_risk_config
from backend.app.services.tenant_email import send_email_for_tenant
from backend.app.services.users import ROLE_ALIAS, TENANT_ROLE_VALUES

logger = logging.getLogger(__name__)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _digest_already_sent_for_bucket(db: AsyncSession, tenant_id: str, bucket_iso: str) -> bool:
    if not bucket_iso:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
    rows = (
        await db.execute(
            select(ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "risk_intel.digest_email_sent",
                ActivityLog.created_at >= cutoff,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(24)
        )
    ).all()
    for (payload,) in rows:
        p = payload if isinstance(payload, dict) else {}
        if str(p.get("bucket_start") or "") == bucket_iso:
            return True
    return False


def _normalize_recipients(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        s = str(x).strip()
        if s and "@" in s:
            out.append(s)
    return out


def normalize_digest_roles(raw: Any) -> List[str]:
    """Map tenant config role strings to canonical `user_memberships.role` values."""
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: set[str] = set()
    for x in raw:
        key = str(x).strip().lower().replace(" ", "_")
        if not key:
            continue
        canon = ROLE_ALIAS.get(key)
        if canon is None and key in TENANT_ROLE_VALUES:
            canon = key
        if canon and canon in TENANT_ROLE_VALUES:
            out.add(canon)
    return sorted(out)


def _dedupe_emails_preserve_order(emails: List[str]) -> List[str]:
    seen: set[str] = set()
    out: list[str] = []
    for e in emails:
        s = str(e).strip()
        if not s or "@" not in s:
            continue
        k = s.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


async def emails_for_tenant_roles(
    db: AsyncSession,
    tenant_id: str,
    roles: List[str],
) -> List[str]:
    """Active users with a membership in this tenant and role in `roles` (canonical values)."""
    if not roles:
        return []
    r = await db.execute(
        select(User.email)
        .distinct()
        .join(user_memberships, user_memberships.c.user_id == User.id)
        .where(
            user_memberships.c.tenant_id == tenant_id,
            user_memberships.c.role.in_(roles),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    return [str(row[0]).strip() for row in r.all() if row[0]]


def _build_digest_body(
    *,
    tenant_id: str,
    snap: dict[str, Any],
    min_band: str,
    frontend_base: Optional[str],
) -> str:
    lines: list[str] = [
        "HostFlow — hourly risk digest (shadow cohort)",
        f"Tenant ID: {tenant_id}",
        f"Bucket (UTC): {snap.get('bucket_start') or '—'}",
        f"Scored at: {snap.get('scored_at') or '—'}",
        f"Model: {snap.get('risk_version') or 'risk_model_v1'}",
        f"Threshold band: {min_band}+",
        f"Matching candidates (in bucket): {snap.get('total_matching', 0)}",
        "",
    ]
    note = snap.get("note")
    if note:
        lines.append(str(note))
        lines.append("")

    items = snap.get("items") or []
    if not items:
        lines.append("No rows in the top list for this run.")
    else:
        lines.append("Top candidates (by score):")
        lines.append("")
        base = (frontend_base or "").rstrip("/")
        for i, it in enumerate(items, start=1):
            eid = str(it.get("entity_id") or "")
            label = (it.get("display_name") or "").strip() or (f"#{it.get('short_id')}" if it.get("short_id") else eid[:8])
            score = it.get("score")
            band = it.get("band")
            stg = it.get("stage_at_score") or "—"
            drivers = it.get("drivers") or []
            dr = "; ".join(str(d) for d in drivers[:3]) if drivers else "—"
            card = f"{base}{spa_candidate(eid)}" if base and eid else (eid or "—")
            lines.append(f"{i}. {label}")
            lines.append(f"   Score: {score} · Band: {band} · Stage @ score: {stg}")
            lines.append(f"   Drivers: {dr}")
            lines.append(f"   Open: {card}")
            lines.append("")

    if base := (frontend_base or "").rstrip("/"):
        lines.append(f"Overview: {base}{OVERVIEW}")
    lines.append("")
    lines.append("—")
    lines.append("To change this digest: Tenant.settings.risk_model_v1.digest_email")
    return "\n".join(lines)


async def maybe_send_risk_shadow_digest_email(
    db: AsyncSession,
    *,
    tenant_id: str,
    tenant_settings: dict[str, Any] | None,
    bucket_start: datetime,
) -> dict[str, Any]:
    """
    After hourly persist: optionally email shadow snapshot to configured addresses.
    Deduped per tenant + bucket_start (ActivityLog).
    """
    merged = resolve_risk_config(tenant_settings if isinstance(tenant_settings, dict) else {})
    de = merged.get("digest_email")
    if not isinstance(de, dict) or de.get("enabled") is not True:
        return {"skipped": True, "reason": "disabled"}

    explicit = _normalize_recipients(de.get("to"))
    roles_canon = normalize_digest_roles(de.get("to_roles"))
    from_roles = await emails_for_tenant_roles(db, tenant_id, roles_canon)
    recipients = _dedupe_emails_preserve_order([*explicit, *from_roles])
    if not recipients:
        return {"skipped": True, "reason": "no_recipients"}

    bs = _utc(bucket_start) or bucket_start
    bucket_iso = bs.isoformat() if bs else ""

    if await _digest_already_sent_for_bucket(db, tenant_id, bucket_iso):
        return {"skipped": True, "reason": "already_sent", "bucket_start": bucket_iso}

    min_band = str(de.get("min_band") or "high")
    max_rows = max(1, min(int(de.get("max_rows") or 25), 200))
    skip_if_empty = de.get("skip_if_empty", True) is not False

    snap = await list_latest_shadow_snapshot(db, tenant_id, limit=max_rows, min_band=min_band)
    total = int(snap.get("total_matching") or 0)
    if skip_if_empty and total == 0:
        return {"skipped": True, "reason": "empty_cohort", "bucket_start": bucket_iso}

    frontend = getattr(settings, "frontend_url", None)
    if isinstance(frontend, str):
        frontend = frontend.strip() or None
    body = _build_digest_body(
        tenant_id=tenant_id,
        snap=snap,
        min_band=min_band,
        frontend_base=frontend,
    )
    subject = f"[HostFlow] Risk digest: {total} candidate(s) at {min_band}+ risk (hourly)"

    sent = 0
    errors = 0
    for to_addr in recipients:
        try:
            await send_email_for_tenant(db, tenant_id=tenant_id, to=to_addr, subject=subject, body=body)
            sent += 1
        except Exception:
            errors += 1
            logger.exception(
                "risk digest email failed tenant=%s to=%s bucket=%s",
                tenant_id,
                to_addr,
                bucket_iso,
            )

    if sent > 0:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=None,
            action="risk_intel.digest_email_sent",
            target_type="tenant",
            target_id=tenant_id,
            payload={
                "bucket_start": bucket_iso,
                "recipient_count": sent,
                "total_matching": total,
                "min_band": min_band,
                "to_roles": roles_canon,
                "explicit_recipient_count": len(explicit),
                "role_recipient_count": len(from_roles),
            },
        )

    return {
        "sent": sent,
        "errors": errors,
        "bucket_start": bucket_iso,
        "total_matching": total,
        "recipients_attempted": len(recipients),
        "to_roles": roles_canon,
        "explicit_recipient_count": len(explicit),
        "role_recipient_count": len(from_roles),
    }
