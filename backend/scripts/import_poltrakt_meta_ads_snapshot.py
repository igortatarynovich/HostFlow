#!/usr/bin/env python3
"""Import Poltrakt Meta Ads **daily** snapshot into Focus Acquisition KPIs.

Creates one Campaign per Meta campaign name + daily Flight spend entries and
synthetic result attributions stamped with the report day (``created_at``),
so Overview / portfolio ``date_from`` / ``date_to`` windows work like Recruitment.

Idempotent: deterministic UUIDs; ``--reset`` removes prior import-marked campaigns.

Usage:

  cd /opt/HostFlow && python3 backend/scripts/import_poltrakt_meta_ads_snapshot.py --reset

  python3 backend/scripts/import_poltrakt_meta_ads_snapshot.py \\
    --csv backend/app/db/seeds/data/poltrakt_meta_ads_daily.csv --reset
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import re
import socket
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID, uuid4, uuid5


def _configure_sys_path() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    repo_root = backend_root.parent
    if (repo_root / "backend").is_dir() and (repo_root / "backend").resolve() == backend_root.resolve():
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
    elif str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))


def _localize_db_host_in_env() -> None:
    override = (os.environ.get("HOSTFLOW_SCRIPT_DB_HOST") or "").strip()
    keys = ("ASYNC_DATABASE_URL", "SYNC_DATABASE_URL", "DATABASE_URL")
    if override:
        for key in keys:
            val = os.environ.get(key)
            if val and "@db:" in val:
                os.environ[key] = re.sub(r"@db:", f"@{override}:", val)
        return
    try:
        socket.getaddrinfo("db", 5432, type=socket.SOCK_STREAM)
        return
    except OSError:
        pass
    for key in keys:
        val = os.environ.get(key)
        if val and "@db:" in val:
            os.environ[key] = re.sub(r"@db:", "@127.0.0.1:", val)


def _load_dotenv_backends() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    backend_root = Path(__file__).resolve().parent.parent
    repo_root = backend_root.parent
    load_dotenv(repo_root / ".env", override=False)
    load_dotenv(backend_root / ".env", override=False)


_configure_sys_path()
_load_dotenv_backends()
_localize_db_host_in_env()

from sqlalchemy import delete, select  # noqa: E402

from backend.app.acquisition.flights.lifecycle import create_flight  # noqa: E402
from backend.app.acquisition.kpi_aggregates import record_flight_spend  # noqa: E402
from backend.app.acquisition.result_attribution import RESULT_TYPE_INTAKE_LEAD  # noqa: E402
from backend.app.acquisition.validation import validate_promotion_target  # noqa: E402
from backend.app.constants.hostflow_canonical_tenants import (  # noqa: E402
    FOCUS_OWN_COMPANY_ID,
    FOCUS_PERSONNEL_TENANT_ID,
    FOCUS_POLTRAKT_COMPANY_ID,
)
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models.campaign import (  # noqa: E402
    Campaign,
    CampaignFlightSpendEntry,
    CampaignResultAttribution,
    CampaignRun,
    CampaignTarget,
)
from backend.app.models.vacancy import Vacancy  # noqa: E402

IMPORT_MARKER = "[hf_meta_ads_import v1]"
IMPORT_NS = UUID("6f0a1b2c-3d4e-5f60-7182-93a4b5c6d7e8")
DEFAULT_CSV = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "db"
    / "seeds"
    / "data"
    / "poltrakt_meta_ads_daily.csv"
)


def _parse_decimal(raw: str) -> Decimal:
    s = str(raw or "").strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    if not s:
        return Decimal("0")
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal: {raw!r}") from exc


def _parse_int(raw: str) -> int:
    s = str(raw or "").strip().replace("\xa0", "").replace(" ", "").replace(",", "")
    if not s:
        return 0
    return int(float(s))


def _load_daily_rows(csv_path: Path) -> list[dict]:
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(text.splitlines())
    # Merge duplicate name+day (Meta export can duplicate campaign names).
    agg: dict[tuple[str, str], dict] = {}
    for row in reader:
        name = (row.get("Nazwa kampanii") or row.get("name") or "").strip()
        day = (row.get("Początek okresu raportowania") or row.get("day") or "").strip()
        if not name or not day:
            continue
        try:
            leads = _parse_int(row.get("Wyniki") or row.get("leads") or "0")
            spend = _parse_decimal(row.get("Wydana kwota (USD)") or row.get("spend") or "0")
            impressions = _parse_int(row.get("Wyświetlenia") or row.get("impressions") or "0")
            reach = _parse_int(row.get("Zasięg") or row.get("reach") or "0")
        except ValueError:
            continue
        key = (name, day)
        cur = agg.get(key)
        if cur is None:
            agg[key] = {
                "name": name,
                "day": day,
                "leads": leads,
                "spend": spend,
                "impressions": impressions,
                "reach": reach,
            }
        else:
            cur["leads"] += leads
            cur["spend"] += spend
            cur["impressions"] += impressions
            cur["reach"] += reach
    out = [v for v in agg.values() if v["spend"] > 0 or v["leads"] > 0]
    out.sort(key=lambda r: (r["name"], r["day"]))
    return out


def _campaign_id(name: str) -> str:
    return str(uuid5(IMPORT_NS, f"meta-ads-campaign:{name}"))


def _flight_id(campaign_id: str) -> str:
    return str(uuid5(IMPORT_NS, f"meta-ads-flight:{campaign_id}"))


def _day_stamp(day: str) -> datetime:
    return datetime.fromisoformat(f"{day}T12:00:00+00:00")


def _pick_vacancy_id(name: str, vacancies: list[Vacancy]) -> str | None:
    lower = name.lower()
    by_title = {str(v.title or "").strip().lower(): str(v.id) for v in vacancies}

    def find(*needles: str) -> str | None:
        for title, vid in by_title.items():
            if any(n in title for n in needles):
                return vid
        return None

    if "dyspozytor" in lower:
        return find("dyspozytor", "planista")
    if "magazyn" in lower:
        return find("magazyn")
    if any(k in lower for k in ("driver", "ce pol", "italy", "c+e", "ce pl", "week/cadence")):
        return find("c+e", "polska", "benelux") or find("poltrakt")
    return find("c+e") or find("polska") or (str(vacancies[0].id) if vacancies else None)


def _description(*, period_start: str, period_end: str, days: int) -> str:
    return (
        f"{IMPORT_MARKER} client=POLTRAKT grain=daily "
        f"period={period_start}..{period_end} days={days} "
        f"currency=USD (Meta Ads daily export; not live sync)"
    )


async def _load_poltrakt_vacancies(db, *, tenant_id: str, company_id: str, own_company_id: str):
    rows = (
        await db.execute(
            select(Vacancy).where(
                Vacancy.tenant_id == tenant_id,
                Vacancy.company_id == company_id,
                Vacancy.own_company_id == own_company_id,
                Vacancy.is_archived.is_(False),
            )
        )
    ).scalars().all()
    return list(rows)


async def _ensure_campaign(
    db,
    *,
    tenant_id: str,
    own_company_id: str,
    name: str,
    vacancy_id: str | None,
    period_start: str,
    period_end: str,
    days: int,
) -> tuple[str, str, bool]:
    campaign_id = _campaign_id(name)
    flight_id = _flight_id(campaign_id)
    existing = await db.get(Campaign, campaign_id)
    if existing is not None and IMPORT_MARKER in str(existing.description or ""):
        existing.description = _description(
            period_start=period_start, period_end=period_end, days=days
        )
        existing.name = name[:255]
        existing.status = "active"
        flight = await db.get(CampaignRun, flight_id)
        if flight is not None:
            flight.status = "completed"
            flight.starts_at = datetime.fromisoformat(f"{period_start}T00:00:00+00:00")
            flight.ends_at = datetime.fromisoformat(f"{period_end}T23:59:59+00:00")
        return campaign_id, flight_id, False

    if existing is not None:
        raise RuntimeError(f"campaign id collision without import marker: {campaign_id} ({name})")

    campaign = Campaign(
        id=campaign_id,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        name=name[:255],
        description=_description(period_start=period_start, period_end=period_end, days=days),
        status="active",
        goal_type="hiring",
        primary_kpi="applications",
        current_flight_id=flight_id,
        created_by_user_id=None,
    )
    db.add(campaign)
    if vacancy_id:
        vt = validate_promotion_target(
            target_type="vacancy",
            target_id=vacancy_id,
            route_intent="candidate_application",
            role="primary",
            sort_order=0,
        )
        db.add(
            CampaignTarget(
                id=str(uuid4()),
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                target_type=vt.target_type,
                target_id=vt.target_id,
                target_module=vt.target_module,
                route_intent=vt.route_intent,
                role=vt.role,
                sort_order=0,
            )
        )
    await create_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        code="meta_daily_1",
        name=f"Meta daily {period_start}…{period_end}",
        actor_type="system",
        actor_id=None,
    )
    flight = await db.get(CampaignRun, flight_id)
    if flight is not None:
        flight.status = "completed"
        flight.starts_at = datetime.fromisoformat(f"{period_start}T00:00:00+00:00")
        flight.ends_at = datetime.fromisoformat(f"{period_end}T23:59:59+00:00")
    return campaign_id, flight_id, True


async def run(*, csv_path: Path, dry_run: bool, reset: bool) -> None:
    rows = _load_daily_rows(csv_path)
    if not rows:
        raise SystemExit(f"No active daily rows in {csv_path}")

    by_campaign: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_campaign[row["name"]].append(row)

    period_start = min(r["day"] for r in rows)
    period_end = max(r["day"] for r in rows)
    tenant_id = FOCUS_PERSONNEL_TENANT_ID
    own_company_id = FOCUS_OWN_COMPANY_ID
    company_id = FOCUS_POLTRAKT_COMPANY_ID

    print(
        f"daily rows={len(rows)} campaigns={len(by_campaign)} "
        f"period={period_start}..{period_end}"
    )
    if dry_run:
        for name, days in sorted(by_campaign.items()):
            spend = sum((d["spend"] for d in days), Decimal("0"))
            leads = sum(d["leads"] for d in days)
            print(f"  dry-run {name!r} days={len(days)} leads={leads} spend={spend}")
        return

    async with async_session_maker() as db:
        if reset:
            existing = (
                await db.execute(
                    select(Campaign).where(
                        Campaign.tenant_id == tenant_id,
                        Campaign.own_company_id == own_company_id,
                        Campaign.description.is_not(None),
                        Campaign.description.contains(IMPORT_MARKER),
                    )
                )
            ).scalars().all()
            for camp in existing:
                await db.execute(
                    delete(CampaignResultAttribution).where(
                        CampaignResultAttribution.campaign_id == str(camp.id)
                    )
                )
                await db.execute(
                    delete(CampaignFlightSpendEntry).where(
                        CampaignFlightSpendEntry.campaign_id == str(camp.id)
                    )
                )
                await db.delete(camp)
            await db.commit()
            print(f"reset: removed {len(existing)} imported campaign(s)")

        vacancies = await _load_poltrakt_vacancies(
            db, tenant_id=tenant_id, company_id=company_id, own_company_id=own_company_id
        )

        for name, day_rows in sorted(by_campaign.items()):
            vac = _pick_vacancy_id(name, vacancies)
            campaign_id, flight_id, created = await _ensure_campaign(
                db,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                name=name,
                vacancy_id=vac,
                period_start=period_start,
                period_end=period_end,
                days=len(day_rows),
            )
            # Clear prior day facts for this campaign (idempotent re-import without --reset).
            await db.execute(
                delete(CampaignResultAttribution).where(
                    CampaignResultAttribution.campaign_id == campaign_id
                )
            )
            await db.execute(
                delete(CampaignFlightSpendEntry).where(
                    CampaignFlightSpendEntry.campaign_id == campaign_id
                )
            )

            total_leads = 0
            total_spend = Decimal("0")
            for day_row in day_rows:
                day = day_row["day"]
                stamp = _day_stamp(day)
                spend = Decimal(day_row["spend"])
                leads = int(day_row["leads"])
                impressions = int(day_row["impressions"])
                reach = int(day_row["reach"])
                total_leads += leads
                total_spend += spend

                if spend > 0 or impressions > 0 or reach > 0:
                    await record_flight_spend(
                        db,
                        tenant_id=tenant_id,
                        flight_id=flight_id,
                        amount=spend,
                        currency="USD",
                        note=(
                            f"meta_day={day} impressions={impressions} reach={reach}"
                        )[:255],
                        spent_at=stamp,
                    )

                attrs = []
                for i in range(leads):
                    rid = str(uuid5(IMPORT_NS, f"meta-ads-result:{campaign_id}:{day}:{i}"))
                    sid = str(uuid5(IMPORT_NS, f"meta-ads-sub:{campaign_id}:{day}:{i}"))
                    lid = str(uuid5(IMPORT_NS, f"meta-ads-lead:{campaign_id}:{day}:{i}"))
                    attrs.append(
                        CampaignResultAttribution(
                            id=str(uuid5(IMPORT_NS, f"meta-ads-attr:{campaign_id}:{day}:{i}")),
                            tenant_id=tenant_id,
                            campaign_id=campaign_id,
                            campaign_run_id=flight_id,
                            result_type=RESULT_TYPE_INTAKE_LEAD,
                            result_id=rid,
                            submission_id=sid,
                            lead_id=lid,
                            route_intent="candidate_application",
                            routing_source="meta_ads_daily_import",
                            created_at=stamp,
                            updated_at=stamp,
                        )
                    )
                if attrs:
                    db.add_all(attrs)

            await db.flush()
            flag = "created" if created else "updated"
            print(
                f"ok {flag} {name!r} days={len(day_rows)} "
                f"leads={total_leads} spend={total_spend} ({campaign_id})"
            )

        await db.commit()
        print("done")


def main() -> None:
    p = argparse.ArgumentParser(description="Import Poltrakt Meta Ads daily snapshot.")
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()
    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")
    asyncio.run(run(csv_path=args.csv, dry_run=args.dry_run, reset=args.reset))


if __name__ == "__main__":
    main()
