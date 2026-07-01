#!/usr/bin/env python3
"""
Скрипт для исправления дубликатов кандидатов.

Находит кандидатов с одинаковыми телефонами (по цифрам) и объединяет их,
помечая более поздние лиды как дубликаты.
"""
from __future__ import annotations

import sys
from pathlib import Path

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
import re
from backend.app.db.session import async_session_maker
from backend.app.modules.leads import crud
from sqlalchemy import select, func, text
from backend.app.models import Candidate, Lead


async def find_duplicate_candidates_by_phone(
    tenant_id: str,
    phone_pattern: str | None = None,
) -> list[dict]:
    """Находит кандидатов с одинаковыми телефонами (по цифрам)."""
    async with async_session_maker() as db:
        # Получаем всех кандидатов с телефонами
        stmt_all = (
            select(
                Candidate.id,
                Candidate.phone,
                Candidate.created_at,
                func.regexp_replace(
                    func.coalesce(Candidate.phone, ""),
                    r"[^0-9]",
                    "",
                    "g"
                ).label("phone_digits"),
            )
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
                Candidate.phone.isnot(None),
                Candidate.phone != "",
            )
        )
        
        if phone_pattern:
            pattern_digits = re.sub(r"\D", "", phone_pattern)
            phone_digits_expr = func.regexp_replace(
                func.coalesce(Candidate.phone, ""),
                r"[^0-9]",
                "",
                "g"
            )
            stmt_all = stmt_all.where(phone_digits_expr.like(f"%{pattern_digits}%"))
        
        result_all = await db.execute(stmt_all)
        candidates = result_all.all()
        
        # Группируем кандидатов по совпадению телефонов
        # Сравниваем по полным цифрам и по последним 9-10 цифрам
        groups: dict[str, list] = {}
        
        for cand in candidates:
            phone_digits = cand.phone_digits or ""
            if not phone_digits:
                continue
            
            # Ищем группу для этого кандидата
            matched_group_key = None
            
            # Проверяем существующие группы
            for group_key, group_candidates in groups.items():
                # Сравниваем с каждым кандидатом в группе
                for group_cand in group_candidates:
                    group_phone_digits = group_cand["phone_digits"]
                    
                    # Точное совпадение
                    if phone_digits == group_phone_digits:
                        matched_group_key = group_key
                        break
                    
                    # Совпадение по последним 9-10 цифрам (для случаев с/без кода страны)
                    if len(phone_digits) >= 9 and len(group_phone_digits) >= 9:
                        last_9_input = phone_digits[-9:]
                        last_9_group = group_phone_digits[-9:]
                        if last_9_input == last_9_group:
                            matched_group_key = group_key
                            break
                    
                    # Также проверяем последние 10 цифр
                    if len(phone_digits) >= 10 and len(group_phone_digits) >= 10:
                        last_10_input = phone_digits[-10:]
                        last_10_group = group_phone_digits[-10:]
                        if last_10_input == last_10_group:
                            matched_group_key = group_key
                            break
                
                if matched_group_key:
                    break
            
            # Добавляем кандидата в группу или создаем новую
            if matched_group_key:
                groups[matched_group_key].append({
                    "id": cand.id,
                    "phone": cand.phone,
                    "phone_digits": phone_digits,
                    "created_at": cand.created_at,
                })
            else:
                # Создаем новую группу
                group_key = phone_digits[-9:] if len(phone_digits) >= 9 else phone_digits
                groups[group_key] = [{
                    "id": cand.id,
                    "phone": cand.phone,
                    "phone_digits": phone_digits,
                    "created_at": cand.created_at,
                }]
        
        # Фильтруем только группы с дубликатами
        duplicates = []
        for group_key, group_candidates in groups.items():
            if len(group_candidates) > 1:
                duplicates.append({
                    "phone_digits": group_key,
                    "candidate_ids": [c["id"] for c in group_candidates],
                    "phones": [c["phone"] for c in group_candidates],
                    "created_ats": [c["created_at"] for c in group_candidates],
                    "count": len(group_candidates),
                })
        
        return duplicates


async def fix_duplicates(
    tenant_id: str,
    phone_pattern: str | None = None,
    dry_run: bool = False,
) -> None:
    """Исправляет дубликаты кандидатов."""
    duplicates = await find_duplicate_candidates_by_phone(tenant_id, phone_pattern)
    
    if not duplicates:
        print("Дубликаты не найдены.")
        return
    
    print(f"Найдено групп дубликатов: {len(duplicates)}\n")
    
    async with async_session_maker() as db:
        for group in duplicates:
            phone_digits = group["phone_digits"]
            candidate_ids = group["candidate_ids"]
            phones = group["phones"]
            created_ats = group["created_ats"]
            
            print(f"📞 Телефон (цифры): {phone_digits}")
            print(f"   Кандидатов: {len(candidate_ids)}")
            
            # Сортируем по дате создания (самый старый - основной)
            sorted_candidates = sorted(
                zip(candidate_ids, phones, created_ats),
                key=lambda x: x[2]
            )
            
            main_candidate_id = sorted_candidates[0][0]
            main_phone = sorted_candidates[0][1]
            duplicate_candidate_ids = [c[0] for c in sorted_candidates[1:]]
            
            print(f"   Основной кандидат: {main_candidate_id} (создан {sorted_candidates[0][2]})")
            print(f"   Телефон: {main_phone}")
            print(f"   Дубликаты: {len(duplicate_candidate_ids)}")
            
            for dup_id, dup_phone, dup_created in sorted_candidates[1:]:
                print(f"     - {dup_id} (создан {dup_created}, телефон: {dup_phone})")
            
            if not dry_run:
                # Обновляем лиды, связанные с дубликатами
                for dup_id in duplicate_candidate_ids:
                    # Находим лиды, связанные с дубликатом
                    stmt_leads = select(Lead).where(
                        Lead.tenant_id == tenant_id,
                        Lead.candidate_id == dup_id,
                    )
                    result_leads = await db.execute(stmt_leads)
                    leads = result_leads.scalars().all()
                    
                    for lead in leads:
                        # Обновляем лид: меняем candidate_id на основной и статус на duplicated
                        await crud.update_lead(
                            db,
                            lead,
                            status="duplicated",
                            candidate_id=main_candidate_id,
                        )
                        print(f"     ✅ Лид {lead.id} обновлен: candidate_id = {main_candidate_id}, status = duplicated")
                
                await db.commit()
                print(f"   ✅ Группа обработана\n")
            else:
                print(f"   [DRY RUN] Группа будет обработана\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Исправление дубликатов кандидатов")
    parser.add_argument(
        "--tenant",
        default="11111111-1111-1111-1111-111111111111",
        help="Tenant UUID",
    )
    parser.add_argument(
        "--phone",
        help="Паттерн телефона для поиска (опционально)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать что будет исправлено, без фактического исправления",
    )
    
    args = parser.parse_args()
    asyncio.run(fix_duplicates(args.tenant, args.phone, args.dry_run))


if __name__ == "__main__":
    main()

