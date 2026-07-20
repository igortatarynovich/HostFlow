"""Capability UI — read-only spine projection (no domain decisions)."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.modules.sales.services.capability_spine_read import (
    SPINE_CONTRACT,
    project_capability_spine,
)
from backend.app.modules.sales.services.ambiguous_match_review import (
    REVIEW_KEY,
    STATUS_REQUIRED,
)
from backend.app.modules.sales.services.convert_mapping import CONVERT_MAPPING_KEY
from backend.app.modules.sales.services.sales_inquiry_traceability import LINEAGE_KEY


def _inquiry(**overrides):  # noqa: ANN003
    base = {
        "id": "si-1",
        "lead_id": "lead-1",
        "status": "open",
        "entity_profile_code": "service_sales.targeted_advertising",
        "meta": {},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_spine_projects_capability_proxy_and_open_convert() -> None:
    out = project_capability_spine(_inquiry())
    assert out["contract"] == SPINE_CONTRACT
    assert out["capability"]["code"] == "service_sales.targeted_advertising"
    assert out["capability"]["source"] == "entity_profile"
    assert out["capability"]["decided"] is False
    assert out["review"]["blocks_convert"] is False
    assert out["convert"]["available"] is True
    assert out["traceability"]["present"] is False


def test_spine_blocks_convert_when_review_required() -> None:
    inquiry = _inquiry(
        meta={
            REVIEW_KEY: {
                "status": STATUS_REQUIRED,
                "version": 1,
                "candidates": [{"client_account_id": "ca-1"}],
            }
        }
    )
    out = project_capability_spine(inquiry)
    assert out["review"]["status"] == STATUS_REQUIRED
    assert out["review"]["blocks_convert"] is True
    assert out["convert"]["available"] is False
    assert out["convert"]["reason"] == "unresolved_review"


def test_spine_shows_convert_result_and_lineage() -> None:
    inquiry = _inquiry(
        status="converted",
        meta={
            CONVERT_MAPPING_KEY: {
                "client_account_id": "ca-9",
                "flights_ledger_id": "lg-1",
                "destination": "sales",
                "converted_at": "2026-07-20T00:00:00Z",
            },
            LINEAGE_KEY: {
                "sales_inquiry_id": "si-1",
                "client_account_id": "ca-9",
                "flights_ledger_id": "lg-1",
                "destination": "sales",
                "chain": ["sales_inquiry", "client_account"],
            },
        },
    )
    out = project_capability_spine(inquiry)
    assert out["convert"]["available"] is False
    assert out["convert"]["reason"] == "already_converted"
    assert out["convert"]["client_account_id"] == "ca-9"
    assert out["traceability"]["present"] is True
    assert out["traceability"]["lineage"]["client_account_id"] == "ca-9"


def test_spine_undecided_capability_without_profile() -> None:
    out = project_capability_spine(_inquiry(entity_profile_code=None))
    assert out["capability"]["code"] is None
    assert out["capability"]["source"] == "undecided"
