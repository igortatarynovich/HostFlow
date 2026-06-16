from backend.app.services.hr_operational_risk import _risk_item


def test_risk_item_uses_canonical_codes() -> None:
    row = _risk_item(
        risk_code="document_expired",
        severity="CRITICAL",
        handoff_id="h1",
        workforce_employee_id="e1",
        candidate_snapshot={},
        reason="expired",
        recommended_action="renew_document",
    )
    assert row["severity"] == "critical"
    assert row["recommended_action"] == "renew_document"


def test_risk_item_invalid_codes_fallback_to_canonical_defaults() -> None:
    row = _risk_item(
        risk_code="x",
        severity="very_bad",
        handoff_id=None,
        workforce_employee_id=None,
        candidate_snapshot={},
        reason="x",
        recommended_action="legacy_phrase",
    )
    assert row["severity"] == "info"
    assert row["recommended_action"] == "verify_document"

