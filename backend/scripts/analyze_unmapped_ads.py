#!/usr/bin/env python3
"""
Скрипт для анализа лидов со статусом needs_routing и поиска новых ad_id.

Использование:
    docker compose exec backend python backend/scripts/analyze_unmapped_ads.py \
      --tenant 11111111-1111-1111-1111-111111111111
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
import json
from collections import defaultdict
from backend.app.db.session import async_session_maker
from backend.app.modules.leads import crud
from sqlalchemy import select, func
from backend.app.models import Lead, MetaAdsMap


async def analyze_unmapped_ads(tenant_id: str) -> None:
    """Анализирует лиды со статусом needs_routing и показывает новые ad_id."""
    async with async_session_maker() as db:
        # Получаем все лиды со статусом needs_routing
        stmt = select(
            Lead.ad_id,
            func.count(Lead.id).label("count"),
            func.min(Lead.created_at).label("first_seen"),
            func.max(Lead.created_at).label("last_seen"),
        ).where(
            Lead.tenant_id == tenant_id,
            Lead.status == "needs_routing",
            Lead.ad_id.isnot(None),
        ).group_by(Lead.ad_id).order_by(func.count(Lead.id).desc())
        
        result = await db.execute(stmt)
        unmapped_ads = result.all()
        
        # Получаем существующие маппинги
        stmt_mappings = select(MetaAdsMap).where(
            MetaAdsMap.tenant_id == tenant_id
        )
        result_mappings = await db.execute(stmt_mappings)
        existing_mappings = {str(m.ad_id): m.vacancy_id for m in result_mappings.scalars()}
        
        print(f"\n=== Анализ лидов со статусом needs_routing ===\n")
        print(f"Всего уникальных ad_id без маппинга: {len(unmapped_ads)}\n")
        
        # Группируем по ad_id и собираем примеры
        ad_details = defaultdict(lambda: {
            "count": 0,
            "first_seen": None,
            "last_seen": None,
            "examples": [],
        })
        
        for row in unmapped_ads:
            ad_id = str(row.ad_id)
            ad_details[ad_id]["count"] = row.count
            ad_details[ad_id]["first_seen"] = row.first_seen
            ad_details[ad_id]["last_seen"] = row.last_seen
        
        # Получаем примеры лидов для каждого ad_id
        for ad_id in ad_details.keys():
            stmt_examples = select(Lead).where(
                Lead.tenant_id == tenant_id,
                Lead.status == "needs_routing",
                Lead.ad_id == int(ad_id),
            ).limit(3)
            
            result_examples = await db.execute(stmt_examples)
            examples = result_examples.scalars().all()
            
            for lead in examples:
                normalized = lead.normalized or {}
                payload = lead.payload or {}
                
                # Извлекаем информацию из payload
                entry = (payload.get("entry") or [{}])[0] or {}
                changes = (entry.get("changes") or [{}])[0] or {}
                value = changes.get("value") or {}
                form_id = value.get("form_id") or normalized.get("form_id")
                
                example_info = {
                    "lead_id": lead.id,
                    "form_id": form_id,
                    "created_at": lead.created_at.isoformat() if lead.created_at else None,
                    "normalized": {
                        "first_name": normalized.get("first_name"),
                        "last_name": normalized.get("last_name"),
                        "email": normalized.get("email"),
                        "phone": normalized.get("phone"),
                        "company_name_hint": normalized.get("company_name_hint"),
                    }
                }
                ad_details[ad_id]["examples"].append(example_info)
        
        # Выводим результаты
        for ad_id, details in sorted(ad_details.items(), key=lambda x: x[1]["count"], reverse=True):
            has_mapping = ad_id in existing_mappings
            status = "✅ В маппинге" if has_mapping else "❌ НЕТ МАППИНГА"
            
            print(f"📊 Ad ID: {ad_id}")
            print(f"   Статус: {status}")
            if has_mapping:
                print(f"   Вакансия: {existing_mappings[ad_id]}")
            print(f"   Количество лидов: {details['count']}")
            print(f"   Первый лид: {details['first_seen']}")
            print(f"   Последний лид: {details['last_seen']}")
            
            if details["examples"]:
                print(f"   Примеры лидов:")
                for i, example in enumerate(details["examples"][:3], 1):
                    norm = example["normalized"]
                    name = f"{norm.get('first_name', '')} {norm.get('last_name', '')}".strip() or "N/A"
                    print(f"     {i}. Lead ID: {example['lead_id']}")
                    print(f"        Имя: {name}")
                    print(f"        Email: {norm.get('email', 'N/A')}")
                    print(f"        Phone: {norm.get('phone', 'N/A')}")
                    print(f"        Form ID: {example.get('form_id', 'N/A')}")
                    print(f"        Создан: {example.get('created_at', 'N/A')}")
            print()
        
        # Показываем существующие маппинги для справки
        print("\n=== Существующие маппинги ===\n")
        if existing_mappings:
            for ad_id, vacancy_id in sorted(existing_mappings.items()):
                print(f"  {ad_id} → {vacancy_id}")
        else:
            print("  Нет маппингов")
        
        # Рекомендации
        print("\n=== Рекомендации ===\n")
        unmapped_count = sum(1 for ad_id in ad_details.keys() if ad_id not in existing_mappings)
        if unmapped_count > 0:
            print(f"Найдено {unmapped_count} новых ad_id без маппинга.")
            print("\nДля добавления маппинга используйте:")
            print("1. Через админку: Settings → Integrations → Meta Leads → Mapping")
            print("2. Через API: POST /api/v1/admin/meta-leads/mapping")
            print("   {")
            print('     "ad_id": "AD_ID",')
            print('     "vacancy_id": "VACANCY_UUID"')
            print("   }")
            print("\n3. Или используйте скрипт для массового добавления маппингов")


def main() -> None:
    parser = argparse.ArgumentParser(description="Анализ лидов со статусом needs_routing")
    parser.add_argument(
        "--tenant",
        default="11111111-1111-1111-1111-111111111111",
        help="Tenant UUID",
    )
    
    args = parser.parse_args()
    asyncio.run(analyze_unmapped_ads(args.tenant))


if __name__ == "__main__":
    main()

