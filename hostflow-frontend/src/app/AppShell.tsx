import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { TenantRecord, WhoAmI } from '../api/types'
import { getCurrentTenant } from '../api/tenants'
import { getOnboardingStatus, settings, type OnboardingStatus } from '../api/client'
import { setTenantId } from '../api/http'
import { CurrentTenantProvider } from '../contexts/CurrentTenant'
import { TenantInfoProvider } from '../contexts/TenantInfo'
import type { NavItem } from './routes'
import { Sidebar } from '../components/nav/Sidebar'
import { Topbar } from '../components/nav/Topbar'
import { SettingsChrome } from '../components/nav/SettingsChrome'
import { LicenseExpiredBanner } from '../components/LicenseExpiredBanner'
import { TrialStatusBanner } from '../components/TrialStatusBanner'
import { usePendingHandoffsCount } from '../hooks/usePendingHandoffsCount'
import { useLicenseStatus } from '../hooks/useLicenseStatus'

type AppShellProps = {
  me: WhoAmI | null
  navItems: NavItem[]
  onLogout: () => void
}

export function AppShell({ me, navItems, onLogout }: AppShellProps) {
  const location = useLocation()
  const isOnboardingPage = location.pathname.startsWith('/app/onboarding/')
  const isSettingsArea = location.pathname.startsWith('/app/settings')
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null)

  const pendingHandoffsCount = usePendingHandoffsCount()
  const { expired: licenseExpired, validUntil } = useLicenseStatus()
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    try {
      const stored = window.localStorage.getItem('hf:ui:sidebar-open')
      if (stored === '1') return true
      if (stored === '0') return false
    } catch {
      // ignore access issues
    }
    return false
  })
  const [tenant, setTenant] = useState<TenantRecord | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.setItem('hf:ui:sidebar-open', sidebarOpen ? '1' : '0')
    } catch {
      // ignore
    }
  }, [sidebarOpen])

  // Sync X-Tenant-Id from JWT as soon as me is available so list/analytics use correct tenant before getCurrentTenant() resolves
  useEffect(() => {
    const id = me?.tenant_id ? String(me.tenant_id).trim() : ''
    if (id) {
      settings.set(id)
      setTenantId(id)
    }
  }, [me?.tenant_id])

  useEffect(() => {
    let cancelled = false
    if (!me?.tenant_id) {
      setTenant(null)
      return () => {
        cancelled = true
      }
    }
    ;(async () => {
      try {
        const info = await getCurrentTenant()
        if (!cancelled) {
          setTenant(info)
          if (info?.id) {
            settings.set(info.id)
            setTenantId(info.id)
          }
        }
      } catch (err) {
        console.warn('[AppShell] failed to load tenant', err)
        if (!cancelled) setTenant(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [me?.tenant_id])

  useEffect(() => {
    if (!me?.tenant_id || isOnboardingPage) {
      if (isOnboardingPage) setOnboardingStatus(null)
      return
    }
    let cancelled = false
    getOnboardingStatus()
      .then((r) => {
        if (!cancelled) setOnboardingStatus(r)
      })
      .catch(() => {
        if (!cancelled) setOnboardingStatus(null)
      })
    return () => {
      cancelled = true
    }
  }, [me?.tenant_id, isOnboardingPage])

  const currentTenantId = tenant?.id ? String(tenant.id) : (me?.tenant_id ? String(me.tenant_id) : null)

  const role = String(me?.role || '').toLowerCase()
  const enforceActivation = role === 'administrator' || role === 'superadmin'
  const canOpenBilling = role === 'administrator' || role === 'superadmin' || role === 'owner' || role === 'admin'
  const isTrialTenant = String(tenant?.status || '').trim().toLowerCase() === 'trial'

  if (!isOnboardingPage && onboardingStatus?.onboarding_required === true) {
    return <Navigate to="/app/onboarding/company" replace />
  }
  if (
    !isOnboardingPage &&
    enforceActivation &&
    onboardingStatus?.onboarding_required === false &&
    onboardingStatus?.activation_required === true
  ) {
    return <Navigate to="/app/onboarding/getting-started" replace />
  }

  return (
    <CurrentTenantProvider value={currentTenantId}>
      <TenantInfoProvider tenant={tenant}>
        <div className="flex h-screen bg-slate-50 text-slate-900">
          <Sidebar
            tenant={tenant}
            items={navItems}
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            onLogout={onLogout}
            pendingHandoffsCount={pendingHandoffsCount}
          />

          <div className="flex flex-1 flex-col overflow-hidden">
            <LicenseExpiredBanner visible={licenseExpired} validUntil={validUntil} />
            <TrialStatusBanner visible={isTrialTenant && !licenseExpired} validUntil={validUntil} canOpenBilling={canOpenBilling} />
            <Topbar
              me={me}
              tenant={tenant}
              onLogout={onLogout}
              onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
            />

            <main className="flex-1 overflow-y-auto">
              <div className="w-full px-6 py-6 lg:px-10">
                {isSettingsArea && <SettingsChrome pathname={location.pathname} />}
                <div className={`app-ui ${isSettingsArea ? 'settings-surface' : ''}`.trim()}>
                  <Outlet />
                </div>
              </div>
            </main>
          </div>
        </div>
      </TenantInfoProvider>
    </CurrentTenantProvider>
  )
}
