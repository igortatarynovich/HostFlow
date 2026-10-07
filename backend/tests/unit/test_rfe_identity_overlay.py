from types import SimpleNamespace

from backend.app.modules.recruitment.services.ready_for_employment_orchestrator import (
    hydrate_package_identity_from_lead,
)


def test_hydrate_copies_lead_citizenship_onto_package_identity() -> None:
    lead = SimpleNamespace(normalized={"citizenship": "PL", "full_name": "Jan Nowak"})
    package = {
        "person": {
            "person_id": "cand-1",
            "identity_facts": {"first_name": "Jan", "last_name": "Nowak"},
        }
    }
    out = hydrate_package_identity_from_lead(package, lead)
    assert out["person"]["identity_facts"]["citizenship"] == "PL"
    assert out["person"]["identity_facts"]["first_name"] == "Jan"


def test_hydrate_does_not_overwrite_existing_citizenship() -> None:
    lead = SimpleNamespace(normalized={"citizenship": "PL"})
    package = {"person": {"identity_facts": {"citizenship": "UA", "first_name": "Ada"}}}
    out = hydrate_package_identity_from_lead(package, lead)
    assert out["person"]["identity_facts"]["citizenship"] == "UA"
