from __future__ import annotations

from backend.app.services.hr_document_verification import _build_profile_context, build_fields_to_review
from backend.app.services.hr_profile_address import format_address_line, promote_address_fields


def test_promote_address_fields_from_structured_dict() -> None:
    target: dict[str, str] = {}
    promote_address_fields(
        target,
        {"country": "PL", "city": "Warsaw", "street": "Main", "house": "1", "zip": "00-001"},
    )
    assert target["address_country"] == "PL"
    assert target["city"] == "Warsaw"
    assert target["address_street"] == "Main"
    assert target["postal_code"] == "00-001"
    assert "Warsaw" in (format_address_line(target) or "")


def test_build_profile_context_flattens_candidate_extra_address() -> None:
    from backend.app.models.workforce_employee import WorkforceEmployee

    emp = WorkforceEmployee(
        id="e1",
        tenant_id="t1",
        display_name="Jan",
        candidate_snapshot={
            "extra": {
                "address": {
                    "country": "UA",
                    "city": "Lviv",
                    "street": "Svobody",
                    "zip": "79000",
                }
            },
            "email": "jan@example.com",
        },
    )
    ctx = _build_profile_context(emp, None, None, None)
    snap = ctx["snapshot"]
    assert snap.get("address_country") == "UA"
    assert snap.get("city") == "Lviv"
    fields = build_fields_to_review("Contacts & address", ctx, None)
    country = next(f for f in fields if f["field_code"] == "address_country")
    assert country["needs_manual_confirmation"] is False
