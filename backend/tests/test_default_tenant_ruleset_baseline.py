"""Default-tenant document ruleset must expose a non-empty required-documents matrix."""

from __future__ import annotations

import pytest

from backend.app.db.session import async_session_maker
from backend.app.modules.documents.crud import get_effective_latest_ruleset_version
from backend.app.modules.documents.rules_engine import compute_candidate_checklist
from backend.app.services.default_tenant_ruleset_baseline import DEFAULT_TENANT_ID
from backend.app.services.ruleset_versioning import normalize_ruleset_payload
from backend.tests.conftest import _set_tenant


@pytest.mark.anyio
async def test_default_tenant_active_global_ruleset_has_required_types() -> None:
    async with async_session_maker() as session:
        await _set_tenant(session, DEFAULT_TENANT_ID)
        row = await get_effective_latest_ruleset_version(
            session,
            DEFAULT_TENANT_ID,
            own_company_id=None,
        )
        assert row is not None, "expected at least one active global ruleset version for default tenant"
        checklist = compute_candidate_checklist(
            {},
            normalize_ruleset_payload(row.json_data),
        )
        assert checklist.get("requiredTypes"), (
            "active global ruleset must define requiredTypes; "
            f"got debug={checklist.get('debug')}"
        )
