"""Recruitment intake destination handlers."""

from backend.app.modules.recruitment.intake.lead_draft_handler import (
    HANDLER_ID,
    handle_candidate_application_draft,
)

__all__ = ["HANDLER_ID", "handle_candidate_application_draft"]
