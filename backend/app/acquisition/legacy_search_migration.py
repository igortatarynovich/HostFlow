"""Legacy Search (Vacancy acquisition) → Campaign + Flight backfill.

PR-A only: data migration. Does not remove Searches UI.
Idempotency is stamp-only (no Activity Timeline marker events).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition import binding_service, campaign_service
from backend.app.acquisition.flights.runtime_commands import execute_flight_command
from backend.app.auth.deps import UserCtx
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.campaign import Campaign
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import MetaAdsMap
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.models.vacancy import Vacancy
from backend.app.services.search_acquisition_service import (
    ACQUISITION_EXTRA_KEY,
    STATIC_ACTIVITY_IDS,
    _loads_extra,
    _migrate_stored_activities,
)

logger = logging.getLogger(__name__)


def _ensure_campaign_form_fk_metadata() -> None:
    """Register ``tenant_lead_forms`` on Campaign MetaData (dual-Base import guard).

    Under ``app.*`` / ``backend.app.*`` dual import, ``TenantLeadForm`` may live on a
    different SQLAlchemy ``MetaData`` than ``CampaignRunForm``. Flush then fails with
    ``NoReferencedTableError``. Copy the table into the Campaign metadata when missing.
    """
    from backend.app.models.campaign import CampaignRunForm
    from backend.app.models.tenant_lead_form import TenantLeadForm

    meta = CampaignRunForm.metadata
    if "tenant_lead_forms" in meta.tables:
        return
    TenantLeadForm.__table__.to_metadata(meta)


_ensure_campaign_form_fk_metadata()

SCRIPT_VERSION = "legacy_search_migration_v1"
STAMP_KEY = "legacy_search_migration_v1"
GOAL_TYPE = "hiring"
PRIMARY_KPI = "applications"
ROUTE_INTENT = "candidate_application"
TARGET_TYPE = "vacancy"

DesiredState = Literal["draft", "active", "paused", "completed"]
RowOutcome = Literal[
    "migrated",
    "already_existed",
    "already_existed_rolled_back",
    "skipped",
    "needs_manual",
    "error",
    "rolled_back",
]


def idempotency_key(tenant_id: str, vacancy_id: str) -> str:
    return f"legacy.search.migrate:{tenant_id}:{vacancy_id}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def system_migration_ctx(tenant_id: str) -> UserCtx:
    return UserCtx(
        sub="legacy_search_migration",
        email="migration@hostflow.local",
        role="administrator",
        tenant_id=str(tenant_id),
        supervisor_id=None,
        raw={"source": SCRIPT_VERSION},
    )


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def vacancy_extra_dict(vacancy: Vacancy) -> dict[str, Any]:
    return _loads_extra(getattr(vacancy, "extra", None))


def get_stamp(extra: dict[str, Any]) -> dict[str, Any] | None:
    raw = extra.get(STAMP_KEY)
    if isinstance(raw, dict) and raw.get("campaign_id"):
        return dict(raw)
    return None


def write_vacancy_extra(vacancy: Vacancy, extra: dict[str, Any]) -> None:
    vacancy.extra = json.dumps(extra, ensure_ascii=False)


def acquisition_block(extra: dict[str, Any]) -> dict[str, Any]:
    block = extra.get(ACQUISITION_EXTRA_KEY)
    return _as_dict(block)


def non_static_activities(extra: dict[str, Any], vacancy_id: str) -> list[dict[str, Any]]:
    block = acquisition_block(extra)
    acts = _migrate_stored_activities(block, str(vacancy_id))
    out: list[dict[str, Any]] = []
    for act in acts:
        if not isinstance(act, dict):
            continue
        aid = str(act.get("id") or "")
        if aid in STATIC_ACTIVITY_IDS:
            continue
        out.append(act)
    return out


def acquisition_signals(
    *,
    extra: dict[str, Any],
    vacancy_id: str,
    has_meta_ads: bool,
) -> list[str]:
    signals: list[str] = []
    if str(extra.get("lead_form_id") or "").strip():
        signals.append("lead_form_id")
    if str(extra.get("lead_form_slug") or "").strip():
        signals.append("lead_form_slug")
    if extra.get("launch_search") is True:
        signals.append("launch_search")
    if str(extra.get("setup_source") or "").strip().lower() == "launch_search":
        signals.append("setup_source_launch_search")
    if non_static_activities(extra, vacancy_id):
        signals.append("acquisition_v1_non_static_activity")
    if has_meta_ads:
        signals.append("meta_ads_map")
    return signals


def is_eligible(*, signals: Sequence[str]) -> bool:
    return bool(signals)


def derive_desired_state(vacancy: Vacancy, extra: dict[str, Any]) -> DesiredState:
    status = str(getattr(vacancy, "status", "") or "").strip().lower()
    if bool(getattr(vacancy, "is_archived", False)) or status in {
        "closed",
        "filled",
        "cancelled",
    }:
        return "completed"
    if status in {"on_hold", "paused"}:
        return "paused"

    acts = non_static_activities(extra, str(vacancy.id))
    if acts:
        lifecycles = [str(a.get("lifecycle") or "").strip().lower() for a in acts]
        statuses = [str(a.get("status") or "").strip().lower() for a in acts]
        if any(x == "active" for x in lifecycles) or any(x == "active" for x in statuses):
            return "active"
        if any(x == "paused" for x in lifecycles) or any(x == "paused" for x in statuses):
            return "paused"
        if lifecycles and all(x in {"", "archived"} for x in lifecycles) and any(
            x == "archived" for x in lifecycles
        ):
            return "completed"
        if all(x in {"", "draft", "needs_attention"} for x in statuses):
            return "draft"

    if status == "open":
        return "active" if bool(getattr(vacancy, "is_active", True)) else "draft"
    return "draft"


def campaign_name_for_vacancy(vacancy: Vacancy) -> str:
    title = str(getattr(vacancy, "title", "") or "").strip()
    if title:
        return title
    short = str(vacancy.id)[:8]
    return f"Подбор {short}"


@dataclass
class MigrationRow:
    tenant_id: str
    vacancy_id: str
    own_company_id: str | None
    title: str
    signals: list[str] = field(default_factory=list)
    desired_state: DesiredState | None = None
    outcome: RowOutcome = "skipped"
    campaign_id: str | None = None
    flight_id: str | None = None
    form_id: str | None = None
    intake_source_profile_id: str | None = None
    manual_reasons: list[str] = field(default_factory=list)
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MigrationReport:
    script_version: str
    mode: str
    found: int = 0
    migrated: int = 0
    already_existed: int = 0
    already_existed_rolled_back: int = 0
    skipped: int = 0
    needs_manual: int = 0
    rolled_back: int = 0
    errors: int = 0
    rows: list[MigrationRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "script_version": self.script_version,
            "mode": self.mode,
            "summary": {
                "found": self.found,
                "migrated": self.migrated,
                "already_existed": self.already_existed,
                "already_existed_rolled_back": self.already_existed_rolled_back,
                "skipped": self.skipped,
                "needs_manual": self.needs_manual,
                "rolled_back": self.rolled_back,
                "errors": self.errors,
            },
            "rows": [r.to_dict() for r in self.rows],
        }

    def _count(self, outcome: RowOutcome) -> None:
        if outcome == "migrated":
            self.migrated += 1
        elif outcome == "already_existed":
            self.already_existed += 1
        elif outcome == "already_existed_rolled_back":
            self.already_existed_rolled_back += 1
        elif outcome == "skipped":
            self.skipped += 1
        elif outcome == "needs_manual":
            self.needs_manual += 1
        elif outcome == "rolled_back":
            self.rolled_back += 1
        elif outcome == "error":
            self.errors += 1


async def _meta_ads_vacancy_ids(
    db: AsyncSession, *, tenant_id: str | None, vacancy_id: str | None
) -> set[str]:
    stmt = select(MetaAdsMap.vacancy_id, MetaAdsMap.tenant_id)
    if tenant_id:
        stmt = stmt.where(MetaAdsMap.tenant_id == str(tenant_id))
    if vacancy_id:
        stmt = stmt.where(MetaAdsMap.vacancy_id == str(vacancy_id))
    rows = (await db.execute(stmt)).all()
    return {str(vid) for vid, _tid in rows if vid}


def _extract_meta_form_keys(activities: Sequence[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    for act in activities:
        provider = _as_dict(act.get("provider"))
        meta = _as_dict(provider.get("meta"))
        for field_name in ("form_id", "lead_form_id", "meta_form_id"):
            val = str(meta.get(field_name) or act.get(field_name) or "").strip()
            if val and val not in keys:
                keys.append(val)
    return keys


async def resolve_meta_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    activities: Sequence[dict[str, Any]],
    has_meta_signal: bool,
) -> tuple[str | None, list[str]]:
    """Return (profile_id, manual_reasons). Ambiguous Meta → no binding."""
    manual: list[str] = []
    if not has_meta_signal and not any(
        str(a.get("channel_type") or a.get("type") or "").lower() == "meta" for a in activities
    ):
        return None, manual

    form_keys = _extract_meta_form_keys(activities)
    candidates: list[str] = []

    if form_keys:
        stmt = (
            select(IntakeSourceProfile.id)
            .join(
                IntakeSourceBinding,
                IntakeSourceBinding.intake_source_profile_id == IntakeSourceProfile.id,
            )
            .where(
                IntakeSourceProfile.tenant_id == tenant_id,
                IntakeSourceProfile.own_company_id == own_company_id,
                IntakeSourceProfile.is_active.is_(True),
                IntakeSourceProfile.provider == "meta",
                IntakeSourceProfile.route_intent == ROUTE_INTENT,
                IntakeSourceBinding.provider == "meta",
                IntakeSourceBinding.is_active.is_(True),
                IntakeSourceBinding.external_key.in_(form_keys),
            )
            .distinct()
        )
        candidates = [str(x) for x in (await db.execute(stmt)).scalars().all()]
    else:
        stmt = select(IntakeSourceProfile.id).where(
            IntakeSourceProfile.tenant_id == tenant_id,
            IntakeSourceProfile.own_company_id == own_company_id,
            IntakeSourceProfile.is_active.is_(True),
            IntakeSourceProfile.provider == "meta",
            IntakeSourceProfile.route_intent == ROUTE_INTENT,
        )
        candidates = [str(x) for x in (await db.execute(stmt)).scalars().all()]

    if len(candidates) == 1:
        return candidates[0], manual
    if len(candidates) == 0:
        if has_meta_signal or form_keys:
            manual.append("meta_source_unresolved")
        return None, manual
    manual.append("meta_source_ambiguous")
    return None, manual


async def _validate_form_id(
    db: AsyncSession, *, tenant_id: str, form_id: str | None
) -> tuple[str | None, list[str]]:
    manual: list[str] = []
    fid = str(form_id or "").strip()
    if not fid:
        return None, manual
    row = (
        await db.execute(
            select(TenantLeadForm).where(
                TenantLeadForm.id == fid,
                TenantLeadForm.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        manual.append("form_not_found")
        return None, manual
    if not row.is_active or str(row.lifecycle_status or "").lower() == "archived":
        manual.append("form_inactive")
        return None, manual
    return fid, manual


async def apply_desired_lifecycle(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    desired: DesiredState,
    own_company_id: str,
    ctx: UserCtx,
) -> None:
    if desired == "draft":
        return
    if desired == "active":
        await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_SYSTEM,
            actor_id=ctx.sub,
            reason="legacy_search_migration",
            own_company_id=own_company_id,
        )
        return
    if desired == "paused":
        await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_SYSTEM,
            actor_id=ctx.sub,
            reason="legacy_search_migration",
            own_company_id=own_company_id,
        )
        await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            command="pause",
            actor_type=ACTOR_TYPE_SYSTEM,
            actor_id=ctx.sub,
            reason="legacy_search_migration",
            own_company_id=own_company_id,
        )
        return
    # completed: launch → complete; then Campaign.completed (existing vocabulary)
    await execute_flight_command(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        command="launch",
        actor_type=ACTOR_TYPE_SYSTEM,
        actor_id=ctx.sub,
        reason="legacy_search_migration",
        own_company_id=own_company_id,
    )
    await execute_flight_command(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        command="complete",
        actor_type=ACTOR_TYPE_SYSTEM,
        actor_id=ctx.sub,
        reason="legacy_search_migration",
        own_company_id=own_company_id,
    )
    await campaign_service.update_campaign(
        db,
        tenant_id=tenant_id,
        ctx=ctx,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        status="completed",
    )


async def list_eligible_vacancies(
    db: AsyncSession,
    *,
    tenant_id: str | None = None,
    vacancy_id: str | None = None,
) -> list[tuple[Vacancy, list[str]]]:
    meta_ids = await _meta_ads_vacancy_ids(db, tenant_id=tenant_id, vacancy_id=vacancy_id)
    stmt = select(Vacancy)
    if tenant_id:
        stmt = stmt.where(Vacancy.tenant_id == str(tenant_id))
    if vacancy_id:
        stmt = stmt.where(Vacancy.id == str(vacancy_id))
    vacancies = list((await db.execute(stmt)).scalars().all())
    eligible: list[tuple[Vacancy, list[str]]] = []
    for vac in vacancies:
        extra = vacancy_extra_dict(vac)
        signals = acquisition_signals(
            extra=extra,
            vacancy_id=str(vac.id),
            has_meta_ads=str(vac.id) in meta_ids,
        )
        if is_eligible(signals=signals):
            eligible.append((vac, signals))
    return eligible


async def migrate_one(
    db: AsyncSession,
    vacancy: Vacancy,
    *,
    signals: Sequence[str],
    dry_run: bool,
) -> MigrationRow:
    extra = vacancy_extra_dict(vacancy)
    row = MigrationRow(
        tenant_id=str(vacancy.tenant_id),
        vacancy_id=str(vacancy.id),
        own_company_id=str(vacancy.own_company_id) if vacancy.own_company_id else None,
        title=str(vacancy.title or ""),
        signals=list(signals),
        desired_state=derive_desired_state(vacancy, extra),
    )
    stamp = get_stamp(extra)
    if stamp:
        row.campaign_id = str(stamp.get("campaign_id") or "") or None
        row.flight_id = str(stamp.get("flight_id") or "") or None
        if stamp.get("campaign_archived") or stamp.get("rolled_back_at"):
            row.outcome = "already_existed_rolled_back"
            row.notes.append("stamp_present_rolled_back; explicit restore required")
        else:
            row.outcome = "already_existed"
            row.notes.append("stamp_present")
        return row

    if not row.own_company_id:
        row.outcome = "needs_manual"
        row.manual_reasons.append("missing_own_company_id")
        return row

    form_id_raw = str(extra.get("lead_form_id") or "").strip() or None
    form_id, form_manual = await _validate_form_id(
        db, tenant_id=row.tenant_id, form_id=form_id_raw
    )
    row.manual_reasons.extend(form_manual)
    if form_id_raw and not form_id:
        pass
    row.form_id = form_id

    acts = non_static_activities(extra, row.vacancy_id)
    has_meta = "meta_ads_map" in signals or any(
        str(a.get("channel_type") or a.get("type") or "").lower() == "meta" for a in acts
    )
    profile_id, meta_manual = await resolve_meta_intake_source(
        db,
        tenant_id=row.tenant_id,
        own_company_id=row.own_company_id,
        activities=acts,
        has_meta_signal=has_meta,
    )
    row.manual_reasons.extend(meta_manual)
    row.intake_source_profile_id = profile_id

    if dry_run:
        row.outcome = "needs_manual" if row.manual_reasons else "migrated"
        row.notes.append("dry_run")
        return row

    ctx = system_migration_ctx(row.tenant_id)
    try:
        campaign = await campaign_service.create_campaign(
            db,
            tenant_id=row.tenant_id,
            ctx=ctx,
            own_company_id=row.own_company_id,
            name=campaign_name_for_vacancy(vacancy),
            goal_type=GOAL_TYPE,
            primary_kpi=PRIMARY_KPI,
            description=(
                f"[{SCRIPT_VERSION}] Migrated from legacy Search vacancy_id={row.vacancy_id}"
            ),
            targets=[
                {
                    "target_type": TARGET_TYPE,
                    "target_id": row.vacancy_id,
                    "route_intent": ROUTE_INTENT,
                    "role": "primary",
                }
            ],
        )
        flight_id = str(campaign.current_flight_id or "")
        if not flight_id and campaign.flights:
            flight_id = str(campaign.flights[0].id)
        row.campaign_id = str(campaign.id)
        row.flight_id = flight_id or None
        if not row.flight_id:
            raise RuntimeError("create_campaign did not reserve a Flight")

        if form_id:
            await binding_service.attach_form(
                db,
                tenant_id=row.tenant_id,
                campaign_id=row.campaign_id,
                form_id=form_id,
                own_company_id=row.own_company_id,
                flight_id=row.flight_id,
                role="primary",
                actor_type=ACTOR_TYPE_SYSTEM,
                actor_id=ctx.sub,
            )
            row.notes.append("form_attached")

        if profile_id:
            await binding_service.attach_intake_source(
                db,
                tenant_id=row.tenant_id,
                campaign_id=row.campaign_id,
                intake_source_profile_id=profile_id,
                own_company_id=row.own_company_id,
                flight_id=row.flight_id,
                role="primary",
                actor_type=ACTOR_TYPE_SYSTEM,
                actor_id=ctx.sub,
            )
            row.notes.append("intake_source_attached")

        assert row.desired_state is not None
        await apply_desired_lifecycle(
            db,
            tenant_id=row.tenant_id,
            campaign_id=row.campaign_id,
            flight_id=row.flight_id,
            desired=row.desired_state,
            own_company_id=row.own_company_id,
            ctx=ctx,
        )

        # Re-read extra in case concurrent writers mutated other keys — we only set stamp.
        fresh_extra = vacancy_extra_dict(vacancy)
        fresh_extra[STAMP_KEY] = {
            "campaign_id": row.campaign_id,
            "flight_id": row.flight_id,
            "migrated_at": _utc_now_iso(),
            "script_version": SCRIPT_VERSION,
            "idempotency_key": idempotency_key(row.tenant_id, row.vacancy_id),
            "rolled_back_at": None,
            "rollback_version": None,
            "campaign_archived": False,
        }
        write_vacancy_extra(vacancy, fresh_extra)
        await db.flush()

        row.outcome = "needs_manual" if row.manual_reasons else "migrated"
        return row
    except Exception as exc:  # noqa: BLE001 — row-level isolation for batch report
        logger.exception(
            "legacy_search_migration.failed",
            extra={"vacancy_id": row.vacancy_id, "tenant_id": row.tenant_id},
        )
        row.outcome = "error"
        row.error = str(exc)
        return row


async def migrate_all(
    db: AsyncSession,
    *,
    tenant_id: str | None = None,
    vacancy_id: str | None = None,
    dry_run: bool = True,
) -> MigrationReport:
    report = MigrationReport(
        script_version=SCRIPT_VERSION,
        mode="dry_run" if dry_run else "apply",
    )
    eligible = await list_eligible_vacancies(
        db, tenant_id=tenant_id, vacancy_id=vacancy_id
    )
    report.found = len(eligible)
    for vac, signals in eligible:
        if dry_run:
            row = await migrate_one(db, vac, signals=signals, dry_run=True)
        else:
            row = MigrationRow(
                tenant_id=str(vac.tenant_id),
                vacancy_id=str(vac.id),
                own_company_id=str(vac.own_company_id) if vac.own_company_id else None,
                title=str(vac.title or ""),
                signals=list(signals),
            )
            try:
                async with db.begin_nested():
                    row = await migrate_one(db, vac, signals=signals, dry_run=False)
                    if row.outcome == "error":
                        raise RuntimeError(row.error or "migrate_one_failed")
            except Exception as exc:  # noqa: BLE001
                row.outcome = "error"
                row.error = row.error or str(exc)
                try:
                    await db.refresh(vac)
                except Exception:  # noqa: BLE001
                    pass
        report.rows.append(row)
        report._count(row.outcome)
    return report


async def rollback_one(
    db: AsyncSession,
    vacancy: Vacancy,
    *,
    dry_run: bool,
) -> MigrationRow:
    extra = vacancy_extra_dict(vacancy)
    stamp = get_stamp(extra)
    row = MigrationRow(
        tenant_id=str(vacancy.tenant_id),
        vacancy_id=str(vacancy.id),
        own_company_id=str(vacancy.own_company_id) if vacancy.own_company_id else None,
        title=str(vacancy.title or ""),
        signals=acquisition_signals(
            extra=extra,
            vacancy_id=str(vacancy.id),
            has_meta_ads=False,
        ),
    )
    if not stamp:
        row.outcome = "skipped"
        row.notes.append("no_stamp")
        return row
    row.campaign_id = str(stamp.get("campaign_id") or "") or None
    row.flight_id = str(stamp.get("flight_id") or "") or None
    if stamp.get("campaign_archived") or stamp.get("rolled_back_at"):
        row.outcome = "already_existed_rolled_back"
        row.notes.append("already_rolled_back")
        return row
    if not row.campaign_id:
        row.outcome = "error"
        row.error = "stamp_missing_campaign_id"
        return row

    if dry_run:
        row.outcome = "rolled_back"
        row.notes.append("dry_run")
        return row

    ctx = system_migration_ctx(row.tenant_id)
    campaign = (
        await db.execute(
            select(Campaign).where(
                Campaign.id == row.campaign_id,
                Campaign.tenant_id == row.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if campaign is None:
        row.outcome = "error"
        row.error = "campaign_not_found"
        return row
    desc = str(campaign.description or "")
    if SCRIPT_VERSION not in desc and row.vacancy_id not in desc:
        row.outcome = "needs_manual"
        row.manual_reasons.append("campaign_not_owned_by_migration_script")
        return row

    await campaign_service.update_campaign(
        db,
        tenant_id=row.tenant_id,
        ctx=ctx,
        campaign_id=row.campaign_id,
        own_company_id=str(campaign.own_company_id),
        status="archived",
    )
    # Stamp must remain — never delete — so re-apply cannot create a duplicate.
    stamp = dict(stamp)
    stamp["rolled_back_at"] = _utc_now_iso()
    stamp["rollback_version"] = SCRIPT_VERSION
    stamp["campaign_archived"] = True
    extra[STAMP_KEY] = stamp
    write_vacancy_extra(vacancy, extra)
    await db.flush()
    row.outcome = "rolled_back"
    row.notes.append("campaign_archived_stamp_retained")
    return row


async def rollback_all(
    db: AsyncSession,
    *,
    tenant_id: str | None = None,
    vacancy_id: str | None = None,
    dry_run: bool = True,
) -> MigrationReport:
    report = MigrationReport(
        script_version=SCRIPT_VERSION,
        mode="rollback_dry_run" if dry_run else "rollback",
    )
    stmt = select(Vacancy)
    if tenant_id:
        stmt = stmt.where(Vacancy.tenant_id == str(tenant_id))
    if vacancy_id:
        stmt = stmt.where(Vacancy.id == str(vacancy_id))
    vacancies = list((await db.execute(stmt)).scalars().all())
    stamped = [v for v in vacancies if get_stamp(vacancy_extra_dict(v))]
    report.found = len(stamped)
    for vac in stamped:
        row = await rollback_one(db, vac, dry_run=dry_run)
        report.rows.append(row)
        report._count(row.outcome)
    return report
