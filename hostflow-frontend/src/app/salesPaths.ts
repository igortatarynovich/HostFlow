import { buildEntityDeepLink } from '../platform/entityDeepLinks'
import { CRM_APP_PATHS } from './crmAppPaths'

/**
 * In-app Sales entry path (relative). Cross-host absolute URLs are produced by
 * `withDeployAwareNavPaths` / `buildModuleAbsoluteUrl` — do not pre-absolutize here
 * or nav links become `https://sales.../https://sales.../app/sales`.
 */
export const SALES_HOME_PATH = `${CRM_APP_PATHS.appShellPrefix}/sales`

/** Channel-independent inquiry work card path — Stage 6C resolver. */
export function salesInquiryPath(leadId: string): string {
  return buildEntityDeepLink('inquiry', leadId) || `${SALES_HOME_PATH}/inquiries/${encodeURIComponent(leadId)}`
}

/** Client account card on Sales host. */
export function clientDetailPath(clientId: string): string {
  return buildEntityDeepLink('client_account', clientId) || `${CRM_APP_PATHS.appShellPrefix}/clients/${encodeURIComponent(clientId)}`
}

/** Parse a leadId out of a channel-independent Sales inquiry path. */
export function parseSalesHomeInquiryLeadId(pathname: string): string | null {
  const marker = '/sales/inquiries/'
  const idx = pathname.indexOf(marker)
  if (idx < 0) return null
  const rest = pathname.slice(idx + marker.length)
  const id = rest.split('/')[0]?.split('?')[0]
  return id || null
}
