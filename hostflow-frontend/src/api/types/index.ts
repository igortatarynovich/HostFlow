/**
 * Central export file for all API types
 * Re-exports all types from module files for backward compatibility
 */

// Common types
export type { UUID, WhoAmI, Address, Manager, Country, Language, DialCodes } from './common';

// User and tenant types
export type {
  UserRole,
  TenantUserRole,
  TenantType,
  TenantStatus,
  TenantUsage,
  TenantModuleSettings,
  TenantModuleSettingsPatch,
  RoleModuleMatrixRole,
  RoleModulePermissions,
  TenantRoleModuleMatrix,
  TenantRoleModuleMatrixPatch,
  EffectiveRoleModules,
  TenantModuleOverrideUser,
  TenantUserModuleOverrides,
  TenantUserModuleOverridesPatch,
  SeatRequest,
  SeatRequestDecisionPayload,
  SeatRequestCreatePayload,
  TenantLicense,
  TenantLicenseInput,
  TenantLicensePatchInput,
  PlatformTenant,
  PlatformTenantListResponse,
  TenantSummary,
  TenantRecord,
  TenantMeResponse,
  TenantImpersonationToken,
  TenantAdminInput,
  TenantAdminResponse,
  PlatformTenantCreatePayload,
  PlatformTenantUpdatePayload,
  TenantStatusChangePayload,
  TenantVacancyAccessItem,
  TenantVacancyAccessListResponse,
  TenantVacancyAccessUpdatePayload,
  TenantVacancyOption,
  TeamOverviewResponse,
  HiringPipelineGatesPublic,
  HiringPipelineGatesPatch,
  TenantBrandingResponse,
  TenantBrandingPayload,
  UserCompanyAccess,
  RecruiterSummary,
  ManagerOption,
  AdminUser,
  AdminUserDetail,
  UserProfile,
  UserProfileUpdate,
  UserUIPreferences,
  UserNotificationPreference,
  UserDefaultsPreferences,
  UserSavedView,
  UserSavedViews,
  UserPreferences,
  UserSecurityCompany,
  UserSecuritySupervisor,
  UserSecuritySummary,
  UserMe,
  UserSessionInfo,
  UserAvatar,
  UserSavedViewsPatch,
  UserPreferencesPatchPayload,
  UserMeUpdatePayload,
  UserInvite,
  UserAuditEntry,
} from './user';

// Candidate types
export type {
  CandidateEmploymentEntry,
  CandidateEmploymentRecord,
  CandidateExtra,
  Candidate,
  CandidatesListOut,
} from './candidate';

// Document types
export type {
  DocumentStatus,
  DocumentKind,
  DocumentRequestedFrom,
  DocumentProcessType,
  DocumentWorkflowStepStatus,
  DocumentFile,
  DocumentReminder,
  DocumentCheck,
  DocumentWorkflowStep,
  DocumentWorkflow,
  DocumentReadinessState,
  Document,
  DocumentSummaryRequired,
  DocumentSummary,
  CandidateDocumentsSummaryResponse,
  CandidateDocumentChecklist,
} from './document';

// Company and vacancy types
export type { Company, CompanyReadiness, Vacancy, CompanyAccessEntry } from './company';

// Service types
export type {
  ServiceItemStatus,
  ServiceOrderStatus,
  ServiceScheduleStatus,
  ServiceUnit,
  AdditionalService,
  AdditionalServiceAttachment,
  AdditionalServiceSchedule,
  AdditionalServiceItem,
  AdditionalServiceOrder,
  AdditionalServiceOrderSummary,
} from './service';

// Invoice and payment types
export type {
  InvoiceStatus,
  PaymentMethod,
  PaymentStatus,
  RefundStatus,
  InvoiceItem,
  Invoice,
  InvoiceActivity,
  Payment,
  Refund,
} from './invoice';

// Metadata types
export type { MetaStages, DeletionRequest, DeletionDecision } from './meta';

// Ruleset types
export type { RulesetVersion, RulesetDiff, RulesetUsageResponse } from './ruleset';

// Lead types
export type {
  LeadStatus,
  Lead,
  LeadListResponse,
  MetaCredentialStatus,
  MetaLeadSettings,
  MetaLeadSettingsPatch,
  MetaLeadCredential,
  MetaCredentialCreatePayload,
  MetaCredentialUpdatePayload,
  MetaCredentialRotateResponse,
  MetaAdsMapEntry,
  MetaAdsMapCreatePayload,
  MetaAdsMapUpdatePayload,
  MetaLeadAdminResponse,
  MetaLeadReroutePayload,
} from './lead';

// Notification types
export type {
  NotificationItem,
  NotificationListResponse,
  ReminderStatus,
  ReminderRecord,
  ReminderListResponse,
} from './notification';

// Pipeline types
export type { PipelineItem, PipelineOut } from './pipeline';
