"""Phase 6 retrieval telemetry — global search request/deny/complete wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from backend.app.security.event_taxonomy import (
    EVENT_SEARCH_RETRIEVAL_COMPLETED,
    EVENT_SEARCH_RETRIEVAL_DENIED,
    EVENT_SEARCH_RETRIEVAL_REQUESTED,
)


@pytest.mark.anyio
async def test_global_search_emits_denied_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.v1 import global_search as mod

    emitted: list[str] = []

    def _capture(**kwargs):  # type: ignore[no-untyped-def]
        emitted.append(str(kwargs.get("event_type")))
        return {"event_type": kwargs.get("event_type")}

    monkeypatch.setattr(mod, "emit_retrieval_security_event_v1", _capture)

    async def _boom(*_a, **_k):  # type: ignore[no-untyped-def]
        raise HTTPException(status_code=403, detail="Forbidden for tenant")

    monkeypatch.setattr(mod, "run_global_search_v1", _boom)

    class _User:
        sub = "user-1"
        tenant_id = "11111111-1111-1111-1111-111111111111"

    class _Db:
        info = {"security_access_kind": "tenant_bound"}

    with pytest.raises(HTTPException) as ei:
        await mod.global_search(
            q="ab",
            limit=4,
            max_results=24,
            scope_tenant_id=None,
            assignee_scope="mine",
            db_tenant=(_Db(), _User.tenant_id),  # type: ignore[arg-type]
            current_user=_User(),  # type: ignore[arg-type]
            own_company_id=None,
            _role="administrator",
        )
    assert ei.value.status_code == 403
    assert EVENT_SEARCH_RETRIEVAL_REQUESTED in emitted
    assert EVENT_SEARCH_RETRIEVAL_DENIED in emitted
    assert EVENT_SEARCH_RETRIEVAL_COMPLETED not in emitted


@pytest.mark.anyio
async def test_global_search_emits_completed_with_filtered(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.api.v1 import global_search as mod

    emitted: list[dict] = []

    def _capture(**kwargs):  # type: ignore[no-untyped-def]
        emitted.append(dict(kwargs))
        return {"event_type": kwargs.get("event_type")}

    monkeypatch.setattr(mod, "emit_retrieval_security_event_v1", _capture)
    monkeypatch.setattr(
        mod,
        "run_global_search_v1",
        AsyncMock(
            return_value={
                "q": "ab",
                "items": [
                    {"type": "candidate", "id": "1", "title": "A", "subtitle": None, "link": "/x"},
                ],
                "_retrieval_stats": {
                    "merged_count": 5,
                    "returned_count": 1,
                    "entity_types": ["candidate"],
                },
            }
        ),
    )

    class _User:
        sub = "user-1"
        tenant_id = "11111111-1111-1111-1111-111111111111"

    class _Db:
        info = {"security_access_kind": "tenant_bound"}

    out = await mod.global_search(
        q="ab",
        limit=4,
        max_results=24,
        scope_tenant_id=None,
        assignee_scope="mine",
        db_tenant=(_Db(), _User.tenant_id),  # type: ignore[arg-type]
        current_user=_User(),  # type: ignore[arg-type]
        own_company_id=None,
        _role="administrator",
    )
    assert len(out.items) == 1
    types = [e["event_type"] for e in emitted]
    assert EVENT_SEARCH_RETRIEVAL_REQUESTED in types
    assert EVENT_SEARCH_RETRIEVAL_COMPLETED in types
    completed = next(e for e in emitted if e["event_type"] == EVENT_SEARCH_RETRIEVAL_COMPLETED)
    assert completed.get("returned_count") == 1
    assert completed.get("filtered_count") == 4
