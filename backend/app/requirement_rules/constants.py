"""Requirement Rules Engine constants."""

from __future__ import annotations

REQUIREMENT_EVALUATION_V1 = "requirement_evaluation_v1"
REQUIREMENT_RULES_V1 = "requirement_rules_v1"

RULE_TYPE_FIELD_REQUIRED = "field_required"
RULE_TYPE_DOCUMENT_REQUIRED = "document_required"
RULE_TYPE_DOCUMENT_SLOT_REQUIRED = "document_slot_required"

SOURCE_ENTITY_PROFILE = "entity_profile"
SOURCE_DOCUMENT_PACK = "document_pack"
SOURCE_PROCESS_PROFILE = "process_profile"
SOURCE_TENANT_OVERRIDE = "tenant_override"

OVERRIDE_KIND_RELAX = "relax"
OVERRIDE_KIND_ADD = "add"
OVERRIDE_KIND_SEVERITY = "severity"

OVERRIDE_STATUS_ACTIVE = "active"
OVERRIDE_STATUS_REVOKED = "revoked"

LEVEL_BLOCKING = "blocking"
LEVEL_WARNING = "warning"

VALID_CONTEXTS = frozenset({"intake", "card_save", "transition", "handoff", "readiness"})

CONTEXT_TO_FIELD_LEVEL: dict[str, str] = {
    "intake": "intake_level",
    "card_save": "card_save_level",
    "transition": "transition_level",
    "handoff": "transition_level",
    "readiness": "card_save_level",
}

DOCUMENT_EVALUATION_CONTEXTS = frozenset({"card_save", "transition", "handoff", "readiness"})
