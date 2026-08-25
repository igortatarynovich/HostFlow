// src/api/types.ts
// This file is kept for backward compatibility
// All types are now exported from ./types/index.ts

export * from './types';
// `export *` on the line above does not always surface type-only re-exports
// chained through `./types/index.ts`, leaving consumers that import these
// symbols from the legacy module with TS2305. Restate them explicitly via
// the directory path so TS resolves to `./types/index.ts` and not back to
// this file (which would trigger a TS2303 circular alias).
export type {
  TenantModuleOverrideUser,
  TenantUserModuleOverrides,
  TenantUserModuleOverridesPatch,
  HiringPipelineGatesPublic,
  HiringPipelineGatesPatch,
  RiskModelV1SettingsOut,
  LeadStage,
  LeadStageContractV1,
  InvoiceActivity,
} from './types/index';
// Re-import the canonical UUID alias so the legacy interface declarations
// below (`id: UUID`, etc.) resolve inside this module after `./types/common`
// became the single source of truth for the alias. Without this import the
// raw references would all fail TS2304 even though they re-export fine.
// We also re-export it so consumers that imported `UUID` directly from this
// legacy module keep compiling (the bare `export *` above does not always
// surface type-only re-exports — see TS2459 cluster).
import type { UUID as _UUID } from './types/common';
export type UUID = _UUID;

/** Текущий пользователь */
export interface WhoAmI {
  /** Stable user id (string UUID); some legacy consumers also read it via `sub`. */
  id?: string;
  email: string;
  role: 'admin' | 'manager' | 'user' | string;
  tenant_id: string;
  sub?: string;
  first_name?: string | null;
  last_name?: string | null;
  full_name?: string | null;
  phone?: string | null;
  position?: string | null;
  country?: string | null;
  city?: string | null;
  birth_date?: string | null;
  avatar_url?: string | null;
  signature?: UserOutgoingSignature | null;
  preferences?: UserPreferences;
  security?: UserSecuritySummary;
  /** G-6 Stage 2e — true when owner-class role and tenant has one active member (from GET /users/me). */
  is_solo_admin?: boolean;
}

export type UserRole = 'superadmin' | 'administrator' | 'employee' | 'viewer';
export type TenantUserRole = UserRole;

export type TenantType = 'agency' | 'company' | 'platform';
export type TenantStatus = 'active' | 'suspended' | 'trial';

export interface TenantUsage {
  administrator_count?: number;
  employee_count?: number;
  viewer_count: number;
  portal_guest_count?: number;
  /** @deprecated alias of employee_count */
  recruiter_count: number;
  /** @deprecated alias of administrator_count */
  supervisor_count: number;
  /** @deprecated alias of portal_guest_count */
  client_manager_count: number;
  storage_used_gb: number;
}

export interface TenantModuleSettings {
  candidates: boolean;
  companies: boolean;
  vacancies: boolean;
  documents: boolean;
  leads: boolean;
  services: boolean;
  client_portal: boolean;
  hr: boolean;
}

export type TenantModuleSettingsPatch = Partial<TenantModuleSettings>;

export type RoleModuleMatrixRole =
  | 'administrator'
  | 'employee'
  | 'supervisor'
  | 'recruiter'
  | 'client_manager'
  | 'client_processor'
  | 'compliance_officer'
  | 'hr_officer'
  | 'viewer';

export interface RoleModulePermissions {
  visible: boolean;
  editable: boolean;
}

export type TenantRoleModuleMatrix = Record<RoleModuleMatrixRole, Record<keyof TenantModuleSettings, RoleModulePermissions>>;

export type TenantRoleModuleMatrixPatch = Partial<{
  [K in RoleModuleMatrixRole]: Partial<Record<keyof TenantModuleSettings, RoleModulePermissions>>;
}>;

export interface EffectiveRoleModules {
  role: string;
  modules: Partial<Record<keyof TenantModuleSettings, RoleModulePermissions>>;
}

export interface SeatRequest {
  id: string;
  tenant_id: string;
  requested_by: string;
  role: string;
  requested_count: number;
  message?: string | null;
  status: 'pending' | 'approved' | 'rejected';
  resolution_notes?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SeatRequestDecisionPayload {
  status: 'approved' | 'rejected';
  resolution_notes?: string | null;
}

export interface TenantLicense {
  id: string;
  tenant_id: string;
  plan: string;
  max_recruiters: number;
  max_supervisors: number;
  max_client_managers: number;
  max_viewers: number;
  max_storage_gb: number;
  max_companies: number;
  expires_at?: string | null;
  auto_renew: boolean;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface TenantLicenseInput {
  plan: string;
  max_recruiters: number;
  max_supervisors: number;
  max_client_managers: number;
  max_viewers: number;
  max_storage_gb: number;
  max_companies: number;
  expires_at?: string | null;
  auto_renew?: boolean;
  notes?: string | null;
}

export type TenantLicensePatchInput = Partial<TenantLicenseInput>;

export interface PlatformTenant {
  id: string;
  name: string;
  slug: string;
  type: TenantType;
  status: TenantStatus;
  parent_tenant_id?: string | null;
  client_portal_enabled: boolean;
  status_sharing_allowed: boolean;
  description?: string | null;
  workspace_label?: string | null;
  logo_url?: string | null;
  logo_meta?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  license?: TenantLicense | null;
  usage: TenantUsage;
  public_domain?: string | null;
  custom_domain?: string | null;
  legal_domain?: string | null;
  public_hosts?: string[];
  domains?: string[];
  legal_hosts?: string[];
}

export interface PlatformTenantListResponse {
  total: number;
  items: PlatformTenant[];
}

export interface PlatformFounderEnrollResponse {
  enrolled: boolean;
  founder_slots_used: number;
  founder_slots_max: number;
}

export interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  status?: TenantStatus;
  workspace_label?: string | null;
  logo_url?: string | null;
  logo_meta?: Record<string, any> | null;
  description?: string | null;
}

export interface TenantRecord extends TenantSummary {
  api_key: string;
  type: TenantType;
  status: TenantStatus;
  is_active: boolean;
  client_portal_enabled: boolean;
  status_sharing_allowed: boolean;
  created_at: string;
  updated_at: string;
}

export interface TenantMeResponse {
  tenant: TenantRecord;
}

export interface TenantImpersonationToken {
  token: string;
  expires_at: string;
}

export interface TenantAdminInput {
  email: string;
  full_name?: string | null;
  password: string;
}

export interface TenantAdminResponse {
  user: AdminUser;
  temporary_password?: string | null;
}

export interface SeatRequestCreatePayload {
  role: string;
  requested_count: number;
  message?: string | null;
}

export interface UserCompanyAccess {
  company_id: string;
  can_edit: boolean;
}

export interface RecruiterSummary {
  user_id: string;
  email: string;
  full_name?: string | null;
  short_id?: string | null;
  status: 'active' | 'inactive';
}

export interface ManagerOption {
  id: string;
  label: string;
  email?: string | null;
  full_name?: string | null;
  short_id?: string | null;
}

export interface AdminUser {
  user_id: string | null;
  invite_id: string | null;
  email: string;
  role: UserRole;
  status: 'active' | 'inactive' | 'invited';
  is_active: boolean;
  full_name?: string | null;
  short_id?: string | null;
  supervisor_id?: string | null;
  invited_at?: string | null;
  invite_expires_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  company_ids?: string[];
  companies?: UserCompanyAccess[];
  recruiters?: RecruiterSummary[];
}

export interface AdminUserDetail extends AdminUser {
  user_id: string;
  companies: UserCompanyAccess[];
  recruiters: RecruiterSummary[];
}

export interface UserOutgoingSignature {
  first_name?: string | null
  last_name?: string | null
  position?: string | null
  phone?: string | null
  email?: string | null
  company?: string | null
  website?: string | null
  logo_url?: string | null
  show_phone?: boolean
  show_email?: boolean
  show_website?: boolean
}

export interface UserProfile {
  user_id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  birth_date?: string | null;
  country?: string | null;
  city?: string | null;
  position?: string | null;
  phone?: string | null;
  tenant_id?: string | null;
  role?: string | null;
  avatar_url?: string | null;
  signature?: UserOutgoingSignature | null;
}

export type UserProfileUpdate = Partial<Omit<UserProfile, 'user_id'>>;

export interface UserUIPreferences {
  locale?: string | null;
  timezone?: string | null;
  date_format?: string | null;
  phone_format?: string | null;
  theme?: 'light' | 'dark' | 'system' | null;
}

export interface UserNotificationPreference {
  enabled: boolean;
  mode: 'immediate' | 'daily_digest';
}

export interface UserDefaultsPreferences {
  company_id?: string | null;
}

export interface UserSavedView {
  id: string;
  name: string;
  filters: Record<string, any>;
  is_default?: boolean;
}

export interface UserSavedViews {
  candidates: UserSavedView[];
  vacancies: UserSavedView[];
}

export interface UserPreferences {
  ui: UserUIPreferences;
  notifications: Record<string, UserNotificationPreference>;
  defaults: UserDefaultsPreferences;
  saved_views: UserSavedViews;
}

export interface UserSecurityCompany {
  id: string;
  name: string;
  can_edit: boolean;
}

export interface UserSecuritySupervisor {
  id: string;
  name?: string | null;
  email?: string | null;
}

export interface UserSecuritySummary {
  role: string;
  companies: UserSecurityCompany[];
  supervisor?: UserSecuritySupervisor | null;
  last_login_at?: string | null;
  sessions_count: number;
}

export interface UserMe {
  profile: UserProfile;
  preferences: UserPreferences;
  security: UserSecuritySummary;
  /** G-6 Stage 2e — see WhoAmI.is_solo_admin */
  is_solo_admin?: boolean;
}

export interface UserSessionInfo {
  id: string;
  created_at: string;
  last_seen_at: string;
  ip_address?: string | null;
  user_agent?: string | null;
  device_label?: string | null;
  expires_at?: string | null;
  revoked_at?: string | null;
}

export interface UserAvatar {
  avatar_url: string | null;
}

export interface UserSavedViewsPatch {
  candidates?: UserSavedView[];
  vacancies?: UserSavedView[];
}

export interface UserPreferencesPatchPayload {
  ui?: Partial<UserUIPreferences>;
  notifications?: Record<string, UserNotificationPreference>;
  defaults?: UserDefaultsPreferences;
  saved_views?: UserSavedViewsPatch;
}

export interface UserMeUpdatePayload {
  profile?: UserProfileUpdate;
  preferences?: UserPreferencesPatchPayload;
}

export interface UserInvite {
  id: string;
  email: string;
  role: UserRole;
  token: string;
  expires_at: string;
  status: 'pending' | 'accepted' | 'revoked';
  invited_user_id?: string | null;
  supervisor_id?: string | null;
  company_ids?: string[];
}

export interface UserAuditEntry {
  id: string;
  tenant_id: string;
  user_id?: string | null;
  actor_id?: string | null;
  action: string;
  payload?: Record<string, any> | null;
  created_at: string;
}

export interface PlatformTenantCreatePayload {
  name: string;
  slug: string;
  type: TenantType;
  status?: TenantStatus;
  parent_tenant_id?: string | null;
  client_portal_enabled?: boolean;
  status_sharing_allowed?: boolean;
  description?: string | null;
  settings?: Record<string, any>;
  workspace_label?: string | null;
  logo_url?: string | null;
  logo_meta?: Record<string, any> | null;
  license: TenantLicenseInput;
  initial_admin?: TenantAdminInput | null;
}

export interface PlatformTenantUpdatePayload {
  name?: string;
  description?: string | null;
  workspace_label?: string | null;
  logo_url?: string | null;
  logo_meta?: Record<string, any> | null;
  client_portal_enabled?: boolean;
  status_sharing_allowed?: boolean;
}

export interface TenantLegalHostSettings {
  public_domain?: string | null;
  custom_domain?: string | null;
  legal_domain?: string | null;
  public_hosts?: string[];
  domains?: string[];
  legal_hosts?: string[];
}

export interface TenantStatusChangePayload {
  status: TenantStatus;
  client_portal_enabled?: boolean;
  reason?: string | null;
}

export interface TenantVacancyAccessItem {
  vacancy_id: string;
  title: string;
  company_name?: string | null;
  status?: string | null;
}

export interface TenantVacancyAccessListResponse {
  items: TenantVacancyAccessItem[];
}

export interface TenantVacancyAccessUpdatePayload {
  vacancy_ids: string[];
}

export interface TenantVacancyOption {
  vacancy_id: string;
  title: string;
  company_name?: string | null;
  tenant_id: string;
  status?: string | null;
}

export interface TeamOverviewResponse {
  members: AdminUser[];
  usage: TenantUsage;
  license?: TenantLicense | null;
  tenant: TenantBrandingResponse;
  modules: TenantModuleSettings;
}

export interface TenantBrandingResponse {
  id: string;
  name: string;
  slug: string;
  workspace_label?: string | null;
  logo_url?: string | null;
  logo_meta?: Record<string, any> | null;
}

export interface TenantBrandingPayload {
  workspace_label?: string | null;
}

/** Компания */
export interface Company {
  id: UUID;
  name: string;
  owner_user_id?: UUID | null;
  manager_user_id?: UUID | null;
  legal_name?: string | null;
  reg_no?: string | null;
  tax_id?: string | null;
  vat_eu?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  notes?: string | null;
  is_archived?: boolean | null;
  country_code?: string | null;
  country?: string | null;
  city?: string | null;
  address?: string | null;
  contacts?: Record<string, unknown> | null;
  extra?: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CompanyReadiness {
  company_id: UUID;
  has_legal: boolean;
  has_primary_contact: boolean;
  has_primary_bank: boolean;
  fin_check_status: string;
  billing_ready: boolean;
  compliance_valid: boolean;
  client_portal_enabled: boolean;
  readiness_score?: number | null;
  readiness_state?: string | null;
}

/** Вакансия */
export interface Vacancy {
  id: UUID;
  company_id: UUID;
  title: string;
  status: string;
  description?: string | null;
  location?: string | null;
  company_name?: string | null;
  currency?: string | null;
  is_open?: boolean | null;
  is_active?: boolean | null;
  is_archived?: boolean | null;
  candidate_profile_id?: string | null;
  candidate_profile_name?: string | null;
  candidate_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
}

/** Структурный адрес */
export type Address = {
  country: string; // ISO-код страны или человекочитаемое имя — на фронте строка
  city: string;
  street: string;
  house: string;
  apt: string;
  zip: string;
};

export interface CandidateEmploymentEntry {
  employer?: string | null;
  country?: string | null;
  position?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  currently_employed?: boolean | null; // работает ли сейчас
}

export interface CandidateEmploymentRecord {
  id: UUID;
  tenant_id: UUID;
  candidate_id: UUID;
  employer_name: string;
  country?: string | null;
  position?: string | null;
  start_date: string;
  end_date?: string | null;
  currently_employed?: boolean | null; // работает ли сейчас
  trailer_types?: string[] | null;
  route_types?: string[] | null;
  truck_brands?: string[] | null;
  eu_routes?: boolean | null;
  reason_for_leaving?: string | null;
  reference_contact?: string | null;
  created_at: string;
  updated_at: string;
}

export type CandidateOpsMode = 'in_work' | 'later' | 'no_reply_needed' | 'escalated';

/** Доп. поля кандидата (extra) */
export interface CandidateExtra {
  // персональные данные
  birth_date?: string | null;        // 'YYYY-MM-DD'
  citizenship?: string | null;       // код страны гражданства (или имя)
  // адреса
  address?: Address;                 // адрес проживания
  reg_address_diff?: boolean;        // адрес регистрации отличается от проживания
  reg_address?: Address;             // адрес регистрации (если отличается)

  // контакты / телефон
  phone_country?: string | null;     // код страны (PL/UA/…)
  phone_prefix?: string | null;      // префикс “+48” (опционально, для UI)
  preferred_contact?: string | null; // предпочтительный канал связи (viber/whatsapp/telegram/phone)
  first_contact_at?: string | null;  // ISO8601 дата/время первого контакта
  /** Citizenship country code mirrored from the candidate model for forms that
   *  edit `extra` (CandidatePersonalSection auto-fill from phone). */
  country_code?: string | null;

  // водительское удостоверение / опыт
  license_number?: string | null;
  license_categories?: string[] | null; // ['B','C','CE']
  experience_years?: number | null;      // устарело, оставляем для совместимости
  experience_eu_years?: number | null;
  experience_non_eu_years?: number | null;
  experience_ce_total?: number | null;
  previous_employers?: string[] | null;  // устаревший формат, поддерживаем чтение
  employment_history?: CandidateEmploymentEntry[] | null;
  trailer_types?: string[] | null;
  route_types?: string[] | null;
  intl_experience?: boolean | null;
  eu_routes?: boolean | null;

  // пребывание в Польше
  in_poland?: boolean | null;
  poland_stay_basis?: string | null; // visa_d / visa_c / karta_pobytu / eu_citizen / other
  current_location?: string | null; // где находится сейчас (в Польше / не в Польше / другое)

  // дополнительный опыт
  frigo_experience?: boolean | null; // опыт работы с холодильниками
  has_adr?: boolean | null; // есть ли ADR

  // документы (чек-лист)
  documents?: {
    passport?: boolean;
    driver_license?: boolean;
    medical?: boolean;
    work_permit?: boolean;
    photo?: boolean;
    contract?: boolean;
    other?: string;
  };

  // операционный режим кандидата (отдельно от этапа)
  candidate_ops?: {
    mode?: CandidateOpsMode | null;
    updated_at?: string | null;
    updated_by?: string | null;
  } | null;

  /** Set by backend when a linked workforce employee is terminated (HR PATCH). */
  workforce_termination?: {
    employee_status?: string | null;
    termination_date?: string | null;
    recorded_at?: string | null;
    recorded_by_user_id?: string | null;
  } | null;
}

/** Кандидат */
export interface Candidate {
  id: UUID;
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null;                 // уже может приходить с префиксом
  phone_country_code?: string | null;
  country_code?: string | null;
  languages?: string[] | null;
  tags?: string[] | null
  is_favorite?: boolean;
  stage?: string | null;
  status_reason?: string[] | null;

  // менеджер
  manager?: string | null;               // id менеджера
  manager_name?: string | null;          // ФИО менеджера (для отображения)
  manager_short?: string | null;         // короткий код (fallback)

  // привязки
  short_id?: string | null;
  company_id?: UUID | null;              // подтягивается автоматически от вакансии
  company_name?: string | null;          // название компании (read-only, для UI)
  vacancy_id?: UUID | null;
  vacancy_name?: string | null;
  recruiter_id?: UUID | null;
  recruiter_name?: string | null;
  recruiter_short?: string | null;
  source?: string | null;
  origin?: Record<string, any> | null;
  created_at?: string | null;
  updated_at?: string | null;

  note?: string | null;

  // произвольные расширения и прогресс документов
  extra?: CandidateExtra | null;
  docs_progress?: Record<string, any> | null;
  docs_readiness_state?: string | null;
  docs_readiness_rank?: number | null;
  docs_last_ordered_at?: string | null;
  docs_next_valid_from?: string | null;
  docs_has_files?: boolean | null;
  risk_score?: number | null;
  risk_band?: string | null;
  risk_drivers?: string[] | null;
  risk_updated_at?: string | null;
  risk_version?: string | null;
  personal_data?: Record<string, any> | null;
  contacts?: Record<string, any> | null;
  intake_status?: string | null;
  intake_submitted_at?: string | null;
  /** From public intake `intake_state.application_kind` (CRM detail/list). */
  intake_application_kind?: 'candidate' | 'client' | null;
  intake_contacts?: Record<string, any> | null;
  intake_personal?: Record<string, any> | null;
  intake_experience?: Record<string, any> | null;
  intake_agreements?: Record<string, any> | null;

  /** From GET candidate: client link contact policy (for stage gates). */
  contact_policy_enabled?: boolean | null;
  /** From GET candidate: logged contact attempts count. */
  contact_attempt_count?: number | null;
  /** Client "database" view: PII masked, hide personal/contacts/documents sections. */
  masked?: boolean;
  /** Handoff-based: false when agency cannot edit (accepted handoff) or client cannot edit (no accepted). */
  can_edit?: boolean;
}

export type LeadStatus =
  | 'new'
  | 'processed'
  | 'duplicated'
  | 'failed'
  | 'needs_routing'
  | 'duplicate_review'
  | 'rejected';
export type LeadType = 'candidate' | 'client';
export type LeadTargetType = 'candidate' | 'client_lead' | 'service_order_lead' | 'partner_lead';

export interface Lead {
  id: UUID;
  tenant_id: UUID;
  business_type?: 'agency' | 'employer' | 'services' | null;
  lead_type?: LeadType;
  lead_target_type?: LeadTargetType;
  company_id?: UUID | null;
  company_name?: string | null;
  vacancy_id?: UUID | null;
  /** Suggested routing target from qualification preview (UI convenience). */
  suggested_vacancy_id?: UUID | string | null;
  /** True when ``intake_vacancy_confirm_v1`` matches committed ``vacancy_id`` (intake gating). */
  vacancy_routing_confirmed?: boolean | null;
  vacancy_title?: string | null;
  funnel_id?: UUID | null;
  source: string;
  ad_id?: number | null;
  status: LeadStatus;
  stage?: 'new' | 'contacted' | 'qualified' | 'converted' | 'lost' | null;
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
  /** Lead-scoped custom fields (definition key → value); see Custom fields admin scope LEAD. */
  custom_fields?: Record<string, unknown>;
  created_at: string;
  last_routed_at?: string | null;
  /** Next-best-action playbook fields surfaced on the Leads list / detail. */
  next_action_status?: 'pending' | 'in_progress' | 'completed' | 'snoozed' | string | null;
  next_action_title?: string | null;
  next_action_due_at?: string | null;
  /** Lead stage contract (gating, nudges) attached to the lead summary. */
  stage_contract?: import('./types/lead').LeadStageContractV1 | null;
  /** Source-system identifier (Meta leadgen leadgen_id / form id / external CRM id). */
  external_id?: string | null;
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
  | 'geo_country'
  | 'contact_channel'
  | 'list'
  | 'csv'
  | 'lower'
  | 'upper';

export interface MetaLeadFieldMappingRule {
  source: string | string[];
  target: string;
  qualified_field_code?: string | null;
  format?: MetaFieldMappingFormat;
  overwrite?: boolean;
}

export type LeadsProcessingModeV1 = 'manual' | 'assisted' | 'automatic';

export interface GenericInboundWebhookRotateResponse {
  secret: string;
  ingest_url: string;
}

/** GET /settings/leads/meta/self-serve-onboarding — tenant self-service Meta setup. */
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
  /** Administrators only; omitted for supervisors when server configures META_LEADS_SHARED_APP_SECRET. */
  shared_meta_app_secret?: string | null;
  developers_console_app_url?: string | null;
  graph_api_explorer_url: string;
  oauth_quick_connect_enabled?: boolean;
  meta_oauth_plan_allowed?: boolean | null;
  meta_oauth_server_ready?: boolean | null;
  oauth_redirect_uri?: string | null;
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
  /** §2.4: when Automatic + auto_create, create candidate on fit only if true */
  leads_auto_convert_on_fit_v1?: boolean;
  leads_processing_mode_v1: LeadsProcessingModeV1;
  reroute_after_hours?: number | null;
  mask_pii_in_logs: boolean;
  pull_field_data_from_graph?: boolean;
  /** Fallback vacancy order when ad/ID mapping is empty (Tenant.settings.lead_fit_routing_v1). */
  lead_fit_ordered_vacancy_ids?: UUID[];
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
  leads_auto_convert_on_fit_v1?: boolean;
  leads_processing_mode_v1?: LeadsProcessingModeV1;
  reroute_after_hours?: number | null;
  mask_pii_in_logs?: boolean;
  pull_field_data_from_graph?: boolean;
  lead_fit_ordered_vacancy_ids?: UUID[];
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

export interface LeadMessageTemplate {
  id: string;
  name: string;
  subject: string;
  body: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LeadMessageTemplatePayload {
  name: string;
  subject: string;
  body: string;
  is_active?: boolean;
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

/** §2.11 View incoming — recent Meta lead payload preview (settings admin). */
export interface MetaIncomingLeadPreviewItem {
  lead_id: string;
  created_at: string;
  external_id?: string | null;
  ad_id?: number | null;
  status: string;
  stage?: string | null;
  payload_json_preview: string;
  payload_truncated: boolean;
  normalized_json_preview?: string | null;
  normalized_truncated: boolean;
}

export interface MetaIncomingLeadsPreviewResponse {
  items: MetaIncomingLeadPreviewItem[];
}

/** Real Meta Graph field_data sample for field-mapping UI. */
export interface MetaGraphFieldDataPreviewField {
  name: string;
  value_preview?: string | null;
}

export interface MetaGraphFieldDataPreviewResponse {
  field_names: string[];
  fields: MetaGraphFieldDataPreviewField[];
  leadgen_id: string;
  page_id: string;
  ad_id?: string | null;
  form_id?: string | null;
}

export type ServiceUnit = 'piece' | 'person' | 'hour' | 'package';
export type ServiceOrderStatus =
  | 'draft'
  | 'confirmed'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'on_hold';

export type ServiceItemStatus =
  | 'pending'
  | 'scheduled'
  | 'in_progress'
  | 'delivered'
  | 'cancelled';

// Invoices ---------------------------------------------------------------
export type InvoiceStatus = 'draft' | 'issued' | 'sent' | 'paid' | 'overdue' | 'cancelled' | 'refunded';
export type PaymentMethod = 'bank_transfer' | 'card' | 'cash' | 'online' | 'other';
export type PaymentStatus = 'pending' | 'confirmed' | 'failed';
export type RefundStatus = 'initiated' | 'completed' | 'cancelled';

export interface InvoiceItem {
  id: string;
  invoice_id: string;
  line_no: number;
  description: string;
  qty: number;
  /** Alias for `qty` exposed by some API responses / accepted by detail UI. */
  quantity?: number;
  unit_price: number;
  vat_rate: number;
  net_total: number;
  vat_amount: number;
  gross_total: number;
  /** Display alias for `gross_total`; some responses surface it directly. */
  amount?: number;
  created_at: string;
}

export interface Invoice {
  id: string;
  tenant_id: string;
  company_id?: string | null;
  candidate_id?: string | null;
  contract_id?: string | null;
  order_id?: string | null;
  service_order_id?: string | null;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  currency: string;
  subtotal: number;
  vat_total: number;
  total_amount: number;
  paid_amount: number;
  status: InvoiceStatus;
  payment_date?: string | null;
  pdf_file_id?: string | null;
  billing_details?: Record<string, any> | null;
  created_by?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  items: InvoiceItem[];
  /** Latest e-mail / portal delivery attempt (denormalised for list views). */
  latest_delivery_status?: 'pending' | 'sent' | 'delivered' | 'failed' | string | null;
  latest_delivery_recipient?: string | null;
  latest_delivery_subject?: string | null;
  latest_delivery_reason?: string | null;
  latest_delivery_at?: string | null;
}

export interface Payment {
  id: string;
  tenant_id: string;
  invoice_id: string;
  amount: number;
  currency: string;
  payment_date: string;
  method: PaymentMethod;
  provider?: string | null;
  provider_reference?: string | null;
  reference_number?: string | null;
  status: PaymentStatus;
  created_at: string;
  updated_at: string;
}

export interface Refund {
  id: string;
  tenant_id: string;
  payment_id: string;
  amount: number;
  reason?: string | null;
  refund_date: string;
  status: RefundStatus;
  created_at: string;
  updated_at: string;
}

export type ServiceScheduleStatus =
  | 'reserved'
  | 'confirmed'
  | 'completed'
  | 'no_show'
  | 'cancelled';

export interface AdditionalService {
  id: UUID;
  tenant_id: UUID;
  code: string;
  name: string;
  description?: string | null;
  category?: string | null;
  unit: ServiceUnit;
  base_price: number;
  estimated_cost: number;
  cost_currency: string;
  currency: string;
  vat_rate: number;
  requires_schedule: boolean;
  requires_candidate: boolean;
  result_document_type?: string | null;
  requires_documents?: string[] | null;
  sla_hours?: number | null;
  is_active: boolean;
  meta?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  metrics_orders_count?: number;
  metrics_revenue_completed?: number;
}

export interface AdditionalServiceAttachment {
  id: UUID;
  tenant_id: UUID;
  item_id: UUID;
  file_id: UUID;
  label?: string | null;
  created_at: string;
}

export interface AdditionalServiceSchedule {
  id: UUID;
  tenant_id: UUID;
  item_id: UUID;
  provider?: string | null;
  slot_start?: string | null;
  slot_end?: string | null;
  location?: string | null;
  status: ServiceScheduleStatus;
  meta?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface AdditionalServiceItem {
  id: UUID;
  tenant_id: UUID;
  order_id: UUID;
  service_id: UUID;
  qty: number;
  unit_price: number;
  estimated_cost: number;
  actual_cost?: number | null;
  cost_currency: string;
  cost_source?: string | null;
  cost_status: string;
  vat_rate: number;
  amount: number;
  status: ServiceItemStatus;
  required_documents?: string[] | null;
  result_document_type?: string | null;
  meta?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  service?: AdditionalService | null;
  schedules?: AdditionalServiceSchedule[];
  attachments?: AdditionalServiceAttachment[];
}

export interface AdditionalServiceOrder {
  id: UUID;
  tenant_id: UUID;
  candidate_id?: UUID | null;
  vacancy_id?: UUID | null;
  company_id?: UUID | null;
  /** Party (client) id — same as company_id when the billable counterparty is a company. */
  client_id?: UUID | null;
  status: ServiceOrderStatus;
  total_amount: number;
  currency: string;
  vat_total: number;
  requested_by: UUID;
  assigned_to?: UUID | null;
  notes?: string | null;
  audit?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  items: AdditionalServiceItem[];
}

export interface AdditionalServiceOrderSummary {
  order: AdditionalServiceOrder;
  blocking_items: AdditionalServiceItem[];
  missing_documents: Record<string, string[]>;
}

export type DocumentStatus =
  | 'missing'
  | 'requested'
  | 'in_progress'
  | 'received'
  | 'approved'
  | 'rejected'
  | 'expired';

export type DocumentKind = 'driver' | 'employer' | 'process';
export type DocumentRequestedFrom = 'driver' | 'employer' | 'agency';
export type DocumentProcessType =
  | 'none'
  | 'work_permit'
  | 'visa'
  | 'residence_card'
  | 'residence_permit'
  | 'tachograph_card'
  | 'driver_license_exchange'
  | 'driver_license'
  | 'eu_driver_license'
  | 'adr'
  | 'code95'
  | 'qualification_code95'
  | 'driver_certificate'
  | 'decision'
  | 'swiadectwo_kierowcy'
  | 'other';

export type DocumentWorkflowStepStatus =
  | 'pending'
  | 'in_progress'
  | 'done'
  | 'blocked'
  | 'waiting'
  | 'paused'
  | 'skipped'
  | (string & {});

export interface DocumentFile {
  name: string;
  url?: string | null;
  size?: number | null;
  mime?: string | null;
  uploaded_at?: string | null;
  uploaded_by?: string | null;
  version?: number | null;
}

export interface DocumentReminder {
  due_at: string;
  message: string;
  offset_days: number;
  status: string;
  kind: 'expiry' | 'workflow_step' | (string & {});
  step_code?: string | null;
}

export interface DocumentCheck {
  id: string;
  document_id: string;
  reviewer_id: string | null;
  decision: 'approved' | 'rejected';
  reason_code?: string | null;
  comment?: string | null;
  payload?: Record<string, any> | null;
  created_at: string;
}

export interface DocumentWorkflowStep {
  code: string;
  title: string;
  status: DocumentWorkflowStepStatus;
  due_at?: string | null;
  due_in_hours?: number | null;
  completed_at?: string | null;
  ordered_at?: string | null;
  actor_id?: string | null;
  reminder_id?: string | null;
  assignee?: string | null;
  notes?: string | null;
}

export interface DocumentWorkflow {
  process_type: DocumentProcessType;
  current_step?: string | null;
  completed?: boolean;
  steps: DocumentWorkflowStep[];
  meta?: Record<string, any>;
}

export type DocumentReadinessState =
  | 'pending'
  | 'requested'
  | 'ordered'
  | 'in_progress'
  | 'awaiting_review'
  | 'ready'
  | 'problem'
  | (string & {});

export interface Document {
  id: string;
  tenant_id: string;
  candidate_id: string;
  /** Workspace slice (multi-entity); mirrors API DocumentOut for debugging / UI hints. */
  own_company_id?: string | null;
  company_id?: string | null;
  kind: DocumentKind;
  doc_type: string;
  type: string;
  type_code: string;
  custom_name?: string | null;
  title?: string | null;
  owner_type: string;
  owner_id?: string | null;
  responsible_user_id?: string | null;
  responsible_name?: string | null;
  requested_from: DocumentRequestedFrom;
  process_type: DocumentProcessType;
  number?: string | null;
  status: DocumentStatus;
  reminder_days_before: number;
  files: DocumentFile[];
  workflow?: DocumentWorkflow | null;
  source?: string | null;
  external_id?: string | null;
  verified_at?: string | null;
  /** Free-form user comment (required for `additional_document`). */
  user_comment?: string | null;
  issue_date?: string | null;
  expire_date?: string | null;
  issued_at?: string | null;
  expires_at?: string | null;
  ordered_at?: string | null;
  valid_from?: string | null;
  has_files?: boolean;
  readiness_state?: DocumentReadinessState | null;
  status_rank?: number | null;
  meta: Record<string, any>;
  extra: Record<string, any>;
  meta_json: Record<string, any>;
  created_at?: string | null;
  updated_at?: string | null;
  reminders: DocumentReminder[];
  version?: number | null;
  last_check?: DocumentCheck | null;
  /** Internal staff comment (separate from `user_comment`); some synthetic placeholder
   *  rows constructed in the UI initialise this field to null. */
  comment?: string | null;
  /** Free-form note attached to the document row (used by the placeholder synthesizer). */
  note?: string | null;
}

export interface NotificationItem {
  id: string;
  event_type: string;
  channel: string;
  payload: Record<string, any>;
  entity_type?: string | null;
  entity_id?: string | null;
  is_read: boolean;
  created_at: string;
  delivered_at?: string | null;
  read_at?: string | null;
  /** Optional priority hint surfaced by SLA-aware notifiers (`critical`/`high`/`normal`). */
  priority?: string | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
}

export type ReminderStatus = 'new' | 'pending' | 'sent' | 'overdue' | 'done' | 'cancelled';

export interface ReminderRecord {
  id: string;
  title?: string | null;
  description?: string | null;
  type: string;
  entity_type: string;
  entity_id: string;
  owner_id?: string | null;
  assignee_id?: string | null;
  priority?: string | null;
  channel?: string | null;
  status: ReminderStatus;
  due_at: string;
  remind_at?: string | null;
  snoozed_until?: string | null;
  completed_at?: string | null;
  recurrence_json?: Record<string, any> | null;
  payload: Record<string, any>;
  created_at?: string | null;
  updated_at?: string | null;
  /** UOS: derived SLA deadline (API projection). */
  sla_due_at?: string | null;
  /** UOS: coarse SLA state — on_track | at_risk | overdue | resolved. */
  sla_status?: string | null;
}

export interface ReminderListResponse {
  items: ReminderRecord[];
}

export interface DocumentSummaryRequired {
  total: number;
  approved: number; // backward-compat alias for ready count
  ready: number;
  in_progress: number;
  missing_count: number;
  problems: number;
  missing: string[];
  problematic: string[];
  ready_types?: string[];
  in_progress_types?: string[];
}

export type DocumentPackStatus = 'valid' | 'warnings' | 'gaps' | 'skeleton';

export interface OwnerExpiryAggregate {
  all_documents_valid: boolean;
  has_expiring_documents: boolean;
  has_expired_documents: boolean;
  has_missing_expiry: boolean;
}

export interface DocumentPackProjection {
  code: string;
  label: string;
  status: DocumentPackStatus;
  skeleton: boolean;
  applies: boolean;
  ref_pack_codes: string[];
  required: string[];
  present: string[];
  missing: string[];
  expired: string[];
  expiring_soon: Array<{
    document_code: string;
    expires_on?: string | null;
    days_left?: number | null;
  }>;
  missing_expiry: string[];
  gaps: string[];
  blockers: string[];
  warnings: string[];
  expiry: OwnerExpiryAggregate;
}

export type ReminderWorkQueueAction =
  | 'upload_document'
  | 'request_update'
  | 'renew_document'
  | 'capture_expiry_date';

export type ReminderWorkQueueSeverity = 'critical' | 'high' | 'medium' | 'low';

export interface ReminderWorkQueueItem {
  task_key: string;
  title: string;
  severity: ReminderWorkQueueSeverity;
  owner_type: 'candidate' | 'employee';
  owner_id: string;
  recipient_role: string;
  due_date?: string | null;
  source_pack: string;
  action: ReminderWorkQueueAction;
  document_code: string;
  reason: string;
}

export interface DocumentSummary {
  status: 'ok' | 'missing' | 'problems' | 'expiring_soon' | 'no_required' | 'in_progress' | 'expired' | 'missing_expiry' | (string & {});
  percent_ready: number;
  required: DocumentSummaryRequired;
  expiring_soon: Array<{ type: string; expires_at: string; days_left?: number | null }>;
  expired?: Array<{ type: string; expires_at?: string | null; days_left?: number | null }>;
  missing_expiry?: Array<{ type: string }>;
  expiry?: OwnerExpiryAggregate;
  packs?: DocumentPackProjection[];
  reminder_work_queue?: ReminderWorkQueueItem[];
  checklist?: CandidateDocumentChecklist;
}

export interface CandidateDocumentsSummaryResponse {
  candidate_id: string;
  summary: DocumentSummary;
  documents: Document[];
  ruleset_version: RulesetVersion;
  checklist?: CandidateDocumentChecklist;
}

export interface CandidateDocumentChecklist {
  requiredTypes: string[];
  optionalTypes: string[];
  debug?: Record<string, any>;
}

export interface RulesetVersion {
  id: string;
  tenant_id: string;
  version: number;
  ruleset: Record<string, any>;
  comment?: string | null;
  created_by?: string | null;
  created_at: string;
  is_active: boolean;
  signature: string;
  origin_version_id?: string | null;
  rollback_comment?: string | null;
}

export interface RulesetDiff {
  version_id: string;
  compare_to?: string | null;
  diff: Record<string, any>;
  computed_with?: string | null;
  created_at?: string | null;
}

export interface RulesetUsageEntry {
  id: string;
  ruleset_version_id: string;
  used_in: string;
  reference_id?: string | null;
  used_at: string;
  meta: Record<string, any>;
}

export interface RulesetUsageResponse {
  items: RulesetUsageEntry[];
  summary: Record<string, number>;
}

/** Канбан/пайплайн */
export interface PipelineItem {
  link_id: UUID;
  candidate: { id: UUID; name?: string | null; email?: string | null };
  status: string; // код этапа
}

export interface PipelineOut {
  statuses: string[];
  columns: Record<string, PipelineItem[]>;
}

export interface CandidatesListOut {
  items: Candidate[];
  total: number;
  summary: { by_stage: Record<string, number>; by_manager: Record<string, number> };
}

/** Метаданные этапов */
export interface MetaStages {
  default: string;
  codes: string[];
  labels: Record<string, string>;       // code -> human label
  groups: Record<string, string[]>;     // column -> codes[]
  column_of: Record<string, string>;    // code -> column
  order: string[];                      // ordered codes
  /** Present when /meta/stages is narrowed for recruitment roles (agency handoff). */
  stage_visibility_mode?: string | null;
  /** Back-compat flag from API; when true, list filters should not surface post-handoff stage noise. */
  recruiter_handoff_stage_filter?: boolean | null;
  reason_choices?: Record<string, { code: string; label: string }[]>;
  custom_stages?: Array<{
    code: string;
    label: string;
    order: number;
    id: number;
  }>;
  meta?: Record<
    string,
    {
      is_system?: boolean;
      visible_for_agency?: boolean;
      visible_for_client?: boolean;
      owner?: string; // 'agency' | 'client' | 'shared' | custom
    }
  >;
}

/** Cправочники */
export type Manager  = { id: string; name: string; email?: string | null };
export type Country  = { code: string; name: string };
export type Language = { code: string; name: string };

/** Телефонные коды: код страны -> префикс */
export type DialCodes = Record<string, string>; // { "PL": "+48", ... }

/** Запись доступа к компании (UI-friendly + backward-compatible) */
export interface CompanyAccessEntry {
  // поля, которые читает админский UI
  id: string;
  email: string;
  role: string;       // 'viewer' | 'editor' | 'admin' | ...
  can_edit: boolean;
  created_at?: string;

  // легаси/низкоуровневые поля сохраним как опциональные,
  // чтобы не ломать старые вызовы API, если где-то используются
  user_id?: string;
  company_id?: string;
  access_level?: string;
  granted_at?: string;
  revoked_at?: string | null;
}

/** Запрос на удаление (расширенный для UI) */
export interface DeletionRequest {
  id: string;
  user_id?: string;                 // может отсутствовать, если денормализовано
  reason?: string;                  // не всегда приходит
  requested_at: string;
  status: 'pending' | 'approved' | 'rejected';

  // Денормализованные поля, которые читает фронт
  candidate_id?: string;
  candidate?: any;                  // { first_name, last_name, ... }

  requested_by_user?: any;          // User объект
  requested_by?: string;            // fallback строка, если user не пришёл

  supervisor_user?: any;
  supervisor_id?: string;

  resolved_by?: string;
  resolved_at?: string;
}

/** Решение по запросу на удаление */
export interface DeletionDecision {
  request_id?: string;
  decided_by?: string;
  decision?: 'approved' | 'rejected';
  decided_at?: string;
  // поле, которое отправляет UI при отклонении
  comment?: string;
  // совместимость с прежним наименованием
  notes?: string | null;
}
