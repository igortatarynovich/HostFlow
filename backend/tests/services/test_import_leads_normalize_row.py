"""CSV lead import: Meta export rows must populate ``ad_id`` for vacancy routing."""

from __future__ import annotations

from backend.app.services.imports.leads import _normalize_row


def test_normalize_row_plain_csv_unchanged():
    row = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+48123123123",
    }
    headers = list(row.keys())
    n, _p, _e = _normalize_row("11111111-1111-1111-1111-111111111111", row, headers)
    assert n.get("ad_id") is None
    assert n.get("email") == "john@example.com"


def test_normalize_row_meta_export_includes_ag_ad_id():
    row = {
        "id": "l:1873229963334208",
        "ad_id": "ag:120245658855070547",
        "email": "finenkooleksandr@gmail.com",
        "phone": "p:+48571794110",
        "full_name": "Oleksandr Finenko",
        "form_id": "f:1621714855640768",
    }
    headers = list(row.keys())
    n, _p, _e = _normalize_row(
        "9497fc29-6051-424d-9344-abb4aed9b110", row, headers, field_mapping=None
    )
    assert n.get("ad_id") == 120245658855070547
    assert n.get("phone") == "+48571794110"
    assert n.get("raw_lead_id") == "l:1873229963334208"
