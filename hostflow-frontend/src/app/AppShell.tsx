import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { TenantRecord, WhoAmI } from '../api/types'
import { invalidateBillingSubscriptionCache } from '../api/billingSubscriptionCache'
import { invalidateBillingQuotaHeadroomCache } from '../api/billingQuotaHeadroomCache'
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
import { LicenseExpiredBanner } from '../components/LicenseExpiredBanner'
import { ImpersonationBanner } from '../components/ImpersonationBanner'
import { TrialStatusBanner } from '../components/TrialStatusBanner'
import { WizardSetupRail } from '../components/onboarding/WizardSetupRail'
import { isOnboardingWizardEnabled } from '../utils/featureFlags'
import { usePendingHandoffsCount } from '../hooks/usePendingHandoffsCount'
import { useLicenseStatus } from '../hooks/useLicenseStatus'
import { useRobotsMeta } from '../hooks/useRobotsMeta'
import { ACTIVATION_PATHS, getActivationSetupTarget, isActivationOnboardingPath } from './activationRoutes'
import { usePermissions } from '../hooks/usePermissions'
import { maybeMigrateDefaultAppHomeToTasks } from '../utils/defaultAppHome'
import { CRM_APP_PATHS } from './crmAppPaths'
import { isEdgeToEdgeTablePath, ownsCrmWorkspaceScroll } from './crmWorkspaceLayout'
import { isPlatformSuperadminRole } from '../utils/platformSuperadmin'

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
  const isOnboardingPage = isActivationOnboardingPath(location.pathname)
  const isSettingsArea = location.pathname.startsWith(CRM_APP_PATHS.settings)
  const onboardingWizardEnabled = isOnboardingWizardEnabled()
  /** Весь CRM workspace: без внешних отступов у main, компактный topbar (как список кандидатов). Onboarding оставляем с полями. */
  const isCrmWorkspace = path.startsWith(CRM_APP_PATHS.appShellPrefix) && !isOnboardingPage
  const isSetupFlowPage =
    path === CRM_APP_PATHS.setup || path.startsWith(`${CRM_APP_PATHS.setup}/`)
  /**
   * Native list tables (Candidates, Отклики, vacancy list, …): no `crm-page-inset`.
   * Detail/form pages stay inset so content does not stick to the screen edges.
   */
  const isEdgeToEdgeTable = isEdgeToEdgeTablePath(path)
  /**
   * Pages that own vertical scroll via `PageShell` (or list `DataTable`).
   * `main` stays `overflow-hidden` so we do not stack an outer scrollbar.
   */
  const ownsWorkspaceScroll = ownsCrmWorkspaceScroll(path)
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
    const jwtTenantId = me?.tenant_id ? String(me.tenant_id).trim() : ''
    if (!jwtTenantId) return
    const isPlatformSuperadmin = isPlatformSuperadminRole(me?.role)
    const storedTenantId = String(settings.get() || '').trim()
    // For superadmin we preserve manually selected tenant context.
    const effectiveTenantId =
      isPlatformSuperadmin && storedTenantId && storedTenantId !== jwtTenantId
        ? storedTenantId
        : jwtTenantId
    settings.set(effectiveTenantId)
    setTenantId(effectiveTenantId)
  }, [me?.role, me?.tenant_id])

  useEffect(() => {
    invalidateBillingSubscriptionCache()
    invalidateBillingQuotaHeadroomCache()
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
            const infoTenantId = String(info.id).trim()
            const jwtTenantId = me?.tenant_id ? String(me.tenant_id).trim() : ''
            const isPlatformSuperadmin = isPlatformSuperadminRole(me?.role)
            const storedTenantId = String(settings.get() || '').trim()
            const effectiveTenantId =
              isPlatformSuperadmin &&
              storedTenantId &&
              storedTenantId !== jwtTenantId &&
              storedTenantId !== infoTenantId
                ? storedTenantId
                : infoTenantId
            settings.set(effectiveTenantId)
            setTenantId(effectiveTenantId)
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
  const isSuperAdmin = isPlatformSuperadminRole(me?.role)
  const canOpenBilling =
    role === 'administrator' ||
    role === 'superadmin' ||
    role === 'super_admin' ||
    role === 'owner' ||
    role === 'admin'
  const isTrialTenant = String(tenant?.status || '').trim().toLowerCase() === 'trial'
  const setupTarget = getActivationSetupTarget(onboardingStatus)
  const shellNavItems = navItems

  useEffect(() => {
    setTrialBannerDismissed(false)
  }, [currentTenantId])

  if (!isOnboardingPage && !isSuperAdmin && onboardingStatus?.onboarding_required === true) {
    return <Navigate to={ACTIVATION_PATHS.platformSetup} replace />
  }

  return (
    <CurrentTenantProvider value={currentTenantId}>
      <TenantInfoProvider tenant={tenant}>
        <TeamOverviewNavProvider tenantId={currentTenantId}>
        <HiringPipelineGatesProvider tenantId={currentTenantId}>
        <div className="hf-app-viewport bg-slate-50 text-slate-900">
          <Sidebar
            tenant={tenant}
            businessType={onboardingStatus?.business_type ?? 'agency'}
            items={shellNavItems}
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            pendingHandoffsCount={pendingHandoffsCount}
          />

          <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            <ImpersonationBanner visible={me?.session_kind === 'impersonation'} />
            <LicenseExpiredBanner visible={licenseExpired && !isSuperAdmin} validUntil={validUntil} />
            <TrialStatusBanner
              visible={
                !isSuperAdmin &&
                isTrialTenant &&
                !licenseExpired &&
                !isOnboardingPage &&
                !trialBannerDismissed
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
              pendingHandoffsCount={pendingHandoffsCount}
            />
            <WizardSetupRail hidden={!onboardingWizardEnabled || isOnboardingPage || !me?.tenant_id} />

            <main
              className={
                ownsWorkspaceScroll
                  ? 'flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden'
                  : 'min-h-0 min-w-0 flex-1 overflow-x-auto overflow-y-auto'
              }
            >
              <div
                className={
                  isCrmWorkspace
                    ? clsx(
                        'flex min-h-0 min-w-0 w-full flex-1 flex-col',
                        isSettingsArea
                          ? 'px-4 pb-10 pt-1 sm:px-6 lg:px-8'
                          : 'px-0 py-0',
                        ownsWorkspaceScroll && 'overflow-hidden',
                      )
                    : ownsWorkspaceScroll
                      ? 'flex min-h-0 min-w-0 w-full flex-1 flex-col overflow-hidden px-6 py-6 lg:px-10'
                      : 'w-full min-w-0 px-6 py-6 lg:px-10'
                }
              >
                <div
                  className={clsx(
                    'app-ui min-h-0 min-w-0',
                    isSettingsArea && 'settings-surface',
                    (isCrmWorkspace || isSetupFlowPage) && 'crm-workspace-fill',
                    isCrmWorkspace &&
                      !isSettingsArea &&
                      !isEdgeToEdgeTable &&
                      'crm-page-inset',
                    ownsWorkspaceScroll && 'flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden',
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
