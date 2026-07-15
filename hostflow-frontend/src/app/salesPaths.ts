import { CRM_APP_PATHS } from './crmAppPaths'

/** Channel-independent Sales entry ("Что дальше" + work session over company inquiries). */
export const SALES_HOME_PATH = `${CRM_APP_PATHS.appShellPrefix}/sales`

/** Channel-independent inquiry work card path. */
export function salesInquiryPath(leadId: string): string {
  return `${SALES_HOME_PATH}/inquiries/${encodeURIComponent(leadId)}`
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
