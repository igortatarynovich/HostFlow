"""Flat CSV row payloads must coerce to field_data before normalize_meta_payload."""

from __future__ import annotations

from backend.app.modules.leads import normalizer
from backend.app.modules.leads.service import (
    _merge_lead_normalized_fallback,
    _payload_needs_flat_field_data_coercion,
)


def test_flat_csv_needs_coercion():
    assert _payload_needs_flat_field_data_coercion({"email": "a@b.co", "phone": "+48111"}) is True
    assert _payload_needs_flat_field_data_coercion({"entry": [{"changes": [{"value": {"field_data": []}}]}]}) is False


def test_coerce_then_normalize_extracts_contacts():
    flat = {"email": "Lead@Example.COM", "phone": "+48 500 600 700"}
    assert _payload_needs_flat_field_data_coercion(flat) is True
    wrapped = normalizer.coerce_generic_json_to_meta_normalizer_payload(flat)
    out = normalizer.normalize_meta_payload(wrapped, field_mapping=None)
    assert out.get("email") == "lead@example.com"
    assert out.get("phone")


def test_coerce_flat_row_ag_ad_id_and_meta_p_phone():
    """Lead Center CSV: ad_id lives in the row as ``ag:…``; phones as ``p:+48…``."""
    flat = {
        "id": "l:833529082441880",
        "ad_id": "ag:120245661643030547",
        "email": "smelovalove@mail.ru",
        "phone": "p:+48575496349",
    }
    wrapped = normalizer.coerce_generic_json_to_meta_normalizer_payload(flat)
    out = normalizer.normalize_meta_payload(wrapped, field_mapping=None)
    assert out.get("ad_id") == 120245661643030547
    assert out.get("phone") == "+48575496349"


def test_coerce_polish_nine_digit_phone_gets_48_prefix():
    flat = {"email": "a@b.pl", "phone": "p:696558716"}
    wrapped = normalizer.coerce_generic_json_to_meta_normalizer_payload(flat)
    out = normalizer.normalize_meta_payload(wrapped, field_mapping=None)
    assert out.get("phone") == "+48696558716"


def test_merge_fallback_preserves_contacts():
    n = {"email": None, "phone": None}
    prior = {"email": "keep@x.pl", "phone": "+48123", "first_name": "A"}
    _merge_lead_normalized_fallback(n, prior)
    assert n["email"] == "keep@x.pl"
    assert n["phone"] == "+48123"
    assert n["first_name"] == "A"
