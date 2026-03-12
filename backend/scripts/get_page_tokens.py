#!/usr/bin/env python3
"""
Скрипт для получения Page Access Tokens для каждой страницы используя User Access Token.

Использование:
    docker compose exec backend python backend/scripts/get_page_tokens.py \
      --user-token <USER_ACCESS_TOKEN> \
      --page-ids 484113398123847,259905353877064
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
import httpx


async def get_page_token(user_token: str, page_id: str) -> dict:
    """Получает Page Access Token для страницы."""
    url = f"https://graph.facebook.com/v21.0/{page_id}"
    params = {
        "fields": "access_token,name",
        "access_token": user_token,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return {
                "page_id": page_id,
                "page_name": data.get("name", "Unknown"),
                "access_token": data.get("access_token"),
                "success": True,
            }
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            return {
                "page_id": page_id,
                "success": False,
                "error": error_data.get("error", {}).get("message", str(e)),
                "code": error_data.get("error", {}).get("code"),
            }
        except Exception as e:
            return {
                "page_id": page_id,
                "success": False,
                "error": str(e),
            }


async def main(user_token: str, page_ids: list[str]) -> None:
    """Получает токены для всех указанных страниц."""
    print(f"Получение Page Access Tokens для {len(page_ids)} страниц...\n")
    
    results = []
    for page_id in page_ids:
        print(f"📄 Страница {page_id}...")
        result = await get_page_token(user_token, page_id)
        results.append(result)
        
        if result["success"]:
            print(f"   ✅ Успешно!")
            print(f"   Название: {result.get('page_name', 'N/A')}")
            print(f"   Token: {result['access_token'][:30]}...{result['access_token'][-10:]}")
        else:
            print(f"   ❌ Ошибка: {result.get('error', 'Unknown')}")
            if result.get("code"):
                print(f"   Код ошибки: {result['code']}")
        print()
    
    print("=== Результаты ===")
    print("\nДля обновления credentials используйте:")
    print("\n# Обновить все credentials одним токеном (если один токен работает для всех):")
    print("docker compose exec backend python backend/scripts/update_meta_tokens.py \\")
    print("  --tenant 11111111-1111-1111-1111-111111111111 \\")
    print("  --access-token '<TOKEN>'")
    print("\n# Или обновить каждый credential отдельно:")
    for result in results:
        if result["success"]:
            print(f"\n# Для страницы {result['page_id']} ({result.get('page_name', 'N/A')}):")
            print(f"docker compose exec backend python backend/scripts/update_meta_tokens.py \\")
            print(f"  --tenant 11111111-1111-1111-1111-111111111111 \\")
            print(f"  --credential-id <CREDENTIAL_ID> \\")
            print(f"  --access-token '{result['access_token']}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Получение Page Access Tokens")
    parser.add_argument(
        "--user-token",
        required=True,
        help="User Access Token от Meta",
    )
    parser.add_argument(
        "--page-ids",
        required=True,
        help="Список page_id через запятую (например: 484113398123847,259905353877064)",
    )
    
    args = parser.parse_args()
    page_ids = [pid.strip() for pid in args.page_ids.split(",") if pid.strip()]
    
    asyncio.run(main(args.user_token, page_ids))

