from __future__ import annotations

from rules_engine import (
    compute_candidate_checklist,
    expiring_threshold_for,
    load_ruleset,
)


def run():
    rs = load_ruleset("data/sample_ruleset.json")

    scenarios = [
        {
            "name": "UA без карты побыту, вакансия требует attestation",
            "ctx": {
                "citizenship": "UA",
                "residency_status": "no_residence_card",
                "vacancy": {"requires_driver_attestation": True},
            },
        },
        {
            "name": "PL/EU гражданин",
            "ctx": {
                "citizenship": "PL",
                "residency_status": "eu_citizen",
                "vacancy": {"requires_driver_attestation": False},
            },
        },
        {
            "name": "IN без карты побыту",
            "ctx": {
                "citizenship": "IN",
                "residency_status": "no_residence_card",
                "vacancy": {"requires_driver_attestation": False},
            },
        },
    ]

    for sc in scenarios:
        print(f"\n=== {sc['name']} ===")
        checklist = compute_candidate_checklist(sc["ctx"], rs)
        print("Required:", checklist["requiredTypes"])
        print("Optional:", checklist["optionalTypes"])
        print("Debug:", checklist["debug"])

    # Пример получения порога "expiring soon"
    for t in ["identity_document", "code95", "swiadectwo_kierowcy"]:
        print(f"Threshold for {t}: {expiring_threshold_for(t, rs)} days")


if __name__ == "__main__":
    run()
