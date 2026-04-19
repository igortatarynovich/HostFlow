#!/usr/bin/env python3
"""
Скрипт для проверки и диагностики токенов доступа Meta Leads.

Проверяет:
- Какие credentials есть в системе
- Какие page_id используются
- Сколько лидов с ошибкой GRAPH_190
- Предлагает решение
"""
from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в путь для импортов ДО всех остальных импортов
THIS = Path(__file__).resolve()
# Скрипт может быть в backend/scripts/ или в scripts/ на хосте
if THIS.parent.name == "scripts" and THIS.parent.parent.name == "backend":
    # backend/scripts/check_meta_tokens.py
    BACKEND_DIR = THIS.parent.parent  # /opt/HostFlow/backend
    PROJECT_ROOT = BACKEND_DIR.parent  # /opt/HostFlow
else:
    # scripts/check_meta_tokens.py (на хосте)
    PROJECT_ROOT = THIS.parent.parent  # /opt/HostFlow
    BACKEND_DIR = PROJECT_ROOT / "backend"

# Добавляем корень проекта для импорта backend.app
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Также добавляем backend для совместимости
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import asyncio
import json
from backend.app.core.crypto import decrypt_secret
from backend.app.db.session import async_session_maker
from backend.app.modules.leads import crud


async def check_tokens(tenant_id: str) -> None:
    """Проверяет credentials и лиды с ошибками."""
    async with async_session_maker() as db:
        # Получаем credentials
        credentials = await crud.list_meta_credentials(db, tenant_id=tenant_id)
        
        print(f"\n=== Credentials для tenant {tenant_id} ===\n")
        if not credentials:
            print("❌ Credentials не найдены!")
            return
        
        for cred in credentials:
            page_id = decrypt_secret(cred.encrypted_page_id) if cred.encrypted_page_id else None
            ad_account_id = (
                decrypt_secret(cred.encrypted_ad_account_id) if cred.encrypted_ad_account_id else None
            )
            has_token = bool(cred.encrypted_access_token)
            
            print(f"📋 {cred.label}")
            print(f"   ID: {cred.id}")
            print(f"   Status: {cred.status}")
            print(f"   Page ID: {page_id or 'НЕ УКАЗАН'}")
            print(f"   Ad account ID: {ad_account_id or 'НЕ УКАЗАН'}")
            print(f"   Has Access Token: {'✅' if has_token else '❌'}")
            print(f"   Last Verified: {cred.last_verified_at or 'НИКОГДА'}")
            print(f"   Last Rotation: {cred.last_rotation_at or 'НИКОГДА'}")
            print()
        
        # Проверяем лиды с ошибками
        from sqlalchemy import func, select
        from backend.app.models import Lead
        
        stmt = select(
            func.count().label("total"),
            func.count(Lead.id).filter(Lead.error == "GRAPH_190").label("graph_190"),
            func.count(Lead.id).filter(Lead.error == "GRAPH_NO_TOKEN").label("no_token"),
            func.count(Lead.id).filter(Lead.status == "failed").label("failed"),
        ).where(
            Lead.tenant_id == tenant_id,
            Lead.source == "meta",
        )
        result = await db.execute(stmt)
        row = result.first()
        
        print("=== Статистика лидов ===\n")
        print(f"Всего лидов: {row.total or 0}")
        print(f"Ошибка GRAPH_190 (недействительный токен): {row.graph_190 or 0}")
        print(f"Ошибка GRAPH_NO_TOKEN (нет токена): {row.no_token or 0}")
        print(f"Всего failed: {row.failed or 0}")
        print()
        
        # Рекомендации
        print("=== Рекомендации ===\n")
        
        if row.graph_190 and row.graph_190 > 0:
            print("⚠️  Обнаружены лиды с ошибкой GRAPH_190 (недействительный токен)")
            print("\n📝 Решение:")
            print("1. Получите новый Page Access Token через Graph API Explorer:")
            print("   - Откройте https://developers.facebook.com/tools/explorer/")
            print("   - Выберите приложение 'HostFlow Leads' (ID: 1102404865044655)")
            print("   - Включите права: pages_read_engagement, pages_manage_metadata, leads_retrieval")
            print("   - Сгенерируйте User Access Token")
            print("   - Обменяйте на long-lived token через:")
            print("     GET /oauth/access_token?grant_type=fb_exchange_token&client_id=...&client_secret=...&fb_exchange_token=...")
            print("   - Получите Page Access Token через:")
            print("     GET /{page-id}?fields=access_token")
            print()
            print("2. Обновите токен в HostFlow:")
            print("   - Через админку: Settings → Integrations → Meta Leads")
            print("   - Или через API: PATCH /api/v1/admin/meta-leads/credentials/{credential_id}")
            print("     {")
            print('       "access_token": "НОВЫЙ_ТОКЕН"')
            print("     }")
            print()
            print("3. Перезапустите обработку лидов с ошибкой:")
            print("   docker compose exec backend python backend/scripts/retry_meta_leads.py \\")
            print("     --tenant 11111111-1111-1111-1111-111111111111 \\")
            print("     --status failed")
            print()
        
        if not credentials or not any(cred.encrypted_access_token for cred in credentials):
            print("⚠️  Не все credentials имеют access_token!")
            print("   Обновите access_token для каждого credential через админку или API.")
            print()


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="Проверка токенов Meta Leads")
    parser.add_argument(
        "--tenant",
        default="11111111-1111-1111-1111-111111111111",
        help="Tenant UUID",
    )
    
    args = parser.parse_args()
    asyncio.run(check_tokens(args.tenant))


if __name__ == "__main__":
    main()

