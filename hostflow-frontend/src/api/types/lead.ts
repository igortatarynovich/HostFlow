/**
 * Lead-related types
 */

import type { UUID } from './common';

export type LeadStatus = 'new' | 'processed' | 'duplicated' | 'failed' | 'needs_routing';
export type LeadType = 'candidate' | 'client';
export type LeadTargetType = 'candidate' | 'client_lead' | 'service_order_lead' | 'partner_lead';
export type LeadStage = 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
export type LeadNextActionStatus = 'scheduled' | 'overdue' | 'no_next_action';

/** From FunnelStage.stage_contract_v1 (§2.3). */
export interface LeadStageContractV1 {
  owner_role?: string | null
  required_actions?: string[] | null
  sla_hours?: number | null
  auto_rules?: Record<string, unknown> | null
}

export interface Lead {
  id: UUID;
  tenant_id: UUID;
  business_type?: 'agency' | 'employer' | 'services' | null;
  lead_type?: LeadType;
  lead_target_type?: LeadTargetType;
  company_id?: UUID | null;
  company_name?: string | null;
  vacancy_id?: UUID | null;
  vacancy_title?: string | null;
  source: string;
  ad_id?: number | null;
  /** Meta leadgen_id / webhook dedupe id — useful for Graph picker labels */
  external_id?: string | null;
  status: LeadStatus;
  stage?: LeadStage | null;
  funnel_id?: UUID | null;
  stage_contract?: LeadStageContractV1 | null;
  candidate_id?: UUID | null;
  candidate_name?: string | null;
  converted_client_id?: UUID | null;
  outcome_entity_type?: 'candidate' | 'company' | null;
  outcome_entity_id?: UUID | null;
  outcome_entity_name?: string | null;
  service_order_id?: UUID | null;
  recruiter_id?: UUID | null;
  error?: string | null;
  payload: Record<string, any>;
  normalized?: Record<string, any> | null;
  /** LEAD-scoped custom field values (key → scalar), mirror of API LeadOut.custom_fields */
  custom_fields?: Record<string, unknown> | null;
  created_at: string;
  last_routed_at?: string | null;
  next_action_status?: LeadNextActionStatus | null;
  next_action_due_at?: string | null;
  next_action_type?: string | null;
  next_action_title?: string | null;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}

export type MetaCredentialStatus = 'active' | 'disabled' | 'rotation_pending';
export type MetaFieldMappingFormat =
  | 'string'
  | 'email'
  | 'phone'
  | 'bool'
  | 'int'
  | 'float'
  | 'uuid'
  | 'country'
  | 'contact_channel'
  | 'list'
  | 'csv'
  | 'lower'
  | 'upper';

export interface MetaLeadFieldMappingRule {
  source: string | string[];
  target: string;
  format?: MetaFieldMappingFormat;
  overwrite?: boolean;
}

export interface MetaLeadFormSummary {
  form_id: string;
  page_id?: string | null;
  source: string;
  form_name?: string | null;
  has_form_mapping: boolean;
  mapping_rules_count: number;
  inherits_tenant_fallback: boolean;
  last_sample_lead_id?: string | null;
  updated_at?: string | null;
  has_intake_route?: boolean;
  intake_route_active?: boolean;
  intake_own_company_id?: string | null;
  intake_lead_target_type?: LeadTargetType | null;
}

export interface MetaLeadFormListResponse {
  items: MetaLeadFormSummary[];
  tenant_fallback_rules_count: number;
}

export interface MetaLeadFormMapping {
  form_id: string;
  page_id?: string | null;
  source: string;
  form_name?: string | null;
  mapping_rules: MetaLeadFieldMappingRule[];
  inherits_tenant_fallback: boolean;
  tenant_fallback_rules: MetaLeadFieldMappingRule[];
  last_sample_lead_id?: string | null;
  updated_at?: string | null;
  updated_by?: string | null;
}

export interface MetaLeadFormMappingUpdate {
  page_id?: string | null;
  source?: 'meta' | 'webhook';
  form_name?: string | null;
  mapping_rules: MetaLeadFieldMappingRule[];
  last_sample_lead_id?: string | null;
}

export interface MetaFormRoute {
  form_id: string;
  page_id?: string | null;
  source: string;
  own_company_id: string;
  own_company_name?: string | null;
  lead_target_type: LeadTargetType;
  pipeline_preset?: string | null;
  default_assignee_id?: string | null;
  is_active: boolean;
  updated_at?: string | null;
  updated_by?: string | null;
}

export interface MetaFormRouteUpdate {
  page_id?: string | null;
  source?: 'meta' | 'webhook';
  own_company_id: string;
  lead_target_type: LeadTargetType;
  pipeline_preset?: string | null;
  default_assignee_id?: string | null;
  is_active?: boolean;
}

export const META_FORM_TENANT_DEFAULT_KEY = '__tenant_default__';

export type LeadsProcessingModeV1 = 'manual' | 'assisted' | 'automatic';

export interface GenericInboundWebhookRotateResponse {
  secret: string;
  ingest_url: string;
}

export interface MetaLeadSelfServeOnboarding {
  meta_app_id?: string | null;
  meta_app_display_name: string;
  documentation_url?: string | null;
  graph_api_version: string;
  graph_permission_names: string[];
  public_api_base_url?: string | null;
  public_api_base_configured: boolean;
  webhook_verify_token_configured: boolean;
  webhook_callback_url?: string | null;
  shared_meta_app_secret?: string | null;
  developers_console_app_url?: string | null;
  graph_api_explorer_url: string;
  oauth_quick_connect_enabled?: boolean;
  /** Tariff allows Meta OAuth (Team+ / Business); independent of server env. */
  meta_oauth_plan_allowed?: boolean | null;
  /** Server has META_LEADS_APP_ID, secret, redirect configured. */
  meta_oauth_server_ready?: boolean | null;
  oauth_redirect_uri?: string | null;
  /** Superadmin bootstrap → operational tenant (e.g. Focus); API stores Meta on that tenant. */
  meta_leads_context_redirected?: boolean;
  meta_leads_data_tenant_id?: UUID | null;
  meta_leads_data_tenant_name?: string | null;
}

export interface MetaLeadSettings {
  tenant_id: UUID;
  meta_leads_context_redirected?: boolean;
  meta_leads_data_tenant_id?: UUID | null;
  meta_leads_data_tenant_name?: string | null;
  default_company_id?: UUID | null;
  fallback_recruiter_id?: UUID | null;
  auto_create_enabled: boolean;
  leads_processing_mode_v1: LeadsProcessingModeV1;
  reroute_after_hours?: number | null;
  mask_pii_in_logs: boolean;
  pull_field_data_from_graph?: boolean;
  lead_rodo_send_mode?: 'manual' | 'auto_on_lead_created' | 'auto_on_first_action';
  lead_rodo_channels?: string[];
  lead_rodo_template_id?: string | null;
  lead_rodo_message_template_id?: string | null;
  lead_communication_enabled?: boolean;
  send_application_received?: boolean;
  send_rejection_notice?: boolean;
  send_moving_forward_notice?: boolean;
  application_received_template_id?: string | null;
  rejection_notice_template_id?: string | null;
  moving_forward_template_id?: string | null;
  field_mapping?: MetaLeadFieldMappingRule[];
  plan_field_mapping_rules_limit?: number | null;
  plan_meta_credentials_limit?: number | null;
  generic_inbound_webhook_enabled?: boolean;
  webhook_url?: string | null;
  last_webhook_check_at?: string | null;
  last_signature_status?: string | null;
  webhook_verify_token?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MetaLeadSettingsPatch {
  default_company_id?: UUID | null;
  fallback_recruiter_id?: UUID | null;
  auto_create_enabled?: boolean;
  leads_processing_mode_v1?: LeadsProcessingModeV1;
  reroute_after_hours?: number | null;
  mask_pii_in_logs?: boolean;
  pull_field_data_from_graph?: boolean;
  lead_rodo_send_mode?: 'manual' | 'auto_on_lead_created' | 'auto_on_first_action';
  lead_rodo_channels?: string[];
  lead_rodo_template_id?: string | null;
  lead_rodo_message_template_id?: string | null;
  lead_communication_enabled?: boolean;
  send_application_received?: boolean;
  send_rejection_notice?: boolean;
  send_moving_forward_notice?: boolean;
  application_received_template_id?: string | null;
  rejection_notice_template_id?: string | null;
  moving_forward_template_id?: string | null;
  field_mapping?: MetaLeadFieldMappingRule[];
  webhook_url?: string | null;
  webhook_verify_token?: string | null;
}

export interface MetaLeadCredential {
  id: UUID;
  label: string;
  status: MetaCredentialStatus;
  has_secret: boolean;
  ad_account_last4?: string | null;
  page_id_masked?: string | null;
  created_at: string;
  updated_at: string;
  last_verified_at?: string | null;
  last_rotation_at?: string | null;
}

export interface MetaCredentialCreatePayload {
  label: string;
  status?: MetaCredentialStatus;
  secret?: string | null;
  access_token?: string | null;
  ad_account_id?: string | null;
  page_id?: string | null;
}

export interface MetaCredentialUpdatePayload {
  label?: string;
  status?: MetaCredentialStatus;
  secret?: string | null;
  access_token?: string | null;
  ad_account_id?: string | null;
  page_id?: string | null;
}

export interface MetaCredentialRotateResponse {
  secret: string;
}

export interface MetaAdsMapEntry {
  ad_id: string;
  vacancy_id: UUID;
  note?: string | null;
  created_at: string;
}

export interface MetaAdsMapCreatePayload {
  ad_id: string;
  vacancy_id: UUID;
  note?: string | null;
}

export interface MetaAdsMapUpdatePayload {
  vacancy_id?: UUID;
  note?: string | null;
}

export interface MetaLeadAdminResponse {
  lead_id: UUID;
  status: LeadStatus;
  vacancy_id?: UUID | null;
  candidate_id?: UUID | null;
  recruiter_id?: UUID | null;
  error?: string | null;
}

export interface MetaLeadReroutePayload {
  vacancy_id?: UUID;
  company_id?: UUID;
  force_process?: boolean;
}
