import { CRM_APP_PATHS } from '../app/crmAppPaths'

/** First URL segment under **`CRM_APP_PATHS.appShellPrefix`** (no query/hash). */
function canonicalWorkShellFirstSegment(canonicalPath: string): string {
  const prefix = `${CRM_APP_PATHS.appShellPrefix}/`
  if (!canonicalPath.startsWith(prefix)) {
    throw new Error(`workShellAlias: expected path under ${prefix}, got ${canonicalPath}`)
  }
  const rest = canonicalPath.slice(prefix.length)
  const first = rest.split('/').filter(Boolean)[0]
  if (!first) throw new Error(`workShellAlias: empty first segment for ${canonicalPath}`)
  return first
}

/**
 * Optional URLs under **`/app/work/...`** that redirect to canonical **`/app/...`** (SSOT §2.13).
 * Derived from **`CRM_APP_PATHS`** so Work shell aliases stay aligned with operational CRM paths.
 */
export const WORK_SHELL_ALIAS_FIRST_SEGMENTS = [
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.candidates),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.clientsDirectory),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.procesowani),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.vacancies),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.leads),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.documents),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.services),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.invoices),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.orders),
  canonicalWorkShellFirstSegment(CRM_APP_PATHS.slaIncidents),
] as const

export function normalizeAppPathSuffix(raw: string): string | null {
  const parts = raw.split('/').filter((p) => p.length > 0)
  if (parts.some((p) => p === '..')) return null
  const cleaned = parts.filter((p) => p !== '.')
  if (cleaned.length === 0) return null
  return cleaned.join('/')
}

export function isWorkShellAliasSuffix(suffix: string): boolean {
  const first = suffix.split('/')[0] || ''
  return (WORK_SHELL_ALIAS_FIRST_SEGMENTS as readonly string[]).includes(first)
}
