"""Async request-scoped context for security logging (correlation_id, optional actor)."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar, Token

_security_correlation_id: ContextVar[str | None] = ContextVar("security_correlation_id", default=None)
_security_actor_id: ContextVar[str | None] = ContextVar("security_actor_id", default=None)


def set_security_correlation_id(value: str | None) -> Token[str | None]:
    return _security_correlation_id.set(value)


def get_security_correlation_id() -> str | None:
    return _security_correlation_id.get()


def set_security_actor_id(value: str | None) -> Token[str | None]:
    return _security_actor_id.set(value)


def get_security_actor_id() -> str | None:
    return _security_actor_id.get()


def reset_security_correlation_token(token: Token[str | None]) -> None:
    _security_correlation_id.reset(token)


def reset_security_actor_token(token: Token[str | None]) -> None:
    _security_actor_id.reset(token)


@asynccontextmanager
async def security_job_context(
    *,
    actor_id: str,
    correlation_id: str | None = None,
):
    """Worker / webhook: bind correlation + actor for nested security_event logging."""
    cid = (correlation_id or "").strip() or str(uuid.uuid4())
    cor_tok = _security_correlation_id.set(cid)
    act_tok = _security_actor_id.set(actor_id)
    try:
        yield
    finally:
        _security_correlation_id.reset(cor_tok)
        _security_actor_id.reset(act_tok)
