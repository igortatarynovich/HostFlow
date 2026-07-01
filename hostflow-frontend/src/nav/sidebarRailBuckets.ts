/**
 * Primary App shell sidebar rail placement (agency bucketed + client flat).
 * Consumed by `Sidebar.tsx`; `sidebarNavIntegrity` tests fail on drift.
 */
import { APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS } from './appShellNav'

export const SIDEBAR_CLIENT_FLAT_ORDER = [
  'overview',
  'work-hub',
  'inbox',
  'candidates',
  'do-procesowania',
  'tasks',
  'notification-alerts',
  'settings-integrations',
  'profile',
] as const

export const SIDEBAR_AGENCY_DASHBOARD_ORDER = ['overview'] as const
export const SIDEBAR_AGENCY_WORK_HUB_ORDER = ['work-hub'] as const
export const SIDEBAR_AGENCY_INBOX_ORDER = ['inbox'] as const
export const SIDEBAR_AGENCY_PIPELINE_ORDER = [
  'candidates',
  'hr-workspace',
  'clients',
  'vacancies',
  'leads',
] as const
export const SIDEBAR_AGENCY_TASKS_ORDER = ['tasks', 'notification-alerts', 'calendar'] as const
export const SIDEBAR_AGENCY_PROCESSING_ORDER = ['do-procesowania'] as const
export const SIDEBAR_AGENCY_TEAM_ORDER = ['team-availability', 'my-availability', 'time-off'] as const
export const SIDEBAR_AGENCY_DOCUMENTS_ORDER = ['documents'] as const
export const SIDEBAR_AGENCY_AUTOMATIONS_ORDER = ['automations'] as const
export const SIDEBAR_AGENCY_INTEGRATIONS_ORDER = ['settings-integrations'] as const
export const SIDEBAR_AGENCY_ANALYTICS_ORDER = [] as const
export const SIDEBAR_AGENCY_ORGANIZATION_ORDER = ['my-company'] as const
export const SIDEBAR_AGENCY_SETTINGS_HUB_ORDER = ['settings'] as const
export const SIDEBAR_AGENCY_PROFILE_ORDER = ['profile'] as const

export function financeSidebarOrder(showFinanceSection: boolean): readonly string[] {
  return showFinanceSection
    ? ['service-orders', 'invoices', 'services']
    : ['service-orders', 'services', 'invoices']
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
  'settings-ruleset',
  'settings-audit',
] as const

/** Entry surfaced elsewhere (e.g. Topbar quick nav), not in bucketed sidebar. */
export const SIDEBAR_STANDALONE_NAV_ITEM_KEYS = ['fleet'] as const

const _agencyRailKeyParts: readonly (readonly string[])[] = [
  SIDEBAR_AGENCY_DASHBOARD_ORDER,
  SIDEBAR_AGENCY_WORK_HUB_ORDER,
  SIDEBAR_AGENCY_INBOX_ORDER,
  SIDEBAR_AGENCY_PIPELINE_ORDER,
  SIDEBAR_AGENCY_TASKS_ORDER,
  SIDEBAR_AGENCY_PROCESSING_ORDER,
  SIDEBAR_AGENCY_TEAM_ORDER,
  ['service-orders', 'invoices', 'services'],
  SIDEBAR_AGENCY_DOCUMENTS_ORDER,
  SIDEBAR_AGENCY_AUTOMATIONS_ORDER,
  SIDEBAR_AGENCY_INTEGRATIONS_ORDER,
  SIDEBAR_AGENCY_ANALYTICS_ORDER,
  SIDEBAR_AGENCY_ORGANIZATION_ORDER,
  SIDEBAR_AGENCY_SETTINGS_HUB_ORDER,
  SIDEBAR_AGENCY_PROFILE_ORDER,
]

/** Union of keys that may appear on the agency primary rail (finance order does not change membership). */
export const ALL_AGENCY_PRIMARY_RAIL_KEYS: ReadonlySet<string> = new Set(_agencyRailKeyParts.flat())

export function isNavKeyAccountedForInSidebarPlacement(key: string): boolean {
  if (ALL_AGENCY_PRIMARY_RAIL_KEYS.has(key)) return true
  if ((SIDEBAR_CLIENT_FLAT_ORDER as readonly string[]).includes(key)) return true
  if ((APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS as readonly string[]).includes(key)) return true
  if ((SIDEBAR_HUB_NAV_ITEM_KEYS as readonly string[]).includes(key)) return true
  if ((SIDEBAR_STANDALONE_NAV_ITEM_KEYS as readonly string[]).includes(key)) return true
  return false
}
