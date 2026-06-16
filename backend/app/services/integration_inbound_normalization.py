from __future__ import annotations

from typing import Any

from backend.app.services.reference_service_facade import ReferenceServiceFacade


def normalize_inbound_country_alpha2(value: Any) -> str | None:
    """Normalize external inbound country value to canonical ISO alpha-2 code."""
    raw = str(value or "").strip()
    if not raw:
        return None
    return ReferenceServiceFacade.normalize_country_alpha2(raw)


def normalize_inbound_citizenship_alpha2(value: Any) -> str | None:
    """Normalize external inbound citizenship value to canonical ISO alpha-2 code."""
    raw = str(value or "").strip()
    if not raw:
        return None
    return ReferenceServiceFacade.normalize_citizenship_alpha2(raw)

