/**
 * Single place for App shell navigation policy (sidebar rail vs hubs).
 * Items stay in NAV_ITEMS for breadcrumbs / deep links; rail stays short and sectioned.
 */
export const APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS = [
  /** §2.14: primary entry via Candidates + queue param / dashboard. */
  'candidates-no-next-action',
  'sla-incidents',
  /** Operator diagnostics — Automations hub / direct URL. */
  'command-audit',
  /** Team detail — Settings landing + Settings chrome only. */
  'settings-users',
] as const

export type AppShellSidebarHiddenItemKey = (typeof APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS)[number]
