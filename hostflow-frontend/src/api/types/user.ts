/**
 * User and tenant-related types
 */

export type UserRole = 'administrator' | 'supervisor' | 'recruiter' | 'client_manager' | 'client_processor' | 'viewer';
export type TenantUserRole = UserRole;

export type TenantType = 'agency' | 'company' | 'platform';
export type TenantStatus = 'active' | 'suspended' | 'trial';

export interface TenantUsage {
  recruiter_count: number;
  supervisor_count: number;
  client_manager_count: number;
  viewer_count: number;
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
}

export type TenantModuleSettingsPatch = Partial<TenantModuleSettings>;

export type RoleModuleMatrixRole =
  | 'administrator'
  | 'supervisor'
  | 'recruiter'
  | 'client_manager'
  | 'client_processor'
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

export interface TenantModuleOverrideUser {
  user_id: string | null;
  email: string;
  full_name?: string | null;
  role: UserRole;
  status: 'active' | 'inactive' | 'invited';
  is_active: boolean;
}

export interface TenantUserModuleOverrides {
  users: Record<string, Partial<Record<keyof TenantModuleSettings, RoleModulePermissions>>>;
}

export interface TenantUserModuleOverridesPatch {
  users: Partial<Record<string, Partial<Record<keyof TenantModuleSettings, RoleModulePermissions>> | null>>;
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

export interface SeatRequestCreatePayload {
  role: string;
  requested_count: number;
  message?: string | null;
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
}

export interface PlatformTenantListResponse {
  total: number;
  items: PlatformTenant[];
}

export interface TenantSummary {
  id: string;
  name: string;
  slug: string;
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

export interface PlatformTenantCreatePayload {
  name: string;
  slug: string;
  workspace_label?: string | null;
  type: TenantType;
  status?: TenantStatus;
  client_portal_enabled?: boolean;
  status_sharing_allowed?: boolean;
  description?: string | null;
  license?: TenantLicenseInput;
  initial_admin: TenantAdminInput;
}

export interface PlatformTenantUpdatePayload {
  name?: string;
  slug?: string;
  workspace_label?: string | null;
  description?: string | null;
  client_portal_enabled?: boolean;
  status_sharing_allowed?: boolean;
}

export interface TenantStatusChangePayload {
  status: TenantStatus;
  reason?: string | null;
}

export interface TenantVacancyAccessItem {
  vacancy_id: string;
  title: string;
  company_name?: string | null;
  tenant_id: string;
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
}

export interface UserSessionInfo {
  id: string;
  created_at: string;
  expires_at: string;
  ip_address?: string | null;
  user_agent?: string | null;
}

export interface UserAvatar {
  url: string;
  meta?: Record<string, any> | null;
}

export interface UserSavedViewsPatch {
  candidates?: UserSavedView[];
  vacancies?: UserSavedView[];
}

export interface UserPreferencesPatchPayload {
  ui?: Partial<UserUIPreferences>;
  notifications?: Record<string, UserNotificationPreference>;
  defaults?: Partial<UserDefaultsPreferences>;
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
  invited_by: string;
  invited_at: string;
  expires_at: string;
  accepted_at?: string | null;
  tenant_id: string;
}

export interface UserAuditEntry {
  id: string;
  user_id: string;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  metadata?: Record<string, any> | null;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
}
