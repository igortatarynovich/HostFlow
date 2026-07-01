#!/usr/bin/env python3
"""
Скрипт для добавления маппингов ad_id → vacancy_id для Meta Leads.

Использование:
    docker compose exec backend python backend/scripts/add_meta_ads_mapping.py \
      --tenant 11111111-1111-1111-1111-111111111111 \
      --ad-id 120237848726550475 \
      --vacancy-id 807759e4-dbb7-4b7e-9a29-4219a97dab09 \
      --note "Описание маппинга"
"""
from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в путь для импортов ДО всех остальных импортов
THIS = Path(__file__).resolve()
if THIS.parent.name == "scripts" and THIS.parent.parent.name == "backend":
    BACKEND_DIR = THIS.parent.parent
    PROJECT_ROOT = BACKEND_DIR.parent
else:
    PROJECT_ROOT = THIS.parent.parent
    BACKEND_DIR = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import argparse
import asyncio
from backend.app.db.session import async_session_maker
from backend.app.modules.leads import admin_service
from backend.app.modules.leads.schemas import MetaAdsMapCreate


async def add_mapping(
    tenant_id: str,
    ad_id: str,
    vacancy_id: str,
    note: str | None = None,
    dry_run: bool = False,
) -> None:
    """Добавляет маппинг ad_id → vacancy_id."""
    async with async_session_maker() as db:
        if dry_run:
            print(f"[DRY RUN] Добавление маппинга:")
            print(f"  Tenant: {tenant_id}")
            print(f"  Ad ID: {ad_id}")
            print(f"  Vacancy ID: {vacancy_id}")
            if note:
                print(f"  Note: {note}")
            return
        
        payload = MetaAdsMapCreate(
            ad_id=ad_id,
            vacancy_id=vacancy_id,
            note=note,
        )
        
        result = await admin_service.upsert_mapping(
            db,
            tenant_id=tenant_id,
            payload=payload,
        )
        await db.commit()
        
        print(f"✅ Маппинг добавлен:")
        print(f"   Ad ID: {result.ad_id}")
        print(f"   Vacancy ID: {result.vacancy_id}")
        if result.note:
            print(f"   Note: {result.note}")
        print(f"   Created: {result.created_at}")


async def add_batch_mappings(
    tenant_id: str,
    mappings: list[dict],
    dry_run: bool = False,
) -> None:
    """Добавляет несколько маппингов."""
    async with async_session_maker() as db:
        print(f"Добавление {len(mappings)} маппингов...\n")
        
        for i, mapping in enumerate(mappings, 1):
            ad_id = mapping["ad_id"]
            vacancy_id = mapping["vacancy_id"]
            note = mapping.get("note")
            
            print(f"[{i}/{len(mappings)}] Ad ID: {ad_id} → Vacancy: {vacancy_id}")
            
            if not dry_run:
                payload = MetaAdsMapCreate(
                    ad_id=ad_id,
                    vacancy_id=vacancy_id,
                    note=note,
                )
                
                result = await admin_service.upsert_mapping(
                    db,
                    tenant_id=tenant_id,
                    payload=payload,
                )
                await db.commit()
                print(f"   ✅ Добавлен")
            else:
                print(f"   [DRY RUN]")
            print()
        
        if not dry_run:
            print(f"✅ Все маппинги добавлены!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Добавление маппингов Meta Ads")
    parser.add_argument(
        "--tenant",
        default="11111111-1111-1111-1111-111111111111",
        help="Tenant UUID",
    )
    parser.add_argument(
        "--ad-id",
        help="Ad ID для маппинга",
    )
    parser.add_argument(
        "--vacancy-id",
        help="Vacancy UUID для маппинга",
    )
    parser.add_argument(
        "--note",
        help="Описание маппинга (опционально)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать что будет добавлено, без фактического добавления",
    )
    
    args = parser.parse_args()
    
    if args.ad_id and args.vacancy_id:
        asyncio.run(add_mapping(
            args.tenant,
            args.ad_id,
            args.vacancy_id,
            args.note,
            args.dry_run,
        ))
    else:
        # Предустановленные маппинги на основе анализа
        default_mappings = [
            {
                "ad_id": "120235023955160475",
                "vacancy_id": "807759e4-dbb7-4b7e-9a29-4219a97dab09",
                "note": "CE Drivers (из документации)",
            },
            # Остальные нужно будет указать вручную
        ]
        
        print("Использование:")
        print("  --ad-id <AD_ID> --vacancy-id <VACANCY_ID> [--note \"описание\"]")
        print("\nИли используйте предустановленные маппинги:")
        for mapping in default_mappings:
            print(f"  Ad ID: {mapping['ad_id']} → Vacancy: {mapping['vacancy_id']}")
        
        if args.dry_run:
            asyncio.run(add_batch_mappings(
                args.tenant,
                default_mappings,
                args.dry_run,
            ))


if __name__ == "__main__":
    main()

