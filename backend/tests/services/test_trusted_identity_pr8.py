"""PR8: merge variables, prep status, export/permit consumers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.services.document_merge.render import resolve_path
from backend.app.services.employment_identity_projection import PROJECTION_STATUS_COMPLETE, PROJECTION_STATUS_STALE
from backend.app.services.employment_identity_read_adapter import (
    CONSUMER_EXPORT,
    CONSUMER_PERMIT_APPLICATION,
    evaluate_consumer_access,
)
from backend.app.services.workforce_downstream_identity import (
    apply_trusted_identity_merge_variables,
    evaluate_export_identity,
    evaluate_permit_application,
)


def test_apply_trusted_identity_merge_variables_namespace() -> None:
    ctx: dict = {"bindings": {}}
    apply_trusted_identity_merge_variables(
        ctx,
        {"legal_name": "Jan Kowalski", "pesel": "123", "citizenship": "PL"},
    )
    assert resolve_path(ctx, "trusted_identity.legal_name") == "Jan Kowalski"
    assert resolve_path(ctx, "trusted_identity.pesel") == "123"
    assert ctx["bindings"]["trusted_identity.citizenship"] == "PL"


def test_export_consumer_allows_stale() -> None:
    ok, code = evaluate_consumer_access(CONSUMER_EXPORT, PROJECTION_STATUS_STALE)
    assert ok is True
    assert code is None


def test_permit_consumer_blocks_stale() -> None:
    ok, code = evaluate_consumer_access(CONSUMER_PERMIT_APPLICATION, PROJECTION_STATUS_STALE)
    assert ok is False
    assert code == "TRUSTED_IDENTITY_STALE"


@pytest.mark.asyncio
async def test_evaluate_export_identity_complete() -> None:
    from backend.app.services.employment_identity_read_adapter import (
        CONSUMER_EXPORT,
        TrustedEmploymentIdentityRead,
    )

    trusted = TrustedEmploymentIdentityRead(
        tenant_id="t1",
        review_id="r1",
        employee_id="e1",
        handoff_id=None,
        consumer=CONSUMER_EXPORT,
        projection={"status": PROJECTION_STATUS_COMPLETE},
        attributes={"legal_name": "A", "citizenship": "PL"},
        projection_status=PROJECTION_STATUS_COMPLETE,
        access_allowed=True,
    )
    with patch(
        "backend.app.services.workforce_downstream_identity.get_trusted_employment_identity_for_employee",
        new_callable=AsyncMock,
        return_value=trusted,
    ):
        result = await evaluate_export_identity(AsyncMock(), "t1", "e1")
    assert result.ready is True
    assert result.bindings["legal_name"] == "A"


@pytest.mark.asyncio
async def test_build_prep_status_lists_consumers() -> None:
    from backend.app.services.employment_identity_read_adapter import TrustedEmploymentIdentityRead
    from backend.app.services.trusted_identity_prep_status import build_trusted_identity_prep_status

    projection = {
        "status": PROJECTION_STATUS_COMPLETE,
        "derived_at": "2026-01-01T00:00:00+00:00",
        "attributes": {"legal_name": "Jan", "citizenship": "PL"},
        "attribute_labels": {"legal_name": "Legal name", "citizenship": "Citizenship"},
        "missing_required": [],
        "conflicts": [],
        "ready_for_downstream": True,
    }
    display = TrustedEmploymentIdentityRead(
        tenant_id="t1",
        review_id="r1",
        employee_id="e1",
        handoff_id=None,
        consumer="hr_review_display",
        projection=projection,
        attributes=projection["attributes"],
        projection_status="complete",
        access_allowed=True,
    )

    async def fake_eval(db, tenant_id, employee_id):
        from backend.app.services.workforce_downstream_identity import DownstreamIdentityPrepResult

        return DownstreamIdentityPrepResult(
            ready=True,
            blocked=False,
            consumer="x",
            projection_status="complete",
            bindings={"legal_name": "Jan"},
        )

    with patch(
        "backend.app.services.trusted_identity_prep_status.get_trusted_employment_identity_for_employee",
        new_callable=AsyncMock,
        return_value=display,
    ):
        with patch.dict(
            "backend.app.services.trusted_identity_prep_status._CONSUMER_EVALUATORS",
            {k: fake_eval for k in __import__(
                "backend.app.services.trusted_identity_prep_status", fromlist=["PREP_STATUS_CONSUMERS"]
            ).PREP_STATUS_CONSUMERS},
        ):
            status = await build_trusted_identity_prep_status(AsyncMock(), tenant_id="t1", employee_id="e1")

    assert status["projection_status"] == "complete"
    assert CONSUMER_EXPORT in status["allowed_consumers"]
    assert len(status["consumers"]) == 6
