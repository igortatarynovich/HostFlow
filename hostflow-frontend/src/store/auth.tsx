import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type PropsWithChildren } from 'react'
import { useLocation } from 'react-router-dom'
import { invalidateBillingSubscriptionCache } from '../api/billingSubscriptionCache'
import { invalidateBillingQuotaHeadroomCache } from '../api/billingQuotaHeadroomCache'
import {
  api,
  clearLocalAuthState,
  ensureSharedSessionCookies,
  getStoredAccessToken,
  IMPERSONATION_BACKUP_STORAGE_KEY,
  reconcileBearerWithSharedCookie,
  setToken,
  settings as tenantSettings,
} from '../api/client'
import { getUserMe } from '../api/users'
import type { UserPreferences, UserSecuritySummary, WhoAmI } from '../api/types'
import { bindUserContext } from '../lib/observability'
import { useI18n, type LocaleCode } from '../i18n'
import {
  clearSessionRevoked,
  hasSharedSessionCookieHint,
  isSessionRevoked,
  markSessionRevoked,
  startCrossOriginLogoutBounce,
} from '../platform/sessionLogout'
import { isPlatformSuperadminRole } from '../utils/platformSuperadmin'

const IMPERSONATION_BACKUP_KEY = IMPERSONATION_BACKUP_STORAGE_KEY
export const LOGIN_NOTICE_STORAGE_KEY = 'hf:last-login-notice'
export type LoginNotice = 'expired' | 'invite_accepted' | 'password_reset_success'

export const rememberLoginNotice = (code: LoginNotice) => {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(LOGIN_NOTICE_STORAGE_KEY, code)
  } catch {
    /* ignore storage errors */
  }
}

export const clearLoginNotice = () => {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(LOGIN_NOTICE_STORAGE_KEY)
  } catch {
    /* ignore storage errors */
  }
}

export const consumeLoginNotice = (): LoginNotice | null => {
  if (typeof window === 'undefined') return null
  try {
    const raw = (window.sessionStorage.getItem(LOGIN_NOTICE_STORAGE_KEY) || '').trim()
    clearLoginNotice()
    if (raw === 'expired' || raw === 'invite_accepted' || raw === 'password_reset_success') {
      return raw
    }
    return null
  } catch {
    return null
  }
}

const extractStatus = (error: unknown): number | undefined => {
  const anyErr = error as any
  if (anyErr?.response?.status) {
    return Number(anyErr.response.status)
  }
  if (typeof anyErr?.status === 'number') {
    return anyErr.status
  }
  return undefined
}

const isPublicAuthPath = (path: string): boolean =>
  path === '/login' ||
  path.startsWith('/login/') ||
  path.startsWith('/public') ||
  path.startsWith('/signup') ||
  path.startsWith('/forgot-password') ||
  path.startsWith('/reset-password') ||
  path.startsWith('/invite/accept')

type AuthCtx = {
  me: WhoAmI | null
  preferences: UserPreferences | null
  security: UserSecuritySummary | null
  sessionId: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void | Promise<void>
  refresh: (opts?: { force?: boolean }) => Promise<void>
  updateProfile: (update: Partial<WhoAmI>) => void
  updatePreferences: (prefs: UserPreferences) => void
  updateSecurity: (summary: UserSecuritySummary) => void
  beginImpersonation: () => void
  canReturnToPlatform: boolean
  restorePlatformSession: () => Promise<void>
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const { setLocale } = useI18n()
  const location = useLocation()
  const [me, setMe] = useState<WhoAmI | null>(null)
  const [loading, setLoading] = useState(true)
  const [preferences, setPreferences] = useState<UserPreferences | null>(null)
  const [security, setSecurity] = useState<UserSecuritySummary | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [canReturnToPlatform, setCanReturnToPlatform] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    try {
      return Boolean(window.localStorage.getItem(IMPERSONATION_BACKUP_KEY))
    } catch {
      return false
    }
  })
  const logoutInFlightRef = useRef(false)

  const applyTheme = useCallback((theme?: string | null) => {
    const root = document.documentElement
    const resolved = theme || 'system'
    const prefersDark = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    const forceDark = resolved === 'dark' || (resolved === 'system' && prefersDark)
    root.classList.toggle('dark', forceDark)
  }, [])

  const refresh = useCallback(async (opts?: { force?: boolean }) => {
    // В публичных страницах не тянем auth/whoami, чтобы не ловить 401
    const path = typeof window !== 'undefined' ? window.location.pathname || '' : ''
    const loginWithLiveCookie =
      (path === '/login' || path.startsWith('/login/')) && hasSharedSessionCookieHint()
    if (!opts?.force && isPublicAuthPath(path) && !loginWithLiveCookie) {
      setLoading(false)
      return
    }
    // Explicit logout / wipe bounce must not be rehydrated from leftover cookies.
    if (!opts?.force && (logoutInFlightRef.current || isSessionRevoked())) {
      setLoading(false)
      setMe(null)
      return
    }
    setLoading(true)
    try {
      // Prefer shared Domain cookie over a stale per-origin Bearer (module-host split-brain).
      await reconcileBearerWithSharedCookie()

      // whoami first: on module hosts localStorage (X-Tenant-Id) is empty — seed tenant
      // from JWT before /users/me, otherwise the API falls back to the demo tenant → 403 → logout loop.
      const { data: whoami } = await api.get('/auth/whoami-verify')
      const whoamiTenant = String(whoami?.tenant_id || '').trim()
      if (whoamiTenant) {
        const isPlatformSuperadmin = isPlatformSuperadminRole(whoami?.role)
        const storedTenantId = String(tenantSettings.getStored() || '').trim()
        // Superadmin may keep an explicit workspace override; everyone else follows JWT tenant.
        if (!(isPlatformSuperadmin && storedTenantId && storedTenantId !== whoamiTenant)) {
          tenantSettings.set(whoamiTenant)
        }
      }

      // Shell-only localStorage / host-only cookies cannot authenticate module hosts.
      // Mint Domain=.hostflow.cc cookies before any cross-subdomain navigation.
      try {
        const hostname = typeof window !== 'undefined' ? window.location.hostname : ''
        if (hostname === 'hostflow.cc' || hostname.endsWith('.hostflow.cc')) {
          await ensureSharedSessionCookies()
        }
      } catch {
        // Cookie sync must not block an otherwise valid shell session.
      }

      const meEnvelope = await getUserMe()

      const profile = meEnvelope.profile
      const computedFullName = profile.first_name || profile.last_name
        ? `${profile.first_name ?? ''} ${profile.last_name ?? ''}`.trim()
        : null
      const jwtRole = whoami.role ?? null
      const profileRole = profile.role ?? null
      const effectiveRole =
        isPlatformSuperadminRole(jwtRole) || isPlatformSuperadminRole(profileRole)
          ? 'superadmin'
          : jwtRole || profileRole || null
      const effectiveTenantId = whoami.tenant_id || profile.tenant_id || null
      const resolvedTenantId = effectiveTenantId ?? whoami.tenant_id ?? profile.tenant_id ?? ''
      const merged: WhoAmI = {
        ...whoami,
        session_kind: whoami.session_kind ?? 'normal',
        impersonated_by: whoami.impersonated_by ?? null,
        exp: whoami.exp ?? null,
        sub: profile.user_id ?? whoami.sub,
        email: profile.email ?? whoami.email,
        tenant_id: resolvedTenantId || whoami.tenant_id,
        role: effectiveRole ?? undefined,
        first_name: profile.first_name ?? whoami.first_name,
        last_name: profile.last_name ?? whoami.last_name,
        full_name: computedFullName || whoami.full_name || null,
        birth_date: profile.birth_date ?? whoami.birth_date,
        country: profile.country ?? whoami.country,
        city: profile.city ?? whoami.city,
        position: profile.position ?? whoami.position,
        phone: profile.phone ?? whoami.phone,
        avatar_url: profile.avatar_url ?? whoami.avatar_url,
        signature: profile.signature ?? whoami.signature ?? null,
        preferences: meEnvelope.preferences,
        security: meEnvelope.security,
        is_solo_admin: meEnvelope.is_solo_admin ?? false,
      }

      setMe(merged)
      if (resolvedTenantId) {
        const isPlatformSuperadmin = isPlatformSuperadminRole(effectiveRole)
        const storedTenantId = String(tenantSettings.get() || '').trim()
        // Keep explicit cross-tenant context for platform superadmin instead of
        // snapping back to JWT tenant on each refresh.
        const shouldKeepStoredTenant =
          isPlatformSuperadmin &&
          storedTenantId.length > 0 &&
          storedTenantId !== String(resolvedTenantId)
        tenantSettings.set(shouldKeepStoredTenant ? storedTenantId : String(resolvedTenantId))
      }
      setPreferences(meEnvelope.preferences)
      setSecurity(meEnvelope.security)
      const preferredLocale = String(meEnvelope.preferences?.ui?.locale || '').trim().toLowerCase()
      const shortLocale = preferredLocale.split('-')[0]
      if (shortLocale === 'ru' || shortLocale === 'en' || shortLocale === 'pl') {
        setLocale(shortLocale as LocaleCode)
      }
      applyTheme(meEnvelope.preferences?.ui?.theme)
      clearLoginNotice()
      try {
        bindUserContext({
          userId: merged.sub ? String(merged.sub) : null,
          tenantId: resolvedTenantId ? String(resolvedTenantId) : null,
          email: merged.email ?? null,
        })
      } catch {
        // observability must never break auth
      }
    } catch (err) {
      const status = extractStatus(err)
      console.warn('[Auth] refresh failed', err)
      if (status === 401) {
        rememberLoginNotice('expired')
        clearLocalAuthState()
        setMe(null)
        setPreferences(null)
        setSecurity(null)
        setSessionId(null)
      } else if (status !== 502 && status !== 503) {
        // 502/503: keep session (temporary server/gateway error); other errors: clear
        setMe(null)
        setPreferences(null)
        setSecurity(null)
        setSessionId(null)
      }
    } finally {
      setLoading(false)
    }
  }, [applyTheme, setLocale])

  const login = useCallback(async (email: string, password: string) => {
    try {
      clearSessionRevoked()
      logoutInFlightRef.current = false
      // New login must not inherit another account's tenant / Bearer leftovers.
      clearLocalAuthState()
      const { data } = await api.post('/auth/login', { email, password })
      setToken(data.access_token)
      if (data.session_id) {
        setSessionId(data.session_id)
      }
      const tenantFromLogin = (data as any)?.tenant_id || (data as any)?.user?.tenant_id
      if (tenantFromLogin) {
        tenantSettings.set(String(tenantFromLogin))
      }
      await refresh({ force: true }) // обновит me в общем контексте даже на /signup
      clearLoginNotice()
    } catch (err) {
      clearLocalAuthState()
      throw err
    }
  }, [refresh])

  const logout = useCallback(async () => {
    if (logoutInFlightRef.current) return
    logoutInFlightRef.current = true
    markSessionRevoked()
    invalidateBillingSubscriptionCache()
    invalidateBillingQuotaHeadroomCache()
    setMe(null)
    setPreferences(null)
    setSecurity(null)
    setSessionId(null)
    setCanReturnToPlatform(false)
    applyTheme('system')
    clearLoginNotice()
    try {
      // Stage 6B: revoke refresh + clear Domain=.hostflow.cc cookies.
      await api.post('/auth/logout')
    } catch {
      /* still wipe client state */
    }
    clearLocalAuthState()
    if (typeof window !== 'undefined') {
      window.location.replace(startCrossOriginLogoutBounce())
    }
  }, [applyTheme])

  const beginImpersonation = useCallback(() => {
    if (typeof window === 'undefined') return
    try {
      const previousToken = getStoredAccessToken()
      const previousTenant = tenantSettings.get()
      window.localStorage.setItem(
        IMPERSONATION_BACKUP_KEY,
        JSON.stringify({ token: previousToken, tenant: previousTenant }),
      )
      if (previousToken) {
        setCanReturnToPlatform(true)
      }
    } catch (err) {
      console.warn('[Auth] begin impersonation failed', err)
    }
  }, [])

  const restorePlatformSession = useCallback(async () => {
    if (typeof window === 'undefined') return
    const raw = window.localStorage.getItem(IMPERSONATION_BACKUP_KEY)
    if (!raw) return
    try {
      const backup = JSON.parse(raw) as { token?: string | null; tenant?: string | null }
      setToken(backup.token || null)
      if (backup.tenant) {
        tenantSettings.set(String(backup.tenant))
      }
      try {
        await ensureSharedSessionCookies()
      } catch {
        /* cookie sync best-effort */
      }
      await refresh({ force: true })
      // Drop backup only after a successful restore so a failed refresh can retry.
      window.localStorage.removeItem(IMPERSONATION_BACKUP_KEY)
      setCanReturnToPlatform(false)
    } catch (err) {
      console.warn('[Auth] restore platform session failed', err)
    }
  }, [refresh])

  useEffect(() => {
    const path = location.pathname || ''
    const loginWithLiveCookie =
      (path === '/login' || path.startsWith('/login/')) && hasSharedSessionCookieHint()
    if (isPublicAuthPath(path) && !loginWithLiveCookie) {
      setLoading(false)
      return
    }
    if (logoutInFlightRef.current || isSessionRevoked()) {
      setLoading(false)
      return
    }
    if (!me) {
      void refresh()
    }
  }, [location.pathname, me, refresh])

  const updateProfile = useCallback((update: Partial<WhoAmI>) => {
    setMe((prev) => (prev ? { ...prev, ...update } : prev))
  }, [])

  const updatePreferences = useCallback((prefs: UserPreferences) => {
    setPreferences(prefs)
    setMe((prev) => (prev ? { ...prev, preferences: prefs } : prev))
    applyTheme(prefs.ui?.theme)
  }, [applyTheme])

  const updateSecurity = useCallback((summary: UserSecuritySummary) => {
    setSecurity(summary)
    setMe((prev) => (prev ? { ...prev, security: summary } : prev))
  }, [])

  const value = useMemo(
    () => ({
      me,
      preferences,
      security,
      sessionId,
      loading,
      login,
      logout,
      refresh,
      updateProfile,
      updatePreferences,
      updateSecurity,
      beginImpersonation,
      canReturnToPlatform,
      restorePlatformSession,
    }),
    [
      me,
      preferences,
      security,
      sessionId,
      loading,
      login,
      logout,
      refresh,
      updateProfile,
      updatePreferences,
      updateSecurity,
      beginImpersonation,
      canReturnToPlatform,
      restorePlatformSession,
    ],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
