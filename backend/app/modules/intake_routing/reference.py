"""Normalize and validate intake routing reference values."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.models.intake_routing_enums import (
    INTAKE_CHANNELS,
    INTAKE_PROVIDERS,
    ROUTE_INTENTS,
    ROUTING_STATUSES,
    IntakeChannel,
    IntakeProvider,
    RouteIntent,
    RoutingStatus,
)


def normalize_provider(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value == "import":
        return IntakeProvider.import_.value
    if value in INTAKE_PROVIDERS:
        return value
    return IntakeProvider.unknown.value


def normalize_channel(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in INTAKE_CHANNELS:
        return value
    return IntakeChannel.unknown.value


def normalize_route_intent(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    # Phase 0 bridge vocabulary (read compat only)
    legacy = {
        "candidate": RouteIntent.candidate_application.value,
        "client_lead": RouteIntent.sales_inquiry.value,
        "service_order_lead": RouteIntent.service_request.value,
        "partner_lead": RouteIntent.partner_inquiry.value,
    }
    if value in legacy:
        return legacy[value]
    if value in ROUTE_INTENTS:
        return value
    return RouteIntent.unknown.value


def normalize_routing_status(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in ROUTING_STATUSES:
        return value
    return RoutingStatus.unknown.value


def normalize_external_key_secondary(raw: Optional[Any]) -> str:
    return str(raw or "").strip()


def reference_catalog() -> dict[str, frozenset[str]]:
    """Seed / API reference snapshot of allowed values."""
    return {
        "provider": INTAKE_PROVIDERS,
        "channel": INTAKE_CHANNELS,
        "route_intent": ROUTE_INTENTS,
        "routing_status": ROUTING_STATUSES,
    }
