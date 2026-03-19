/**
 * Lead-related types
 */

import type { UUID } from './common';

export type LeadStatus = 'new' | 'processed' | 'duplicated' | 'failed' | 'needs_routing';
export type LeadStage = 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
export type LeadNextActionStatus = 'scheduled' | 'overdue' | 'no_next_action';

export interface Lead {
  id: UUID;
  tenant_id: UUID;
  business_type?: 'agency' | 'employer' | 'services' | null;
  company_id: UUID;
  company_name?: string | null;
  vacancy_id?: UUID | null;
  vacancy_title?: string | null;
  source: string;
  ad_id?: number | null;
  status: LeadStatus;
  stage?: LeadStage | null;
  candidate_id?: UUID | null;
  candidate_name?: string | null;
  outcome_entity_type?: 'candidate' | 'company' | null;
  outcome_entity_id?: UUID | null;
  outcome_entity_name?: string | null;
  service_order_id?: UUID | null;
  recruiter_id?: UUID | null;
  error?: string | null;
  payload: Record<string, any>;
  normalized?: Record<string, any> | null;
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

export interface MetaLeadSettings {
  tenant_id: UUID;
  default_company_id?: UUID | null;
  fallback_recruiter_id?: UUID | null;
  auto_create_enabled: boolean;
  reroute_after_hours?: number | null;
  mask_pii_in_logs: boolean;
  pull_field_data_from_graph?: boolean;
  field_mapping?: MetaLeadFieldMappingRule[];
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
  reroute_after_hours?: number | null;
  mask_pii_in_logs?: boolean;
  pull_field_data_from_graph?: boolean;
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
