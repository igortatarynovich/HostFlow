"""Unit tests for lead distribution pick logic used at ingest (process_normalized_lead)."""

import uuid

from backend.app.models.user import Role
from backend.app.services.lead_distribution import (
    DEFAULTS,
    filter_team_by_pipeline_owner_roles,
    language_from_lead_normalized,
    pick_assignee_member_from_team,
    roles_for_pipeline_owner_role,
)


def test_roles_for_pipeline_owner_role_maps_synonyms() -> None:
    r = roles_for_pipeline_owner_role("recruiter")
    assert r == {Role.recruiter}
    r2 = roles_for_pipeline_owner_role("Manager, Admin")
    assert r2 == {Role.supervisor, Role.administrator}
    assert roles_for_pipeline_owner_role("") is None
    assert roles_for_pipeline_owner_role("unknown_role_xyz") is None


def test_filter_team_by_pipeline_owner_roles_falls_back_when_empty() -> None:
    team = [
        {"user_id": "a", "role": Role.recruiter.value},
        {"user_id": "b", "role": Role.supervisor.value},
    ]
    out = filter_team_by_pipeline_owner_roles(team, {Role.administrator})
    assert out == team
    out2 = filter_team_by_pipeline_owner_roles(team, {Role.recruiter})
    assert len(out2) == 1 and out2[0]["user_id"] == "a"


def test_language_from_lead_normalized() -> None:
    assert language_from_lead_normalized(None) is None
    assert language_from_lead_normalized({}) is None
    assert language_from_lead_normalized({"language": "  PL  "}) == "PL"
    assert language_from_lead_normalized({"locale": "en"}) == "en"
    assert language_from_lead_normalized({"preferred_language": "pl"}) == "pl"


def test_pick_assignee_member_smart_prefers_lower_load() -> None:
    cfg = {
        **DEFAULTS,
        "strategy": "smart",
        "max_leads_per_person": 10,
        "only_active_employees": True,
    }
    team = [
        {"user_id": "a", "display_name": "A", "status": "available", "lead_load": 5, "languages": ["PL"]},
        {"user_id": "b", "display_name": "B", "status": "available", "lead_load": 1, "languages": ["PL"]},
    ]
    picked = pick_assignee_member_from_team(team, cfg, "pl", "tenant-1")
    assert picked is not None
    assert picked["user_id"] == "b"


def test_pick_assignee_member_respects_offline_when_only_active() -> None:
    cfg = {**DEFAULTS, "strategy": "smart", "max_leads_per_person": 10, "only_active_employees": True}
    team = [
        {"user_id": "a", "display_name": "A", "status": "offline", "lead_load": 0, "languages": ["PL"]},
        {"user_id": "b", "display_name": "B", "status": "available", "lead_load": 2, "languages": ["PL"]},
    ]
    picked = pick_assignee_member_from_team(team, cfg, "pl", "tenant-1")
    assert picked is not None
    assert picked["user_id"] == "b"


def test_pick_assignee_member_round_robin_sequential_in_team_order() -> None:
    cfg = {
        **DEFAULTS,
        "strategy": "round_robin",
        "max_leads_per_person": 10,
        "only_active_employees": True,
        "round_robin_last_user_id": None,
    }
    team = [
        {"user_id": "a", "display_name": "A", "status": "available", "lead_load": 0, "languages": ["PL"]},
        {"user_id": "b", "display_name": "B", "status": "available", "lead_load": 0, "languages": ["PL"]},
    ]
    p1 = pick_assignee_member_from_team(team, cfg, "pl", "t")
    assert p1 is not None and p1["user_id"] == "a"

    cfg2 = {**cfg, "round_robin_last_user_id": "a"}
    p2 = pick_assignee_member_from_team(team, cfg2, "pl", "t")
    assert p2 is not None and p2["user_id"] == "b"

    cfg3 = {**cfg, "round_robin_last_user_id": "b"}
    p3 = pick_assignee_member_from_team(team, cfg3, "pl", "t")
    assert p3 is not None and p3["user_id"] == "a"


def test_pick_assignee_explicit_language_route_prefers_ordered_uuid_pool() -> None:
    u1 = str(uuid.uuid4())
    u2 = str(uuid.uuid4())
    cfg = {
        **DEFAULTS,
        "strategy": "smart",
        "max_leads_per_person": 10,
        "only_active_employees": True,
        "language_routing_v1": {"pl": [u2, u1]},
    }
    team = [
        {
            "user_id": u1,
            "display_name": "FirstInRouteButHeavier",
            "status": "available",
            "lead_load": 0,
            "languages": ["EN"],
        },
        {
            "user_id": u2,
            "display_name": "SecondInRouteLighter",
            "status": "available",
            "lead_load": 1,
            "languages": ["EN"],
        },
    ]
    picked = pick_assignee_member_from_team(team, cfg, "pl", "tenant-1")
    assert picked is not None
    # Lower load wins; explicit order is tie-breaker only.
    assert picked["user_id"] == u1

    team2 = [
        {**team[0], "lead_load": 2},
        {**team[1], "lead_load": 2},
    ]
    picked2 = pick_assignee_member_from_team(team2, cfg, "pl", "tenant-1")
    assert picked2 is not None
    assert picked2["user_id"] == u2


def test_pick_assignee_member_round_robin_unknown_last_resets_to_first() -> None:
    cfg = {
        **DEFAULTS,
        "strategy": "round_robin",
        "max_leads_per_person": 10,
        "only_active_employees": True,
        "round_robin_last_user_id": "gone-user",
    }
    team = [
        {"user_id": "x", "display_name": "X", "status": "available", "lead_load": 0, "languages": ["PL"]},
        {"user_id": "y", "display_name": "Y", "status": "available", "lead_load": 0, "languages": ["PL"]},
    ]
    picked = pick_assignee_member_from_team(team, cfg, "pl", "t")
    assert picked is not None
    assert picked["user_id"] == "x"
