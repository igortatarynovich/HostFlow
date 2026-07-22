/**
 * Deployment / URL Boundaries — Stage 6A/6B Module Host Runtime (ADR-023 §3.7).
 *
 * SSOT: `shared/module_deploy_hosts.json`
 * Entity deep links: `platform/entityDeepLinks.ts` (Stage 6C).
 */
import registry from '@shared/module_deploy_hosts.json'

export type ModuleDeployHost =
  | 'shell'
  | 'recruitment'
  | 'hr'
  | 'sales'
  | 'fleet'
  | 'finance'

export const DEPLOYMENT_HOSTS = registry.hosts as Record<ModuleDeployHost, string>
export const BUSINESS_MODULE_HOSTS = registry.business_modules as readonly ModuleDeployHost[]
export const APEX_DOMAIN = registry.apex_domain
export const COOKIE_DOMAIN = registry.cookie_domain

export const NAV_KEY_TO_DEPLOY_HOST = registry.nav_key_to_host as Record<string, ModuleDeployHost>
export const APP_PATH_PREFIX_TO_DEPLOY_HOST = registry.app_path_prefixes as ReadonlyArray<{
  prefix: string
  host: ModuleDeployHost
}>
export const SHELL_SHARED_NAV_KEYS = new Set(registry.shell_shared_nav_keys)
export const SHELL_PLATFORM_PATH_PREFIXES = registry.shell_platform_path_prefixes as readonly string[]

const MODULE_HOME_PATH = registry.module_home_paths as Record<ModuleDeployHost, string>
const HOST_TO_MODULE: Record<string, ModuleDeployHost> = Object.fromEntries(
  Object.entries(DEPLOYMENT_HOSTS).map(([module, host]) => [host.toLowerCase(), module as ModuleDeployHost]),
)

/** @deprecated Stage 6B removed hash handoff — status kept for integrity tests. */
export const AUTH_HANDOFF_HASH_PREFIX = registry.auth_handoff.hash_prefix
export const AUTH_HANDOFF_STATUS = registry.auth_handoff.status
export const SESSION_COOKIE_NAMES = (registry as { session_cookies?: Record<string, string> }).session_cookies || {
  access: 'hf_access',
  refresh: 'hf_refresh',
  csrf: 'hf_csrf',
}

function normalizeHostname(hostname: string): string {
  return hostname.trim().toLowerCase().replace(/\.$/, '')
}

function parseModuleOverride(raw: string | null | undefined): ModuleDeployHost | null {
  const v = String(raw || '')
    .trim()
    .toLowerCase()
  if (!v) return null
  if ((BUSINESS_MODULE_HOSTS as readonly string[]).includes(v) || v === 'shell') {
    return v as ModuleDeployHost
  }
  return null
}

export function resolveDeployHost(opts?: {
  hostname?: string
  search?: string
  envModuleHost?: string | undefined
}): ModuleDeployHost {
  const search =
    opts?.search ?? (typeof window !== 'undefined' ? window.location.search : undefined)
  const fromQuery = parseModuleOverride(
    search ? new URLSearchParams(search.startsWith('?') ? search : `?${search}`).get('hf_module') : null,
  )
  if (fromQuery) return fromQuery

  const fromEnv = parseModuleOverride(opts?.envModuleHost ?? import.meta.env.VITE_MODULE_HOST)
  if (fromEnv) return fromEnv

  const hostname = normalizeHostname(
    opts?.hostname ?? (typeof window !== 'undefined' ? window.location.hostname : 'localhost'),
  )
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.endsWith('.local')) {
    return 'shell'
  }

  const bare = hostname.startsWith('www.') ? hostname.slice(4) : hostname
  if (HOST_TO_MODULE[bare]) return HOST_TO_MODULE[bare]

  for (const module of BUSINESS_MODULE_HOSTS) {
    if (bare.startsWith(`${module}.`)) return module
  }

  // Unknown *.hostflow.cc → shell, never invent a business module context.
  if (bare === APEX_DOMAIN || bare.endsWith(`.${APEX_DOMAIN}`)) return 'shell'
  return 'shell'
}

export function isShellDeployHost(host: ModuleDeployHost = resolveDeployHost()): boolean {
  return host === 'shell'
}

export function deployHostPublicOrigin(host: ModuleDeployHost, opts?: { protocol?: string }): string {
  const protocol = opts?.protocol ?? (typeof window !== 'undefined' ? window.location.protocol : 'https:')
  if (typeof window !== 'undefined') {
    const hn = normalizeHostname(window.location.hostname)
    if (hn === 'localhost' || hn === '127.0.0.1' || hn.endsWith('.local')) {
      return window.location.origin
    }
  }
  return `${protocol}//${DEPLOYMENT_HOSTS[host]}`
}

export function moduleHomePath(host: ModuleDeployHost): string {
  return MODULE_HOME_PATH[host] || '/app/overview'
}

export function resolvePathDeployHost(pathname: string): ModuleDeployHost | null {
  const path = pathname.split('?')[0] || ''
  if (!path.startsWith('/app')) return null
  const ranked = [...APP_PATH_PREFIX_TO_DEPLOY_HOST].sort((a, b) => b.prefix.length - a.prefix.length)
  for (const { prefix, host } of ranked) {
    if (path === prefix || path.startsWith(`${prefix}/`)) return host
  }
  // Shell platform prefixes
  for (const prefix of SHELL_PLATFORM_PATH_PREFIXES) {
    if (path === prefix || path.startsWith(`${prefix}/`)) return 'shell'
  }
  return 'shell'
}

/** True when path is a shell/platform surface (not a business-object workspace). */
export function isShellPlatformPath(pathname: string): boolean {
  const owner = resolvePathDeployHost(pathname)
  return owner === 'shell'
}

export function isNavKeyAllowedOnHost(navKey: string, host: ModuleDeployHost): boolean {
  if (SHELL_SHARED_NAV_KEYS.has(navKey)) return true
  const owner = NAV_KEY_TO_DEPLOY_HOST[navKey]
  if (!owner) return host === 'shell'
  // Every deploy host shows the full licensed business nav; foreign modules are
  // rewritten to absolute module-host URLs (same launcher pattern as shell).
  // Isolation is Stage 2B entitlement/API gates — not by hiding sibling modules.
  return true
}

export function filterNavItemsForDeployHost<T extends { key: string }>(
  items: T[],
  host: ModuleDeployHost = resolveDeployHost(),
): T[] {
  return items.filter((item) => isNavKeyAllowedOnHost(item.key, host))
}

/**
 * Rewrite foreign business nav paths to absolute module-host URLs (cross-host launcher).
 * Same-origin local emulation keeps path + hf_module.
 */
export function withDeployAwareNavPaths<T extends { key: string; path?: string }>(
  items: T[],
  host: ModuleDeployHost = resolveDeployHost(),
): T[] {
  return items.map((item) => {
    if (!item.path) return item
    const owner = NAV_KEY_TO_DEPLOY_HOST[item.key]
    if (!owner) return item
    // Platform / shell-owned surfaces (e.g. Marketing) must hard-link to hostflow.cc
    // when the operator is on a business module host.
    if (owner === 'shell') {
      if (host === 'shell') return item
      return { ...item, path: buildModuleAbsoluteUrl('shell', item.path) }
    }
    if (host === 'shell' || host !== owner) {
      return { ...item, path: buildModuleAbsoluteUrl(owner, item.path) }
    }
    // Already on owning host: keep a relative path even if the item was pre-absolutized.
    if (/^https?:\/\//i.test(item.path)) {
      try {
        const u = new URL(item.path)
        return { ...item, path: `${u.pathname}${u.search}${u.hash}` }
      } catch {
        return item
      }
    }
    return item
  })
}

export function buildModuleAbsoluteUrl(
  host: ModuleDeployHost,
  pathAndSearch: string,
  opts?: { preserveHash?: boolean },
): string {
  const raw = (pathAndSearch || '').trim()
  // Idempotent: never turn an absolute URL into origin + "/https://..."
  if (/^https?:\/\//i.test(raw)) {
    try {
      const u = new URL(raw)
      return buildModuleAbsoluteUrl(host, `${u.pathname}${u.search}${u.hash}`, opts)
    } catch {
      return raw
    }
  }

  const origin = deployHostPublicOrigin(host)
  const path = raw.startsWith('/') ? raw : `/${raw}`
  const currentOrigin = typeof window !== 'undefined' ? window.location.origin : null
  // Same-origin (local emulation or already on target host): keep relative path.
  // When `window` is absent (SSR/tests), always emit the absolute registry URL.
  if (currentOrigin && origin === currentOrigin) {
    if (host !== 'shell') {
      const url = new URL(path, origin)
      if (!url.searchParams.get('hf_module')) url.searchParams.set('hf_module', host)
      if (!opts?.preserveHash) {
        // Strip temporary auth hash when building normal deep links.
        if (url.hash.startsWith(`#${AUTH_HANDOFF_HASH_PREFIX}`)) url.hash = ''
      }
      return `${url.pathname}${url.search}${url.hash}`
    }
    return path
  }
  return `${origin}${path}`
}

export function shellLoginUrl(nextAbsoluteOrPath: string): string {
  const next = nextAbsoluteOrPath
  if (typeof window !== 'undefined') {
    const hn = normalizeHostname(window.location.hostname)
    if (hn === 'localhost' || hn === '127.0.0.1' || hn.endsWith('.local')) {
      const local = new URL('/login', window.location.origin)
      local.searchParams.set('next', next)
      return `${local.pathname}${local.search}`
    }
  }
  const url = new URL(`https://${DEPLOYMENT_HOSTS.shell}/login`)
  url.protocol = typeof window !== 'undefined' ? window.location.protocol : 'https:'
  url.searchParams.set('next', next)
  return url.toString()
}

/**
 * Stage 6B: hash auth handoff removed. Shared cookie session on .hostflow.cc.
 * Kept as no-ops only so accidental imports fail closed (never put tokens in the URL).
 */
export function withAuthHandoffHash(targetUrl: string, _token?: string): string {
  // Strip any legacy auth fragment if present.
  try {
    const url = new URL(targetUrl, typeof window !== 'undefined' ? window.location.origin : `https://${APEX_DOMAIN}`)
    if (url.hash.startsWith(`#${AUTH_HANDOFF_HASH_PREFIX}`)) url.hash = ''
    return url.toString()
  } catch {
    return targetUrl
  }
}

/** Stage 6B: hash handoff removed — always null. */
export function consumeAuthHandoffHash(_hash?: string): string | null {
  return null
}

const PRODUCTION_ALLOWED_NEXT_HOSTS = new Set<string>([
  ...Object.values(DEPLOYMENT_HOSTS).map((h) => h.toLowerCase()),
  `www.${APEX_DOMAIN}`,
])

function queryValuesAreAllowedNextTargets(url: URL, opts?: { allowLocalhost?: boolean }): boolean {
  for (const value of url.searchParams.values()) {
    const v = value.trim()
    if (!v) continue
    if (v.startsWith('//') || /^https?:\/\//i.test(v)) {
      if (!isAllowedHandoffNext(v, opts)) return false
    }
  }
  return true
}

/**
 * Strict open-redirect guard for login `?next=`.
 * Allows only registry hosts; rejects protocol-relative, credentials, exotic ports,
 * and nested absolute URLs in the query that point outside the allowlist.
 */
export function isAllowedHandoffNext(
  nextUrl: string,
  opts?: { allowLocalhost?: boolean },
): boolean {
  const raw = (nextUrl || '').trim()
  if (!raw) return false
  if (raw.startsWith('//') || raw.includes('\\')) return false

  // Relative path on current origin
  if (raw.startsWith('/') && !raw.startsWith('//')) {
    if (raw.includes('://')) return false
    try {
      const asUrl = new URL(raw, `https://${DEPLOYMENT_HOSTS.shell}`)
      return queryValuesAreAllowedNextTargets(asUrl, opts)
    } catch {
      return false
    }
  }

  let url: URL
  try {
    url = new URL(raw)
  } catch {
    return false
  }

  if (url.protocol !== 'http:' && url.protocol !== 'https:') return false
  if (url.username || url.password) return false

  const host = normalizeHostname(url.hostname)
  const allowLocal = opts?.allowLocalhost ?? true
  if (host === 'localhost' || host === '127.0.0.1') {
    return allowLocal && queryValuesAreAllowedNextTargets(url, opts)
  }

  if (!PRODUCTION_ALLOWED_NEXT_HOSTS.has(host)) return false

  // Production hosts: only default ports
  if (url.port && url.port !== '80' && url.port !== '443') return false

  return queryValuesAreAllowedNextTargets(url, opts)
}

/** Preserve path/query/fragment for cross-host redirect, but never carry `#hf_auth=`. */
export function locationTargetWithoutAuthHash(pathname: string, search: string, hash: string): string {
  const h = hash.startsWith('#') ? hash.slice(1) : hash
  const safeHash = h.startsWith(AUTH_HANDOFF_HASH_PREFIX) ? '' : hash
  return `${pathname}${search}${safeHash}`
}

export function listRegistryHostsForProxy(): string[] {
  return [
    DEPLOYMENT_HOSTS.shell,
    `www.${APEX_DOMAIN}`,
    ...BUSINESS_MODULE_HOSTS.map((m) => DEPLOYMENT_HOSTS[m]),
  ]
}
