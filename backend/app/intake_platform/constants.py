"""ADR-022 Intake Platform enums."""

from __future__ import annotations

from enum import Enum


class FormPurpose(str, Enum):
    questionnaire = "questionnaire"
    inquiry = "inquiry"
    application = "application"
    registration = "registration"
    update = "update"
    consent = "consent"
    survey = "survey"
    document_collection = "document_collection"


class SubmissionPolicyMode(str, Enum):
    create = "create"
    match_or_create = "match_or_create"
    attach = "attach"
    review = "review"
    ignore = "ignore"
    notify = "notify"


class MatchConfidence(str, Enum):
    none = "none"
    strong_single = "strong_single"
    possible = "possible"
    conflict = "conflict"
    multiple = "multiple"


FORM_PURPOSES: frozenset[str] = frozenset(p.value for p in FormPurpose)
SUBMISSION_POLICY_MODES: frozenset[str] = frozenset(m.value for m in SubmissionPolicyMode)

SUBMISSIONS_V1_KEY = "submissions_v1"

DEFAULT_SALES_MATCH_POLICY: dict = {
    "identifier_fields": ["email", "phone"],
    "target_route_intent": "sales_inquiry",
    "require_entity_profile_match": True,
    "require_offering_match": False,
    "allowed_lifecycle_statuses": ["new", "reviewing", "waiting_for_information"],
    "window_days": 90,
    "auto_attach_on": "strong_single",
    "review_on": ["possible", "conflict", "multiple"],
}

DEFAULT_INQUIRY_POLICY: dict = {
    "mode": SubmissionPolicyMode.match_or_create.value,
    "match_policy": DEFAULT_SALES_MATCH_POLICY,
}

DEFAULT_INVITE_POLICY: dict = {
    "mode": SubmissionPolicyMode.attach.value,
}

DEFAULT_RECRUITMENT_APPLICATION_POLICY: dict = {
    "mode": SubmissionPolicyMode.create.value,
}
