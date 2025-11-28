from __future__ import annotations

from rules_engine import compute_candidate_checklist, load_ruleset


def run():
    rs = load_ruleset("data/ruleset.v1_1.json")

    ctx_driver = {
        "citizenship": "UA",
        "residency_status": "no_residence_card",
        "vacancy": {"category": "driver", "requires_driver_attestation": True},
    }
    print("DRIVER:", compute_candidate_checklist(ctx_driver, rs))

    ctx_non = {
        "citizenship": "PL",
        "residency_status": "eu_citizen",
        "vacancy": {"category": "non_driver"},
    }
    print("NON-DRIVER:", compute_candidate_checklist(ctx_non, rs))


if __name__ == "__main__":
    run()
