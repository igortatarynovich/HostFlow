"""Stripe catalog helpers for checkout_payment pack increments."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.services.stripe_price_catalog import sku_pack_increment, sku_price_from_settings


def test_sku_pack_increment_portal_and_portal_5() -> None:
    s = SimpleNamespace(portal_candidates_pack_increment=500)
    assert sku_pack_increment(s, "pack_portal_candidates") == 500
    assert sku_pack_increment(s, "pack_client_portal_5") == 5


def test_sku_price_from_settings_missing() -> None:
    s = SimpleNamespace()
    assert sku_price_from_settings(s, "pack_leads_500") is None
