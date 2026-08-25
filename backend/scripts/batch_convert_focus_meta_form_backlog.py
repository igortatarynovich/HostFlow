#!/usr/bin/env python3
"""Operational cleanup: dry-run then convert Focus Meta form backlog (Отклики).

Default is dry-run only. Convert requires ``--execute`` and only processes rows
classified as ``ready`` in the dry-run report.

Example:
  python3 backend/scripts/batch_convert_focus_meta_form_backlog.py \\
    --tenant-id 9497fc29-6051-424d-9344-abb4aed9b110 \\
    --form-id 1352242509195886 \\
    --report-dir var/ops-reports

  python3 backend/scripts/batch_convert_focus_meta_form_backlog.py \\
    --tenant-id 9497fc29-6051-424d-9344-abb4aed9b110 \\
    --form-id 1352242509195886 \\
    --report-dir var/ops-reports \\
    --execute
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

THIS = Path(__file__).resolve()
# Container layout: /app/scripts/... → REPO_ROOT=/app (contains app/ and backend/).
REPO_ROOT = THIS.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from backend.app.auth.deps import UserCtx  # noqa: E402
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models import Candidate, Lead, MetaFormRoute, OwnCompany, User  # noqa: E402
from backend.app.models.intake_routing import IntakeSourceBinding  # noqa: E402
from backend.app.modules.applications import mutations  # noqa: E402
from backend.app.modules.leads import crud  # noqa: E402
from backend.app.services.lead_rodo import lead_rodo_satisfied  # noqa: E402

DEFAULT_FORM_ID = "1352242509195886"
DEFAULT_TENANT_ID = "9497fc29-6051-424d-9344-abb4aed9b110"


@dataclass
class RowReport:
    application_id: str
    status: str  # ready | skip_* | error | converted | already_converted
    form_id: Optional[str] = None
    ad_id: Optional[str] = None
    page_id: Optional[str] = None
    route_found: bool = False
    form_route_ok: bool = False
    binding_ok: bool = False
    ad_map_ok: bool = False
    mapped_vacancy_id: Optional[str] = None
    lead_vacancy_id: Optional[str] = None
    resolved_vacancy_id: Optional[str] = None
    vacancy_match: Optional[bool] = None
    rodo_ok: bool = False
    rodo_status: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    existing_candidate_id: Optional[str] = None
    existing_candidate_vacancy_id: Optional[str] = None
    email_match_ids: List[str] = field(default_factory=list)
    phone_match_ids: List[str] = field(default_factory=list)
    predicted_action: Optional[str] = None  # create | reuse | skip
    predicted_candidate_id: Optional[str] = None
    result_candidate_id: Optional[str] = None
    result_vacancy_id: Optional[str] = None
    reason: Optional[str] = None
    detail: Optional[str] = None


def _digits(phone: Optional[str]) -> str:
    return re.sub(r"\D", "", str(phone or "").strip())


def _norm_email(email: Optional[str]) -> str:
    return str(email or "").strip().lower()


async def _load_open_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
) -> List[Lead]:
    stmt = (
        select(Lead)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.source == "meta",
            Lead.candidate_id.is_(None),
        )
        .order_by(Lead.created_at.asc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    out: List[Lead] = []
    for lead in rows:
        st = str(getattr(lead, "status", "") or "").strip().lower()
        if st in {"rejected", "processed"}:
            continue
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        fid = str(norm.get("form_id") or "").strip()
        if fid != str(form_id).strip():
            continue
        out.append(lead)
    return out


async def _routing_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_id: str,
    page_id: Optional[str],
    ad_id: Optional[int],
) -> Dict[str, Any]:
    form_routes = list(
        (
            await db.execute(
                select(MetaFormRoute).where(
                    MetaFormRoute.tenant_id == tenant_id,
                    MetaFormRoute.form_id == form_id,
                    MetaFormRoute.is_active.is_(True),
                )
            )
        ).scalars().all()
    )
    bindings = list(
        (
            await db.execute(
                select(IntakeSourceBinding).where(
                    IntakeSourceBinding.tenant_id == tenant_id,
                    IntakeSourceBinding.provider == "meta",
                    IntakeSourceBinding.external_key == f"form_id:{form_id}",
                    IntakeSourceBinding.is_active.is_(True),
                )
            )
        ).scalars().all()
    )
    ad_entry = None
    if ad_id is not None:
        ad_entry = await crud.get_meta_ads_entry(db, tenant_id=tenant_id, ad_id=ad_id)

    page_match_routes = [
        r
        for r in form_routes
        if not page_id or str(r.page_id or "").strip() in {"", str(page_id)}
    ]
    return {
        "form_routes": form_routes,
        "page_match_routes": page_match_routes,
        "bindings": bindings,
        "ad_entry": ad_entry,
    }


async def _candidate_matches(
    db: AsyncSession,
    *,
    tenant_id: str,
    email: Optional[str],
    phone: Optional[str],
) -> Tuple[List[Candidate], List[Candidate]]:
    email_hits: List[Candidate] = []
    phone_hits: List[Candidate] = []
    em = _norm_email(email)
    ph = _digits(phone)
    if em:
        rows = list(
            (
                await db.execute(
                    select(Candidate).where(
                        Candidate.tenant_id == tenant_id,
                        Candidate.email.is_not(None),
                    )
                )
            ).scalars().all()
        )
        email_hits = [c for c in rows if _norm_email(c.email) == em]
    if ph and len(ph) >= 9:
        rows = list(
            (
                await db.execute(
                    select(Candidate).where(
                        Candidate.tenant_id == tenant_id,
                        Candidate.phone.is_not(None),
                    )
                )
            ).scalars().all()
        )
        tail = ph[-9:]
        phone_hits = []
        for c in rows:
            cd = _digits(c.phone)
            if not cd:
                continue
            if cd == ph or cd.endswith(tail) or ph.endswith(cd[-9:] if len(cd) >= 9 else cd):
                phone_hits.append(c)
    return email_hits, phone_hits


def _classify(row: RowReport) -> RowReport:
    if not row.route_found:
        row.status = "skip_no_route"
        row.predicted_action = "skip"
        row.reason = row.reason or "no_form_or_ad_route"
        return row
    if row.resolved_vacancy_id is None:
        row.status = "skip_ambiguous_route"
        row.predicted_action = "skip"
        row.reason = row.reason or "vacancy_unresolved"
        return row
    if row.vacancy_match is False:
        row.status = "skip_ambiguous_route"
        row.predicted_action = "skip"
        row.reason = row.reason or "lead_vacancy_conflicts_with_ad_map"
        return row
    if not row.rodo_ok:
        row.status = "skip_rodo"
        row.predicted_action = "skip"
        row.reason = row.reason or "LEAD_RODO_REQUIRED"
        return row

    email_ids = set(row.email_match_ids)
    phone_ids = set(row.phone_match_ids)
    if email_ids and phone_ids and email_ids != phone_ids and not (email_ids & phone_ids):
        row.status = "skip_duplicate_conflict"
        row.predicted_action = "skip"
        row.reason = "email_and_phone_match_different_candidates"
        return row
    if len(email_ids) > 1:
        row.status = "skip_duplicate_conflict"
        row.predicted_action = "skip"
        row.reason = "multiple_candidates_same_email"
        return row
    if len(phone_ids) > 1 and not email_ids:
        row.status = "skip_duplicate_conflict"
        row.predicted_action = "skip"
        row.reason = "multiple_candidates_same_phone"
        return row

    shared = list(email_ids & phone_ids) if email_ids and phone_ids else list(email_ids or phone_ids)
    if shared:
        cand_id = shared[0]
        row.existing_candidate_id = cand_id
        if (
            row.existing_candidate_vacancy_id
            and row.resolved_vacancy_id
            and str(row.existing_candidate_vacancy_id) != str(row.resolved_vacancy_id)
        ):
            row.status = "skip_duplicate_conflict"
            row.predicted_action = "skip"
            row.reason = "existing_candidate_vacancy_mismatch"
            return row
        row.status = "ready"
        row.predicted_action = "reuse"
        row.predicted_candidate_id = cand_id
        row.reason = "reuse_existing_candidate"
        return row

    row.status = "ready"
    row.predicted_action = "create"
    row.predicted_candidate_id = None
    row.reason = "create_new_candidate"
    return row


async def assess_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    form_id: str,
) -> RowReport:
    norm = lead.normalized if isinstance(lead.normalized, dict) else {}
    email = str(norm.get("email") or "").strip() or None
    phone = str(norm.get("phone") or "").strip() or None
    page_id = str(norm.get("page_id") or "").strip() or None
    raw_ad = getattr(lead, "ad_id", None)
    if raw_ad is None:
        raw_ad = norm.get("ad_id")
    ad_id: Optional[int]
    try:
        ad_id = int(str(raw_ad).strip()) if raw_ad is not None and str(raw_ad).strip() else None
    except (TypeError, ValueError):
        ad_id = None

    payload = lead.payload if isinstance(lead.payload, dict) else {}
    if not page_id:
        try:
            page_id = str(
                (((payload.get("entry") or [{}])[0].get("changes") or [{}])[0].get("value") or {}).get("page_id")
                or ""
            ).strip() or None
        except Exception:
            page_id = None

    ctx = await _routing_context(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        page_id=page_id,
        ad_id=ad_id,
    )
    form_route_ok = len(ctx["page_match_routes"]) == 1 or (
        len(ctx["form_routes"]) == 1 and len(ctx["page_match_routes"]) <= 1
    )
    if len(ctx["page_match_routes"]) > 1 or len(ctx["form_routes"]) > 1 and not ctx["page_match_routes"]:
        form_route_ok = False
    binding_ok = len(ctx["bindings"]) >= 1
    ad_entry = ctx["ad_entry"]
    mapped_vacancy = str(ad_entry.vacancy_id) if ad_entry and ad_entry.vacancy_id else None
    lead_vacancy = str(lead.vacancy_id).strip() if getattr(lead, "vacancy_id", None) else None

    route_found = bool(form_route_ok and binding_ok) or bool(mapped_vacancy)
    resolved = lead_vacancy or mapped_vacancy
    vacancy_match: Optional[bool] = None
    if lead_vacancy and mapped_vacancy:
        vacancy_match = lead_vacancy == mapped_vacancy
    elif resolved:
        vacancy_match = True

    rodo_block = norm.get("rodo") if isinstance(norm.get("rodo"), dict) else {}
    rodo_status = str(rodo_block.get("status") or "").strip().lower() or None
    rodo_ok = lead_rodo_satisfied(lead)

    email_hits, phone_hits = await _candidate_matches(db, tenant_id=tenant_id, email=email, phone=phone)
    existing_vac = None
    if len(email_hits) == 1:
        existing_vac = str(email_hits[0].vacancy_id) if email_hits[0].vacancy_id else None
    elif len(phone_hits) == 1 and not email_hits:
        existing_vac = str(phone_hits[0].vacancy_id) if phone_hits[0].vacancy_id else None

    row = RowReport(
        application_id=str(lead.id),
        status="pending",
        form_id=form_id,
        ad_id=str(ad_id) if ad_id is not None else None,
        page_id=page_id,
        route_found=route_found,
        form_route_ok=form_route_ok,
        binding_ok=binding_ok,
        ad_map_ok=bool(mapped_vacancy),
        mapped_vacancy_id=mapped_vacancy,
        lead_vacancy_id=lead_vacancy,
        resolved_vacancy_id=resolved,
        vacancy_match=vacancy_match,
        rodo_ok=rodo_ok,
        rodo_status=rodo_status,
        email=email,
        phone=phone,
        existing_candidate_vacancy_id=existing_vac,
        email_match_ids=[str(c.id) for c in email_hits],
        phone_match_ids=[str(c.id) for c in phone_hits],
    )
    if not getattr(lead, "payload", None):
        row.status = "skip_no_route"
        row.reason = "missing_payload"
        row.predicted_action = "skip"
        return row
    if len(ctx["form_routes"]) > 1 and len(ctx["page_match_routes"]) != 1:
        row.route_found = False
        row.reason = "ambiguous_form_routes"
    return _classify(row)


async def _actor(db: AsyncSession, tenant_id: str) -> UserCtx:
    row = (
        await db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.asc())
            .limit(20)
        )
    ).scalars().all()
    pick = None
    for u in row:
        role = str(getattr(u, "role", "") or "").lower()
        if role in {"administrator", "admin", "owner", "supervisor"}:
            pick = u
            break
    if pick is None and row:
        pick = row[0]
    if pick is None:
        raise RuntimeError(f"No user for tenant {tenant_id}")
    role = str(pick.role or "administrator").strip().lower()
    return UserCtx(
        sub=str(pick.id),
        email=str(pick.email or ""),
        role=role,
        tenant_id=str(tenant_id),
        supervisor_id=None,
        raw={"sub": str(pick.id), "email": str(pick.email or ""), "role": role, "tenant_id": tenant_id},
    )


async def convert_ready(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    actor: UserCtx,
    application_id: str,
) -> RowReport:
    before = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if before is None:
        return RowReport(application_id=application_id, status="error", reason="lead_not_found")
    if before.candidate_id:
        return RowReport(
            application_id=application_id,
            status="already_converted",
            result_candidate_id=str(before.candidate_id),
            result_vacancy_id=str(before.vacancy_id) if before.vacancy_id else None,
            reason="already_has_candidate",
        )
    try:
        result = await mutations.recruitment_process_application(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            application_id=application_id,
            current_user=actor,
        )
    except Exception as exc:  # noqa: BLE001 — ops report must capture failures
        # Partial success: conversion may commit before a side-effect import/error.
        after_err = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
        if after_err and after_err.candidate_id:
            return RowReport(
                application_id=application_id,
                status="converted",
                result_candidate_id=str(after_err.candidate_id),
                result_vacancy_id=str(after_err.vacancy_id) if after_err.vacancy_id else None,
                reason="ok_after_side_effect_error",
                detail=str(getattr(exc, "detail", None) or exc)[:500],
            )
        detail = getattr(exc, "detail", None)
        code = None
        if isinstance(detail, dict):
            code = detail.get("code")
        return RowReport(
            application_id=application_id,
            status="error",
            reason=str(code or type(exc).__name__),
            detail=str(detail or exc)[:500],
        )
    cand = str(result.candidate_id) if result.candidate_id else None
    vac = None
    if result.application and result.application.extensions:
        vac = str(result.application.extensions.get("vacancy_id") or "") or None
    after = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if after and after.vacancy_id:
        vac = str(after.vacancy_id)
    if not cand:
        return RowReport(
            application_id=application_id,
            status="error",
            reason=str(result.message or "no_candidate_id"),
            detail="process returned without candidate_id",
            result_vacancy_id=vac,
        )
    return RowReport(
        application_id=application_id,
        status="converted",
        result_candidate_id=cand,
        result_vacancy_id=vac,
        predicted_action="create_or_reuse",
        reason="ok",
    )


def _write_reports(report_dir: Path, stamp: str, rows: Sequence[RowReport], *, label: str) -> Tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"meta_form_backlog_{label}_{stamp}.json"
    csv_path = report_dir / f"meta_form_backlog_{label}_{stamp}.csv"
    payload = [asdict(r) for r in rows]
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(asdict(rows[0]).keys()) if rows else list(asdict(RowReport(application_id="", status="")).keys())
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            d = asdict(r)
            d["email_match_ids"] = ",".join(d.get("email_match_ids") or [])
            d["phone_match_ids"] = ",".join(d.get("phone_match_ids") or [])
            w.writerow(d)
    return json_path, csv_path


async def _own_company_id(db: AsyncSession, tenant_id: str) -> str:
    row = (
        await db.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id)
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not row:
        raise RuntimeError("own_company_id missing")
    return str(row)


async def main_async(args: argparse.Namespace) -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = Path(args.report_dir)

    async with async_session_maker() as db:
        leads = await _load_open_leads(db, tenant_id=args.tenant_id, form_id=args.form_id)
        dry_rows: List[RowReport] = []
        for lead in leads:
            dry_rows.append(
                await assess_lead(db, tenant_id=args.tenant_id, lead=lead, form_id=args.form_id)
            )

    dry_json, dry_csv = _write_reports(report_dir, stamp, dry_rows, label="dryrun")
    counts: Dict[str, int] = {}
    for r in dry_rows:
        counts[r.status] = counts.get(r.status, 0) + 1
    print(f"DRY-RUN leads={len(dry_rows)} by_status={counts}")
    print(f"DRY-RUN report: {dry_json}")
    print(f"DRY-RUN csv:    {dry_csv}")

    ready = [r for r in dry_rows if r.status == "ready"]
    print(f"READY count={len(ready)}")
    if not args.execute:
        print("Dry-run only (pass --execute to convert ready rows).")
        return 0

    # Snapshot candidate count before convert
    async with async_session_maker() as db:
        from sqlalchemy import func

        before_cnt = int(
            (
                await db.execute(
                    select(func.count()).select_from(Candidate).where(Candidate.tenant_id == args.tenant_id)
                )
            ).scalar_one()
            or 0
        )
        actor = await _actor(db, args.tenant_id)
        own_company_id = await _own_company_id(db, args.tenant_id)

    exec_rows: List[RowReport] = []
    created = 0
    reused = 0
    errors = 0
    for plan in ready:
        async with async_session_maker() as db:
            out = await convert_ready(
                db,
                tenant_id=args.tenant_id,
                own_company_id=own_company_id,
                actor=actor,
                application_id=plan.application_id,
            )
            # enrich with plan fields for final report
            out.form_id = plan.form_id
            out.ad_id = plan.ad_id
            out.resolved_vacancy_id = plan.resolved_vacancy_id
            out.predicted_action = plan.predicted_action
            out.predicted_candidate_id = plan.predicted_candidate_id
            out.rodo_ok = plan.rodo_ok
            out.route_found = plan.route_found
            if out.status == "converted":
                if plan.predicted_action == "reuse" and out.result_candidate_id == plan.predicted_candidate_id:
                    reused += 1
                else:
                    created += 1
            elif out.status == "already_converted":
                reused += 1
            else:
                errors += 1
            exec_rows.append(out)

    # Idempotent second pass: candidate count must not grow; candidate_ids stable.
    async with async_session_maker() as db:
        from sqlalchemy import func

        mid_cnt = int(
            (
                await db.execute(
                    select(func.count()).select_from(Candidate).where(Candidate.tenant_id == args.tenant_id)
                )
            ).scalar_one()
            or 0
        )

    second_new = 0
    first_ids = {
        r.application_id: r.result_candidate_id
        for r in exec_rows
        if r.result_candidate_id
    }
    for plan in ready:
        async with async_session_maker() as db:
            out = await convert_ready(
                db,
                tenant_id=args.tenant_id,
                own_company_id=own_company_id,
                actor=actor,
                application_id=plan.application_id,
            )
            prev = first_ids.get(plan.application_id)
            if (
                out.result_candidate_id
                and prev
                and out.result_candidate_id != prev
                and out.status in {"converted", "already_converted"}
            ):
                second_new += 1

    async with async_session_maker() as db:
        from sqlalchemy import func

        after_cnt = int(
            (
                await db.execute(
                    select(func.count()).select_from(Candidate).where(Candidate.tenant_id == args.tenant_id)
                )
            ).scalar_one()
            or 0
        )
    second_pass_delta = after_cnt - mid_cnt

    final_json, final_csv = _write_reports(report_dir, stamp, exec_rows, label="execute")
    delta = after_cnt - before_cnt
    ready_create = sum(1 for r in ready if r.predicted_action == "create")
    ready_reuse = sum(1 for r in ready if r.predicted_action == "reuse")

    print(
        json.dumps(
            {
                "ready": len(ready),
                "ready_create": ready_create,
                "ready_reuse": ready_reuse,
                "converted_ok": sum(1 for r in exec_rows if r.status in {"converted", "already_converted"}),
                "errors": errors,
                "candidates_before": before_cnt,
                "candidates_after_first_pass": mid_cnt,
                "candidates_after_second_pass": after_cnt,
                "delta_total": delta,
                "second_pass_delta": second_pass_delta,
                "second_pass_new": second_new,
                "execute_report_json": str(final_json),
                "execute_report_csv": str(final_csv),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    # Hard checks requested by operator
    ok = True
    if second_new != 0 or second_pass_delta != 0:
        print("FAIL: second pass created new candidates")
        ok = False
    if delta != ready_create:
        # reuse should not increase count; create should match delta
        print(f"FAIL: delta={delta} != ready_create={ready_create}")
        ok = False
    if errors:
        print(f"FAIL: {errors} conversion errors")
        ok = False
    return 0 if ok else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    p.add_argument("--form-id", default=DEFAULT_FORM_ID)
    p.add_argument(
        "--report-dir",
        default=str(REPO_ROOT / "uploads" / "ops-reports"),
        help="Directory for dry-run/execute CSV+JSON reports (default: uploads/ops-reports)",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Convert only dry-run ready rows (default: dry-run only)",
    )
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
