from __future__ import annotations

# backend/app/services/notifications.py
import os
from typing import Any, Dict, List, Optional

import httpx

WEBHOOK_URL = os.getenv("WEBHOOK_URL") or ""
WEBHOOK_TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT") or "3")


async def send_webhook(
    event: str, payload: Dict[str, Any], webhook_url: Optional[str] = None
) -> None:
    """
    Отправляет POST webhook с JSON телом:
    {
      "event": "<event_name>",
      "payload": { ... },
      "source": "hostflow"
    }
    Если WEBHOOK_URL не задан — тихо выходим.
    Ошибки сети не пробрасываем (чтобы не ломать основной поток).
    """
    url = (webhook_url or WEBHOOK_URL).strip()
    if not url:
        return

    body = {
        "event": event,
        "payload": payload,
        "source": "hostflow",
    }

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
            await client.post(
                url, json=body, headers={"Content-Type": "application/json"}
            )
    except Exception:
        # можно залогировать при необходимости
        return


# Совместимость со старым кодом: некоторые места импортируют notify(...)
# Делаем простую обёртку, которая шлёт webhook "notify".
async def notify(
    to: str,
    subject: str,
    text: str,
    *,
    template_key: Optional[str] = None,
    template_context: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "to": to,
        "subject": subject,
        "text": text,
    }
    if template_key:
        payload["template_key"] = template_key
    if template_context:
        payload["template_context"] = template_context
    if channels:
        payload["channels"] = channels
    await send_webhook("notify", payload)
