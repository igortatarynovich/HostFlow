"""portal_candidate_usage — monthly idempotent candidate ids (§2.16)."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from backend.app.services import portal_candidate_usage


def test_merge_dedupes_same_month() -> None:
    at = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    s: dict = {}
    s = portal_candidate_usage.merge_record_into_settings(s, "c1", at_utc=at)
    s = portal_candidate_usage.merge_record_into_settings(s, "c1", at_utc=at)
    s = portal_candidate_usage.merge_record_into_settings(s, "c2", at_utc=at)
    assert portal_candidate_usage.count_for_utc_month(s, at_utc=at) == 2


def test_ensure_can_add_blocks_at_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(portal_candidate_usage, "monthly_cap_for_plan_code", lambda _pc: 3)
    at = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    s = portal_candidate_usage.merge_record_into_settings({}, "c1", at_utc=at)
    s = portal_candidate_usage.merge_record_into_settings(s, "c2", at_utc=at)
    s = portal_candidate_usage.merge_record_into_settings(s, "c3", at_utc=at)
    tenant_like = type("T", (), {"settings": s})()
    with pytest.raises(HTTPException) as ei:
        portal_candidate_usage.ensure_can_add_portal_candidate_month(
            tenant_like, "c4", at_utc=at, plan_code="team"
        )
    assert ei.value.status_code == 402
    assert ei.value.detail["code"] == "portal_active_candidates_limit_reached"


def test_ensure_can_add_allows_existing_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(portal_candidate_usage, "monthly_cap_for_plan_code", lambda _pc: 3)
    at = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    s = portal_candidate_usage.merge_record_into_settings({}, "c1", at_utc=at)
    s = portal_candidate_usage.merge_record_into_settings(s, "c2", at_utc=at)
    s = portal_candidate_usage.merge_record_into_settings(s, "c3", at_utc=at)
    tenant_like = type("T", (), {"settings": s})()
    portal_candidate_usage.ensure_can_add_portal_candidate_month(
        tenant_like, "c1", at_utc=at, plan_code="team"
    )


def test_pack_addon_increases_effective_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(portal_candidate_usage, "monthly_cap_for_plan_code", lambda _pc: 10)
    at = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    s_base: dict = {}
    for i in range(10):
        s_base = portal_candidate_usage.merge_record_into_settings(s_base, f"c{i}", at_utc=at)
    tenant_base = type("T", (), {"settings": s_base})()
    with pytest.raises(HTTPException) as ei:
        portal_candidate_usage.ensure_can_add_portal_candidate_month(
            tenant_base, "c10", at_utc=at, plan_code="team"
        )
    assert ei.value.status_code == 402
    assert ei.value.detail.get("pack_addon") == 0

    s_pack = portal_candidate_usage.merge_increment_portal_monthly_cap_addon(dict(s_base), 5)
    tenant_pack = type("T", (), {"settings": s_pack})()
    portal_candidate_usage.ensure_can_add_portal_candidate_month(
        tenant_pack, "c10", at_utc=at, plan_code="team"
    )
    for i in range(10, 15):
        s_pack = portal_candidate_usage.merge_record_into_settings(s_pack, f"c{i}", at_utc=at)
    tenant_full = type("T", (), {"settings": s_pack})()
    with pytest.raises(HTTPException):
        portal_candidate_usage.ensure_can_add_portal_candidate_month(
            tenant_full, "c15", at_utc=at, plan_code="team"
        )


def test_merge_separate_months() -> None:
    m1 = datetime(2026, 3, 1, tzinfo=UTC)
    m2 = datetime(2026, 4, 1, tzinfo=UTC)
    s = portal_candidate_usage.merge_record_into_settings({}, "c1", at_utc=m1)
    s = portal_candidate_usage.merge_record_into_settings(s, "c1", at_utc=m2)
    assert portal_candidate_usage.count_for_utc_month(s, at_utc=m1) == 1
    assert portal_candidate_usage.count_for_utc_month(s, at_utc=m2) == 1
