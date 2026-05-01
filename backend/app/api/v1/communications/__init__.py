"""Communications API package.

After the Phase 1 god-module split (steps 1/N..7/N), this ``__init__.py``
is intentionally a thin shell that:

1. Declares the parent ``router`` (``/communications``).
2. Re-exports helpers from ``._helpers.*`` so existing intra-package
   imports (and a small number of historical external callers) keep
   working.
3. Imports per-topic sub-routers from ``.routes.*`` and mounts them on
   the parent ``router``.
4. Re-exports the public route-handler functions that other modules
   call directly (``services.communications_scheduler`` invokes
   ``run_email_poll_worker`` / ``run_email_dispatch_worker`` outside of
   the HTTP cycle).

All actual handler code lives in ``.routes.{accounts,audit,dispatch,
ingest,messages,oauth,planner,threads,webhooks}`` and helper logic in
``._helpers.{...}``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

router = APIRouter(prefix="/communications", tags=["communications"])
logger = logging.getLogger(__name__)

# Helpers extracted to ``._helpers`` (Phase 1 god-module split, step 2/N).
# Re-exported at module scope so existing route handlers that referenced
# them as bare names keep working without churn.
from ._helpers.utils import (  # noqa: E402,F401
    _now_utc,
    _as_dict,
    _as_list,
    _coerce_datetime,
    _clamp_db_str,
    _deep_merge_dict,
    _json_dict,
    _normalize_email_value,
    _digits_only,
    _looks_like_phone,
    _is_six_digit_code,
)
from ._helpers.working_hours import (  # noqa: E402,F401
    _CLOCK_RE,
    _parse_clock_minutes,
    _normalize_working_hours,
    _validate_iso_date_range,
    _partial_day_blocks_now,
)
from ._helpers.account_settings import (  # noqa: E402,F401
    _derive_account_status,
    _sanitize_account_settings_for_out,
    _account_out,
    _normalize_account_settings_for_store,
)
from ._helpers.oauth import (  # noqa: E402,F401
    _oauth_client_secret,
    _oauth_refresh_token,
    _oauth_access_token,
    _oauth_expires_soon,
    _refresh_oauth_tokens_in_settings_json,
    _ensure_oauth_access_for_mailbox,
    _oauth_provider_for_account,
    _oauth_authorize_url_for_provider,
    _oauth_default_scopes,
    _build_oauth_auth_url,
)
from ._helpers.channels import (  # noqa: E402,F401
    _imap_config_from_account_settings,
    _telegram_config_from_account_settings,
    _whatsapp_config_from_account_settings,
    _viber_config_from_account_settings,
    _messenger_graph_config_from_account_settings,
    _instagram_graph_config_from_account_settings,
)
from ._helpers.tenant_settings import (  # noqa: E402,F401
    _comm_settings_channels,
    _comm_settings_root,
    _tenant_sla_escalation_targets,
    _tenant_comm_allowed_roles,
    _canonical_membership_role_for_escalation,
)
from ._helpers.dto import (  # noqa: E402,F401
    _thread_out,
    _message_out,
    _timeoff_out,
    _planner_event_out,
    _allocation_audit_out,
    _command_audit_out,
)
from ._helpers.access import (  # noqa: E402,F401
    _get_thread_or_404,
    _default_own_company_id_for_tenant,
    _ensure_thread_matches_own_company_scope,
    _get_tenant_or_404,
    _feature_for_channel,
    _message_templates_for_user,
    _require_comm_feature,
    _require_any_comm_feature,
)
from ._helpers.sla import (  # noqa: E402,F401
    _channel_response_sla_minutes,
    _apply_thread_sla_policy_from_message,
    _touch_thread_from_message,
    _resolve_thread_sla_alerts,
)
from ._helpers.dispatch import (  # noqa: E402,F401
    _pick_thread_recipient_address,
    _normalize_email_text,
    _parse_iso_datetime,
    _dispatch_attempt_count,
    _dispatch_next_retry_at,
    _schedule_dispatch_retry,
    _resolve_comm_local_attachment_path,
    _mock_dispatch_outbound_message,
    _dispatch_email_message_via_tenant_smtp,
    _dispatch_telegram_message_via_bot_api,
    _dispatch_whatsapp_message_via_cloud_api,
    _dispatch_messenger_message_via_graph_api,
    _dispatch_instagram_message_via_graph_api,
    _dispatch_viber_message_via_bot_api,
)
from ._helpers.billing import (  # noqa: E402,F401
    _load_tenant_license_row,
    _require_outbound_comms_not_billing_blocked,
)
from ._helpers.escalation import (  # noqa: E402,F401
    _resolve_manual_escalation_recipient_user_ids,
    _emit_manual_thread_escalation_bridge,
)
from ._helpers.ingest import (  # noqa: E402,F401
    _find_thread_for_inbound_email,
    _find_thread_for_inbound_channel,
    _ingest_email_outbound_from_mailbox,
    _find_telegram_account_by_webhook_secret,
    _find_whatsapp_account_by_webhook_secret,
    _find_channel_account_by_webhook_secret,
)
from ._helpers.candidate_lookup import (  # noqa: E402,F401
    _candidate_name,
    _candidate_public_status_url,
    _candidate_apply_url,
    _find_candidate_by_bind_token,
    _find_candidate_by_telegram_chat,
    _candidate_email_options,
    _candidate_phone_options,
    _find_candidates_by_contact,
)
from ._helpers.telegram_intake import (  # noqa: E402,F401
    _telegram_extract_command,
    _telegram_otp_hash,
    _telegram_onboarding_text,
    _candidate_verification_email_body,
    _telegram_name_parts,
    _create_candidate_from_telegram_intake,
    _link_candidate_to_telegram_chat,
    _send_telegram_link_code,
    _find_candidate_by_pending_verification,
    _telegram_vacancies_text,
    _telegram_keyboard,
    _send_candidate_telegram_reply,
    _telegram_help_text,
    _telegram_docs_summary_text,
    _candidate_owner_context_for_docs,
    _format_doc_types_bullets,
    _tg_answer_yes_no,
    _tg_get_intake_sections,
    _tg_incomplete_steps,
    _tg_step_prompt,
    _tg_step_label,
    _tg_intake_progress_text,
    _tg_intake_skipped_text,
    _tg_intake_help_text,
    _tg_reset_intake_runtime,
    _tg_skip_intake_step,
    _tg_unskip_intake_step,
    _tg_parse_step_answer,
    _tg_apply_step_answer,
    _tg_start_or_resume_intake,
    _tg_process_intake_answer,
    _telegram_docs_checklist_text,
    _tg_intake_completion_docs_text,
    _generate_public_candidate_token,
    _ensure_candidate_intake_token,
    _candidate_intake_documents_url,
    _telegram_required_docs_snapshot,
    _telegram_scan_command_text,
    _process_public_telegram_candidate_command,
)


# Pydantic schemas extracted to ``.schemas`` (Phase 1 god-module split).
# Re-exported here so existing call sites (services, tests) keep working
# via ``backend.app.api.v1.communications`` without relying on the package
# layout change.
from .schemas import (  # noqa: E402,F401
    MAX_COMM_MESSAGE_ATTACHMENT_BYTES,
    WorkingHoursWindowIn,
    WorkingHoursDayIn,
    WorkingHoursScheduleIn,
    WorkingHoursScheduleOut,
    NotificationSettingsIn,
    NotificationSettingsOut,
    CommunicationThreadOut,
    CommunicationMessageOut,
    CommunicationThreadListResponse,
    CommunicationMessageListResponse,
    CommunicationMessageTemplateOut,
    CommunicationMessageTemplateListResponse,
    CommunicationThreadDetailResponse,
    CommunicationThreadCreate,
    CommunicationThreadPatch,
    CommunicationMessageAttachmentUploadOut,
    CommunicationMessageCreate,
    CommunicationMarkReadRequest,
    CommunicationUnreadReconcileRequest,
    CommunicationUnreadReconcileResponse,
    CommunicationAutoAssignResponse,
    CommunicationAllocatorPreviewRequest,
    CommunicationAllocatorPreviewResponse,
    CommunicationAllocationAuditOut,
    CommunicationAllocationAuditListResponse,
    CommunicationCommandAuditOut,
    CommunicationCommandAuditListResponse,
    CommunicationCommandAuditBatchCreate,
    CommunicationCommandAuditBatchResponse,
    CommunicationChannelAccountOut,
    CommunicationChannelAccountListResponse,
    CommunicationChannelAccountCreate,
    CommunicationChannelAccountPatch,
    EmailIngestRequest,
    EmailIngestResponse,
    GenericInboundIngestRequest,
    GenericInboundIngestResponse,
    CommunicationDispatchRequest,
    CommunicationDispatchResponse,
    CommunicationDispatchQueuedRequest,
    CommunicationDispatchQueuedResponse,
    CommunicationDeliveryStatusPatch,
    CommunicationAccountActionResponse,
    CommunicationAccountOAuthStartRequest,
    CommunicationAccountOAuthStartResponse,
    CommunicationAccountOAuthCompleteRequest,
    CommunicationAccountOAuthCompleteResponse,
    CommunicationAccountOAuthRefreshRequest,
    CommunicationAccountSyncCursorPatch,
    CommunicationAccountSyncCursorOut,
    TelegramWebhookSimulateRequest,
    CommunicationEmailWorkerDispatchRequest,
    CommunicationEmailWorkerPollRequest,
    CommunicationEmailWorkerPollResponse,
    CommunicationSchedulerStatusOut,
    CommunicationSchedulerRunNowResponse,
    CommunicationPlannerEventOut,
    CommunicationPlannerEventListResponse,
    CommunicationPlannerEventCreate,
    CommunicationPlannerEventPatch,
    TimeOffRequestOut,
    TimeOffRequestListResponse,
    TimeOffRequestCreate,
    TimeOffRequestDecision,
    TimeOffRequestCancel,
)


# NOTE(Phase 1 god-module split, step 7/N): all route handlers
# extracted into per-topic modules under ``.routes`` — threads,
# messages, ingest, webhooks, accounts. See per-module docstrings
# for endpoint inventories. Mounting happens at module bottom via
# ``router.include_router(...)``.


# NOTE(Phase 1 god-module split, step 7/N): channel-account CRUD +
# lifecycle routes (list/create/patch/delete + test-connection,
# Telegram webhook set/delete, sync-now) moved to ``.routes.accounts``.
# Mounted at module bottom via ``router.include_router(accounts_routes.router)``.


# NOTE(Phase 1 god-module split, step 3/N): channel-account OAuth +
# sync-cursor routes moved to ``.routes.oauth``. Mounted at module
# bottom via ``router.include_router(oauth_routes.router)``.


# ---------------------------------------------------------------------------
# Sub-router mounting (Phase 1 god-module split, step 3/N).
#
# Per-topic routers are imported at the very bottom so all module-level
# helper symbols (re-exported via ``from ._helpers.* import *`` above) are
# already defined and any future intra-package import does not clash.
#
# Sub-routers carry no prefix, so they inherit ``/communications`` from the
# parent ``router`` declared at the top of this module.
# ---------------------------------------------------------------------------
from .routes import accounts as _accounts_routes  # noqa: E402
from .routes import audit as _audit_routes  # noqa: E402
from .routes import dispatch as _dispatch_routes  # noqa: E402
from .routes import ingest as _ingest_routes  # noqa: E402
from .routes import messages as _messages_routes  # noqa: E402
from .routes import oauth as _oauth_routes  # noqa: E402
from .routes import planner as _planner_routes  # noqa: E402
from .routes import threads as _threads_routes  # noqa: E402
from .routes import threads_next_action as _threads_next_action_routes  # noqa: E402
from .routes import webhooks as _webhooks_routes  # noqa: E402

# Re-export route handlers that other modules import as functions
# (notably ``services.communications_scheduler`` calls
# ``run_email_dispatch_worker`` and ``run_email_poll_worker`` directly,
# and tests import them from this package). Public names of moved
# handlers stay reachable via ``backend.app.api.v1.communications``.
from .routes.dispatch import (  # noqa: E402,F401
    dispatch_message,
    dispatch_queued_messages,
    patch_message_delivery_status,
    get_communications_scheduler_status,
    run_communications_scheduler_now,
    run_email_dispatch_worker,
)
from .routes.ingest import (  # noqa: E402,F401
    ingest_email,
    ingest_generic_channel,
    run_email_poll_worker,
    simulate_telegram_webhook,
)
from .routes.threads import (  # noqa: E402,F401
    auto_assign_thread,
    create_thread,
    get_thread,
    list_threads,
    mark_thread_read,
    patch_thread,
    reconcile_thread_unread,
)
from .routes.messages import (  # noqa: E402,F401
    create_thread_message,
    list_message_templates,
    list_thread_messages,
    upload_thread_message_attachment,
)
from .routes.accounts import (  # noqa: E402,F401
    create_channel_account,
    delete_channel_account,
    delete_telegram_channel_account_webhook,
    list_channel_accounts,
    patch_channel_account,
    set_telegram_channel_account_webhook,
    sync_channel_account_now,
    test_channel_account_connection,
)
from .routes.webhooks import (  # noqa: E402,F401
    instagram_webhook_public,
    instagram_webhook_verify,
    messenger_webhook_public,
    messenger_webhook_verify,
    telegram_webhook_public,
    viber_webhook_public,
    whatsapp_webhook_public,
    whatsapp_webhook_verify,
)

router.include_router(_audit_routes.router)
router.include_router(_dispatch_routes.router)
router.include_router(_planner_routes.router)
router.include_router(_oauth_routes.router)
router.include_router(_accounts_routes.router)
router.include_router(_threads_routes.router)
# G-8 stage 2.3: per-thread "what to do next" CTA. Lives in its own
# sub-router file (`routes/threads_next_action.py`). Registration order
# vs `_threads_routes` does not matter for Starlette here — the next-action
# path has more segments than `/threads/{thread_id}` so they cannot
# alias each other — but we include it adjacent for code locality.
router.include_router(_threads_next_action_routes.router)
router.include_router(_messages_routes.router)
router.include_router(_ingest_routes.router)
router.include_router(_webhooks_routes.router)
