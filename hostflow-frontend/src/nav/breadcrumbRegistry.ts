import { CRM_APP_PATHS } from '../app/crmAppPaths'
import type { Permission } from '../hooks/usePermissions'

/**
 * Breadcrumb registry — maps a canonical SPA path to its display metadata.
 *
 * Replaces the legacy {@link CrmContourWayfindingStrip} chip-row with a true
 * hierarchical breadcrumb (`Home › Section › Subsection › Current`).
 *
 * Each entry resolves a `labelKey` (i18n key under `app.nav.items.*` whenever
 * possible) and an optional `parentPath` that points to its parent entry.
 * Dynamic detail pages (e.g. `/app/candidates/:id`) are not registered here —
 * those are handled inline by the page passing `currentLabel` to
 * {@link PageBreadcrumb}, while the parent path is matched against the
 * registry by **longest known prefix**.
 */
export type BreadcrumbEntry = {
  /** i18n key for the display label. */
  labelKey: string
  /** Parent canonical path; omit for top-level entries. */
  parentPath?: string
  /** Optional permission gate — if user lacks it, the link still renders as plain text (no nav). */
  permission?: Permission
}

const P = CRM_APP_PATHS

/**
 * Single source of truth for IA breadcrumb trails. Keep ordered by area:
 * 1) hubs, 2) work surfaces, 3) clients/candidates/vacancies, 4) leads,
 * 5) services/invoices/documents/processing, 6) tasks/reminders/automations,
 * 7) communications, 8) personal, 9) onboarding, 10) settings.
 */
export const BREADCRUMB_REGISTRY: Record<string, BreadcrumbEntry> = {
  [P.overview]: { labelKey: 'app.nav.items.overview' },
  [P.work]: { labelKey: 'app.nav.items.work' },
  [P.analytics]: { labelKey: 'app.nav.items.analytics' },
  [P.analyticsLeadConversionFunnel]: {
    labelKey: 'app.nav.items.analytics',
    parentPath: P.analytics,
  },

  [P.clientsDirectory]: { labelKey: 'app.nav.items.clients', permission: 'companies.view' },
  [P.agencyClients]: { labelKey: 'app.nav.items.clients', permission: 'companies.view' },
  [P.clientsLinkBase]: { labelKey: 'app.nav.items.clients', parentPath: P.clientsDirectory },
  [P.clientNew]: { labelKey: 'app.nav.items.clients', parentPath: P.clientsDirectory },
  [P.companiesLegacy]: { labelKey: 'app.nav.items.clients', permission: 'companies.view' },

  [P.candidates]: { labelKey: 'app.nav.items.candidates', permission: 'candidates.view' },
  [P.candidatesNoNextActionPage]: {
    labelKey: 'app.nav.items.candidates',
    parentPath: P.candidates,
  },
  [P.candidateNew]: { labelKey: 'app.nav.items.candidates', parentPath: P.candidates },
  [P.pipeline]: { labelKey: 'app.nav.items.candidates' },

  [P.vacancies]: { labelKey: 'app.nav.items.vacancies' },
  [P.vacancyNew]: { labelKey: 'app.nav.items.vacancies', parentPath: P.vacancies },

  [P.leads]: { labelKey: 'app.nav.items.leads', permission: 'leads.view' },
  [P.leadsDistribution]: {
    labelKey: 'app.nav.items.leads_distribution',
    parentPath: P.leads,
  },
  [P.leadsDistributionRules]: {
    labelKey: 'app.nav.items.leads_distribution_rules',
    parentPath: P.leadsDistribution,
  },

  [P.services]: { labelKey: 'app.nav.items.services' },
  [P.invoices]: { labelKey: 'app.nav.items.invoices' },
  [P.invoiceNew]: { labelKey: 'app.nav.items.invoices', parentPath: P.invoices },
  [P.orders]: { labelKey: 'app.nav.items.orders' },
  [P.documents]: { labelKey: 'app.nav.items.documents' },
  [P.procesowani]: { labelKey: 'app.nav.items.do_procesowania' },
  [P.doProcesowaniaLegacy]: { labelKey: 'app.nav.items.do_procesowania' },

  [P.tasks]: { labelKey: 'app.nav.items.tasks' },
  [P.remindersLegacy]: { labelKey: 'app.nav.items.reminders' },
  [P.activitiesLegacy]: { labelKey: 'app.nav.items.activities' },
  [P.plannerLegacy]: { labelKey: 'app.nav.items.planner' },

  [P.automations]: { labelKey: 'app.nav.items.automations' },
  [P.automationRules]: { labelKey: 'app.nav.items.automation_rules', parentPath: P.automations },
  [P.automationLog]: { labelKey: 'app.nav.items.automation_log', parentPath: P.automations },
  [P.acquisitionActivity]: { labelKey: 'app.nav.items.acquisition_activity' },

  [P.inbox]: { labelKey: 'app.nav.items.inbox', permission: 'notifications.view' },
  [P.inboxThreadsBase]: { labelKey: 'app.nav.items.inbox', parentPath: P.inbox },
  [P.communicationsLegacyHub]: { labelKey: 'app.nav.items.communications' },
  [P.communicationsThreadsBase]: {
    labelKey: 'app.nav.items.inbox',
    parentPath: P.communicationsLegacyHub,
  },
  [P.communicationsCommandAudit]: {
    labelKey: 'app.nav.items.command_audit',
    parentPath: P.communicationsLegacyHub,
  },
  [P.calendar]: { labelKey: 'app.nav.items.calendar' },
  [P.slaIncidents]: { labelKey: 'app.nav.items.sla_incidents' },
  [P.messages]: { labelKey: 'app.nav.items.messages_inbox' },
  [P.email]: { labelKey: 'app.nav.items.email_inbox' },
  [P.setupCommunications]: {
    labelKey: 'app.nav.items.communications_setup',
    parentPath: P.settings,
  },

  [P.profile]: { labelKey: 'app.nav.items.profile' },
  [P.myCompany]: { labelKey: 'app.nav.items.my_company' },
  [P.myAvailability]: { labelKey: 'app.nav.items.my_availability' },
  [P.teamAvailability]: { labelKey: 'app.nav.items.team_availability' },
  [P.timeOff]: { labelKey: 'app.nav.items.time_off' },

  [P.onboarding]: { labelKey: 'app.nav.items.setup' },
  [P.onboardingCompany]: { labelKey: 'app.nav.items.my_company', parentPath: P.onboarding },
  [P.onboardingGettingStarted]: {
    labelKey: 'app.nav.items.setup',
    parentPath: P.onboarding,
  },

  [P.settings]: { labelKey: 'app.nav.items.settings' },
}

/**
 * Path → entry lookup using exact match first, then longest-prefix match.
 * Trailing slashes are normalised. Settings sub-paths automatically chain
 * back to {@link CRM_APP_PATHS.settings} via prefix; explicit entries above
 * win where present.
 */
export function lookupBreadcrumbEntry(pathname: string): { path: string; entry: BreadcrumbEntry } | null {
  const norm = pathname.replace(/\/+$/, '') || '/'
  const direct = BREADCRUMB_REGISTRY[norm]
  if (direct) return { path: norm, entry: direct }
  let bestPath: string | null = null
  let bestLen = -1
  for (const path of Object.keys(BREADCRUMB_REGISTRY)) {
    const base = path.replace(/\/+$/, '') || '/'
    if (base === '/' ) continue
    if (norm === base || norm.startsWith(`${base}/`)) {
      if (base.length > bestLen) {
        bestLen = base.length
        bestPath = base
      }
    }
  }
  if (bestPath) return { path: bestPath, entry: BREADCRUMB_REGISTRY[bestPath] }
  if (norm.startsWith(`${P.settings}/`)) {
    return { path: P.settings, entry: BREADCRUMB_REGISTRY[P.settings] }
  }
  return null
}

/**
 * Walks the {@link BREADCRUMB_REGISTRY} parent chain from the given pathname
 * to the root (top-level entry with no `parentPath`). Returns the trail in
 * **root-first** order so callers can render `Home › Section › Current`
 * without re-reversing.
 */
export function buildBreadcrumbTrail(pathname: string): { path: string; entry: BreadcrumbEntry }[] {
  const start = lookupBreadcrumbEntry(pathname)
  if (!start) return []
  const trail: { path: string; entry: BreadcrumbEntry }[] = [start]
  let cursor: BreadcrumbEntry = start.entry
  const guard = new Set<string>([start.path])
  while (cursor?.parentPath) {
    const parentPath: string = cursor.parentPath
    if (guard.has(parentPath)) break
    guard.add(parentPath)
    const parent: BreadcrumbEntry | undefined = BREADCRUMB_REGISTRY[parentPath]
    if (!parent) break
    trail.unshift({ path: parentPath, entry: parent })
    cursor = parent
  }
  return trail
}
