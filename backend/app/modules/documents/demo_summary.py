from __future__ import annotations

from datetime import date, timedelta

from owner_summary import compute_owner_summary
from rules_engine import load_ruleset


def run():
    rs = load_ruleset("data/sample_ruleset.json")
    ctx = {
        "citizenship": "PL",
        "residency_status": "eu_citizen",
        "vacancy": {"requires_driver_attestation": False},
    }
    docs = [
        {
            "type": "identity_document",
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
    print(out)


if __name__ == "__main__":
    run()
