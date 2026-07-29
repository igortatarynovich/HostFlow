"""Unit tests for mapping_applied_v1 fingerprint / stamp helpers."""

from __future__ import annotations

from backend.app.acquisition.mapping_applied_stamp import (
    MAPPING_APPLIED_V1_KEY,
    fingerprint_mapping_rules,
    stamp_mapping_applied_v1,
)


def test_fingerprint_order_insensitive() -> None:
    a = [{"source": "email", "target": "email"}, {"source": "phone", "target": "phone"}]
    b = [{"target": "phone", "source": "phone"}, {"target": "email", "source": "email"}]
    assert fingerprint_mapping_rules(a) == fingerprint_mapping_rules(b)


def test_stamp_mapping_applied_writes_key() -> None:
    norm: dict = {}
    stamp = stamp_mapping_applied_v1(
        norm,
        rules=[{"source": "email", "target": "email"}],
        source_id="11111111-1111-1111-1111-111111111111",
        rules_source="profile",
    )
    assert MAPPING_APPLIED_V1_KEY in norm
    assert stamp["rules_count"] == 1
    assert stamp["rules_fingerprint"]
    assert stamp["rules_source"] == "profile"
