import type { SearchRole } from './launchSearchRoleDefaults'

export type LaunchSearchVacancyExtra = {
  launch_search?: boolean
  search_role?: SearchRole | string
  lead_form_id?: string
  lead_form_slug?: string
  setup_source?: string
}

export function parseLaunchSearchVacancyExtra(extra: unknown): LaunchSearchVacancyExtra {
  if (!extra || typeof extra !== 'object') return {}
  const row = extra as Record<string, unknown>
  const role = String(row.search_role || '').trim()
  return {
    launch_search: Boolean(row.launch_search),
    search_role: (['driver', 'warehouse', 'office', 'other'].includes(role) ? role : undefined) as
      | SearchRole
      | undefined,
    lead_form_id: String(row.lead_form_id || '').trim() || undefined,
    lead_form_slug: String(row.lead_form_slug || '').trim() || undefined,
    setup_source: String(row.setup_source || '').trim() || undefined,
  }
}
