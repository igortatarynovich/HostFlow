#!/usr/bin/env python3
"""Backfill lead RODO undelivered/deferred from Gmail DSN notices (ops).

Usage (inside backend container or venv with DATABASE_URL):

  PYTHONPATH=/app:/app/backend python backend/scripts/backfill_lead_rodo_delivery_feedback.py \\
    --tenant-id 9497fc29-6051-424d-9344-abb4aed9b110 --days 7 --dry-run

  PYTHONPATH=/app:/app/backend python backend/scripts/backfill_lead_rodo_delivery_feedback.py \\
    --tenant-id ... --days 7 --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

import httpx
from sqlalchemy import select, text

from backend.app.core.crypto import decrypt_secret
from backend.app.db.session import async_session_maker
from backend.app.models.communication import CommunicationChannelAccount
from backend.app.services.communications_oauth import refresh_oauth_access_token
from backend.app.services.lead_rodo_delivery_feedback import (
    maybe_apply_rodo_delivery_feedback_from_inbound,
)


def _body_of(dj: dict) -> str:
    import base64

    texts: list[str] = []

    def walk(p: dict | None) -> None:
        if not p:
            return
        data = (p.get("body") or {}).get("data")
        if data and str(p.get("mimeType") or "").startswith("text/"):
            texts.append(base64.urlsafe_b64decode(data + "===").decode("utf-8", "replace"))
        for c in p.get("parts") or []:
            walk(c)

    walk(dj.get("payload") if isinstance(dj.get("payload"), dict) else None)
    return "\n".join(texts)


async def _gmail_token(settings_json: dict) -> str:
    oauth = settings_json.get("oauth") if isinstance(settings_json.get("oauth"), dict) else {}
    tok = await refresh_oauth_access_token(
        provider="gmail",
        refresh_token=decrypt_secret(str(oauth.get("refresh_token_encrypted") or "")) or "",
        client_id=str(oauth.get("client_id") or ""),
        client_secret=decrypt_secret(str(oauth.get("client_secret_encrypted") or "")) or "",
    )
    return tok.access_token


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        print("Pass --dry-run or --apply", file=sys.stderr)
        return 2

    tenant_id = args.tenant_id
    updated_total = 0
    scanned = 0

    async with async_session_maker() as db:
        await db.execute(text("SELECT set_config('app.bypass_rls','true', true)"))
        acc = (
            await db.execute(
                select(CommunicationChannelAccount).where(
                    CommunicationChannelAccount.tenant_id == tenant_id,
                    CommunicationChannelAccount.channel == "email",
                    CommunicationChannelAccount.is_active.is_(True),
                )
            )
        ).scalars().first()
        if acc is None:
            print("No active email channel account", file=sys.stderr)
            return 1
        settings_json = acc.settings_json if isinstance(acc.settings_json, dict) else {}
        token = await _gmail_token(settings_json)
        inbox = str(acc.inbox_address or "")

        q = (
            f'newer_than:{int(args.days)}d '
            f'("Адрес не найден" OR "Пока не доставлено" OR "Address not found" '
            f'OR "Not yet delivered" OR subject:undeliverable OR from:mailer-daemon)'
        )
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=60) as client:
            page_token = None
            while True:
                params: dict = {"q": q, "maxResults": 50}
                if page_token:
                    params["pageToken"] = page_token
                r = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    headers=headers,
                    params=params,
                )
                r.raise_for_status()
                data = r.json()
                for m in data.get("messages") or []:
                    scanned += 1
                    mid = m["id"]
                    det = await client.get(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}",
                        headers=headers,
                        params={"format": "full"},
                    )
                    det.raise_for_status()
                    dj = det.json()
                    hdrs = {
                        h["name"].lower(): h["value"]
                        for h in (dj.get("payload") or {}).get("headers") or []
                        if isinstance(h, dict)
                    }
                    subject = hdrs.get("subject")
                    from_address = hdrs.get("from")
                    body = (dj.get("snippet") or "") + "\n" + _body_of(dj)
                    if args.dry_run:
                        from backend.app.services.lead_rodo_delivery_feedback import (
                            parse_rodo_delivery_feedback,
                        )

                        parsed = parse_rodo_delivery_feedback(
                            subject=subject,
                            body_text=body,
                            from_address=from_address,
                            exclude_addresses={inbox.lower()} if inbox else set(),
                        )
                        print(
                            json.dumps(
                                {
                                    "gmail_id": mid,
                                    "parsed": None
                                    if parsed is None
                                    else {
                                        "recipient": parsed.recipient_email,
                                        "outcome": parsed.outcome,
                                        "reason_code": parsed.reason_code,
                                    },
                                },
                                ensure_ascii=False,
                            )
                        )
                        continue
                    ids = await maybe_apply_rodo_delivery_feedback_from_inbound(
                        db,
                        tenant_id=tenant_id,
                        subject=subject,
                        body_text=body,
                        from_address=from_address,
                        external_message_ref=mid,
                        inbox_address=inbox,
                    )
                    if ids:
                        updated_total += len(ids)
                        print(json.dumps({"gmail_id": mid, "updated_leads": ids}))
                page_token = data.get("nextPageToken")
                if not page_token or scanned >= 200:
                    break
        if args.apply:
            await db.commit()

    print(json.dumps({"scanned": scanned, "updated_leads": updated_total, "dry_run": args.dry_run}))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
