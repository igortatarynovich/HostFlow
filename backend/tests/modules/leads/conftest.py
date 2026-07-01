"""PR-4A: session-scoped FastAPI client for leads integration tests."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
import sqlalchemy as sa
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from backend.app.core.settings import settings
from backend.app.db.session import async_session_maker
from backend.app.main import app
from backend.tests.conftest import DEFAULT_TENANT_ID, _init_data

_lifespan_manager: LifespanManager | None = None
_session_loop: asyncio.AbstractEventLoop | None = None


def meta_ingest_headers(manager_headers: dict[str, str], payload: dict) -> dict[str, str]:
    secret = str(settings.meta_webhook_secret or "").encode("utf-8")
    body = json.dumps(payload).encode("utf-8")
    digest = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return {**manager_headers, "X-Hub-Signature-256": f"sha256={digest}"}


async def post_meta_lead(client: AsyncClient, manager_headers: dict[str, str], payload: dict):
    return await client.post(
        "/api/v1/leads/meta",
        headers=meta_ingest_headers(manager_headers, payload),
        content=json.dumps(payload),
    )


async def _clear_meta_credentials() -> None:
    async with async_session_maker() as session:
        await session.execute(
            sa.text("DELETE FROM meta_lead_credentials WHERE tenant_id = :tenant_id"),
            {"tenant_id": DEFAULT_TENANT_ID},
        )
        await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def _reset_tenant_intake_routing_settings() -> None:
    """Remove intake_routing_v1 default profile between leads integration tests."""
    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                UPDATE tenants
                SET settings = COALESCE(settings::jsonb, '{}'::jsonb) - 'intake_routing_v1'
                WHERE id = :tenant_id
                """
            ),
            {"tenant_id": DEFAULT_TENANT_ID},
        )
        await session.commit()


async def _enter_leads_session_lifespan() -> None:
    global _lifespan_manager
    if _lifespan_manager is not None:
        return
    await _init_data()
    await _clear_meta_credentials()
    manager = LifespanManager(app, startup_timeout=120.0, shutdown_timeout=30.0)
    await manager.__aenter__()
    _lifespan_manager = manager


async def _exit_leads_session_lifespan() -> None:
    global _lifespan_manager
    if _lifespan_manager is None:
        return
    await _lifespan_manager.__aexit__(None, None, None)
    _lifespan_manager = None


@pytest.fixture(scope="session")
def _leads_app_session() -> Iterator[None]:
    """Sync session hook: start FastAPI lifespan once per test session."""
    global _session_loop
    _session_loop = asyncio.new_event_loop()
    try:
        _session_loop.run_until_complete(_enter_leads_session_lifespan())
        yield
    finally:
        _session_loop.run_until_complete(_exit_leads_session_lifespan())
        _session_loop.close()
        _session_loop = None


@pytest_asyncio.fixture
async def client(_leads_app_session: None) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest_asyncio.fixture
async def app_with_db(_leads_app_session: None) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
