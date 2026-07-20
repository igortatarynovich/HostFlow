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
    # Lead operational communication (non-RODO)
    lead_communication_application_received_sent = "lead.communication.application_received_sent"
    lead_communication_rejection_sent = "lead.communication.rejection_sent"
    lead_communication_moving_forward_sent = "lead.communication.moving_forward_sent"
    # Deprecated producer (C0.3): do not emit for new failures — use communication.delivery.*.
    lead_communication_failed = "lead.communication.failed"
    communication_delivery_failed = "communication.delivery.failed"
    communication_delivery_retry_manual = "communication.delivery.retry_manual"
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
