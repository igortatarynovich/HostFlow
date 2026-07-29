"""Unit tests for Client Account commercial defaults prefill helpers (FE logic mirrored)."""

from __future__ import annotations

from backend.app.modules.client_accounts.schemas import CommercialDefaults, ClientAccountUpdate


def test_commercial_defaults_currency_upper():
    d = CommercialDefaults(currency="pln", payment_term_days=21)
    assert d.currency == "PLN"
    assert d.payment_term_days == 21


def test_commercial_defaults_dump_json():
    d = CommercialDefaults(currency="EUR", vat_rate="23.00", payment_model="per_hire")
    payload = d.model_dump(mode="json", exclude_none=True)
    assert payload["currency"] == "EUR"
    assert "guarantee_days" not in payload


def test_client_account_update_accepts_defaults():
    u = ClientAccountUpdate(commercial_defaults=CommercialDefaults(currency="USD", payment_term_days=7))
    assert u.commercial_defaults is not None
    assert u.commercial_defaults.currency == "USD"
