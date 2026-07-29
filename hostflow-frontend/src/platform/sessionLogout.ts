/**
 * Cross-origin session wipe for Stage 6B module hosts.
 *
 * Cookies are shared on `.hostflow.cc`, but Bearer tokens live in per-origin
 * localStorage. Logout must clear every module host origin or a leftover Bearer
 * wins over the cleared cookie on the next hard navigation.
 */
import { clearLocalAuthState } from '../api/client'
import {
  BUSINESS_MODULE_HOSTS,
  DEPLOYMENT_HOSTS,
  SYSTEM_MODULE_HOSTS,
  deployHostPublicOrigin,
  isAllowedHandoffNext,
  resolveDeployHost,
  type ModuleDeployHost,
} from './deployHosts'

export const SESSION_REVOKED_KEY = 'hf:session_revoked'
export const LOGOUT_QUERY = 'hf_logout'
export const LOGOUT_HOSTS_QUERY = 'hf_logout_hosts'
export const LOGOUT_RETURN_QUERY = 'hf_logout_return'

function normalizeHostname(hostname: string): string {
  return hostname.trim().toLowerCase().replace(/\.$/, '')
}

function isLocalDevHost(hostname?: string): boolean {
  const hn = normalizeHostname(
    hostname ?? (typeof window !== 'undefined' ? window.location.hostname : 'localhost'),
  )
  return hn === 'localhost' || hn === '127.0.0.1' || hn.endsWith('.local')
}

export function markSessionRevoked(): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(SESSION_REVOKED_KEY, '1')
  } catch {
    /* ignore */
  }
}

export function clearSessionRevoked(): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(SESSION_REVOKED_KEY)
  } catch {
    /* ignore */
  }
}

export function isSessionRevoked(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.sessionStorage.getItem(SESSION_REVOKED_KEY) === '1'
  } catch {
    return false
  }
}

function shellLoginAbsoluteUrl(): string {
  if (typeof window === 'undefined') {
    return `https://${DEPLOYMENT_HOSTS.shell}/login`
  }
  if (isLocalDevHost()) {
    return `${window.location.origin}/login`
  }
  const protocol = window.location.protocol || 'https:'
  return `${protocol}//${DEPLOYMENT_HOSTS.shell}/login`
}

function resolveLogoutReturnUrl(raw: string | null | undefined): string {
  const candidate = (raw || '').trim()
  if (candidate && isAllowedHandoffNext(candidate, { allowLocalhost: true })) {
    // Relative paths are allowlisted for login next=; logout return must be absolute
    // module/shell hosts only (or localhost in local emulation).
    if (candidate.startsWith('/') && !candidate.startsWith('//')) {
      if (isLocalDevHost()) {
        return `${window.location.origin}${candidate.startsWith('/login') ? candidate : '/login'}`
      }
      return shellLoginAbsoluteUrl()
    }
    return candidate
  }
  return shellLoginAbsoluteUrl()
}

/** Hosts whose per-origin localStorage must be wiped (current host first-caller clears itself). */
export function remainingLogoutWipeHosts(currentHost?: ModuleDeployHost): ModuleDeployHost[] {
  const current = currentHost ?? resolveDeployHost()
  const ordered: ModuleDeployHost[] = ['shell', ...SYSTEM_MODULE_HOSTS, ...BUSINESS_MODULE_HOSTS]
  return ordered.filter((host) => host !== current)
}

/**
 * After local logout + cookie clear: bounce through sibling module origins to wipe LS,
 * then land on shell /login.
 */
export function startCrossOriginLogoutBounce(): string {
  if (typeof window === 'undefined') return '/login'
  if (isLocalDevHost()) {
    return `${window.location.origin}/login`
  }

  const returnTo = shellLoginAbsoluteUrl()
  const remaining = remainingLogoutWipeHosts()
  if (remaining.length === 0) {
    return returnTo
  }

  const [nextHost, ...rest] = remaining
  const url = new URL('/login', deployHostPublicOrigin(nextHost))
  url.searchParams.set(LOGOUT_QUERY, '1')
  if (rest.length > 0) {
    url.searchParams.set(LOGOUT_HOSTS_QUERY, rest.join(','))
  }
  url.searchParams.set(LOGOUT_RETURN_QUERY, returnTo)
  return url.toString()
}

/**
 * Run before React boot. Clears this origin's auth LS and continues the wipe chain.
 * Returns true when a redirect was scheduled (caller must not mount the app).
 */
export function consumeLogoutWipeAndContinue(): boolean {
  if (typeof window === 'undefined') return false

  const params = new URLSearchParams(window.location.search)
  if (params.get(LOGOUT_QUERY) !== '1') return false

  markSessionRevoked()
  clearLocalAuthState()

  const returnTo = resolveLogoutReturnUrl(params.get(LOGOUT_RETURN_QUERY))
  const hostsRaw = (params.get(LOGOUT_HOSTS_QUERY) || '').trim()
  const hosts = hostsRaw
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean) as ModuleDeployHost[]

  if (hosts.length === 0) {
    window.location.replace(returnTo)
    return true
  }

  const [nextHost, ...rest] = hosts
  const known = nextHost in DEPLOYMENT_HOSTS
  if (!known) {
    window.location.replace(returnTo)
    return true
  }

  const url = new URL('/login', deployHostPublicOrigin(nextHost))
  url.searchParams.set(LOGOUT_QUERY, '1')
  if (rest.length > 0) {
    url.searchParams.set(LOGOUT_HOSTS_QUERY, rest.join(','))
  }
  url.searchParams.set(LOGOUT_RETURN_QUERY, returnTo)
  window.location.replace(url.toString())
  return true
}
