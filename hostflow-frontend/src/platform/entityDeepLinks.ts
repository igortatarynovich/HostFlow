/**
 * Stage 6C — canonical entity deep-link resolver.
 * Shared surfaces must not hand-build business `/app/...` URLs.
 */
import registry from '@shared/module_deploy_hosts.json'
import {
  AUTH_HANDOFF_HASH_PREFIX,
  buildModuleAbsoluteUrl,
  type ModuleDeployHost,
} from './deployHosts'

export type EntityDeepLinkKind = keyof typeof registry.entity_deep_links

const ENTITY_DEEP_LINKS = registry.entity_deep_links as Record<
  string,
  { host: ModuleDeployHost; path_template: string }
>
const ENTITY_ALIASES = (registry as { entity_type_aliases?: Record<string, string> }).entity_type_aliases || {}
const QUERY_ALLOWLIST = new Set(
  ((registry as { deep_link_query_allowlist?: string[] }).deep_link_query_allowlist || []).map(String),
)
const SHELL_ENTITY_TYPES = new Set(
  ((registry as { shell_entity_types?: string[] }).shell_entity_types || []).map((s) => s.toLowerCase()),
)
const PRODUCT_HOSTS = new Set(['recruitment', 'hr', 'sales', 'fleet', 'finance'])

export function normalizeEntityType(entityType: string): string | null {
  const raw = String(entityType || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
  if (!raw) return null
  if (SHELL_ENTITY_TYPES.has(raw)) return null
  const aliased = ENTITY_ALIASES[raw]
  if (aliased) return String(aliased).trim().toLowerCase()
  if (ENTITY_DEEP_LINKS[raw]) return raw
  return null
}

export function isShellEntityType(entityType: string): boolean {
  return SHELL_ENTITY_TYPES.has(String(entityType || '').trim().toLowerCase())
}

function filterQuery(params?: Record<string, string | undefined | null>): Record<string, string> {
  const out: Record<string, string> = {}
  if (!params) return out
  for (const [key, value] of Object.entries(params)) {
    if (!QUERY_ALLOWLIST.has(key)) continue
    const v = String(value ?? '').trim()
    if (v) out[key] = v
  }
  return out
}

export type ResolvedEntityDeepLink = {
  entityType: string
  host: ModuleDeployHost
  path: string
  href: string
}

/** Resolve entity → owning module host + canonical path/href. No shell business fallback. */
export function resolveEntityDeepLink(
  entityType: string,
  entityId: string,
  opts?: { query?: Record<string, string | undefined | null> },
): ResolvedEntityDeepLink | null {
  const canon = normalizeEntityType(entityType)
  if (!canon) return null
  const id = String(entityId || '').trim()
  if (!id) return null
  const row = ENTITY_DEEP_LINKS[canon]
  if (!row?.path_template || !PRODUCT_HOSTS.has(row.host)) return null

  let path = row.path_template.replace('{id}', encodeURIComponent(id))
  const url = new URL(path, 'https://hostflow.cc')
  const merged = filterQuery({
    ...Object.fromEntries(url.searchParams.entries()),
    ...(opts?.query || {}),
  })
  url.search = ''
  for (const [k, v] of Object.entries(merged)) url.searchParams.set(k, v)
  const relative = `${url.pathname}${url.search}`
  const href = buildModuleAbsoluteUrl(row.host, relative)
  return { entityType: canon, host: row.host, path: relative, href }
}

/** @deprecated Prefer resolveEntityDeepLink — kept as thin wrapper for existing imports. */
export function buildEntityDeepLink(
  entity: EntityDeepLinkKind | string,
  entityId: string,
  opts?: { search?: string; hash?: string; query?: Record<string, string | undefined | null> },
): string | null {
  let query = opts?.query
  if (!query && opts?.search) {
    const q = opts.search.startsWith('?') ? opts.search.slice(1) : opts.search
    query = Object.fromEntries(new URLSearchParams(q).entries())
  }
  const resolved = resolveEntityDeepLink(entity, entityId, { query })
  if (!resolved) return null
  if (opts?.hash && !opts.hash.includes(AUTH_HANDOFF_HASH_PREFIX)) {
    const h = opts.hash.startsWith('#') ? opts.hash : `#${opts.hash}`
    return `${resolved.href}${h}`
  }
  return resolved.href
}

/**
 * Open an entity deep link: cross-host hard navigation when needed, else in-app navigate.
 * Returns false when the entity type is unknown / not linkable.
 */
export function openEntityDeepLink(
  entityType: string,
  entityId: string,
  opts?: {
    query?: Record<string, string | undefined | null>
    navigate?: (to: string) => void
  },
): boolean {
  const resolved = resolveEntityDeepLink(entityType, entityId, { query: opts?.query })
  if (!resolved) return false
  const href = resolved.href
  if (typeof window !== 'undefined' && /^https?:\/\//i.test(href)) {
    try {
      const target = new URL(href)
      if (target.origin !== window.location.origin) {
        window.location.assign(href)
        return true
      }
      const next = `${target.pathname}${target.search}${target.hash}`
      if (opts?.navigate) opts.navigate(next)
      else window.location.assign(next)
      return true
    } catch {
      /* fall through */
    }
  }
  if (opts?.navigate) opts.navigate(href)
  else if (typeof window !== 'undefined') window.location.assign(href)
  return true
}

/** Rewrite a relative business `/app/...` path through ownership when possible. */
export function rewriteBusinessAppPath(pathAndSearch: string): string | null {
  const raw = String(pathAndSearch || '').trim()
  if (!raw.startsWith('/app')) return null
  const url = new URL(raw, 'https://hostflow.cc')
  const path = url.pathname
  const idMatch = path.match(
    /^\/app\/(?:candidates|vacancies|leads|clients|invoices|hr\/employees|fleet\/vehicles|sales\/inquiries|recruitment\/(?:inbox|searches))\/([^/]+)/,
  )
  if (!idMatch) {
    // service order query form
    if (path === '/app/services' || path === '/app/orders' || path === '/app/service-orders') {
      const orderId = url.searchParams.get('order') || url.searchParams.get('order_id')
      if (orderId) return buildEntityDeepLink('service_order', orderId)
    }
    return null
  }
  const id = decodeURIComponent(idMatch[1])
  if (path.startsWith('/app/candidates/')) return buildEntityDeepLink('candidate', id)
  if (path.startsWith('/app/vacancies/')) return buildEntityDeepLink('vacancy', id)
  if (path.startsWith('/app/leads/')) return buildEntityDeepLink('lead', id)
  if (path.startsWith('/app/clients/')) return buildEntityDeepLink('client_account', id)
  if (path.startsWith('/app/invoices/')) return buildEntityDeepLink('invoice', id)
  if (path.startsWith('/app/hr/employees/')) return buildEntityDeepLink('employee', id)
  if (path.startsWith('/app/fleet/vehicles/')) return buildEntityDeepLink('vehicle', id)
  if (path.startsWith('/app/sales/inquiries/')) return buildEntityDeepLink('inquiry', id)
  if (path.startsWith('/app/recruitment/inbox/')) return buildEntityDeepLink('recruitment_application', id)
  if (path.startsWith('/app/recruitment/searches/')) return buildEntityDeepLink('search', id)
  return null
}

/**
 * Normalize a path/href through the entity registry when it is a business `/app/...` URL.
 * Shell platform paths and unknown shapes pass through unchanged.
 */
export function canonicalizeAppOrModuleHref(href: string): string {
  const raw = String(href || '').trim()
  if (!raw) return raw
  if (/^https?:\/\//i.test(raw)) {
    try {
      const u = new URL(raw)
      const rewritten = rewriteBusinessAppPath(`${u.pathname}${u.search}`)
      if (rewritten) return rewritten
      return raw
    } catch {
      return raw
    }
  }
  return rewriteBusinessAppPath(raw) || raw
}

/**
 * Navigate to a deep link that may be absolute (cross-subdomain) or relative.
 * Relative business `/app/...` paths are rewritten via the entity ownership registry.
 */
export function navigateAppOrModuleLink(
  href: string,
  navigate: (to: string) => void,
): void {
  const raw = canonicalizeAppOrModuleHref(href)
  if (!raw) return
  if (/^https?:\/\//i.test(raw) && typeof window !== 'undefined') {
    try {
      const target = new URL(raw)
      if (target.origin !== window.location.origin) {
        window.location.assign(raw)
        return
      }
      navigate(`${target.pathname}${target.search}${target.hash}`)
      return
    } catch {
      /* fall through */
    }
  }
  navigate(raw)
}
