"""Recruitment application handoff surface — public contract."""

from __future__ import annotations

from backend.app.services.recruitment_application_lifecycle import (
    InvalidRecruitmentApplicationTransition,
    normalize_application_status,
    set_recruitment_application_status,
)
from backend.app.services.recruitment_application_service import (
    ensure_recruitment_application_for_external_intent,
    ensure_recruitment_application_for_lead_intent,
    get_application_for_handoff,
)
from backend.app.services.recruitment_application_service import (
    _explicit_pool_intent as explicit_pool_intent,
)

__all__ = [
    "InvalidRecruitmentApplicationTransition",
    "ensure_recruitment_application_for_external_intent",
    "ensure_recruitment_application_for_lead_intent",
    "explicit_pool_intent",
    "get_application_for_handoff",
    "normalize_application_status",
    "set_recruitment_application_status",
]
