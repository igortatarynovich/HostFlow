/**
 * App shell navigation policy: items hidden from the primary sidebar rail (still in NAV_ITEMS for deep links).
 * Bucket order and hub/standalone keys live in `sidebarRailBuckets.ts` (guarded by `sidebarNavIntegrity` test).
 */
export const APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS = [
  /** UI Constitution v1: Lead is internal — not a primary CRM surface. */
  'leads',
  /** Activation home — entry via AppShell redirect, not primary rail. */
  'launchpad',
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
] as const

export type AppShellSidebarHiddenItemKey = (typeof APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS)[number]
