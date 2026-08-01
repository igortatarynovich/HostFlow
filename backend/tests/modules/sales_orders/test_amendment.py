"""Unit tests for Sales Order commercial amendment."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app.modules.sales_orders.amendment import apply_amendment, snapshot_commercial


def test_snapshot_commercial():
    order = SimpleNamespace(
        currency="PLN",
        payment_term_days=14,
        payment_model="per_hire",
        vat_rate=23,
        guarantee_days=90,
        invoice_right_policy="on_start",
        payer_company_id="c1",
        commercial_snapshot={"currency": "PLN"},
    )
    snap = snapshot_commercial(order)
    assert snap["currency"] == "PLN"
    assert snap["vat_rate"] == "23"
    assert snap["payer_company_id"] == "c1"


def test_apply_amendment_bumps_version_and_history():
    order = SimpleNamespace(
        currency="PLN",
        payment_term_days=14,
        payment_model="per_hire",
        vat_rate=None,
        guarantee_days=None,
        invoice_right_policy=None,
        payer_company_id=None,
        billing_notes=None,
        commercial_snapshot={"currency": "PLN"},
        commercial_version=1,
        commercial_versions=None,
    )
    apply_amendment(
        order,
        changes={"currency": "EUR", "payment_term_days": 30, "reason_ignored": "x"},
        reason="client renegotiation",
        actor_user_id="u1",
    )
    assert order.commercial_version == 2
    assert order.currency == "EUR"
    assert order.payment_term_days == 30
    assert isinstance(order.commercial_versions, list)
    assert len(order.commercial_versions) == 1
    assert order.commercial_versions[0]["version"] == 1
    assert order.commercial_versions[0]["commercial"]["currency"] == "PLN"
    assert order.commercial_versions[0]["reason"] == "client renegotiation"
    assert order.commercial_snapshot["currency"] == "EUR"


def test_apply_amendment_second_round():
    order = SimpleNamespace(
        currency="EUR",
        payment_term_days=30,
        payment_model=None,
        vat_rate=None,
        guarantee_days=None,
        invoice_right_policy=None,
        payer_company_id=None,
        billing_notes=None,
        commercial_snapshot={"currency": "EUR"},
        commercial_version=2,
        commercial_versions=[{"version": 1, "commercial": {"currency": "PLN"}}],
    )
    apply_amendment(order, changes={"currency": "USD"}, reason=None, actor_user_id=None)
    assert order.commercial_version == 3
    assert len(order.commercial_versions) == 2
    assert order.currency == "USD"
