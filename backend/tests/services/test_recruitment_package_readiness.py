"""PR16 recruitment package readiness tests."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.services.recruitment_package_readiness import _missing_contact_fields_legacy as _missing_contact_fields


def test_missing_contact_fields_detects_gaps() -> None:
    cand = SimpleNamespace(
        phone="",
        email="",
        address=None,
        _get_contacts=lambda: {},
        _get_personal_data=lambda: {},
        _get_extra=lambda: {},
    )
    missing = _missing_contact_fields(cand)  # type: ignore[arg-type]
    codes = {m["field_code"] for m in missing}
    assert "phone" in codes
    assert "email" in codes
    assert "address" in codes


def test_missing_contact_fields_passes_when_complete() -> None:
    cand = SimpleNamespace(
        phone="+48111222333",
        email="a@b.c",
        address="Street 1",
        _get_contacts=lambda: {},
        _get_personal_data=lambda: {"address": "Street 1"},
        _get_extra=lambda: {},
    )
    assert _missing_contact_fields(cand) == []  # type: ignore[arg-type]
