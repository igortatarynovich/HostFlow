/**
 * Primary App shell sidebar rail placement (agency bucketed + client flat).
 * Consumed by `Sidebar.tsx`; `sidebarNavIntegrity` tests fail on drift.
 *
 * Canon: ADR-023 Stage 1 — Module Surface Separation.
 * Domain ownership ≠ nav convenience: Employee → HR; Invoice → Finance.
 * Do not reintroduce a mixed Pipeline / CRM / Leads bucket.
 */
import { APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS } from './appShellNav'

export const SIDEBAR_CLIENT_FLAT_ORDER = [
  'overview',
  'work-hub',
  'inbox',
  'vacancies',
  'candidates',
  'tasks',
  'notification-alerts',
  'settings-integrations',
  'profile',
] as const

export const SIDEBAR_AGENCY_DASHBOARD_ORDER = ['overview'] as const
export const SIDEBAR_AGENCY_WORK_HUB_ORDER = ['work-hub'] as const
/** Horizontal Communications — not nested under Recruitment or Sales. */
export const SIDEBAR_AGENCY_INBOX_ORDER = ['inbox'] as const

/** Recruitment owns Applications / Candidates / Vacancies — not Employees (ADR-023 §2.2). Attraction → Marketing. */
export const SIDEBAR_AGENCY_RECRUITMENT_ORDER = [
  'vacancies',
  'recruitment-inbox',
  'candidates',
] as const

/** HR / Workforce owns Employee Workspace after handoff. */
export const SIDEBAR_AGENCY_HR_ORDER = ['hr-workspace'] as const

/** Sales owns Inquiry + ClientAccount — not Invoice/Payment model. Marketing = Campaign/Flight workspace. */
export const SIDEBAR_AGENCY_SALES_ORDER = ['sales', 'marketing', 'clients'] as const

/** Services owns catalog + service order lifecycle. */
export const SIDEBAR_AGENCY_SERVICES_ORDER = ['service-orders', 'services'] as const

/** Finance owns Invoice (and later Payments / receivables). */
export const SIDEBAR_AGENCY_FINANCE_ORDER = ['invoices'] as const

/** @deprecated Prefer module-specific orders (ADR-023 amended). */
export const SIDEBAR_AGENCY_PIPELINE_ORDER = [
  ...SIDEBAR_AGENCY_RECRUITMENT_ORDER,
  ...SIDEBAR_AGENCY_SALES_ORDER,
] as const

export const SIDEBAR_AGENCY_TASKS_ORDER = ['tasks', 'notification-alerts', 'calendar'] as const
export const SIDEBAR_AGENCY_PROCESSING_ORDER = [] as const
export const SIDEBAR_AGENCY_TEAM_ORDER = ['team-availability', 'my-availability', 'time-off'] as const
/** Document Hub — platform horizontal (ADR-009). */
export const SIDEBAR_AGENCY_DOCUMENTS_ORDER = ['documents'] as const
export const SIDEBAR_AGENCY_AUTOMATIONS_ORDER = ['automations', 'acquisition-activity'] as const
export const SIDEBAR_AGENCY_INTEGRATIONS_ORDER = ['settings-integrations'] as const
export const SIDEBAR_AGENCY_ANALYTICS_ORDER = [] as const
export const SIDEBAR_AGENCY_ORGANIZATION_ORDER = ['my-company'] as const
export const SIDEBAR_AGENCY_SETTINGS_HUB_ORDER = ['settings'] as const
export const SIDEBAR_AGENCY_PROFILE_ORDER = ['profile'] as const

/** @deprecated Use SIDEBAR_AGENCY_FINANCE_ORDER / SIDEBAR_AGENCY_SERVICES_ORDER. */
export function financeSidebarOrder(_showFinanceSection: boolean): readonly string[] {
  return [...SIDEBAR_AGENCY_FINANCE_ORDER]
}

/** Deep links opened from Automations / Settings / Integrations hubs — not primary rail rows. */
export const SIDEBAR_HUB_NAV_ITEM_KEYS = [
  'automation-rules',
  'automation-log',
  'leads-distribution',
  'leads-distribution-rules',
  'settings-billing',
  'settings-tenants',
  'settings-funnels',
  'settings-hiring-gates',
  'settings-risk-intel',
  'settings-docs',
  'settings-candidate-profiles',
  'settings-custom-fields',
  'settings-legal',
  'settings-company-access',
  'settings-email',
  'settings-tenant-links',
  'integrations-meta',
  'integrations-google',
  'integrations-webhook',
  'settings-communications',
  'settings-communications-messengers',
  'settings-communications-queue',
  'settings-communications-sla',
  'settings-communications-templates',
  'settings-communications-automation',
  'settings-ruleset',
  'settings-audit',
] as const

/** Entry surfaced elsewhere (e.g. Topbar quick nav), not in bucketed sidebar. */
export const SIDEBAR_STANDALONE_NAV_ITEM_KEYS = ['fleet'] as const

const _agencyRailKeyParts: readonly (readonly string[])[] = [
  SIDEBAR_AGENCY_DASHBOARD_ORDER,
  SIDEBAR_AGENCY_WORK_HUB_ORDER,
  SIDEBAR_AGENCY_INBOX_ORDER,
  SIDEBAR_AGENCY_RECRUITMENT_ORDER,
  SIDEBAR_AGENCY_HR_ORDER,
  SIDEBAR_AGENCY_SALES_ORDER,
  SIDEBAR_AGENCY_SERVICES_ORDER,
  SIDEBAR_AGENCY_FINANCE_ORDER,
  SIDEBAR_AGENCY_TASKS_ORDER,
  SIDEBAR_AGENCY_PROCESSING_ORDER,
  SIDEBAR_AGENCY_TEAM_ORDER,
  SIDEBAR_AGENCY_DOCUMENTS_ORDER,
  SIDEBAR_AGENCY_AUTOMATIONS_ORDER,
  SIDEBAR_AGENCY_INTEGRATIONS_ORDER,
  SIDEBAR_AGENCY_ANALYTICS_ORDER,
  SIDEBAR_AGENCY_ORGANIZATION_ORDER,
  SIDEBAR_AGENCY_SETTINGS_HUB_ORDER,
  SIDEBAR_AGENCY_PROFILE_ORDER,
]

/** Union of keys that may appear on the agency primary rail. */
export const ALL_AGENCY_PRIMARY_RAIL_KEYS: ReadonlySet<string> = new Set(_agencyRailKeyParts.flat())

export function isNavKeyAccountedForInSidebarPlacement(key: string): boolean {
  if (ALL_AGENCY_PRIMARY_RAIL_KEYS.has(key)) return true
  if ((SIDEBAR_CLIENT_FLAT_ORDER as readonly string[]).includes(key)) return true
  if ((APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS as readonly string[]).includes(key)) return true
  if ((SIDEBAR_HUB_NAV_ITEM_KEYS as readonly string[]).includes(key)) return true
  if ((SIDEBAR_STANDALONE_NAV_ITEM_KEYS as readonly string[]).includes(key)) return true
  return false
}
