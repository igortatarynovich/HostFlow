"""FlightAdBinding helpers — Ad ID → Flight resolve, write, auto-reprocess."""

from __future__ import annotations

from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.campaign import FlightAdBinding
from backend.app.models.lead import Lead

MISSING_CAMPAIGN_FLIGHT = "missing_campaign_flight"
PROVIDER_META = "meta"
# Batch size only — not a hard ceiling on total waiting leads.
REPROCESS_BATCH_SIZE = 200


def normalize_provider_ad_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def get_active_flight_ad_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    provider_ad_id: str,
) -> Optional[FlightAdBinding]:
    prov = str(provider or "").strip().lower() or PROVIDER_META
    ad = normalize_provider_ad_id(provider_ad_id)
    if not ad:
        return None
    row = await db.execute(
        select(FlightAdBinding).where(
            FlightAdBinding.tenant_id == str(tenant_id),
            FlightAdBinding.provider == prov,
            FlightAdBinding.provider_ad_id == ad,
            FlightAdBinding.is_active.is_(True),
        )
    )
    return row.scalar_one_or_none()


def lead_matches_missing_campaign_flight(lead: Lead) -> bool:
    err = str(getattr(lead, "error", None) or "").strip()
    if err == MISSING_CAMPAIGN_FLIGHT:
        return True
    normalized = getattr(lead, "normalized", None)
    if not isinstance(normalized, dict):
        return False
    stamp = normalized.get("acquisition_routing_v1")
    if not isinstance(stamp, dict):
        return False
    return str(stamp.get("unresolved_reason") or "").strip() == MISSING_CAMPAIGN_FLIGHT


async def list_leads_awaiting_ad_flight(
    db: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    provider_ad_id: str,
    limit: int = REPROCESS_BATCH_SIZE,
    exclude_ids: Optional[Sequence[str]] = None,
) -> list[Lead]:
    """One page of leads eligible for auto-reprocess after Ad→Flight binding commit."""
    prov = str(provider or "").strip().lower() or PROVIDER_META
    ad = normalize_provider_ad_id(provider_ad_id)
    if not ad:
        return []
    ad_int: Optional[int] = None
    try:
        ad_int = int(ad)
    except (TypeError, ValueError):
        ad_int = None

    batch_limit = max(1, int(limit))
    clauses = [
        Lead.tenant_id == str(tenant_id),
        Lead.candidate_id.is_(None),
    ]
    if prov == PROVIDER_META:
        clauses.append(Lead.source == PROVIDER_META)
    if ad_int is not None:
        clauses.append(Lead.ad_id == ad_int)
    excluded = [str(x).strip() for x in (exclude_ids or ()) if str(x).strip()]
    if excluded:
        clauses.append(Lead.id.notin_(excluded))

    # Oversample then filter in Python (reason may live only in normalized JSON).
    fetch_n = min(batch_limit * 5, 2000)
    rows = (
        await db.execute(
            select(Lead)
            .where(*clauses)
            .order_by(Lead.created_at.asc())
            .limit(fetch_n)
        )
    ).scalars().all()

    out: list[Lead] = []
    for lead in rows:
        lead_ad = normalize_provider_ad_id(getattr(lead, "ad_id", None))
        if lead_ad is None:
            normalized = getattr(lead, "normalized", None)
            if isinstance(normalized, dict):
                lead_ad = normalize_provider_ad_id(normalized.get("ad_id"))
        if lead_ad != ad:
            continue
        if not lead_matches_missing_campaign_flight(lead):
            continue
        out.append(lead)
        if len(out) >= batch_limit:
            break
    return out


async def reprocess_leads_for_ad_binding(
    *,
    tenant_id: str,
    provider: str,
    provider_ad_id: str,
    batch_size: int = REPROCESS_BATCH_SIZE,
) -> dict[str, Any]:
    """Idempotent auto-reprocess in separate tenant sessions (post-binding commit).

    Processes waiting leads in batches of ``batch_size`` until none remain.
    Commits after each batch. Per-lead failures use savepoints so one bad lead
    does not roll back the batch; failed ids are skipped for the rest of this run
    so a subsequent trigger can resume safely.
    """
    from backend.app.db.deps import tenant_enforced_session
    from backend.app.modules.leads.service._bulk import reprocess_stored_lead_payload

    tid = str(tenant_id).strip()
    page = max(1, int(batch_size))
    processed = 0
    skipped = 0
    matched = 0
    batches = 0
    errors: list[dict[str, str]] = []
    # Leads attempted in this invocation — skip on later batches so a lead that
    # stays "waiting" after a soft failure cannot infinite-loop this run.
    # A later trigger still picks them up (new exclude set).
    attempted_ids: set[str] = set()

    while True:
        async with tenant_enforced_session(
            UUID(tid),
            actor_id="system:flight_ad_binding_reprocess",
        ) as db:
            batch = await list_leads_awaiting_ad_flight(
                db,
                tenant_id=tid,
                provider=provider,
                provider_ad_id=provider_ad_id,
                limit=page,
                exclude_ids=sorted(attempted_ids),
            )
            if not batch:
                break

            batches += 1
            matched += len(batch)
            for lead in batch:
                lead_id = str(lead.id)
                attempted_ids.add(lead_id)
                if getattr(lead, "candidate_id", None):
                    skipped += 1
                    continue
                try:
                    async with db.begin_nested():
                        await reprocess_stored_lead_payload(
                            db,
                            tenant_id=tid,
                            own_company_id=str(getattr(lead, "own_company_id", None) or "").strip()
                            or None,
                            payload=lead.payload if isinstance(lead.payload, dict) else {},
                            source=str(lead.source or provider or "meta"),
                            force_existing=True,
                            external_id_hint=str(lead.external_id).strip()
                            if lead.external_id
                            else None,
                            prior_normalized=lead.normalized
                            if isinstance(lead.normalized, dict)
                            else None,
                            stored_db_vacancy_id=str(lead.vacancy_id) if lead.vacancy_id else None,
                            stored_db_ad_id=getattr(lead, "ad_id", None),
                            stored_lead_id=lead_id,
                        )
                    processed += 1
                except Exception as exc:  # noqa: BLE001 — isolate per-lead failures
                    errors.append({"lead_id": lead_id, "error": str(exc)[:240]})

            await db.commit()

    return {
        "matched": matched,
        "processed": processed,
        "skipped": skipped,
        "batches": batches,
        "errors": errors,
    }


__all__ = [
    "MISSING_CAMPAIGN_FLIGHT",
    "PROVIDER_META",
    "REPROCESS_BATCH_SIZE",
    "get_active_flight_ad_binding",
    "lead_matches_missing_campaign_flight",
    "list_leads_awaiting_ad_flight",
    "normalize_provider_ad_id",
    "reprocess_leads_for_ad_binding",
]
