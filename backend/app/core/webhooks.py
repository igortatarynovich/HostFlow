from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, Optional

import httpx

WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL")
WEBHOOK_TIMEOUT: float = float(os.getenv("WEBHOOK_TIMEOUT", "3"))
WEBHOOK_MAX_RETRIES: int = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))
WEBHOOK_RETRY_BASE_SEC: float = float(os.getenv("WEBHOOK_RETRY_BASE_SEC", "1.0"))


async def _post_once(event: str, payload: Dict[str, Any]) -> int:
    if not WEBHOOK_URL:
        return 0  # вебхуки выключены
    async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
        r = await client.post(
            WEBHOOK_URL,
            headers={"Content-Type": "application/json", "X-Event": event},
            content=json.dumps(payload, default=str),
        )
        return r.status_code


async def send_webhook(event: str, payload: Dict[str, Any]) -> None:
    """
    Отправка с ретраями (1, 2, 4 сек…) при 5xx/таймауте/сетевой ошибке.
    Не бросает исключений наружу.
    """
    if not WEBHOOK_URL:
        return
    delay = WEBHOOK_RETRY_BASE_SEC
    for attempt in range(1, WEBHOOK_MAX_RETRIES + 1):
        try:
            status = await _post_once(event, payload)
            if 200 <= status < 300:
                return
            # 4xx не ретраим
            if 400 <= status < 500:
                return
        except Exception:
            # сеть/таймаут — ретраим
            pass
        if attempt < WEBHOOK_MAX_RETRIES:
            await asyncio.sleep(delay)
            delay *= 2.0  # экспоненциальная пауза
    # После всех попыток — просто сдаёмся молча (или тут можно логировать)
