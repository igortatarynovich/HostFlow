"""Telegram-driven candidate intake & command-handling for the inbox.

After the Phase 1 god-module split (step 8/N), this is a package whose
``__init__.py`` re-exports every public symbol from 5 internal sub-modules,
preserving the historical ``from ..._helpers.telegram_intake import …`` API.

Sub-modules (acyclic dependency layering, lower → higher):

* ``ui_text``        — pure rendering helpers (text, keyboards, OTP hash).
                       No DB, no internal deps.
* ``docs_bridge``    — public-token issuing + ruleset/owner-summary snapshot;
                       depends on ``ui_text``.
* ``intake_state``   — 7-step in-chat questionnaire state-machine;
                       depends on ``docs_bridge`` for completion-text.
* ``candidate_link`` — bootstrap candidate from chat + OTP-by-email link;
                       depends on ``ui_text`` + ``docs_bridge``.
* ``dispatcher``     — ``_process_public_telegram_candidate_command``,
                       the single webhook entry point.
"""

from __future__ import annotations

from .ui_text import (  # noqa: F401
    _candidate_owner_context_for_docs,
    _candidate_verification_email_body,
    _format_doc_types_bullets,
    _send_candidate_telegram_reply,
    _telegram_docs_summary_text,
    _telegram_extract_command,
    _telegram_help_text,
    _telegram_keyboard,
    _telegram_name_parts,
    _telegram_onboarding_text,
    _telegram_otp_hash,
    _telegram_vacancies_text,
)
from .intake_state import (  # noqa: F401
    _TG_INTAKE_OPTIONAL_STEPS,
    _TG_INTAKE_STEP_ORDER,
    _TG_INTL_BOOL_FALSE,
    _TG_INTL_BOOL_TRUE,
    _tg_answer_yes_no,
    _tg_apply_step_answer,
    _tg_get_intake_sections,
    _tg_incomplete_steps,
    _tg_intake_help_text,
    _tg_intake_progress_text,
    _tg_intake_skipped_text,
    _tg_parse_step_answer,
    _tg_process_intake_answer,
    _tg_reset_intake_runtime,
    _tg_skip_intake_step,
    _tg_start_or_resume_intake,
    _tg_step_label,
    _tg_step_prompt,
    _tg_unskip_intake_step,
)
from .candidate_link import (  # noqa: F401
    _create_candidate_from_telegram_intake,
    _find_candidate_by_pending_verification,
    _link_candidate_to_telegram_chat,
    _send_telegram_link_code,
)
from .docs_bridge import (  # noqa: F401
    _candidate_intake_documents_url,
    _ensure_candidate_intake_token,
    _generate_public_candidate_token,
    _telegram_docs_checklist_text,
    _telegram_required_docs_snapshot,
    _telegram_scan_command_text,
    _tg_intake_completion_docs_text,
)
from .dispatcher import (  # noqa: F401
    _process_public_telegram_candidate_command,
)

__all__ = [
    "_candidate_owner_context_for_docs",
    "_candidate_verification_email_body",
    "_format_doc_types_bullets",
    "_send_candidate_telegram_reply",
    "_telegram_docs_summary_text",
    "_telegram_extract_command",
    "_telegram_help_text",
    "_telegram_keyboard",
    "_telegram_name_parts",
    "_telegram_onboarding_text",
    "_telegram_otp_hash",
    "_telegram_vacancies_text",
    "_TG_INTAKE_OPTIONAL_STEPS",
    "_TG_INTAKE_STEP_ORDER",
    "_TG_INTL_BOOL_FALSE",
    "_TG_INTL_BOOL_TRUE",
    "_tg_answer_yes_no",
    "_tg_apply_step_answer",
    "_tg_get_intake_sections",
    "_tg_incomplete_steps",
    "_tg_intake_help_text",
    "_tg_intake_progress_text",
    "_tg_intake_skipped_text",
    "_tg_parse_step_answer",
    "_tg_process_intake_answer",
    "_tg_reset_intake_runtime",
    "_tg_skip_intake_step",
    "_tg_start_or_resume_intake",
    "_tg_step_label",
    "_tg_step_prompt",
    "_tg_unskip_intake_step",
    "_create_candidate_from_telegram_intake",
    "_find_candidate_by_pending_verification",
    "_link_candidate_to_telegram_chat",
    "_send_telegram_link_code",
    "_candidate_intake_documents_url",
    "_ensure_candidate_intake_token",
    "_generate_public_candidate_token",
    "_telegram_docs_checklist_text",
    "_telegram_required_docs_snapshot",
    "_telegram_scan_command_text",
    "_tg_intake_completion_docs_text",
    "_process_public_telegram_candidate_command",
]
