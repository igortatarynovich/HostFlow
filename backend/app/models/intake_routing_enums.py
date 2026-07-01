"""Reference values for Intake Routing Foundation (PR-2)."""

from __future__ import annotations

from enum import Enum


class IntakeProvider(str, Enum):
    meta = "meta"
    tiktok = "tiktok"
    website = "website"
    public_intake = "public_intake"
    whatsapp = "whatsapp"
    telegram = "telegram"
    referral = "referral"
    import_ = "import"
    api = "api"
    manual = "manual"
    unknown = "unknown"


class IntakeChannel(str, Enum):
    paid = "paid"
    organic = "organic"
    referral = "referral"
    direct = "direct"
    internal = "internal"
    unknown = "unknown"


class RouteIntent(str, Enum):
    candidate_application = "candidate_application"
    sales_inquiry = "sales_inquiry"
    service_request = "service_request"
    partner_inquiry = "partner_inquiry"
    unknown = "unknown"


class RoutingStatus(str, Enum):
    resolved = "resolved"
    fallback = "fallback"
    unknown = "unknown"


INTAKE_PROVIDERS: frozenset[str] = frozenset(p.value for p in IntakeProvider)
INTAKE_CHANNELS: frozenset[str] = frozenset(c.value for c in IntakeChannel)
ROUTE_INTENTS: frozenset[str] = frozenset(r.value for r in RouteIntent)
ROUTING_STATUSES: frozenset[str] = frozenset(s.value for s in RoutingStatus)
