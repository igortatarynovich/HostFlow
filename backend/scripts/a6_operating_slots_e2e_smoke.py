#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _resolve_docs_root() -> Path:
    candidates = [
        Path("/app/docs"),
        REPO_ROOT.parent / "docs",
        Path.cwd() / "docs",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]

from sqlalchemy import delete, select, text

from backend.app.db.session import async_session_maker
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantLicense, TenantStatus, TenantType
from backend.app.models.user import Role as UserRole, User
from backend.app.modules.companies import crud, schemas
from backend.app.modules.companies.crud import OperatingCompanyLimitReached
from backend.app.services.operating_company_slots import get_operating_company_slots


@dataclass
class SmokeStep:
    step: str
    status: str
    detail: str


@dataclass
class SlotsSnapshot:
    included_limit: int
    extra_slots: int
    effective_limit: int
    used: int
    available: int
    unlimited: bool


def _slots_snapshot(slots) -> SlotsSnapshot:
    return SlotsSnapshot(
        included_limit=int(slots.included_limit),
        extra_slots=int(slots.extra_slots),
        effective_limit=int(slots.effective_limit),
        used=int(slots.used),
        available=int(slots.available),
        unlimited=bool(slots.unlimited),
    )


async def _set_tenant_context(db, tenant_id: str) -> None:
    db.info["tenant_id"] = tenant_id
    await db.execute(text("SELECT set_config('app.tenant_id', :tenant_id, false)"), {"tenant_id": tenant_id})


async def run_smoke() -> dict:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    created_company_ids: list[str] = []
    steps: list[SmokeStep] = []
    snapshots: dict[str, SlotsSnapshot] = {}

    async with async_session_maker() as db:
        tenant = Tenant(
            id=tenant_id,
            name=f"A6 S7 Smoke {tenant_id[:8]}",
            slug=f"a6-s7-smoke-{tenant_id[:8]}",
            api_key=f"a6-s7-smoke-{uuid4().hex}",
            is_active=True,
            status=TenantStatus.active,
            type=TenantType.agency,
            settings={"billing": {"subscription": {"plan_code": "starter", "extra_operating_company_slots": 0}}},
        )
        license_row = TenantLicense(
            id=str(uuid4()),
            tenant_id=tenant_id,
            plan="starter",
            max_companies=1,
        )
        user = User(
            id=user_id,
            email=f"a6-s7-smoke-{tenant_id[:8]}@example.com",
            password_hash="x",
            role=UserRole.administrator,
            tenant_id=tenant_id,
            is_active=True,
            deleted_at=None,
        )
        db.add_all([tenant, license_row, user])
        await db.commit()

        try:
            await _set_tenant_context(db, tenant_id)

            initial = await get_operating_company_slots(db, tenant_id)
            snapshots["initial"] = _slots_snapshot(initial)
            steps.append(SmokeStep("initial-slots", "PASS", f"effective={initial.effective_limit}, used={initial.used}"))

            first = await crud.create_company(
                db,
                schemas.CompanyCreate(name="A6 S7 Smoke Operating #1", company_type="services", company_role="operating"),
                actor_user_id=user_id,
            )
            created_company_ids.append(str(first.id))
            after_first = await get_operating_company_slots(db, tenant_id)
            snapshots["after_first_create"] = _slots_snapshot(after_first)
            if after_first.used == 1 and after_first.available == 0:
                steps.append(SmokeStep("create-first-operating", "PASS", "used=1 and available=0"))
            else:
                steps.append(SmokeStep("create-first-operating", "FAIL", f"unexpected slots: {asdict(snapshots['after_first_create'])}"))

            blocked_before_addon = False
            try:
                await crud.create_company(
                    db,
                    schemas.CompanyCreate(
                        name="A6 S7 Smoke should block before addon",
                        company_type="services",
                        company_role="operating",
                    ),
                    actor_user_id=user_id,
                )
            except OperatingCompanyLimitReached:
                blocked_before_addon = True
            steps.append(
                SmokeStep(
                    "block-second-before-addon",
                    "PASS" if blocked_before_addon else "FAIL",
                    "second operating create blocked before add-on slot" if blocked_before_addon else "second create unexpectedly allowed",
                )
            )

            tenant.settings = {"billing": {"subscription": {"plan_code": "starter", "extra_operating_company_slots": 1}}}
            db.add(tenant)
            await db.commit()
            after_addon = await get_operating_company_slots(db, tenant_id)
            snapshots["after_addon"] = _slots_snapshot(after_addon)
            steps.append(
                SmokeStep(
                    "add-slot",
                    "PASS" if after_addon.effective_limit == 2 and after_addon.available == 1 else "FAIL",
                    f"effective={after_addon.effective_limit}, available={after_addon.available}",
                )
            )

            second = await crud.create_company(
                db,
                schemas.CompanyCreate(name="A6 S7 Smoke Operating #2", company_type="services", company_role="operating"),
                actor_user_id=user_id,
            )
            created_company_ids.append(str(second.id))
            after_second = await get_operating_company_slots(db, tenant_id)
            snapshots["after_second_create"] = _slots_snapshot(after_second)
            steps.append(
                SmokeStep(
                    "create-second-after-addon",
                    "PASS" if after_second.used == 2 else "FAIL",
                    f"used={after_second.used}",
                )
            )

            tenant.settings = {"billing": {"subscription": {"plan_code": "starter", "extra_operating_company_slots": 0}}}
            db.add(tenant)
            await db.commit()
            after_downgrade = await get_operating_company_slots(db, tenant_id)
            snapshots["after_downgrade"] = _slots_snapshot(after_downgrade)
            over_limit = after_downgrade.used > after_downgrade.effective_limit > 0
            steps.append(
                SmokeStep(
                    "downgrade-over-limit-state",
                    "PASS" if over_limit else "FAIL",
                    f"effective={after_downgrade.effective_limit}, used={after_downgrade.used}",
                )
            )

            blocked_after_downgrade = False
            try:
                await crud.create_company(
                    db,
                    schemas.CompanyCreate(
                        name="A6 S7 Smoke should block after downgrade",
                        company_type="services",
                        company_role="operating",
                    ),
                    actor_user_id=user_id,
                )
            except OperatingCompanyLimitReached:
                blocked_after_downgrade = True
            steps.append(
                SmokeStep(
                    "block-new-after-downgrade",
                    "PASS" if blocked_after_downgrade else "FAIL",
                    "new operating create blocked after downgrade" if blocked_after_downgrade else "new create unexpectedly allowed",
                )
            )

            persisted = (
                await db.execute(select(Company).where(Company.tenant_id == tenant_id).order_by(Company.created_at.asc()))
            ).scalars().all()
            data_preserved = len(persisted) == 2
            steps.append(
                SmokeStep(
                    "data-preserved-after-downgrade",
                    "PASS" if data_preserved else "FAIL",
                    f"operating companies persisted={len(persisted)}",
                )
            )

            overall = "PASS" if all(step.status == "PASS" for step in steps) else "FAIL"
            return {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "overall_status": overall,
                "tenant_id": tenant_id,
                "tenant_slug": tenant.slug,
                "steps": [asdict(step) for step in steps],
                "slots_snapshots": {key: asdict(value) for key, value in snapshots.items()},
            }
        finally:
            if created_company_ids:
                await db.execute(delete(Company).where(Company.id.in_(created_company_ids)))
            await db.execute(delete(User).where(User.id == user_id))
            await db.execute(delete(TenantLicense).where(TenantLicense.tenant_id == tenant_id))
            await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await db.commit()


def to_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append("# A6-S7 Operating Slots Smoke Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{report['generated_at_utc']}`")
    lines.append(f"- Overall status: `{report['overall_status']}`")
    lines.append(f"- Synthetic tenant slug: `{report['tenant_slug']}`")
    lines.append("")
    lines.append("## Steps")
    lines.append("")
    lines.append("| Step | Status | Detail |")
    lines.append("|---|---|---|")
    for step in report["steps"]:
        lines.append(f"| `{step['step']}` | `{step['status']}` | {step['detail']} |")
    lines.append("")
    lines.append("## Slot Snapshots")
    lines.append("")
    lines.append("| Snapshot | included | extra | effective | used | available | unlimited |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for key, snapshot in report["slots_snapshots"].items():
        lines.append(
            f"| `{key}` | {snapshot['included_limit']} | {snapshot['extra_slots']} | {snapshot['effective_limit']} | {snapshot['used']} | {snapshot['available']} | {'YES' if snapshot['unlimited'] else 'NO'} |"
        )
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description="A6-S7 synthetic e2e smoke for operating company slots flow.")
    today = date.today().isoformat()
    docs_root = _resolve_docs_root()
    default_report = docs_root / "manual-checklist" / f"a6-s7-operating-slots-smoke-{today}.md"
    default_json = docs_root / "manual-checklist" / f"a6-s7-operating-slots-smoke-{today}.json"
    parser.add_argument(
        "--report",
        default=str(default_report),
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--json",
        default=str(default_json),
        help="JSON report output path.",
    )
    args = parser.parse_args()

    report = await run_smoke()
    report_md = to_markdown(report)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")
    print(f"[a6-s7] markdown report written: {report_path}")

    if args.json:
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
        print(f"[a6-s7] json report written: {json_path}")

    print(f"[a6-s7] overall status: {report['overall_status']}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
