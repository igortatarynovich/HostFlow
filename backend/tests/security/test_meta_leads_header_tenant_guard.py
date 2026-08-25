"""Unit tests for Meta leads header/JWT tenant guard."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from backend.app.db.meta_leads_tenant_dep import ensure_token_matches_header_tenant


@dataclass
class _Ctx:
    sub: str
    email: str
    role: str
    tenant_id: str
    supervisor_id: str | None = None
    raw: dict | None = None


def test_empty_jwt_tenant_is_forbidden() -> None:
    ctx = _Ctx("u1", "a@b.c", "administrator", "")
    with pytest.raises(HTTPException) as exc:
        ensure_token_matches_header_tenant(ctx, "11111111-1111-1111-1111-111111111111")
    assert exc.value.status_code == 403


def test_mismatched_jwt_tenant_is_forbidden() -> None:
    ctx = _Ctx("u1", "a@b.c", "administrator", "11111111-1111-1111-1111-111111111111")
    with pytest.raises(HTTPException) as exc:
        ensure_token_matches_header_tenant(ctx, "22222222-2222-2222-2222-222222222222")
    assert exc.value.status_code == 403


def test_matching_jwt_tenant_ok() -> None:
    tid = "11111111-1111-1111-1111-111111111111"
    ctx = _Ctx("u1", "a@b.c", "administrator", tid)
    ensure_token_matches_header_tenant(ctx, tid)
