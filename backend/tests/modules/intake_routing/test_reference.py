"""Reference enum normalization and catalog (PR-2)."""

from __future__ import annotations

from backend.app.models.intake_routing_enums import (
    INTAKE_CHANNELS,
    INTAKE_PROVIDERS,
    ROUTE_INTENTS,
    ROUTING_STATUSES,
    IntakeProvider,
    RouteIntent,
)
from backend.app.modules.intake_routing.reference import (
    normalize_channel,
    normalize_external_key_secondary,
    normalize_provider,
    normalize_route_intent,
    normalize_routing_status,
    reference_catalog,
)


def test_reference_catalog_contains_all_enums() -> None:
    catalog = reference_catalog()
    assert catalog["provider"] == INTAKE_PROVIDERS
    assert catalog["channel"] == INTAKE_CHANNELS
    assert catalog["route_intent"] == ROUTE_INTENTS
    assert catalog["routing_status"] == ROUTING_STATUSES
    assert "meta" in catalog["provider"]
    assert "sales_inquiry" in catalog["route_intent"]
    assert "resolved" in catalog["routing_status"]


def test_normalize_provider_import_alias() -> None:
    assert normalize_provider("import") == IntakeProvider.import_.value
    assert normalize_provider("META") == IntakeProvider.meta.value
    assert normalize_provider("nope") == IntakeProvider.unknown.value


def test_normalize_route_intent_legacy_phase0_mapping() -> None:
    assert normalize_route_intent("candidate") == RouteIntent.candidate_application.value
    assert normalize_route_intent("client_lead") == RouteIntent.sales_inquiry.value
    assert normalize_route_intent("service_order_lead") == RouteIntent.service_request.value
    assert normalize_route_intent("partner_lead") == RouteIntent.partner_inquiry.value
    assert normalize_route_intent("sales_inquiry") == RouteIntent.sales_inquiry.value
    assert normalize_route_intent("") == RouteIntent.unknown.value


def test_normalize_routing_status_and_secondary_key() -> None:
    assert normalize_routing_status("fallback") == "fallback"
    assert normalize_routing_status("bad") == "unknown"
    assert normalize_external_key_secondary(None) == ""
    assert normalize_external_key_secondary(" page_id:123 ") == "page_id:123"


def test_normalize_channel() -> None:
    assert normalize_channel("paid") == "paid"
    assert normalize_channel("PAID") == "paid"
    assert normalize_channel("invalid") == "unknown"
