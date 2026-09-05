/**
 * App shell navigation policy: items hidden from the primary sidebar rail (still in NAV_ITEMS for deep links).
 * Bucket order and hub/standalone keys live in `sidebarRailBuckets.ts` (guarded by `sidebarNavIntegrity` test).
 *
 * Primary agency rail is production-ready surfaces only. Hide unfinished modules here
 * (or drop them from agency bucket orders) until the operator can complete the job E2E.
 */
export const APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS = [
  /** Retired unused artifacts — not product surfaces. Routes remain for redirects / deep links. */
  'leads',
  'launchpad',
  'recruitment-searches',
  /** Channel-centric client acquisition is a source config, not a daily work surface.
   *  Company inquiries are worked in Sales (`/app/sales`). */
  'client-acquisition-channels',
  /** §2.14: primary entry via Candidates + queue param / dashboard. */
  'candidates-no-next-action',
  'sla-incidents',
  /** Operator diagnostics — Automations hub / direct URL. */
  'command-audit',
  /** Team detail — Settings landing + Settings chrome only. */
  'settings-users',
  /** Not production-ready: hide from the rail until the module ships. Agency buckets are empty. */
  'hr-workspace',
  'marketing-forms',
  'marketing-diagnostics',
  'acquisition-activity',
  'service-orders',
  'services',
  'invoices',
  'calendar',
  'team-availability',
  'my-availability',
  'time-off',
  'documents',
  'automations',
  'organization',
] as const

export type AppShellSidebarHiddenItemKey = (typeof APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS)[number]
