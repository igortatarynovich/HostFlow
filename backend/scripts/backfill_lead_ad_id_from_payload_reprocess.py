#!/usr/bin/env python3
"""
Восстановление маршрутизации для лидов ``needs_routing`` без ``candidate_id`` и без ``ad_id`` в строке лида.

Проблемы на проде:
1) В UI колонка ошибки «—» → ``Lead.error`` часто **NULL**, а не ``VACANCY_NOT_RESOLVED`` — старый фильтр по ошибке ничего не находил.
2) Импортировали **урезанный CSV** без колонки ``ad_id`` — в ``payload`` нет объявления; эталонные выгрузки лежат в репозитории в ``hostflow-frontend/public/leads/*.csv``.

Алгоритм:
- Выбрать лиды: ``needs_routing``, ``candidate_id IS NULL``, ``ad_id IS NULL``, источник csv_import или meta (настраивается).
- Взять ``ad_id``: из ``payload.ad_id`` **или** по **email** из эталонных CSV в репо (табуляция, UTF-8/UTF-16).
- Записать ``ad_id`` в строку лида и в ``payload``, слить ``normalized``, вызвать ``reprocess_stored_lead_payload`` с ``force_candidate_conversion=True``.

  cd /opt/HostFlow && PYTHONPATH=/opt/HostFlow python3 backend/scripts/backfill_lead_ad_id_from_payload_reprocess.py \\
    --tenant 9497fc29-6051-424d-9344-abb4aed9b110 --dry-run

  # без эталонных CSV (только payload):
  --no-repo-csv

  # каталог с эталонными выгрузками Meta (по умолчанию …/hostflow-frontend/public/leads)
  --repo-csv-dir /opt/HostFlow/hostflow-frontend/public/leads

На хосте задайте ``--database-url 'postgresql://...@127.0.0.1:5432/hostflow'``, если в ``.env`` указан hostname ``db`` (вне Docker он не резолвится).
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set


def _apply_database_url_from_argv() -> None:
    """Set DATABASE_URL / ASYNC_DATABASE_URL before ``Settings()`` when running on the host."""
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg.startswith("--database-url="):
            raw = arg.split("=", 1)[1].strip()
            break
        if arg == "--database-url" and i + 1 < len(argv):
            raw = argv[i + 1].strip()
            break
    else:
        return
    if not raw:
        return
    os.environ["DATABASE_URL"] = raw
    os.environ["ASYNC_DATABASE_URL"] = raw


_apply_database_url_from_argv()

THIS = Path(__file__).resolve()
if THIS.parent.name == "scripts" and THIS.parent.parent.name == "backend":
    BACKEND_DIR = THIS.parent.parent
    PROJECT_ROOT = BACKEND_DIR.parent
else:
    PROJECT_ROOT = THIS.parent.parent
    BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from backend.app.core.settings import settings  # noqa: F401
from backend.app.db.session import async_session_maker
from backend.app.models import Lead
from backend.app.modules.leads import normalizer, service as lead_service


def _open_csv_text(path: Path):
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return path.open(newline="", encoding="utf-16")
    return path.open(newline="", encoding="utf-8-sig")


def load_email_to_ad_id_from_repo(csv_dir: Path) -> Dict[str, int]:
    """email lower -> Graph ad_id int из колонки ``ad_id`` (``ag:…``)."""
    out: Dict[str, int] = {}
    if not csv_dir.is_dir():
        return out
    for path in sorted(csv_dir.glob("*.csv")):
        try:
            with _open_csv_text(path) as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                for row in reader:
                    em = (row.get("email") or "").strip().lower()
                    if not em:
                        continue
                    aid = normalizer.parse_meta_export_ad_id(row.get("ad_id"))
                    if aid is not None:
                        out[em] = aid
        except OSError:
            continue
    return out


def _email_from_lead(lead: Lead) -> Optional[str]:
    pl = lead.payload if isinstance(lead.payload, dict) else {}
    em = pl.get("email") or (lead.normalized or {}).get("email")
    if isinstance(em, str) and em.strip():
        return em.strip().lower()
    return None


def _ad_from_payload(payload: Any) -> Optional[int]:
    if not isinstance(payload, dict):
        return None
    return normalizer.parse_meta_export_ad_id(payload.get("ad_id"))


async def run(
    *,
    tenant_id: str,
    dry_run: bool,
    limit: Optional[int],
    use_repo_csv: bool,
    repo_csv_dir: Path,
    sources: Set[str],
) -> None:
    email_ad: Dict[str, int] = (
        load_email_to_ad_id_from_repo(repo_csv_dir) if use_repo_csv else {}
    )

    async with async_session_maker() as db:
        stmt = (
            select(Lead)
            .where(
                Lead.tenant_id == tenant_id,
                Lead.status == "needs_routing",
                Lead.candidate_id.is_(None),
                Lead.ad_id.is_(None),
                Lead.source.in_(tuple(sources)),
            )
            .order_by(Lead.created_at.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        rows = list((await db.execute(stmt)).scalars().all())

    summary: dict[str, Any] = {
        "tenant_id": tenant_id,
        "matched_leads": len(rows),
        "repo_csv_emails_indexed": len(email_ad),
        "would_fix": 0,
        "skipped_no_ad_anywhere": 0,
        "ad_from_payload": 0,
        "ad_from_repo_csv": 0,
        "errors": [],
    }

    for lead in rows:
        ad_int = _ad_from_payload(lead.payload)
        source_tag = "payload"
        if ad_int is None and use_repo_csv:
            em = _email_from_lead(lead)
            if em and em in email_ad:
                ad_int = email_ad[em]
                source_tag = "repo_csv"
        if ad_int is None:
            summary["skipped_no_ad_anywhere"] += 1
            continue
        if source_tag == "payload":
            summary["ad_from_payload"] += 1
        else:
            summary["ad_from_repo_csv"] += 1

        summary["would_fix"] += 1
        if dry_run:
            continue

        async with async_session_maker() as wdb:
            row = await wdb.get(Lead, lead.id)
            if row is None or str(row.tenant_id) != str(tenant_id):
                continue

            ad_int2 = _ad_from_payload(row.payload)
            if ad_int2 is None and use_repo_csv:
                em = _email_from_lead(row)
                if em and em in email_ad:
                    ad_int2 = email_ad[em]
            if ad_int2 is None:
                continue

            payload_dict = dict(row.payload) if isinstance(row.payload, dict) else {}
            if payload_dict.get("ad_id") is None:
                payload_dict["ad_id"] = f"ag:{ad_int2}"

            merged_norm = dict(row.normalized or {})
            merged_norm["ad_id"] = ad_int2
            row.payload = payload_dict
            row.ad_id = ad_int2
            row.normalized = merged_norm
            await wdb.flush()
            try:
                prior = dict(row.normalized or {})
                await lead_service.reprocess_stored_lead_payload(
                    wdb,
                    tenant_id=tenant_id,
                    own_company_id=getattr(row, "own_company_id", None),
                    payload=payload_dict,
                    source=(getattr(row, "source", None) or "meta").strip().lower()
                    or "meta",
                    force_existing=True,
                    external_id_hint=getattr(row, "external_id", None),
                    prior_normalized=prior,
                    force_candidate_conversion=True,
                    stored_lead_id=str(row.id),
                    stored_db_vacancy_id=None,
                    stored_db_ad_id=ad_int2,
                )
            except Exception as exc:
                summary["errors"].append({"lead_id": str(row.id), "error": str(exc)})
                await wdb.rollback()
                continue

    print(json.dumps(summary, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help=(
            "Override DATABASE_URL / ASYNC_DATABASE_URL for this process (e.g. postgresql://...@127.0.0.1:5432/... "
            "on the host when .env uses hostname db)."
        ),
    )
    parser.add_argument("--tenant", required=True, help="Tenant UUID")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--no-repo-csv",
        action="store_true",
        help="Не подставлять ad_id по email из hostflow-frontend/public/leads",
    )
    parser.add_argument(
        "--repo-csv-dir",
        type=Path,
        default=PROJECT_ROOT / "hostflow-frontend" / "public" / "leads",
        help="Каталог с эталонными TSV выгрузками Meta",
    )
    parser.add_argument(
        "--sources",
        default="csv_import,meta",
        help="Через запятую: csv_import, meta",
    )
    args = parser.parse_args()
    srcs = {s.strip().lower() for s in args.sources.split(",") if s.strip()}
    asyncio.run(
        run(
            tenant_id=str(args.tenant).strip(),
            dry_run=bool(args.dry_run),
            limit=args.limit,
            use_repo_csv=not bool(args.no_repo_csv),
            repo_csv_dir=args.repo_csv_dir,
            sources=srcs or {"csv_import", "meta"},
        )
    )


if __name__ == "__main__":
    main()
