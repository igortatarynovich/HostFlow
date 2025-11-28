#!/usr/bin/env python3
"""
Скрипт для тестирования Document Scanner.

Использование:
    python test_scanner.py --tenant-id <TENANT_ID> --doc-type driver_license
    python test_scanner.py --tenant-id <TENANT_ID> --doc-type passport --image /path/to/image.jpg
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

import httpx

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000"


async def create_intake(tenant_id: str) -> dict:
    """Создать публичную заявку и получить token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/v1/public/intake",
            headers={"X-Tenant-Id": tenant_id, "Content-Type": "application/json"},
            json={
                "contacts": {
                    "phone_country_code": "+48",
                    "phone": f"555{str(uuid4())[:6].replace('-', '')}",
                },
                "email": f"test+{str(uuid4())[:8]}@example.com",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def create_scan_session(tenant_id: str, token: str, doc_type: str) -> dict:
    """Создать сессию сканирования."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/v1/public/scan-sessions",
            headers={"X-Tenant-Id": tenant_id, "Content-Type": "application/json"},
            json={"token": token, "document_type": doc_type},
        )
        resp.raise_for_status()
        return resp.json()


async def upload_page(
    tenant_id: str, session_id: str, page_code: str, image_path: Path | None = None
) -> dict:
    """Загрузить страницу документа."""
    if image_path and image_path.exists():
        files = {"file": (image_path.name, image_path.read_bytes(), "image/jpeg")}
    else:
        # Создаём минимальный тестовый JPEG (1x1 пиксель)
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="white")
        import io

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        files = {"file": ("test.jpg", buf.getvalue(), "image/jpeg")}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/v1/public/scan-sessions/{session_id}/pages",
            headers={"X-Tenant-Id": tenant_id},
            data={"page_code": page_code, "rotation": "0"},
            files=files,
        )
        resp.raise_for_status()
        return resp.json()


async def process_session(tenant_id: str, session_id: str) -> dict:
    """Обработать сессию сканирования."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/v1/public/scan-sessions/{session_id}/process",
            headers={"X-Tenant-Id": tenant_id},
        )
        resp.raise_for_status()
        return resp.json()


async def get_session(tenant_id: str, session_id: str) -> dict:
    """Получить статус сессии."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/api/v1/public/scan-sessions/{session_id}",
            headers={"X-Tenant-Id": tenant_id},
        )
        resp.raise_for_status()
        return resp.json()


async def list_presets(tenant_id: str) -> list[dict]:
    """Получить список доступных пресетов."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/api/v1/public/scan/presets",
            headers={"X-Tenant-Id": tenant_id},
        )
        resp.raise_for_status()
        return resp.json()


async def main():
    parser = argparse.ArgumentParser(description="Test Document Scanner")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID")
    parser.add_argument("--doc-type", default="driver_license", help="Document type")
    parser.add_argument("--image", type=Path, help="Path to test image")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")
    parser.add_argument("--web-url", action="store_true", help="Generate web URL for testing")

    args = parser.parse_args()

    if args.list_presets:
        print("📋 Available scanner presets:")
        presets = await list_presets(args.tenant_id)
        for preset in presets:
            print(f"  • {preset['code']:30s} - {preset['name']}")
            print(f"    Pages: {', '.join(preset['expected_pages'])}")
        return

    print("🔍 Testing Document Scanner...")
    print(f"   Document type: {args.doc_type}")
    print(f"   Tenant ID: {args.tenant_id}")

    # Step 1: Create intake
    print("\n1️⃣ Creating public intake...")
    intake = await create_intake(args.tenant_id)
    token = intake["token"]
    candidate_id = intake["candidate_id"]
    print(f"   ✓ Token: {token[:20]}...")
    print(f"   ✓ Candidate ID: {candidate_id}")

    if args.web_url:
        print(f"\n🌐 Web URL for testing:")
        print(f"   https://hostflow.cc/public/scan?token={token}&doc={args.doc_type}")

    # Step 2: Create scan session
    print("\n2️⃣ Creating scan session...")
    session = await create_scan_session(args.tenant_id, token, args.doc_type)
    session_id = session["id"]
    print(f"   ✓ Session ID: {session_id}")
    print(f"   ✓ Expected pages: {', '.join(session['expected_pages'])}")
    print(f"   ✓ Preset: {session['preset_code']}")

    # Step 3: Upload pages
    print("\n3️⃣ Uploading pages...")
    for page_code in session["expected_pages"]:
        print(f"   Uploading {page_code}...")
        upload_result = await upload_page(
            args.tenant_id, session_id, page_code, args.image
        )
        page_status = next(
            (p["status"] for p in upload_result["pages"] if p["page_code"] == page_code),
            "unknown",
        )
        print(f"   ✓ {page_code}: {page_status}")

    # Step 4: Process session
    print("\n4️⃣ Processing session...")
    processed = await process_session(args.tenant_id, session_id)
    print(f"   ✓ Status: {processed['status']}")

    # Step 5: Get results
    print("\n5️⃣ Results:")
    final = await get_session(args.tenant_id, session_id)
    for page in final["pages"]:
        quality = page.get("quality_score", "N/A")
        quality_level = page.get("quality_level", "N/A")
        issues = page.get("issues", [])
        print(f"   • {page['page_code']}:")
        print(f"     Status: {page['status']}")
        print(f"     Quality: {quality} ({quality_level})")
        if issues:
            print(f"     Issues: {', '.join(issues)}")
        if page.get("preview_url"):
            print(f"     Preview: {BASE_URL}{page['preview_url']}")

    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())

