import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AUTH_ISOLATION_WIPE_STORAGE_KEY,
  applyAuthIsolationWipeOnce,
  clearLocalAuthState,
  decodeJwtPayload,
  getStoredAccessToken,
  setToken,
  settings,
} from '../../api/client'
import {
  LOGOUT_HOSTS_QUERY,
  LOGOUT_QUERY,
  LOGOUT_RETURN_QUERY,
  SESSION_REVOKED_KEY,
  clearSessionRevoked,
  consumeLogoutWipeAndContinue,
  isSessionRevoked,
  markSessionRevoked,
  remainingLogoutWipeHosts,
  startCrossOriginLogoutBounce,
} from '../sessionLogout'

function b64url(json: object): string {
  const raw = btoa(JSON.stringify(json))
  return raw.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function fakeJwt(claims: object): string {
  return `hdr.${b64url(claims)}.sig`
}

describe('clearLocalAuthState / setToken', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('clears every token and tenant alias used by clients', () => {
    localStorage.setItem('access_token', 'a')
    localStorage.setItem('token', 'a')
    localStorage.setItem('accessToken', 'a')
    localStorage.setItem('auth_token', 'a')
    localStorage.setItem('jwt', 'a')
    localStorage.setItem('Authorization', 'Bearer a')
    localStorage.setItem('tenant_id', 'tenant-a')
    localStorage.setItem('X-Tenant-Id', 'tenant-a')
    localStorage.setItem('x-tenant-id', 'tenant-a')
    localStorage.setItem('tenant', 'tenant-a')
    localStorage.setItem('hf_own_company_id', '11111111-1111-1111-1111-111111111111')
    localStorage.setItem('hf:platform-session-backup', '{}')

    clearLocalAuthState()

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('accessToken')).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('jwt')).toBeNull()
    expect(localStorage.getItem('Authorization')).toBeNull()
    expect(localStorage.getItem('tenant_id')).toBeNull()
    expect(localStorage.getItem('X-Tenant-Id')).toBeNull()
    expect(localStorage.getItem('x-tenant-id')).toBeNull()
    expect(localStorage.getItem('tenant')).toBeNull()
    expect(localStorage.getItem('hf_own_company_id')).toBeNull()
    expect(localStorage.getItem('hf:platform-session-backup')).toBeNull()
    expect(settings.getStored()).toBeNull()
  })

  it('setToken(null) clears alias keys that logout used to leave behind', () => {
    localStorage.setItem('access_token', 'a')
    localStorage.setItem('token', 'a')
    localStorage.setItem('auth_token', 'stale')
    localStorage.setItem('jwt', 'stale')
    setToken(null)
    expect(getStoredAccessToken()).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(localStorage.getItem('jwt')).toBeNull()
  })

  it('applyAuthIsolationWipeOnce clears stale LS once then no-ops', () => {
    localStorage.setItem('access_token', 'stale-bearer')
    localStorage.setItem('tenant_id', 'old-tenant')
    expect(applyAuthIsolationWipeOnce()).toBe(true)
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('tenant_id')).toBeNull()
    expect(localStorage.getItem(AUTH_ISOLATION_WIPE_STORAGE_KEY)).toBe('1')
    localStorage.setItem('access_token', 'after-wipe')
    expect(applyAuthIsolationWipeOnce()).toBe(false)
    expect(localStorage.getItem('access_token')).toBe('after-wipe')
  })
})

describe('decodeJwtPayload', () => {
  it('reads sub/email/tenant_id without verification', () => {
    const token = fakeJwt({
      sub: 'user-1',
      email: 'a@example.com',
      tenant_id: 'tenant-1',
    })
    expect(decodeJwtPayload(token)).toMatchObject({
      sub: 'user-1',
      email: 'a@example.com',
      tenant_id: 'tenant-1',
    })
  })
})

describe('sessionLogout wipe chain', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.unstubAllGlobals()
  })

  it('marks and clears session revoked flag', () => {
    expect(isSessionRevoked()).toBe(false)
    markSessionRevoked()
    expect(sessionStorage.getItem(SESSION_REVOKED_KEY)).toBe('1')
    expect(isSessionRevoked()).toBe(true)
    clearSessionRevoked()
    expect(isSessionRevoked()).toBe(false)
  })

  it('sticky revoke on shell blocks cookie rehydrate until login clears it', () => {
    // Regression: Logout on shell → landing must not rehydrate from Domain cookies.
    // Module hosts may heal when cookies prove a fresh shell login (originating module
    // is excluded from the wipe chain and can retain a leftover revoke flag).
    markSessionRevoked()
    expect(isSessionRevoked()).toBe(true)
    expect(sessionStorage.getItem(SESSION_REVOKED_KEY)).toBe('1')
    clearSessionRevoked()
    expect(isSessionRevoked()).toBe(false)
  })

  it('remainingLogoutWipeHosts excludes the current host', () => {
    const remaining = remainingLogoutWipeHosts('recruitment')
    expect(remaining).not.toContain('recruitment')
    expect(remaining[0]).toBe('shell')
    expect(remaining).toContain('sales')
  })

  it('startCrossOriginLogoutBounce stays on localhost in local dev', () => {
    vi.stubGlobal('location', {
      hostname: 'localhost',
      origin: 'http://localhost:5173',
      protocol: 'http:',
      href: 'http://localhost:5173/app',
      search: '',
    })
    expect(startCrossOriginLogoutBounce()).toBe('http://localhost:5173/login')
  })

  it('consumeLogoutWipeAndContinue clears LS and follows the host chain', () => {
    localStorage.setItem('access_token', 'stale-bearer')
    localStorage.setItem('tenant_id', 'stale-tenant')

    const replace = vi.fn()
    vi.stubGlobal('location', {
      hostname: 'recruitment.hostflow.cc',
      origin: 'https://recruitment.hostflow.cc',
      protocol: 'https:',
      href: 'https://recruitment.hostflow.cc/login?hf_logout=1&hf_logout_hosts=hr,shell&hf_logout_return=https%3A%2F%2Fhostflow.cc%2Flogin',
      search:
        '?hf_logout=1&hf_logout_hosts=hr,shell&hf_logout_return=https%3A%2F%2Fhostflow.cc%2Flogin',
      replace,
    })

    const redirected = consumeLogoutWipeAndContinue()
    expect(redirected).toBe(true)
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('tenant_id')).toBeNull()
    // Intermediate wipe hops must not leave a sticky revoke (blocks later module login).
    expect(isSessionRevoked()).toBe(false)
    expect(replace).toHaveBeenCalledTimes(1)
    const nextUrl = String(replace.mock.calls[0][0])
    expect(nextUrl).toContain('https://hr.hostflow.cc/login')
    expect(nextUrl).toContain(`${LOGOUT_QUERY}=1`)
    expect(nextUrl).toContain(`${LOGOUT_HOSTS_QUERY}=shell`)
    expect(nextUrl).toContain(LOGOUT_RETURN_QUERY)
  })

  it('consumeLogoutWipeAndContinue finishes on return URL when chain is empty', () => {
    const replace = vi.fn()
    vi.stubGlobal('location', {
      hostname: 'sales.hostflow.cc',
      origin: 'https://sales.hostflow.cc',
      protocol: 'https:',
      href: 'https://sales.hostflow.cc/login?hf_logout=1&hf_logout_return=https%3A%2F%2Fhostflow.cc%2Flogin',
      search: '?hf_logout=1&hf_logout_return=https%3A%2F%2Fhostflow.cc%2Flogin',
      replace,
    })

    expect(consumeLogoutWipeAndContinue()).toBe(true)
    expect(replace).toHaveBeenCalledWith('https://hostflow.cc/login')
  })

  it('rejects external hf_logout_return and falls back to shell login', () => {
    const replace = vi.fn()
    vi.stubGlobal('location', {
      hostname: 'sales.hostflow.cc',
      origin: 'https://sales.hostflow.cc',
      protocol: 'https:',
      href: 'https://sales.hostflow.cc/login?hf_logout=1&hf_logout_return=https%3A%2F%2Fevil.example%2Fphish',
      search: '?hf_logout=1&hf_logout_return=https%3A%2F%2Fevil.example%2Fphish',
      replace,
    })

    expect(consumeLogoutWipeAndContinue()).toBe(true)
    expect(replace).toHaveBeenCalledWith('https://hostflow.cc/login')
  })
})
