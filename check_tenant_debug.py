#!/usr/bin/env python3
"""
Скрипт для проверки типа тенанта и настроек маскирования
Использование: python check_tenant_debug.py citronex@hostflow.dev
"""

import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Добавьте путь к вашему проекту
sys.path.insert(0, '/opt/HostFlow')

from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant, TenantLink
from backend.app.models.user import User
from backend.app.services.handoff import is_client_tenant_for_list


async def check_tenant(email: str):
    """Проверяет тип тенанта и настройки маскирования"""
    async with async_session_maker() as db:
        # Найти пользователя
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ Пользователь {email} не найден")
            return
        
        tenant_id = user.tenant_id
        print(f"✅ Пользователь найден: {user.email}")
        print(f"   Tenant ID: {tenant_id}")
        
        # Найти tenant
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            print(f"❌ Tenant {tenant_id} не найден")
            return
        
        print(f"\n📋 Информация о тенанте:")
        print(f"   ID: {tenant.id}")
        print(f"   Name: {tenant.name}")
        print(f"   Slug: {tenant.slug}")
        print(f"   Type: {tenant.type}")
        print(f"   Status: {tenant.status}")
        
        # Проверить is_client_tenant_for_list
        is_client = await is_client_tenant_for_list(db, tenant_id)
        print(f"\n🔍 Результат is_client_tenant_for_list:")
        print(f"   Результат: {is_client}")
        
        # Проверить TenantLink
        result = await db.execute(
            select(TenantLink).where(
                (TenantLink.client_tenant_id == tenant_id) |
                (TenantLink.agency_tenant_id == tenant_id)
            ).where(TenantLink.status == "active")
        )
        links = result.scalars().all()
        
        print(f"\n🔗 TenantLinks:")
        if links:
            for link in links:
                print(f"   Link ID: {link.id}")
                print(f"   Agency Tenant ID: {link.agency_tenant_id}")
                print(f"   Client Tenant ID: {link.client_tenant_id}")
                print(f"   Client Company ID: {link.client_company_id}")
                print(f"   Status: {link.status}")
                print()
        else:
            print("   Нет активных TenantLinks")
        
        # Вывод рекомендаций
        print(f"\n💡 Рекомендации:")
        if tenant.type != "company":
            print(f"   ⚠️  Tenant type = '{tenant.type}', должен быть 'company' для клиентского тенанта")
            print(f"   💡 Решение: Обновите type в таблице tenants на 'company'")
        
        if not is_client:
            if tenant.type != "company" and not links:
                print(f"   ⚠️  Tenant не определяется как клиентский")
                print(f"   💡 Решение 1: Установите tenant.type = 'company'")
                print(f"   💡 Решение 2: Создайте TenantLink где client_tenant_id = {tenant_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python check_tenant_debug.py <email>")
        print("Пример: python check_tenant_debug.py citronex@hostflow.dev")
        sys.exit(1)
    
    email = sys.argv[1]
    asyncio.run(check_tenant(email))
