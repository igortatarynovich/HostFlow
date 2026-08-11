import { CRM_APP_PATHS, recruitmentSearchPath } from '../app/crmAppPaths'
import type { PlatformHandoff } from '../api/platformCompletion'
import { detectStoredLocale, lookupScopedTranslation } from '../i18n'
import { createLaunchSearch } from './createLaunchSearch'
import { persistLaunchSearch } from './launchSearchSession'
import type { SearchRole } from '../utils/launchSearchRoleDefaults'

function fallbackClientName(): string {
  return lookupScopedTranslation(detectStoredLocale(), 'common.labels', 'client') || 'Client'
}

export const SALES_CLIENT_ACTIVE_EVENT = 'sales.client_active'

export type SalesClientActiveContext = {
  client_id: string
  client_name: string
  lead_id?: string
  channel_id?: string
  search_role?: SearchRole | string
}

export type PlatformHandoffResult = {
  /** Route to navigate to after a successful handoff (executor workspace). */
  navigateTo?: string
  /** Informational code when the executor is recognized but not yet available. */
  pending?: string
}

export async function executePlatformHandoff(handoff: PlatformHandoff): Promise<PlatformHandoffResult | null> {
  if (handoff.action === 'recruitment.create_search') {
    const ctx = handoff.context as SalesClientActiveContext
    const clientId = String(ctx.client_id || '').trim()
    if (!clientId) throw new Error('client_id_required')
    const role = (ctx.search_role as SearchRole) || 'driver'
    const created = await createLaunchSearch({
      role,
      target: 'client',
      existingClientId: clientId,
      clientName: String(ctx.client_name || '').trim() || fallbackClientName(),
    })
    persistLaunchSearch(created)
    return { navigateTo: recruitmentSearchPath(created.searchId) }
  }
  if (handoff.action === 'marketing.create_project') {
    // Executor module not wired yet — surfaced as a pluggable handoff on the order line.
    return { pending: 'marketing.create_project' }
  }
  return null
}

export function clientDetailPath(clientId: string): string {
  return `${CRM_APP_PATHS.agencyClients}/${encodeURIComponent(clientId)}`
}
