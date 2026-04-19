import { useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { TenantRecord, WhoAmI } from '../api/types'
import { invalidateBillingSubscriptionCache } from '../api/billingSubscriptionCache'
import { getCurrentTenant } from '../api/tenants'
import { getOnboardingStatus, settings, type OnboardingStatus } from '../api/client'
import { setTenantId } from '../api/http'
import { CurrentTenantProvider } from '../contexts/CurrentTenant'
import { TenantInfoProvider } from '../contexts/TenantInfo'
import { TeamOverviewNavProvider } from '../contexts/TeamOverviewNavContext'
import { HiringPipelineGatesProvider } from '../contexts/HiringPipelineGatesContext'
import type { NavItem } from './routes'
import { Sidebar } from '../components/nav/Sidebar'
import { Topbar } from '../components/nav/Topbar'
import WorkContextTabs from '../components/nav/WorkContextTabs'
import { SettingsChrome } from '../components/nav/SettingsChrome'
import { LicenseExpiredBanner } from '../components/LicenseExpiredBanner'
import { TrialStatusBanner } from '../components/TrialStatusBanner'
import { usePendingHandoffsCount } from '../hooks/usePendingHandoffsCount'
import { useLicenseStatus } from '../hooks/useLicenseStatus'
import { useRobotsMeta } from '../hooks/useRobotsMeta'
import { ACTIVATION_PATHS, getActivationSetupTarget } from './activationRoutes'
import { usePermissions } from '../hooks/usePermissions'
import { maybeMigrateDefaultAppHomeToTasks } from '../utils/defaultAppHome'
import { CRM_APP_PATHS } from './crmAppPaths'

type AppShellProps = {
  me: WhoAmI | null
  navItems: NavItem[]
  onLogout: () => void
}

export function AppShell({ me, navItems, onLogout }: AppShellProps) {
  const { can } = usePermissions()
  useRobotsMeta({ index: false, follow: false })
  const location = useLocation()
  const navigate = useNavigate()
  const path = location.pathname
  const isOnboardingPage = location.pathname.startsWith(ACTIVATION_PATHS.onboarding)
  const isSettingsArea = location.pathname.startsWith(CRM_APP_PATHS.settings)
  /** Весь CRM workspace: без внешних отступов у main, компактный topbar (как список кандидатов). Onboarding оставляем с полями. */
  const isCrmWorkspace = path.startsWith(CRM_APP_PATHS.appShellPrefix) && !isOnboardingPage
  /** Список кандидатов (таблица): убираем scroll у main — иначе два скролла (main + таблица) ломают hit-testing/клики. */
  const isCandidatesTablePage = path === CRM_APP_PATHS.candidates
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null)
  const [trialBannerDismissed, setTrialBannerDismissed] = useState(false)

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
    invalidateBillingSubscriptionCache()
  }, [me?.tenant_id])

  useEffect(() => {
    if (!me) return
    maybeMigrateDefaultAppHomeToTasks(can('notifications.view'))
  }, [me, can])

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
  const isSuperAdmin = role === 'superadmin'
  const canOpenBilling = role === 'administrator' || role === 'superadmin' || role === 'owner' || role === 'admin'
  const isTrialTenant = String(tenant?.status || '').trim().toLowerCase() === 'trial'
  const guidedTrialWorkspace = Boolean(!isSuperAdmin && role === 'administrator' && isTrialTenant)
  const setupTarget = getActivationSetupTarget(onboardingStatus)
  const shellNavItems = useMemo(() => {
    if (!guidedTrialWorkspace) return navItems
    return navItems.filter((item) => {
      if (!item.path) return false
      if (
        item.path === CRM_APP_PATHS.settings ||
        item.path.startsWith(`${CRM_APP_PATHS.settings}/`)
      )
        return false
      return item.group !== 'admin'
    })
  }, [guidedTrialWorkspace, navItems])

  useEffect(() => {
    setTrialBannerDismissed(false)
  }, [currentTenantId])

  if (!isOnboardingPage && onboardingStatus?.onboarding_required === true) {
    return <Navigate to={ACTIVATION_PATHS.onboardingCompany} replace />
  }
  if (
    guidedTrialWorkspace &&
    path.startsWith(CRM_APP_PATHS.settings) &&
    path !== ACTIVATION_PATHS.billing
  ) {
    return <Navigate to={ACTIVATION_PATHS.overview} replace />
  }

  return (
    <CurrentTenantProvider value={currentTenantId}>
      <TenantInfoProvider tenant={tenant}>
        <TeamOverviewNavProvider tenantId={currentTenantId}>
        <HiringPipelineGatesProvider tenantId={currentTenantId}>
        <div className="flex h-screen bg-slate-50 text-slate-900">
          <Sidebar
            tenant={tenant}
            businessType={onboardingStatus?.business_type ?? 'agency'}
            items={shellNavItems}
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            pendingHandoffsCount={pendingHandoffsCount}
          />

          <div className="flex flex-1 flex-col overflow-hidden">
            <LicenseExpiredBanner visible={licenseExpired} validUntil={validUntil} />
            <TrialStatusBanner
              visible={
                isTrialTenant &&
                !licenseExpired &&
                !isOnboardingPage &&
                !trialBannerDismissed &&
                !guidedTrialWorkspace
              }
              validUntil={validUntil}
              canOpenBilling={canOpenBilling}
              onSetupClick={() => {
                setTrialBannerDismissed(true)
                if (path !== setupTarget) navigate(setupTarget)
              }}
            />
            <Topbar
              me={me}
              tenant={tenant}
              onLogout={onLogout}
              onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
              compact={isCrmWorkspace}
            />

            <main
              className={
                isCandidatesTablePage
                  ? 'flex min-h-0 flex-1 flex-col overflow-hidden'
                  : 'min-h-0 flex-1 overflow-y-auto'
              }
            >
              <div
                className={
                  isCrmWorkspace
                    ? clsx(
                        'flex min-h-0 w-full flex-1 flex-col',
                        isSettingsArea
                          ? 'px-4 pb-10 pt-1 sm:px-6 lg:px-8'
                          : 'px-0 py-0',
                        isCandidatesTablePage && 'overflow-hidden',
                      )
                    : 'w-full px-6 py-6 lg:px-10'
                }
              >
                {isCrmWorkspace && !isSettingsArea && !isOnboardingPage && (
                  <WorkContextTabs businessType={onboardingStatus?.business_type ?? 'agency'} />
                )}
                {isSettingsArea && (
                  <SettingsChrome
                    pathname={location.pathname}
                    search={location.search}
                    compactMode={guidedTrialWorkspace}
                  />
                )}
                <div
                  className={clsx(
                    'app-ui min-h-0',
                    isSettingsArea && 'settings-surface',
                    isCrmWorkspace && 'crm-workspace-fill',
                    isCrmWorkspace &&
                      !isSettingsArea &&
                      !isCandidatesTablePage &&
                      'crm-page-inset',
                    isCandidatesTablePage && 'flex min-h-0 flex-1 flex-col overflow-hidden',
                  )}
                >
                  <Outlet />
                </div>
              </div>
            </main>
          </div>
        </div>
        </HiringPipelineGatesProvider>
        </TeamOverviewNavProvider>
      </TenantInfoProvider>
    </CurrentTenantProvider>
  )
}
