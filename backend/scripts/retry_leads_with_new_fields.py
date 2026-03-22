#!/usr/bin/env python3
"""
Скрипт для перезапуска обработки лидов Meta с новыми полями.

Находит лиды, которые содержат новые поля:
- ce_driving_experience_in_europe
- preferred_way_of_contact
- what_is_the_legal_basis_of_your_stay_in_poland?

И перезапускает их обработку для заполнения новых полей в карточках кандидатов.

Использование:
    # В Docker контейнере:
    docker compose exec backend python backend/scripts/retry_leads_with_new_fields.py --tenant <tenant_id> --dry-run
    
    # Или локально (если БД доступна):
    cd /opt/HostFlow/backend
    python3 scripts/retry_leads_with_new_fields.py --tenant <tenant_id> --dry-run
"""
from __future__ import annotations

import sys
from pathlib import Path

# Добавляем backend в путь для импортов ДО всех остальных импортов
THIS = Path(__file__).resolve()
# Скрипт может быть в backend/scripts/ или в scripts/ на хосте
if THIS.parent.name == "scripts" and THIS.parent.parent.name == "backend":
    # backend/scripts/retry_leads_with_new_fields.py
    BACKEND_DIR = THIS.parent.parent  # /opt/HostFlow/backend
    PROJECT_ROOT = BACKEND_DIR.parent  # /opt/HostFlow
else:
    # scripts/retry_leads_with_new_fields.py (на хосте)
    PROJECT_ROOT = THIS.parent.parent  # /opt/HostFlow
    BACKEND_DIR = PROJECT_ROOT / "backend"

# Добавляем корень проекта для импорта backend.app
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Также добавляем backend для совместимости
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import argparse
import asyncio
import json
from typing import List, Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings  # noqa: F401 - ensure settings initialised
from backend.app.db.session import async_session_maker
from backend.app.models import Lead
from backend.app.modules.leads import service


# Новые поля, которые нужно искать
NEW_FIELDS = [
    "ce_driving_experience_in_europe",
    "preferred_way_of_contact",
    "what_is_the_legal_basis_of_your_stay_in_poland?",
    "what_is_the_legal_basis_of_your_stay_in_poland",  # без знака вопроса
]


def _has_new_fields(payload: dict) -> bool:
    """Проверяет наличие новых полей в payload лида."""
    if not payload or not isinstance(payload, dict):
        return False
    
    # Проверяем в field_data
    entry = payload.get("entry") or []
    if not entry:
        return False
    
    for entry_item in entry:
        if not isinstance(entry_item, dict):
            continue
        changes = entry_item.get("changes") or []
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value") or {}
            if not isinstance(value, dict):
                continue
            field_data = value.get("field_data") or []
            if not isinstance(field_data, list):
                continue
            
            # Проверяем наличие новых полей
            field_names = {item.get("name") for item in field_data if isinstance(item, dict)}
            for new_field in NEW_FIELDS:
                if new_field in field_names:
                    return True
    
    return False


async def find_leads_with_new_fields(
    db: AsyncSession,
    tenant_id: str,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Lead]:
    """Находит лиды с новыми полями в payload."""
    filters = [
        Lead.tenant_id == tenant_id,
        Lead.source == "meta",
    ]
    
    if status:
        filters.append(Lead.status == status)
    
    stmt = select(Lead).where(*filters).order_by(Lead.created_at.desc())
    
    if limit:
        stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    all_leads = result.scalars().all()
    
    # Фильтруем по наличию новых полей
    leads_with_new_fields = []
    for lead in all_leads:
        payload = lead.payload
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                continue
        
        if _has_new_fields(payload):
            leads_with_new_fields.append(lead)
    
    return leads_with_new_fields


async def _run(
    tenant_id: str,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    refresh_graph: bool = True,
    dry_run: bool = False,
) -> None:
    """Основная функция для поиска и перезапуска лидов."""
    async with async_session_maker() as session:
        # Находим лиды с новыми полями
        print(f"Поиск лидов с новыми полями (tenant: {tenant_id})...")
        leads = await find_leads_with_new_fields(
            session,
            tenant_id=tenant_id,
            status=status,
            limit=limit,
        )
        
        print(f"Найдено лидов с новыми полями: {len(leads)}")
        
        if not leads:
            print("Нет лидов для перезапуска.")
            return
        
        if dry_run:
            print("\n=== DRY RUN MODE ===")
            print("Лиды, которые будут перезапущены:")
            for lead in leads[:10]:  # Показываем первые 10
                print(f"  - {lead.id} (status: {lead.status}, candidate: {lead.candidate_id})")
            if len(leads) > 10:
                print(f"  ... и еще {len(leads) - 10} лидов")
            return
        
        # Перезапускаем обработку
        lead_ids = [lead.id for lead in leads]
        print(f"\nПерезапуск обработки {len(lead_ids)} лидов...")
        
        outcomes = await service.retry_meta_leads(
            session,
            tenant_id=tenant_id,
            own_company_id=None,
            lead_ids=lead_ids,
            statuses=None,  # Уже фильтруем по ID
            limit=None,
            refresh_graph=refresh_graph,
        )
        
        await session.commit()
        
        # Статистика
        summary = {
            "total": len(outcomes),
            "processed": sum(1 for item in outcomes if item.processed),
            "failed": sum(
                1
                for item in outcomes
                if not item.processed and (item.message is None or "payload" not in (item.message or "").lower())
            ),
            "skipped": sum(
                1
                for item in outcomes
                if item.message and "payload is empty" in item.message.lower()
            ),
        }
        
        print("\n=== Результаты ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
        # Детали для первых 20
        if outcomes:
            details = [
                {
                    "lead_id": item.lead_id,
                    "status_before": item.status_before,
                    "status_after": item.status_after,
                    "candidate_id": item.candidate_id,
                    "processed": item.processed,
                    "message": item.message,
                }
                for item in outcomes[:20]
            ]
            print("\n=== Детали (первые 20) ===")
            print(json.dumps(details, indent=2, ensure_ascii=False))
            if len(outcomes) > 20:
                print(f"\n... и еще {len(outcomes) - 20} результатов")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Перезапуск обработки лидов Meta с новыми полями для заполнения карточек кандидатов."
    )
    parser.add_argument(
        "--tenant",
        default="11111111-1111-1111-1111-111111111111",
        help="Tenant UUID scope",
    )
    parser.add_argument(
        "--status",
        help="Фильтр по статусу лида (например: processed, duplicated). По умолчанию - все статусы",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Ограничение количества лидов для обработки",
    )
    parser.add_argument(
        "--no-graph",
        action="store_true",
        help="Пропустить обогащение через Graph API при перезапуске",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать какие лиды будут перезапущены, без фактического перезапуска",
    )

    args = parser.parse_args()

    asyncio.run(
        _run(
            tenant_id=args.tenant,
            status=args.status,
            limit=args.limit,
            refresh_graph=not args.no_graph,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()

