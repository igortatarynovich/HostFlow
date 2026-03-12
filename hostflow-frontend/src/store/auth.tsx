import { createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { useLocation } from 'react-router-dom'
import { api, setToken, settings as tenantSettings } from '../api/client'
import { getUserMe } from '../api/users'
import type { UserPreferences, UserSecuritySummary, WhoAmI } from '../api/types'

const IMPERSONATION_BACKUP_KEY = 'hf:platform-session-backup'
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
  logout: () => void
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
    if (!opts?.force && isPublicAuthPath(path)) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const [{ data: whoami }, meEnvelope] = await Promise.all([
        api.get('/auth/whoami-verify'),
        getUserMe(),
      ])

      const profile = meEnvelope.profile
      const computedFullName = profile.first_name || profile.last_name
        ? `${profile.first_name ?? ''} ${profile.last_name ?? ''}`.trim()
        : null
      const effectiveRole = whoami.role || profile.role || null
      const effectiveTenantId = whoami.tenant_id || profile.tenant_id || null
      const resolvedTenantId = effectiveTenantId ?? whoami.tenant_id ?? profile.tenant_id ?? ''
      const merged: WhoAmI = {
        ...whoami,
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
        preferences: meEnvelope.preferences,
        security: meEnvelope.security,
      }

      setMe(merged)
      if (resolvedTenantId) {
        tenantSettings.set(String(resolvedTenantId))
      }
      setPreferences(meEnvelope.preferences)
      setSecurity(meEnvelope.security)
      applyTheme(meEnvelope.preferences?.ui?.theme)
      clearLoginNotice()
    } catch (err) {
      const status = extractStatus(err)
      console.warn('[Auth] refresh failed', err)
      if (status === 401) {
        rememberLoginNotice('expired')
        setToken(null)
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
  }, [applyTheme])

  const login = useCallback(async (email: string, password: string) => {
    try {
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
      setToken(null)
      throw err
    }
  }, [refresh])

  const logout = useCallback(() => {
    setToken(null)
    setMe(null)
    setPreferences(null)
    setSecurity(null)
    setSessionId(null)
    applyTheme('system')
    clearLoginNotice()
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.removeItem(IMPERSONATION_BACKUP_KEY)
      } catch {}
    }
    setCanReturnToPlatform(false)
  }, [applyTheme])

  const beginImpersonation = useCallback(() => {
    if (typeof window === 'undefined') return
    try {
      const previousToken =
        window.localStorage.getItem('access_token') ||
        window.localStorage.getItem('token') ||
        null
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
      window.localStorage.removeItem(IMPERSONATION_BACKUP_KEY)
      setCanReturnToPlatform(false)
      await refresh()
    } catch (err) {
      console.warn('[Auth] restore platform session failed', err)
    }
  }, [refresh])

  useEffect(() => {
    const path = location.pathname || ''
    if (isPublicAuthPath(path)) {
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
