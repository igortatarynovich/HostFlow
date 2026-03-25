"""Unit tests for risk_intel_v1 decay and scoring helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.services.risk_intel_digest_email import normalize_digest_roles
from backend.app.services.risk_intel_v1 import (
    band_from_score,
    decay_factor,
    hour_bucket_start,
    parse_shadow_bucket_iso,
    resolve_risk_config,
    risk_from_delay_hours,
    score_single_candidate,
)


def test_decay_factor_half_life() -> None:
    assert decay_factor(0, 24) == pytest.approx(1.0)
    assert decay_factor(24, 24) == pytest.approx(0.5)
    assert decay_factor(48, 24) == pytest.approx(0.25)


def test_risk_from_delay_monotonic() -> None:
    a = risk_from_delay_hours(1, 30)
    b = risk_from_delay_hours(72, 30)
    assert b > a


def test_band_from_score() -> None:
    assert band_from_score(10) == "low"
    assert band_from_score(40) == "medium"
    assert band_from_score(70) == "high"
    assert band_from_score(90) == "critical"


def test_resolve_risk_config_merges_tenant() -> None:
    cfg = resolve_risk_config({"risk_model_v1": {"weights": {"response": 0.5, "stagnation": 0.5}}})
    w = cfg["weights"]
    assert "action" in w and "context" in w
    assert sum(float(w[k]) for k in w) == pytest.approx(1.0)
    # merged defaults + tenant overrides, then renormalized to sum 1
    assert w["response"] > w["context"]


def test_resolve_risk_config_digest_email_defaults() -> None:
    cfg = resolve_risk_config({})
    de = cfg["digest_email"]
    assert de["enabled"] is False
    assert de["to"] == []
    assert de["to_roles"] == []
    assert de["min_band"] == "high"
    assert de["max_rows"] == 25
    assert de["skip_if_empty"] is True


def test_parse_shadow_bucket_iso_normalizes_hour() -> None:
    dt = parse_shadow_bucket_iso("2026-03-22T14:37:12+00:00")
    assert dt is not None
    assert dt == hour_bucket_start(dt)
    assert dt.minute == 0 and dt.second == 0 and dt.microsecond == 0
    assert dt.tzinfo == timezone.utc
    assert parse_shadow_bucket_iso("not-a-date") is None


def test_normalize_digest_roles_aliases() -> None:
    assert normalize_digest_roles(["admin", "Manager", "recruiter"]) == [
        "administrator",
        "recruiter",
        "supervisor",
    ]
    assert normalize_digest_roles("supervisor") == ["supervisor"]
    assert normalize_digest_roles(["nope", "", 123]) == []


def test_score_single_candidate_pipeline_completed_zero() -> None:
    now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=30)
    for stage in ("rejected", "declined", "employed", "probation_ok"):
        score, band, drivers = score_single_candidate(
            created_at=created,
            now=now,
            stage=stage,
            first_touch_at=None,
            last_outbound_at=None,
            last_inbound_at=now - timedelta(hours=2),
            has_next_action=False,
            next_action_overdue_hours=48.0,
            interaction_count_7d=0,
            stage_entered_at=created,
            stage_reopen_30d=3,
            overdue_completed_reminders_7d=2,
            tenant_settings=None,
        )
        assert score == 0.0
        assert band == "low"
        assert drivers == []


def test_score_single_candidate_terminal_low() -> None:
    now = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=30)
    score, band, drivers = score_single_candidate(
        created_at=created,
        now=now,
        stage="probation_ok",
        first_touch_at=None,
        last_outbound_at=None,
        last_inbound_at=None,
        has_next_action=False,
        next_action_overdue_hours=0,
        interaction_count_7d=0,
        stage_entered_at=created,
        stage_reopen_30d=0,
        overdue_completed_reminders_7d=0,
        tenant_settings=None,
    )
    assert score < 35
    assert band == "low"
    assert drivers
