from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.constants.spa_paths import LEADS as SPA_LEADS


LeadStatus = Literal[
    "new",
    "processed",
    "duplicated",
    "failed",
    "needs_routing",
    "duplicate_review",
    "rejected",
]
LeadType = Literal["candidate", "client"]
LeadTargetType = Literal["candidate", "client_lead", "service_order_lead", "partner_lead"]
LeadStage = Literal["new", "contacted", "qualified", "converted", "lost"]
LeadImportStatus = Literal["pending", "running", "completed", "failed"]
LeadNextActionStatus = Literal["scheduled", "overdue", "no_next_action"]
LeadFitStatus = Literal["fit", "no_fit", "needs_info", "no_criteria"]


class LeadStageContractOut(BaseModel):
    """Mirrors FunnelStage.stage_contract_v1 (§2.3)."""

    model_config = ConfigDict(extra="forbid")

    owner_role: Optional[str] = None
    required_actions: Optional[List[str]] = None
    sla_hours: Optional[int] = None
    auto_rules: Optional[Dict[str, Any]] = None


class MetaLeadResponse(BaseModel):
    lead_id: UUID
    status: LeadStatus
    vacancy_id: Optional[UUID] = None
    candidate_id: Optional[UUID] = None
    recruiter_id: Optional[UUID] = None
    business_type: Optional[str] = None
    outcome_entity_type: Optional[str] = None
    outcome_entity_id: Optional[UUID] = None
    outcome_entity_name: Optional[str] = None
    error: Optional[str] = None


def lead_vacancy_routing_aux(normalized: Any, lead_vacancy_id: Any) -> tuple[bool, bool]:
    """Return ``(has_suggested_routing, recruiter_confirmed_for_lead_vacancy)`` for intake gating."""
    norm = normalized if isinstance(normalized, dict) else {}
    lv = str(lead_vacancy_id).strip() if lead_vacancy_id else ""
    suggested = bool(
        lv
        or norm.get("vacancy_id")
        or norm.get("vacancy_id_hint")
        or norm.get("resolved_vacancy_id")
    )
    confirm = norm.get("intake_vacancy_confirm_v1")
    if not isinstance(confirm, dict):
        return suggested, False
    cv = str(confirm.get("vacancy_id") or "").strip()
    confirmed = bool(lv and cv and cv == lv)
    return suggested, confirmed


def intake_vacancy_confirm_triage_bypass(normalized: Any, vacancy: Any) -> bool:
    """When assisted/fit triage would block, allow conversion if recruiter confirmed this vacancy."""
    if vacancy is None:
        return False
    norm = normalized if isinstance(normalized, dict) else {}
    confirm = norm.get("intake_vacancy_confirm_v1")
    if not isinstance(confirm, dict):
        return False
    cv = str(confirm.get("vacancy_id") or "").strip()
    vid = str(getattr(vacancy, "id", "") or "").strip()
    return bool(cv and vid and cv == vid)


class LeadVacancyConfirmIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID = Field(description="Vacancy the recruiter commits for this lead (routing + process).")


IntakeResolutionDecision = Literal["qualify", "reject", "pool", "request_info", "duplicate_review"]


class LeadIntakeDecisionIn(BaseModel):
    """Operator intake resolution (not candidate pipeline). ``reason_code`` is required for ``reject``."""

    model_config = ConfigDict(extra="forbid")

    decision: IntakeResolutionDecision
    reason_code: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Canonical reject code when decision is reject.",
    )
    note: Optional[str] = Field(default=None, max_length=2000)
    funnel_id: Optional[UUID] = Field(
        default=None,
        description="Optional funnel when decision is pool (talent pool intent).",
    )


DuplicateDecisionType = Literal["attach_existing", "create_new", "ignore"]


class LeadDuplicateDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DuplicateDecisionType
    note: Optional[str] = Field(default=None, max_length=2000)


class LeadQuestionnaireInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mark_sent: bool = Field(
        default=False,
        description="When true, marks the invite as sent (Wyślij ankietę).",
    )
    lead_form_id: Optional[UUID] = Field(
        default=None,
        description="Optional B2B questionnaire form; defaults to tenant targeted-advertising form.",
    )


class LeadQuestionnaireFormOptionOut(BaseModel):
    id: UUID
    title: str
    public_slug: Optional[str] = None
    is_system_preset: bool = False


class LeadQuestionnaireInviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    lead_form_id: Optional[UUID] = None
    token: str
    apply_url: str
    status: str
    entity_profile_code: Optional[str] = None
    presentation_code: Optional[str] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class LeadOut(BaseModel):
    id: UUID
    tenant_id: UUID
    business_type: Optional[str] = None
    lead_type: LeadType = "candidate"
    lead_target_type: LeadTargetType = "candidate"
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
    vacancy_id: Optional[UUID] = None
    vacancy_title: Optional[str] = None
    source: str
    ad_id: Optional[int] = None
    external_id: Optional[str] = Field(
        default=None,
        description="Source-native stable id (e.g. Meta leadgen_id, or public-intake:{candidate_id}); dedupe + admin Graph picker labels.",
    )
    status: LeadStatus
    stage: Optional[str] = None
    funnel_id: Optional[UUID] = None
    stage_contract: Optional[LeadStageContractOut] = None
    candidate_id: Optional[UUID] = None
    candidate_name: Optional[str] = None
    converted_client_id: Optional[UUID] = None
    client_account_id: Optional[UUID] = None
    outcome_entity_type: Optional[str] = None
    outcome_entity_id: Optional[UUID] = None
    outcome_entity_name: Optional[str] = None
    service_order_id: Optional[UUID] = None
    recruiter_id: Optional[UUID] = None
    error: Optional[str] = None
    payload: Dict[str, Any]
    normalized: Optional[Dict[str, Any]] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_routed_at: Optional[datetime] = None
    # Next action (reminders-based activity loop)
    next_action_status: Optional[LeadNextActionStatus] = None
    next_action_due_at: Optional[datetime] = None
    next_action_type: Optional[str] = None
    next_action_title: Optional[str] = None
    # Vacancy fit check (criteria-based)
    fit_status: Optional[LeadFitStatus] = None
    fit_reasons: List[str] = Field(default_factory=list)
    vacancy_routing_confirmed: Optional[bool] = Field(
        default=None,
        description="True when ``intake_vacancy_confirm_v1`` matches the lead's committed ``vacancy_id``.",
    )

    model_config = ConfigDict(from_attributes=True)


class LeadStageUpdate(BaseModel):
    stage: Optional[LeadStage] = None
    assignment_locked: Optional[bool] = Field(
        default=None,
        description="When set, merges normalized.assignment_lock_v1 (blocks auto-distribution for this lead).",
    )
    lost_reason_code: Optional[str] = Field(
        default=None,
        max_length=64,
        description="When moving to stage lost, optional stable code (stored in audit + normalized.lead_lost_reason_v1).",
    )
    lost_reason_note: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional free-text note when marking lost.",
    )

    @field_validator("lost_reason_code", "lost_reason_note", mode="before")
    @classmethod
    def _strip_lost_reason(cls, v: Any) -> Any:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @model_validator(mode="after")
    def _lost_reason_only_with_lost_stage(self) -> "LeadStageUpdate":
        has = bool(self.lost_reason_code) or bool(self.lost_reason_note)
        if has and str(self.stage or "") != "lost":
            raise ValueError("lost_reason_code and lost_reason_note are only allowed when stage is 'lost'")
        return self


class BulkLeadUpdateRequest(BaseModel):
    lead_ids: List[UUID] = Field(min_length=1)
    stage: Optional[LeadStage] = None
    status: Optional[LeadStatus] = None
    lost_reason_code: Optional[str] = Field(
        default=None,
        max_length=64,
        description="When bulk-setting stage to lost, optional reason code (audit + normalized per lead).",
    )
    lost_reason_note: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional shared note for all leads moved to lost in this bulk call.",
    )

    @field_validator("lost_reason_code", "lost_reason_note", mode="before")
    @classmethod
    def _strip_bulk_lost_reason(cls, v: Any) -> Any:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @model_validator(mode="after")
    def _bulk_lost_reason_only_lost_stage(self) -> "BulkLeadUpdateRequest":
        has = bool(self.lost_reason_code) or bool(self.lost_reason_note)
        if has and str(self.stage or "") != "lost":
            raise ValueError("lost_reason_code and lost_reason_note are only allowed when stage is 'lost'")
        return self


class BulkLeadUpdateResponse(BaseModel):
    updated: int


class BulkAutoProcessQueueRequest(BaseModel):
    """§2.3 Dashboard auto-fix: batch Meta lead processing (Team+ plan)."""

    max_items: int = Field(default=25, ge=1, le=50, description="Max Meta leads to process in one call.")
    only_without_candidate: bool = Field(
        default=False,
        description="If true, only leads with no candidate_id (typical backlog cleanup).",
    )
    error_equals: Optional[str] = Field(
        default=None,
        description="If set, only leads whose stored error equals this (e.g. VACANCY_NOT_RESOLVED).",
    )
    concurrency: int = Field(
        default=12,
        ge=1,
        le=32,
        description="Parallel workers; each lead uses its own DB session (bounded pool).",
    )
    force_candidate_conversion: bool = Field(
        default=False,
        description="Bypass assisted/fit gates and create candidates when vacancy+contacts allow (operator bulk).",
    )


class BulkAutoProcessQueueItemOut(BaseModel):
    lead_id: str
    ok: bool
    status_after: Optional[str] = None
    error: Optional[str] = None


class BulkAutoProcessQueueResponse(BaseModel):
    results: List[BulkAutoProcessQueueItemOut]
    attempted: int
    succeeded: int
    failed: int


class LeadListResponse(BaseModel):
    items: List[LeadOut]
    total: int
    limit: int
    offset: int


class NextActionQueryParams(BaseModel):
    """Query keys for SPA drill-down (leads list, candidates quick view, tasks inbox)."""

    status: Optional[str] = None
    stage: Optional[str] = None
    conversion_root: Optional[str] = Field(
        default=None,
        description="§2.12 GET /leads filter: lead | qualified | active | final",
    )
    lost_reason_code: Optional[str] = Field(
        default=None,
        description="§2.12 GET /leads: processed + lost + normalized.lead_lost_reason_v1.code (conversion_root ignored).",
    )
    lost_from_crm_stage: Optional[str] = Field(
        default=None,
        description="§2.12 GET /leads: prior CRM stage code on audit transition into lost (or 'unknown').",
    )
    next_action: Optional[str] = None
    pipeline_error: Optional[str] = Field(
        default=None,
        description="GET /leads: exact Lead.error (whitelist: LEAD_FIT_NO_MATCH, LEAD_FIT_NEEDS_INFO).",
    )
    tab: Optional[str] = None
    t_status: Optional[str] = None
    t_entity: Optional[str] = None
    t_due_bucket: Optional[str] = None


class NextActionGroupOut(BaseModel):
    """One grouped NBA bucket (leads and/or candidates)."""

    id: str
    entity: Literal["lead", "candidate"] = "lead"
    reason: str
    title: str
    count: int
    priority: int = 0
    query: NextActionQueryParams
    path: str = Field(default=SPA_LEADS, description="SPA path; merge query client-side.")
    locked: bool = Field(
        default=False,
        description="True when tenant plan is below required_plan — count still visible, drill-down disabled.",
    )
    required_plan: Optional[str] = Field(
        default=None,
        description="Minimum plan code to use this bucket (e.g. team, pro).",
    )
    nba_detail: Optional[Dict[str, Union[str, int, float]]] = Field(
        default=None,
        description="Optional metrics for dashboard i18n (funnel insights §2.12).",
    )


class LeadNextActionsResponse(BaseModel):
    generated_at: datetime
    own_company_id: Optional[str] = None
    plan_code: str = Field(default="starter", description="Resolved TenantLicense.plan (lowercase).")
    nba_tier: Literal["solo", "team"] = Field(
        default="solo",
        description="solo: starter/trial/free/solo — some NBA groups may be locked; team: Team-tier and above.",
    )
    groups: List[NextActionGroupOut] = Field(default_factory=list)


class LeadStageHealthRow(BaseModel):
    """Per CRM stage: processed volume + next-action health (§2.3)."""

    stage: str
    processed_total: int
    no_next_action: int
    overdue: int
    stuck: int


class LeadStageHealthResponse(BaseModel):
    generated_at: datetime
    own_company_id: Optional[str] = None
    stages: List[LeadStageHealthRow] = Field(default_factory=list)


class LeadConversionFunnelStage(BaseModel):
    """One conversion root on the win path (§2.12): exact count + cumulative at-or-beyond."""

    model_config = ConfigDict(extra="forbid")

    stage: str = Field(
        description="Root funnel bucket: lead | qualified | active | final (from funnel_stage mapping + legacy fallback)."
    )
    count: int
    at_or_beyond: int
    dwell_avg_days: Optional[float] = Field(
        default=None,
        description="Mean days since last transition into this stage (ActivityLog), else lead.created_at.",
    )
    dwell_p50_days: Optional[float] = Field(default=None, description="Median days in current stage.")
    dwell_sample_size: int = Field(default=0, description="Leads with computed dwell for this stage.")


class LeadConversionFunnelEdge(BaseModel):
    """Snapshot progression: at_or_beyond(next) / at_or_beyond(from); None if denominator is 0."""

    model_config = ConfigDict(extra="forbid")

    from_stage: str
    to_stage: str
    progressed_share: Optional[float] = None


class LeadConversionFunnelLostFromStage(BaseModel):
    """Distinct leads that reached CRM stage lost from a prior stage (audit `lead.stage_changed`)."""

    model_config = ConfigDict(extra="forbid")

    from_stage: str
    lead_count: int


class LeadConversionFunnelLostReasonRow(BaseModel):
    """Distinct leads marked lost per audit payload.lost_reason_code (unknown if unset)."""

    model_config = ConfigDict(extra="forbid")

    reason_code: str
    lead_count: int


class LeadConversionFunnelCohortWindow(BaseModel):
    """§2.12 stretch: one cohort time window snapshot (for WoW compare)."""

    model_config = ConfigDict(extra="forbid")

    cohort_created_at_min: datetime
    cohort_created_at_max_exclusive: datetime
    total_win_path_processed: int
    lost_processed_count: int
    status_new_count: int
    stages: List[LeadConversionFunnelStage] = Field(default_factory=list)
    edges: List[LeadConversionFunnelEdge] = Field(default_factory=list)


class LeadConversionFunnelResponse(BaseModel):
    """Conversion snapshot using §2.12 root buckets (funnel_stages.conversion_root_v1 + legacy CRM codes)."""

    model_config = ConfigDict(extra="forbid")

    aggregation_mode: Literal["conversion_roots"] = Field(
        default="conversion_roots",
        description="Stages are cross-pipeline root buckets, not raw CRM codes.",
    )
    generated_at: datetime
    own_company_id: Optional[str] = None
    filter_source: Optional[str] = Field(default=None, description="Applied slice: lead.source (case-insensitive exact).")
    filter_vacancy_id: Optional[str] = Field(default=None, description="Applied slice: Lead.vacancy_id.")
    filter_funnel_id: Optional[str] = Field(default=None, description="Applied slice: Lead.funnel_id.")
    filter_assignee_user_id: Optional[str] = Field(
        default=None,
        description="Applied slice: Candidate.recruiter_id for linked candidate.",
    )
    status_new_count: int = Field(description="Leads with status=new (ingest / not yet processed).")
    lost_processed_count: int = Field(description="Processed leads currently in CRM stage lost.")
    lost_dwell_avg_days: Optional[float] = Field(default=None, description="Mean days in lost for processed leads.")
    lost_dwell_p50_days: Optional[float] = Field(default=None, description="Median days in lost.")
    lost_dwell_sample_size: int = Field(default=0, description="Processed leads in lost with dwell computed.")
    total_win_path_processed: int = Field(
        description="Processed leads on the win path (non-lost with a resolved conversion root)."
    )
    lost_from_stage: List[LeadConversionFunnelLostFromStage] = Field(
        default_factory=list,
        description="Count of distinct leads per prior CRM stage on transitions into lost (ActivityLog).",
    )
    lost_reason_breakdown: List[LeadConversionFunnelLostReasonRow] = Field(
        default_factory=list,
        description="Distinct leads per lost_reason_code on transitions into lost (ActivityLog).",
    )
    stages: List[LeadConversionFunnelStage] = Field(default_factory=list)
    edges: List[LeadConversionFunnelEdge] = Field(default_factory=list)
    cohort_created_after: Optional[datetime] = Field(
        default=None,
        description="When set: funnel counts include only leads with created_at >= this (inclusive).",
    )
    cohort_created_before_exclusive: Optional[datetime] = Field(
        default=None,
        description="When set: funnel counts include only leads with created_at < this (exclusive).",
    )
    cohort_prior_window: Optional[LeadConversionFunnelCohortWindow] = Field(
        default=None,
        description="Previous period of equal length when cohort_compare_prior was requested (Team+).",
    )


class LeadTimelineEventOut(BaseModel):
    at: datetime
    kind: str
    source: str
    title: Optional[str] = None
    description: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class LeadTimelineResponse(BaseModel):
    items: List[LeadTimelineEventOut]


class UnmappedAdGroup(BaseModel):
    ad_id: str
    count: int
    leads: List[LeadOut]


class UnmappedLeadsResponse(BaseModel):
    groups: List[UnmappedAdGroup]


class LeadImportJobOut(BaseModel):
    id: UUID
    filename: str
    status: LeadImportStatus
    total_rows: int
    processed_rows: int
    success_rows: int
    duplicate_rows: int
    failed_rows: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_report: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)


class LeadImportJobListResponse(BaseModel):
    items: List[LeadImportJobOut]


MetaCredentialStatus = Literal["active", "disabled", "rotation_pending"]
MetaFieldMappingFormat = Literal[
    "string",
    "email",
    "phone",
    "bool",
    "int",
    "float",
    "uuid",
    "country",
    "geo_country",
    "contact_channel",
    "list",
    "csv",
    "lower",
    "upper",
]


class MetaLeadFieldMappingRule(BaseModel):
    source: Union[str, List[str]]
    target: str = ""
    qualified_field_code: Optional[str] = None
    format: MetaFieldMappingFormat = "string"
    overwrite: bool = True

    @model_validator(mode="before")
    @classmethod
    def _coerce_qualified_and_target(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        from backend.app.field_registry.intake_mapping import enrich_mapping_rule_for_storage

        enriched = enrich_mapping_rule_for_storage(data)
        qualified = str(enriched.get("qualified_field_code") or "").strip()
        target = str(enriched.get("target") or "").strip()
        if not target and not qualified:
            raise ValueError("target or qualified_field_code is required")
        return enriched

    @field_validator("target")
    @classmethod
    def _validate_target(cls, value: str) -> str:
        return str(value or "").strip()

    @field_validator("source")
    @classmethod
    def _validate_source(cls, value: Union[str, List[str]]) -> Union[str, List[str]]:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("source must not be empty")
            return text
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if not cleaned:
                raise ValueError("source list must not be empty")
            return cleaned
        raise TypeError("source must be string or list of strings")


class MetaCredentialCreate(BaseModel):
    label: str
    status: MetaCredentialStatus = "active"
    secret: Optional[str] = None
    access_token: Optional[str] = None
    ad_account_id: Optional[str] = None
    page_id: Optional[str] = None


class MetaCredentialUpdate(BaseModel):
    label: Optional[str] = None
    status: Optional[MetaCredentialStatus] = None
    secret: Optional[str] = None
    access_token: Optional[str] = None
    ad_account_id: Optional[str] = None
    page_id: Optional[str] = None


class MetaCredentialOut(BaseModel):
    id: UUID
    label: str
    status: MetaCredentialStatus
    has_secret: bool
    ad_account_last4: Optional[str] = None
    page_id_masked: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_verified_at: Optional[datetime] = None
    last_rotation_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MetaCredentialRotateResponse(BaseModel):
    secret: str


LeadsProcessingModeV1 = Literal["manual", "assisted", "automatic"]


class GenericInboundWebhookRotateResponse(BaseModel):
    """Returned once when rotating the §2.11 generic webhook path secret (full URL for copy/paste)."""

    secret: str
    ingest_url: str


class MetaLeadSettingsOut(BaseModel):
    tenant_id: UUID
    meta_leads_context_redirected: bool = Field(
        default=False,
        description="True when JWT/header workspace was bootstrap but Meta data is stored on another tenant.",
    )
    meta_leads_data_tenant_id: Optional[UUID] = Field(
        default=None,
        description="Tenant that owns meta_lead_settings / credentials when context_redirected.",
    )
    meta_leads_data_tenant_name: Optional[str] = Field(
        default=None,
        description="Workspace name for meta_leads_data_tenant_id (UI banner).",
    )
    default_company_id: Optional[UUID] = None
    fallback_recruiter_id: Optional[UUID] = None
    auto_create_enabled: bool
    leads_auto_convert_on_fit_v1: bool = True
    leads_processing_mode_v1: LeadsProcessingModeV1 = "assisted"
    reroute_after_hours: Optional[int] = None
    mask_pii_in_logs: bool
    pull_field_data_from_graph: bool
    field_mapping: List[MetaLeadFieldMappingRule] = Field(default_factory=list)
    # §2.5 / §2.10: Tenant.settings.lead_fit_routing_v1.ordered_vacancy_ids (fallback when no ad/id map).
    lead_fit_ordered_vacancy_ids: List[UUID] = Field(default_factory=list)
    lead_rodo_send_mode: str = Field(
        default="manual",
        description="manual | auto_on_lead_created | auto_on_first_action (Tenant.settings.lead_rodo_v1).",
    )
    lead_rodo_channels: List[str] = Field(default_factory=lambda: ["email"])
    lead_rodo_template_id: Optional[str] = None
    lead_rodo_message_template_id: Optional[str] = None
    lead_communication_enabled: bool = False
    send_application_received: bool = False
    send_rejection_notice: bool = False
    send_moving_forward_notice: bool = False
    application_received_template_id: Optional[str] = None
    rejection_notice_template_id: Optional[str] = None
    moving_forward_template_id: Optional[str] = None
    application_received_subject: Optional[str] = None
    application_received_body: Optional[str] = None
    rejection_notice_subject: Optional[str] = None
    rejection_notice_body: Optional[str] = None
    moving_forward_subject: Optional[str] = None
    moving_forward_body: Optional[str] = None
    # §2.11 plan hints for UI (None = no cap on Team+).
    plan_field_mapping_rules_limit: Optional[int] = None
    plan_meta_credentials_limit: Optional[int] = None
    generic_inbound_webhook_enabled: bool = Field(
        default=False,
        description="True when a generic inbound webhook secret is configured (Team+).",
    )
    webhook_url: Optional[str] = None
    last_webhook_check_at: Optional[datetime] = None
    last_signature_status: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetaLeadSettingsUpdate(BaseModel):
    default_company_id: Optional[UUID] = None
    fallback_recruiter_id: Optional[UUID] = None
    auto_create_enabled: Optional[bool] = None
    leads_auto_convert_on_fit_v1: Optional[bool] = None
    leads_processing_mode_v1: Optional[LeadsProcessingModeV1] = None
    reroute_after_hours: Optional[int] = None
    mask_pii_in_logs: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    pull_field_data_from_graph: Optional[bool] = None
    field_mapping: Optional[List[MetaLeadFieldMappingRule]] = None
    lead_fit_ordered_vacancy_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Replaces Tenant.settings.lead_fit_routing_v1.ordered_vacancy_ids (ordered fallback list).",
    )
    lead_rodo_send_mode: Optional[str] = Field(
        default=None,
        description="manual | auto_on_lead_created | auto_on_first_action.",
    )
    lead_rodo_channels: Optional[List[str]] = None
    lead_rodo_template_id: Optional[str] = None
    lead_rodo_message_template_id: Optional[str] = None
    lead_communication_enabled: Optional[bool] = None
    send_application_received: Optional[bool] = None
    send_rejection_notice: Optional[bool] = None
    send_moving_forward_notice: Optional[bool] = None
    application_received_template_id: Optional[str] = None
    rejection_notice_template_id: Optional[str] = None
    moving_forward_template_id: Optional[str] = None
    application_received_subject: Optional[str] = None
    application_received_body: Optional[str] = None
    rejection_notice_subject: Optional[str] = None
    rejection_notice_body: Optional[str] = None
    moving_forward_subject: Optional[str] = None
    moving_forward_body: Optional[str] = None


class MetaIncomingLeadPreviewItem(BaseModel):
    """Recent Meta lead row for troubleshooting / field-mapping trust (§2.11 View incoming)."""

    lead_id: str
    created_at: datetime
    external_id: Optional[str] = None
    ad_id: Optional[int] = None
    status: str
    stage: Optional[str] = None
    payload_json_preview: str = Field(description="Truncated JSON text of Lead.payload")
    payload_truncated: bool = False
    normalized_json_preview: Optional[str] = Field(default=None, description="Truncated JSON of Lead.normalized if present")
    normalized_truncated: bool = False


class LeadMessageTemplateOut(BaseModel):
    id: str
    name: str
    subject: str
    body: str
    is_active: bool = True
    created_at: str
    updated_at: str


class LeadMessageTemplateCreateUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    subject: str = Field(default="", max_length=500)
    body: str = Field(default="", max_length=20000)
    is_active: bool = True


class MetaIncomingLeadsPreviewResponse(BaseModel):
    items: List[MetaIncomingLeadPreviewItem]


class MetaLeadFormSummaryOut(BaseModel):
    """One Meta lead form (discovered from leads and/or saved mapping row)."""

    form_id: str
    page_id: Optional[str] = None
    source: str = "meta"
    form_name: Optional[str] = None
    has_form_mapping: bool = False
    mapping_rules_count: int = 0
    inherits_tenant_fallback: bool = True
    last_sample_lead_id: Optional[str] = None
    updated_at: Optional[datetime] = None
    has_intake_route: bool = False
    intake_route_active: bool = False
    intake_own_company_id: Optional[str] = None
    intake_lead_target_type: Optional[LeadTargetType] = None


class MetaLeadFormListResponse(BaseModel):
    items: List[MetaLeadFormSummaryOut] = Field(default_factory=list)
    tenant_fallback_rules_count: int = 0


class MetaLeadFormMappingOut(BaseModel):
    form_id: str
    page_id: Optional[str] = None
    source: str = "meta"
    form_name: Optional[str] = None
    mapping_rules: List[MetaLeadFieldMappingRule] = Field(default_factory=list)
    inherits_tenant_fallback: bool = False
    tenant_fallback_rules: List[MetaLeadFieldMappingRule] = Field(default_factory=list)
    last_sample_lead_id: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class MetaLeadFormMappingUpdate(BaseModel):
    page_id: Optional[str] = None
    source: Literal["meta", "webhook"] = "meta"
    form_name: Optional[str] = None
    mapping_rules: List[MetaLeadFieldMappingRule] = Field(default_factory=list)
    last_sample_lead_id: Optional[str] = None


class MetaFormRouteOut(BaseModel):
    form_id: str
    page_id: Optional[str] = None
    source: str = "meta"
    own_company_id: UUID
    own_company_name: Optional[str] = None
    lead_target_type: LeadTargetType = "candidate"
    pipeline_preset: Optional[str] = None
    default_assignee_id: Optional[UUID] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class MetaFormRouteUpdate(BaseModel):
    page_id: Optional[str] = None
    source: Literal["meta", "webhook"] = "meta"
    own_company_id: UUID
    lead_target_type: LeadTargetType = "candidate"
    pipeline_preset: Optional[str] = Field(default=None, max_length=64)
    default_assignee_id: Optional[UUID] = None
    is_active: bool = True


class MetaLeadSelfServeOnboardingOut(BaseModel):
    """Deployment + tenant hints so customers connect Meta without operator hand-holding."""

    meta_app_id: Optional[str] = Field(default=None, description="Facebook App ID (META_LEADS_APP_ID).")
    meta_app_display_name: str = "HostFlow Leads"
    documentation_url: Optional[str] = None
    graph_api_version: str = "v24.0"
    graph_permission_names: List[str] = Field(
        default_factory=list,
        description="Permissions to enable in Graph API Explorer / token tool.",
    )
    public_api_base_url: Optional[str] = None
    public_api_base_configured: bool = False
    webhook_verify_token_configured: bool = False
    webhook_callback_url: Optional[str] = Field(
        default=None,
        description="Paste into Meta Webhooks when verify token is saved for this tenant.",
    )
    shared_meta_app_secret: Optional[str] = Field(
        default=None,
        description="Populated for tenant administrators when META_LEADS_SHARED_APP_SECRET is set on the server.",
    )
    developers_console_app_url: Optional[str] = None
    graph_api_explorer_url: str = "https://developers.facebook.com/tools/explorer/"
    oauth_quick_connect_enabled: bool = Field(
        default=False,
        description="Team+ plan and server OAuth config (app id, secret, redirect URI).",
    )
    meta_oauth_plan_allowed: bool = Field(
        default=False,
        description="True when tenant plan allows Meta quick connect (Team tier or higher).",
    )
    meta_oauth_server_ready: bool = Field(
        default=False,
        description="True when deployment has META_LEADS_APP_ID, META_LEADS_SHARED_APP_SECRET, and redirect URI.",
    )
    oauth_redirect_uri: Optional[str] = Field(
        default=None,
        description="Register this exact URL in the Meta app Valid OAuth Redirect URIs.",
    )
    meta_leads_context_redirected: bool = Field(
        default=False,
        description="True when JWT/header workspace was bootstrap but Meta data is stored on another tenant.",
    )
    meta_leads_data_tenant_id: Optional[UUID] = Field(
        default=None,
        description="Tenant that owns meta_lead_settings / credentials when context_redirected.",
    )
    meta_leads_data_tenant_name: Optional[str] = Field(
        default=None,
        description="Workspace name for meta_leads_data_tenant_id (UI banner).",
    )


class MetaOAuthStartOut(BaseModel):
    authorize_url: str
    state: str


class MetaOAuthCompleteIn(BaseModel):
    code: str
    state: str


class MetaOAuthPageOptionOut(BaseModel):
    id: str
    name: str


class MetaOAuthCompleteOut(BaseModel):
    pending_id: str
    pages: List[MetaOAuthPageOptionOut]


class MetaOAuthFinalizeIn(BaseModel):
    pending_id: str
    page_id: str
    label: str
    subscribe_leadgen: bool = True


class MetaOAuthFinalizeOut(BaseModel):
    credential: MetaCredentialOut
    subscribed_leadgen: bool = False
    warning: Optional[str] = None


class MetaGraphFieldDataPreviewRequest(BaseModel):
    """Load real field_data from Meta Graph for field-mapping UI (§2.11)."""

    leadgen_id: Optional[str] = Field(default=None, description="Meta lead id from Ads / webhook")
    page_id: Optional[str] = Field(default=None, description="Facebook Page id (must match a stored credential)")
    hostflow_lead_id: Optional[UUID] = Field(
        default=None,
        description="Optional HostFlow lead row: resolves leadgen_id + page_id from stored payload",
    )


class MetaGraphFieldDataPreviewField(BaseModel):
    name: str
    value_preview: Optional[str] = None


class MetaGraphFieldDataPreviewResponse(BaseModel):
    field_names: List[str]
    fields: List[MetaGraphFieldDataPreviewField]
    leadgen_id: str
    page_id: str
    ad_id: Optional[str] = None
    form_id: Optional[str] = None


class MetaAdsMapEntry(BaseModel):
    ad_id: str
    vacancy_id: UUID
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("ad_id", mode="before")
    @classmethod
    def _ensure_string(cls, value: Any) -> str:
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("ad_id must not be empty")
            return stripped
        raise TypeError("ad_id must be a string value")


class MetaAdsMapCreate(BaseModel):
    ad_id: str
    vacancy_id: UUID
    note: Optional[str] = None

    @field_validator("ad_id", mode="before")
    @classmethod
    def _normalize_ad_id(cls, value: Any) -> str:
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("ad_id must not be empty")
            if not stripped.isdigit():
                raise ValueError("ad_id must be numeric")
            return stripped
        raise TypeError("ad_id must be a string or integer")


class MetaAdsMapUpdate(BaseModel):
    vacancy_id: Optional[UUID] = None
    note: Optional[str] = None


class MetaLeadRerouteRequest(BaseModel):
    vacancy_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    force_process: bool = False


class MetaLeadRetryItem(BaseModel):
    lead_id: UUID
    status_before: LeadStatus
    status_after: LeadStatus
    candidate_id: Optional[UUID] = None
    error_before: Optional[str] = None
    error_after: Optional[str] = None
    processed: bool = False
    message: Optional[str] = None


class MetaLeadRetryRequest(BaseModel):
    lead_ids: Optional[List[UUID]] = None
    statuses: Optional[List[LeadStatus]] = None
    limit: Optional[int] = None
    refresh_graph: bool = True


class MetaLeadRetryResponse(BaseModel):
    items: List[MetaLeadRetryItem]
    processed: int
    failed: int
    skipped: int


# --- Lead auto-distribution (control panel) ---------------------------------

DistributionMode = Literal["automatic", "manual"]
DistributionStrategy = Literal["smart", "round_robin", "manual_rules"]


class LeadDistributionTeamMemberOut(BaseModel):
    user_id: str
    display_name: str
    status: Literal["available", "busy", "offline"]
    lead_load: int
    languages: List[str] = Field(default_factory=list)
    working_hours_configured: bool = False
    within_working_hours: bool = True
    role: Optional[str] = Field(
        default=None,
        description="Tenant User.role (for pipeline stage_contract.owner_role filtering at ingest, §2.3).",
    )


class LeadDistributionNextPreview(BaseModel):
    user_id: str
    display_name: str
    reason_codes: List[str] = Field(default_factory=list)
    subtitle: str = ""
    detail_lines: List[str] = Field(default_factory=list)


class LeadDistributionAlert(BaseModel):
    severity: str
    code: str
    message: str


class LeadDistributionFeatureGate(BaseModel):
    automatic_allowed: bool
    advanced_rules_allowed: bool
    load_balance_pro: bool
    plan_code: str = "starter"


class LeadDistributionStats(BaseModel):
    unassigned_processed_leads: int = 0


class LeadDistributionOut(BaseModel):
    mode: DistributionMode
    strategy: DistributionStrategy
    criteria_order: List[str]
    max_leads_per_person: int
    only_active_employees: bool
    preview_language: str = "pl"
    language_routing_v1: Dict[str, List[str]] = Field(default_factory=dict)
    assignment_detail_lines: List[str] = Field(
        default_factory=list,
        description="Working hours / language routing context (even when no assignee).",
    )
    rules_summary_lines: List[str] = Field(default_factory=list)
    next_preview: Optional[LeadDistributionNextPreview] = None
    team: List[LeadDistributionTeamMemberOut] = Field(default_factory=list)
    flow_steps: List[str] = Field(default_factory=list)
    alerts: List[LeadDistributionAlert] = Field(default_factory=list)
    stats: LeadDistributionStats = Field(default_factory=LeadDistributionStats)
    feature_gate: LeadDistributionFeatureGate


class LeadDistributionPatch(BaseModel):
    mode: Optional[DistributionMode] = None
    strategy: Optional[DistributionStrategy] = None
    criteria_order: Optional[List[str]] = None
    max_leads_per_person: Optional[int] = Field(default=None, ge=1, le=500)
    only_active_employees: Optional[bool] = None
    preview_language: Optional[str] = Field(default=None, max_length=16)
    language_routing_v1: Optional[Dict[str, List[str]]] = None
