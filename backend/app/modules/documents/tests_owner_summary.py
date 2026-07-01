from __future__ import annotations

from datetime import date, timedelta

from owner_summary import compute_owner_summary
from rules_engine import load_ruleset

RS_PATH = "data/sample_ruleset.json"


def test_summary_ok():
    rs = load_ruleset(RS_PATH)
    ctx = {
        "citizenship": "PL",
        "residency_status": "eu_citizen",
        "vacancy": {"requires_driver_attestation": False},
    }
    # required: national_id, code95
    docs = [
        {
            "type": "national_id",
            "status": "approved",
            "expires_at": (date.today() + timedelta(days=200)).isoformat(),
        },
        {
            "type": "code95",
            "status": "approved",
            "expires_at": (date.today() + timedelta(days=100)).isoformat(),
        },
    ]
    out = compute_owner_summary(ctx, rs, docs)
    assert out["status"] == "ok"
    assert out["percent_ready"] == 100
    assert out["required"]["missing"] == []
    assert out["required"]["problematic"] == []
    assert "code95" in out["checklist"]["requiredTypes"]


def test_summary_incomplete_and_problems_priority():
    rs = load_ruleset(RS_PATH)
    ctx = {
        "citizenship": "PL",
        "residency_status": "eu_citizen",
        "vacancy": {"requires_driver_attestation": False},
    }
    docs = [
        {"type": "national_id", "status": "missing"},
        {"type": "code95", "status": "rejected"},
    ]
    out = compute_owner_summary(ctx, rs, docs)
    # rejected имеет приоритет -> problems
    assert out["status"] == "problems"
    assert "code95" in out["required"]["problematic"]
    assert "national_id" in out["required"]["missing"]
    assert out["percent_ready"] == 0


def test_summary_expiring_soon():
    rs = load_ruleset(RS_PATH)
    ctx = {
        "citizenship": "PL",
        "residency_status": "eu_citizen",
        "vacancy": {"requires_driver_attestation": False},
    }
    # approved, но документ истекает через 10 дней (порог 180) — expiring_soon
    docs = [
        {
            "type": "national_id",
            "status": "approved",
            "expires_at": (date.today() + timedelta(days=10)).isoformat(),
        },
        {
            "type": "code95",
            "status": "approved",
            "expires_at": (date.today() + timedelta(days=120)).isoformat(),
        },
    ]
    out = compute_owner_summary(ctx, rs, docs)
    assert out["status"] == "expiring_soon"
    assert any(x["type"] == "national_id" for x in out["expiring_soon"])
    assert out["expiry"]["has_expiring_documents"] is True
    assert out["expiry"]["all_documents_valid"] is False


def test_summary_expired_and_missing_expiry():
    rs = load_ruleset(RS_PATH)
    ctx = {
        "citizenship": "PL",
        "residency_status": "eu_citizen",
        "vacancy": {"requires_driver_attestation": False},
    }
    docs = [
        {
            "type": "national_id",
            "status": "approved",
            "expires_at": (date.today() - timedelta(days=1)).isoformat(),
        },
        {
            "type": "code95",
            "status": "approved",
        },
    ]
    out = compute_owner_summary(ctx, rs, docs)
    assert out["status"] == "expired"
    assert out["expiry"]["has_expired_documents"] is True
    assert out["expiry"]["has_missing_expiry"] is True
    assert out["expiry"]["all_documents_valid"] is False
