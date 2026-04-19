"""Leads service package — public surface assembly.

This ``__init__`` is intentionally a re-export hub: every helper / analytic /
pipeline function lives in a sub-module (``_helpers``, ``_listing``,
``_funnel``, ``_nba``, ``_timeline``, ``_processing``, ``_bulk``, ``_retry``,
``_reroute``) and is re-exported here so the historical ``service.<name>``
access pattern (router, ``admin_service``, scripts, tests, importers) keeps
working without churn.

Phase 1 #3 god-module decomposition: ``service.py`` (4145 LOC) →
``service/`` package, ``__init__.py`` ≤ 200 LOC + 9 sub-modules, all
≤ 1500 LOC. See ``docs/HOSTFLOW_AUDIT_AND_PLAN.md``.
"""

from __future__ import annotations

# Step 2/N: helpers — types, validators, loaders, event/reminder helpers,
# processing-mode resolution, vacancy resolution, qualification preview/audit.
from ._helpers import (  # noqa: F401
    LeadProcessingError,
    MetaLeadResult,
    MetaLeadRetryOutcome,
    _apply_leads_processing_mode_v1_to_normalized,
    _audit_lead_qualification_rule_match,
    _build_lead_outcome,
    _create_lead_followup_reminder,
    _emit_lead_event,
    _load_settings,
    _load_supervisor_id,
    _load_tenant_business_type,
    _normalize_business_type,
    _normalize_stored_leads_processing_mode_v1,
    _pick_lead_assignee_id,
    _resolve_vacancy,
    _rule_recruiter_id_from_normalized,
    _stamp_lead_qualification_preview_v1,
    _triage_bypass_from_vacancy_fallback,
    _vacancy_allows_auto_convert_on_fit,
    _validate_company_id,
    _validate_recruiter_id,
    lead_processing_error_as_http,
    resolve_vacancy_for_lead_processing,
)

# Step 3/N: listing/filter/count helpers.
from ._listing import (  # noqa: F401
    CONVERSION_ROOTS_SET,
    CONVERSION_ROOT_ORDER,
    LEAD_LIST_PIPELINE_ERROR_WHITELIST,
    _LEAD_LEGACY_STAGE_TO_ROOT,
    _build_lead_list_filters,
    _lead_list_text_search_or,
    _sql_effective_lead_conversion_root,
    count_candidate_overdue_reminders_for_assignee,
    count_candidates_no_next_action_for_assignee,
    count_leads,
    list_leads,
)

# Step 4/N: funnel + stage-health analytics.
from ._funnel import (  # noqa: F401
    ConversionFunnelSliceParams,
    LEAD_CRM_STAGES_FOR_HEALTH,
    _DWELL_LOG_CHUNK,
    _as_utc,
    _compute_lead_conversion_funnel,
    _conversion_funnel_slice_predicates,
    _count_leads_for_conversion_funnel,
    _count_leads_for_conversion_root,
    _dwell_avg_p50,
    _lead_conversion_funnel_dwell_by_root,
    _lead_conversion_funnel_dwell_by_stage,
    _load_lead_funnel_root_lookup,
    _lost_from_stage_breakdown,
    _lost_reason_code_breakdown,
    _percentile_sorted,
    _python_effective_conversion_root,
    lead_conversion_funnel_snapshot,
    lead_stage_health_snapshot,
)

# Step 5/N: NBA + timeline.
from ._nba import (  # noqa: F401
    NBA_FUNNEL_MIN_AT_OR_BEYOND,
    NBA_FUNNEL_MIN_DWELL_SAMPLE,
    NBA_FUNNEL_MIN_TOTAL_WIN,
    NBA_FUNNEL_SLOW_DWELL_DAYS,
    NBA_FUNNEL_WEAK_SHARE_MAX,
    _nba_lead_locked_and_required,
    lead_next_actions_snapshot,
    nba_conversion_funnel_insight_groups,
)
from ._timeline import get_lead_timeline  # noqa: F401

# Step 6/N: lead-processing pipeline core.
from ._processing import process_normalized_lead  # noqa: F401

# Step 7/N: bulk + reprocess + Meta entry-points.
from ._bulk import (  # noqa: F401
    _ad_id_from_meta_lead_export_row,
    _apply_stored_lead_row_ids_to_normalized,
    _bulk_auto_process_meta_queue_filters,
    _bulk_auto_process_single_lead,
    _coerce_lead_payload_to_dict,
    _merge_lead_normalized_fallback,
    _payload_needs_flat_field_data_coercion,
    bulk_auto_process_meta_lead_queue,
    count_bulk_auto_process_meta_lead_queue,
    process_generic_inbound_webhook_lead,
    process_meta_lead,
    reprocess_stored_lead_payload,
)
from ._retry import retry_meta_leads  # noqa: F401
from ._reroute import reroute_lead_manual  # noqa: F401
