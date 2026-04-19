#!/usr/bin/env python3
"""
Создать недостающие строки в ``meta_ads_map`` для Graph ``ad_id`` из выгрузок Poltrakt/Meta.

По умолчанию сканирует ``hostflow-frontend/public/leads/*.csv`` (колонка ``ad_id``, ``ag:…``),
определяет кампанию по имени файла (PL / ENG / RU) и **создаёт маппинг для каждого найденного
``ad_id`` — не только для трёх «канонических» чисел, так что новые объявления в тех же CSV попадут
в таблицу автоматически.

PK таблицы — ``ad_id`` (одна строка на объявление в БД).

Режимы:
  * ``--auto-resolve`` — подобрать ``vacancy_id`` по шаблонам ``ILIKE`` на ``vacancies.title``
    (можно повторить запуском с ``--dry-run`` и проверить список).
  * Явные UUID: ``--vacancy-pl``, ``--vacancy-eng``, ``--vacancy-ru`` (перекрывают авто для слота).

По умолчанию пропускает ``ad_id``, для которых уже есть маппинг (``--force`` перезаписывает).

Пример:

  cd /opt/HostFlow && PYTHONPATH=/opt/HostFlow python3 backend/scripts/ensure_poltrakt_canonical_meta_ad_mappings.py \\
    --tenant 9497fc29-6051-424d-9344-abb4aed9b110 --auto-resolve --dry-run

На хосте (вне Docker-сети) hostname ``db`` из ``.env`` не резолвится — задайте URL с ``127.0.0.1`` или запускайте из контейнера ``backend``:

  ... ensure_poltrakt_canonical_meta_ad_mappings.py \\
    --database-url 'postgresql://USER:PASS@127.0.0.1:5432/hostflow' \\
    --tenant ... --auto-resolve --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


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

from sqlalchemy import or_, select

from backend.app.core.settings import settings  # noqa: F401
from backend.app.db.session import async_session_maker
from backend.app.models import Vacancy
from backend.app.modules.leads import crud, normalizer


# Слот → ILIKE на ``vacancies.title`` (OR), если нет явных ``--vacancy-*``
SLOT_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "vacancy_pl": ("%magazynier%",),
    "vacancy_eng": ("%african%", "%włoch%", "%wloch%", "%eng%african%"),
    "vacancy_ru": ("%image ru%", "%ru ce%", "%poltrakt%ru%", "% ru %"),
}

DEFAULT_NOTE: Dict[str, str] = {
    "vacancy_pl": "Image PL Magazynier (export)",
    "vacancy_eng": "Image ENG African Man / Polska–Włochy",
    "vacancy_ru": "Image RU / Poltrakt RU CE",
}

# Fallback, если каталог CSV пуст или отключён ``--from-repo-csv``
_FALLBACK_SEED_AD_IDS: Tuple[Tuple[int, str], ...] = (
    (120245661643030547, "vacancy_pl"),
    (120245658843840547, "vacancy_eng"),
    (120245658855070547, "vacancy_ru"),
)


@dataclass(frozen=True)
class _WorkItem:
    ad_id: int
    slot_key: str
    note: str


def _open_csv_text(path: Path):
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return path.open(newline="", encoding="utf-16")
    return path.open(newline="", encoding="utf-8-sig")


def _slot_key_from_leads_csv_filename(name: str) -> Optional[str]:
    """Имя файла выгрузки Meta → слот маршрутизации."""
    stem = Path(name).stem.lower()
    if "image ru" in stem or stem.startswith("image_ru"):
        return "vacancy_ru"
    if "magazynier" in stem or "image pl" in stem:
        return "vacancy_pl"
    if "african" in stem or "image eng" in stem:
        return "vacancy_eng"
    return None


def _collect_from_repo_csvs(csv_dir: Path) -> Tuple[Dict[int, _WorkItem], List[str]]:
    """Все ``ad_id`` из TSV + предупреждения (неизвестное имя файла, конфликт слота)."""
    by_ad: Dict[int, _WorkItem] = {}
    warnings: List[str] = []
    if not csv_dir.is_dir():
        warnings.append(f"repo csv dir missing or not a directory: {csv_dir}")
        return by_ad, warnings

    for path in sorted(csv_dir.glob("*.csv")):
        sk = _slot_key_from_leads_csv_filename(path.name)
        if not sk:
            warnings.append(f"skip CSV (cannot infer PL/ENG/RU slot): {path.name}")
            continue
        base_note = DEFAULT_NOTE[sk]
        try:
            with _open_csv_text(path) as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                for row in reader:
                    aid = normalizer.parse_meta_export_ad_id(row.get("ad_id"))
                    if aid is None:
                        continue
                    note = f"{base_note} ({path.name})"
                    prev = by_ad.get(aid)
                    if prev is not None and prev.slot_key != sk:
                        warnings.append(
                            f"ad_id {aid} appears under conflicting slots "
                            f"{prev.slot_key} vs {sk} — keeping first"
                        )
                        continue
                    by_ad[aid] = _WorkItem(ad_id=aid, slot_key=sk, note=note)
        except OSError as exc:
            warnings.append(f"read error {path.name}: {exc}")

    return by_ad, warnings


def _merge_work_items(
    *,
    from_repo: Dict[int, _WorkItem],
    use_repo: bool,
    use_fallback_seeds: bool,
) -> Dict[int, _WorkItem]:
    """Репозиторий перекрывает seed; при отсутствии repo — три фиксированных ad_id."""
    out: Dict[int, _WorkItem] = {}
    if use_repo and from_repo:
        out.update(from_repo)
    if use_fallback_seeds and not out:
        for ad_id, sk in _FALLBACK_SEED_AD_IDS:
            out[ad_id] = _WorkItem(
                ad_id=ad_id,
                slot_key=sk,
                note=DEFAULT_NOTE[sk],
            )
    elif use_fallback_seeds:
        for ad_id, sk in _FALLBACK_SEED_AD_IDS:
            if ad_id not in out:
                out[ad_id] = _WorkItem(
                    ad_id=ad_id,
                    slot_key=sk,
                    note=DEFAULT_NOTE[sk],
                )
    return out


async def _pick_vacancy_id(
    db: Any,
    *,
    tenant_id: str,
    patterns: Sequence[str],
) -> Tuple[Optional[str], List[Dict[str, str]]]:
    conds = [Vacancy.title.ilike(p) for p in patterns]
    stmt = (
        select(Vacancy.id, Vacancy.title)
        .where(Vacancy.tenant_id == tenant_id)
        .where(or_(*conds))
        .order_by(Vacancy.created_at.desc())
    )
    rows = list((await db.execute(stmt)).all())
    matches = [{"id": str(r[0]), "title": str(r[1])} for r in rows]
    if not rows:
        return None, matches
    return str(rows[0][0]), matches


async def main_async(
    *,
    tenant_id: str,
    vacancy_pl: Optional[str],
    vacancy_eng: Optional[str],
    vacancy_ru: Optional[str],
    auto_resolve: bool,
    dry_run: bool,
    force: bool,
    repo_csv_dir: Path,
    use_repo_csv: bool,
) -> None:
    explicit = {
        "vacancy_pl": (vacancy_pl or "").strip() or None,
        "vacancy_eng": (vacancy_eng or "").strip() or None,
        "vacancy_ru": (vacancy_ru or "").strip() or None,
    }

    from_repo, repo_warnings = _collect_from_repo_csvs(repo_csv_dir)
    work = _merge_work_items(
        from_repo=from_repo,
        use_repo=use_repo_csv,
        use_fallback_seeds=True,
    )

    report: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "repo_csv_dir": str(repo_csv_dir),
        "use_repo_csv": use_repo_csv,
        "repo_warnings": repo_warnings,
        "work_ad_ids": sorted(work.keys()),
        "actions": [],
        "skipped_existing": [],
        "errors": [],
    }

    async with async_session_maker() as db:
        for ad_id in sorted(work.keys()):
            item = work[ad_id]
            slot_key = item.slot_key
            note = item.note
            patterns = SLOT_PATTERNS[slot_key]

            entry: Dict[str, Any] = {
                "ad_id": ad_id,
                "slot": slot_key,
                "note": note,
            }

            existing = await crud.get_meta_ads_entry(
                db, tenant_id=tenant_id, ad_id=ad_id
            )
            if existing is not None and not force:
                report["skipped_existing"].append(
                    {
                        "ad_id": ad_id,
                        "vacancy_id": str(existing.vacancy_id),
                        "note": existing.note,
                    }
                )
                continue

            vid: Optional[str] = explicit.get(slot_key)
            auto_matches: List[Dict[str, str]] = []
            if not vid and auto_resolve:
                picked, auto_matches = await _pick_vacancy_id(
                    db, tenant_id=tenant_id, patterns=patterns
                )
                vid = picked
                entry["auto_resolve_patterns"] = list(patterns)
                entry["candidates"] = auto_matches

            if not vid:
                report["errors"].append(
                    {
                        "ad_id": ad_id,
                        "slot": slot_key,
                        "message": "vacancy_id not provided and auto-resolve found no row",
                        "patterns": list(patterns),
                        "candidates_seen": auto_matches,
                    }
                )
                continue

            entry["vacancy_id"] = vid
            report["actions"].append(entry)

            if dry_run:
                continue

            await crud.upsert_meta_ads_map(
                db,
                tenant_id=tenant_id,
                ad_id=ad_id,
                vacancy_id=vid,
                note=note,
            )
            await db.commit()

    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--database-url",
        default=None,
        help=(
            "Override DATABASE_URL / ASYNC_DATABASE_URL for this process (e.g. postgresql://...@127.0.0.1:5432/... "
            "on the host when .env uses hostname db)."
        ),
    )
    p.add_argument("--tenant", required=True)
    p.add_argument("--vacancy-pl", default=None, help="UUID вакансии PL Magazynier")
    p.add_argument("--vacancy-eng", default=None, help="UUID вакансии ENG / Włochy")
    p.add_argument("--vacancy-ru", default=None, help="UUID вакансии Image RU")
    p.add_argument(
        "--auto-resolve",
        action="store_true",
        help="Подобрать вакансии по ILIKE-паттернам на title",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать существующие строки meta_ads_map для этих ad_id",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--repo-csv-dir",
        type=Path,
        default=None,
        help="Каталог с TSV выгрузками Meta (по умолчанию …/hostflow-frontend/public/leads)",
    )
    p.add_argument(
        "--no-repo-csv",
        action="store_true",
        help="Не сканировать CSV: только три fallback ad_id из скрипта",
    )
    args = p.parse_args()

    repo_csv_dir = args.repo_csv_dir
    if repo_csv_dir is None:
        repo_csv_dir = PROJECT_ROOT / "hostflow-frontend" / "public" / "leads"

    if not args.auto_resolve and not (
        args.vacancy_pl and args.vacancy_eng and args.vacancy_ru
    ):
        p.error(
            "Нужно либо все три --vacancy-pl / --vacancy-eng / --vacancy-ru, "
            "либо --auto-resolve (можно смешивать: явные UUID + --auto-resolve для недостающих)."
        )

    asyncio.run(
        main_async(
            tenant_id=args.tenant.strip(),
            vacancy_pl=args.vacancy_pl,
            vacancy_eng=args.vacancy_eng,
            vacancy_ru=args.vacancy_ru,
            auto_resolve=bool(args.auto_resolve),
            dry_run=bool(args.dry_run),
            force=bool(args.force),
            repo_csv_dir=repo_csv_dir,
            use_repo_csv=not bool(args.no_repo_csv),
        )
    )


if __name__ == "__main__":
    main()
