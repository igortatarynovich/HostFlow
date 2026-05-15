"""Audit event types for upgrade spec (RODO, Handoff, Contact attempts)."""

from __future__ import annotations

from enum import Enum


class AuditEntityType(str, Enum):
    """Entity types for audit events."""
    candidate = "candidate"
    lead = "lead"
    handoff = "handoff"
    rodo_notification = "rodo_notification"
    contact_attempt = "contact_attempt"


class AuditEventType(str, Enum):
    """Event types for audit log (action field)."""
    # Handoff
    handoff_requested = "handoff_requested"
    handoff_accepted = "handoff_accepted"
    handoff_rejected = "handoff_rejected"
    handoff_returned = "handoff_returned"
    handoff_cancelled = "handoff_cancelled"
    # RODO
    rodo_sent = "rodo_sent"
    rodo_sent_failed = "rodo_sent_failed"
    # Contact attempts
    contact_attempt_logged = "contact_attempt_logged"
    # Auto-reject
    rejected_no_contact = "rejected_no_contact"
    # Processor
    processor_changed = "processor_changed"
    # Pipeline document overrides (stage / handoff gates)
    pipeline_override_requested = "pipeline_override_requested"
    pipeline_override_approved = "pipeline_override_approved"
    pipeline_override_rejected = "pipeline_override_rejected"
    pipeline_override_revoked = "pipeline_override_revoked"
    # Privileged recruitment lock bypass (handoff / handed_off application)
    recruitment_lock_write_override = "recruitment_lock_write_override"
    # System automation skipped mutating candidate because workforce HR row owns the dossier
    system_automation_skipped_workforce_lock = "system_automation_skipped_workforce_lock"
