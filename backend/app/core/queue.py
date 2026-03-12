"""Task queue abstraction. In-process async tasks; ARQ/Redis when configured."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Coroutine, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def enqueue(
    name: str,
    coro: Coroutine[Any, Any, T],
    *,
    fire_and_forget: bool = True,
) -> T | None:
    """
    Enqueue a coroutine for execution.
    If fire_and_forget=True, runs in background and returns None.
    If fire_and_forget=False, awaits and returns the result.
    """
    if fire_and_forget:
        asyncio.create_task(_run_and_log(name, coro))
        return None
    return await _run_and_log(name, coro)


async def _run_and_log(name: str, coro: Coroutine[Any, Any, T]) -> T:
    """Run coroutine and log errors."""
    try:
        return await coro
    except Exception as exc:
        logger.exception("[queue] Task %s failed: %s", name, exc)
        raise


def run_later(name: str, fn: Callable[[], Awaitable[Any]]) -> None:
    """
    Schedule async function to run later (fire-and-forget).
    Use for reminders, notifications, heavy ops.
    """
    asyncio.create_task(_run_and_log(name, fn()))
