#!/usr/bin/env python3
"""
Скрипт для обновления токенов доступа Meta Leads.

Использование:
    docker compose exec backend python backend/scripts/update_meta_tokens.py \
      --tenant 11111111-1111-1111-1111-111111111111 \
      --credential-id <credential_id> \
      --access-token <новый_токен>
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


async def update_token(
    tenant_id: str,
    credential_id: str,
    access_token: str,
    dry_run: bool = False,
) -> None:
    """Обновляет access_token для credential."""
    async with async_session_maker() as db:
        from backend.app.modules.leads.schemas import MetaCredentialUpdate
        
        if dry_run:
            print(f"[DRY RUN] Обновление токена для credential {credential_id}")
            print(f"  Tenant: {tenant_id}")
            print(f"  Access Token: {access_token[:20]}...{access_token[-10:]}")
            return
        
        payload = MetaCredentialUpdate(access_token=access_token)
        result = await admin_service.update_credential(
            db,
            tenant_id=tenant_id,
            credential_id=credential_id,
            payload=payload,
        )
        await db.commit()
        
        print(f"✅ Токен обновлен для credential: {result.label}")
        print(f"   ID: {result.id}")
        print(f"   Status: {result.status}")


async def update_all_credentials(
    tenant_id: str,
    access_token: str,
    dry_run: bool = False,
) -> None:
    """Обновляет токен для всех активных credentials."""
    async with async_session_maker() as db:
        from backend.app.modules.leads import crud
        
        credentials = await crud.list_meta_credentials(db, tenant_id=tenant_id)
        active_credentials = [c for c in credentials if c.status == "active"]
        
        if not active_credentials:
            print("❌ Не найдено активных credentials")
            return
        
        print(f"Найдено активных credentials: {len(active_credentials)}")
        
        for cred in active_credentials:
            print(f"\n📋 Обновление: {cred.label} (ID: {cred.id})")
            await update_token(tenant_id, cred.id, access_token, dry_run=dry_run)
            if not dry_run:
                await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Обновление токенов Meta Leads")
    parser.add_argument(
        "--tenant",
        default="11111111-1111-1111-1111-111111111111",
        help="Tenant UUID",
    )
    parser.add_argument(
        "--credential-id",
        help="ID конкретного credential для обновления (если не указан - обновляются все активные)",
    )
    parser.add_argument(
        "--access-token",
        required=True,
        help="Новый Page Access Token",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать что будет обновлено, без фактического обновления",
    )
    
    args = parser.parse_args()
    
    if args.credential_id:
        asyncio.run(update_token(
            args.tenant,
            args.credential_id,
            args.access_token,
            args.dry_run,
        ))
    else:
        asyncio.run(update_all_credentials(
            args.tenant,
            args.access_token,
            args.dry_run,
        ))


if __name__ == "__main__":
    main()

