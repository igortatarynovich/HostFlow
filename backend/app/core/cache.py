"""Cache abstraction for read-heavy endpoints. In-memory with TTL; Redis when REDIS_URL is set."""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from typing import Any, Awaitable, Callable, Optional, TypeVar, Union

T = TypeVar("T")

_DEFAULT_TTL_SEC = 300  # 5 min
_memory_store: dict[str, tuple[Any, float]] = {}
_memory_lock = threading.Lock()
_redis_client: Any = None
_redis_available: Optional[bool] = None


def _get_redis():
    """Lazy-init Redis client if REDIS_URL is set."""
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import os
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            _redis_available = False
            return None
        import redis.asyncio as redis_async
        _redis_client = redis_async.from_url(redis_url, decode_responses=True)
        _redis_available = True
        return _redis_client
    except ImportError:
        _redis_available = False
        return None
    except Exception:
        _redis_available = False
        return None


def _make_key(prefix: str, tenant_id: str, params: dict[str, Any]) -> str:
    """Build cache key from prefix, tenant, and params."""
    parts = [prefix, tenant_id]
    for k in sorted(params.keys()):
        v = params[k]
        if v is not None:
            parts.append(f"{k}={v}")
    raw = ":".join(str(p) for p in parts)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"hf:{prefix}:{tenant_id}:{h}"


def _serialize(value: Any) -> str:
    """Serialize value for Redis."""
    return json.dumps(value, default=str)


def _deserialize(raw: str) -> Any:
    """Deserialize from Redis."""
    return json.loads(raw)


async def cache_get(prefix: str, tenant_id: str, params: dict[str, Any]) -> Optional[Any]:
    """Get cached value. Returns None if miss or expired."""
    key = _make_key(prefix, tenant_id, params)
    client = _get_redis()
    if client:
        try:
            raw = await client.get(key)
            if raw:
                return _deserialize(raw)
        except Exception:
            pass
        return None
    with _memory_lock:
        entry = _memory_store.get(key)
        if not entry:
            return None
        val, expires_at = entry
        if time.monotonic() > expires_at:
            del _memory_store[key]
            return None
        return val


async def cache_set(
    prefix: str,
    tenant_id: str,
    params: dict[str, Any],
    value: Any,
    ttl_sec: int = _DEFAULT_TTL_SEC,
) -> None:
    """Set cached value with TTL."""
    key = _make_key(prefix, tenant_id, params)
    client = _get_redis()
    if client:
        try:
            await client.setex(
                key,
                ttl_sec,
                _serialize(value),
            )
        except Exception:
            pass
        return
    with _memory_lock:
        expires_at = time.monotonic() + ttl_sec
        _memory_store[key] = (value, expires_at)
        # Simple cleanup: drop expired entries when store grows
        if len(_memory_store) > 1000:
            now = time.monotonic()
            expired = [k for k, (_, ex) in _memory_store.items() if ex < now]
            for k in expired[:100]:
                del _memory_store[k]


async def cache_get_or_set(
    prefix: str,
    tenant_id: str,
    params: dict[str, Any],
    factory: Callable[[], Union[Any, Awaitable[Any]]],
    ttl_sec: int = _DEFAULT_TTL_SEC,
) -> Any:
    """Get from cache or compute and store."""
    val = await cache_get(prefix, tenant_id, params)
    if val is not None:
        return val
    result = factory()
    if asyncio.iscoroutine(result):
        result = await result
    await cache_set(prefix, tenant_id, params, result, ttl_sec)
    return result


async def cache_invalidate(prefix: str, tenant_id: Optional[str] = None) -> None:
    """Invalidate cache entries by prefix (and optionally tenant)."""
    client = _get_redis()
    if client:
        try:
            pattern = f"hf:{prefix}:*" if not tenant_id else f"hf:{prefix}:{tenant_id}:*"
            keys = []
            async for k in client.scan_iter(match=pattern):
                keys.append(k)
            if keys:
                await client.delete(*keys)
        except Exception:
            pass
        return
    with _memory_lock:
        t_prefix = f"hf:{prefix}:"
        to_del = [
            k for k in _memory_store
            if k.startswith(t_prefix) and (tenant_id is None or f":{tenant_id}:" in k)
        ]
        for k in to_del:
            del _memory_store[k]
