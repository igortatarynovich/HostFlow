import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
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
import WorkspaceBackBar from '../components/nav/WorkspaceBackBar'
import { SettingsChrome } from '../components/nav/SettingsChrome'
import { LicenseExpiredBanner } from '../components/LicenseExpiredBanner'
import { ImpersonationBanner } from '../components/ImpersonationBanner'
import { WizardSetupRail } from '../components/onboarding/WizardSetupRail'
import { isOnboardingWizardEnabled } from '../utils/featureFlags'
import { usePendingHandoffsCount } from '../hooks/usePendingHandoffsCount'
import { useLicenseStatus } from '../hooks/useLicenseStatus'
import { useRobotsMeta } from '../hooks/useRobotsMeta'
import { ACTIVATION_PATHS } from './activationRoutes'
import { usePermissions } from '../hooks/usePermissions'
import { maybeMigrateDefaultAppHomeToTasks } from '../utils/defaultAppHome'
import { CRM_APP_PATHS } from './crmAppPaths'
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
  const path = location.pathname
  // Company setup lives at /app/platform/setup (onboarding/company only redirects there).
  // Must be treated as onboarding or AppShell Navigate→onboarding/company→setup loops forever.
  const isOnboardingPage =
    path.startsWith(ACTIVATION_PATHS.onboarding) ||
    path === CRM_APP_PATHS.platformSetup ||
    path.startsWith(`${CRM_APP_PATHS.platformSetup}/`)
  const isSettingsArea = location.pathname.startsWith(CRM_APP_PATHS.settings)
  const onboardingWizardEnabled = isOnboardingWizardEnabled()
  /** Весь CRM workspace: без внешних отступов у main, компактный topbar (как список кандидатов). Onboarding оставляем с полями. */
  const isCrmWorkspace = path.startsWith(CRM_APP_PATHS.appShellPrefix) && !isOnboardingPage
  /** Список кандидатов (таблица): убираем scroll у main — иначе два скролла (main + таблица) ломают hit-testing/клики. */
  const isCandidatesTablePage = path === CRM_APP_PATHS.candidates
  /**
   * Full-bleed list pages (единая система списков): страница сама владеет
   * вертикальным скроллом через внутреннюю таблицу — как у «Кандидатов»:
   * без `crm-page-inset`, `main` без своего скролла.
   */
  const isInboxWorkspacePage =
    path === CRM_APP_PATHS.inbox || path.startsWith(`${CRM_APP_PATHS.inbox}/`)
  const isRecruitmentSearchesWorkspace =
    path === CRM_APP_PATHS.recruitmentSearches ||
    (path.startsWith(`${CRM_APP_PATHS.recruitmentSearches}/`) &&
      path !== CRM_APP_PATHS.recruitmentSearchesNew)
  const isHrWorkspacePage = path === CRM_APP_PATHS.hr || path.startsWith(`${CRM_APP_PATHS.hr}/`)
  const isHubWorkspacePage =
    path === CRM_APP_PATHS.overview ||
    path === CRM_APP_PATHS.work ||
    path.startsWith(`${CRM_APP_PATHS.work}/`)
  const isProfileWorkspacePage = path === CRM_APP_PATHS.profile
  const isMyCompanyWorkspacePage =
    path === CRM_APP_PATHS.myCompany || path.startsWith(`${CRM_APP_PATHS.myCompany}/`)
  const isOrganizationHubPage = path === CRM_APP_PATHS.organization
  const isAutomationsWorkspacePage =
    path === CRM_APP_PATHS.automations ||
    path === CRM_APP_PATHS.automationRules ||
    path === CRM_APP_PATHS.automationLog ||
    path === CRM_APP_PATHS.acquisitionActivity ||
    path.startsWith(`${CRM_APP_PATHS.automationAreaPrefix}/`)
  const isCalendarOrDocumentsPage =
    path === CRM_APP_PATHS.calendar || path === CRM_APP_PATHS.documents
  const isSetupFlowPage =
    path === CRM_APP_PATHS.setup || path.startsWith(`${CRM_APP_PATHS.setup}/`)
  /**
   * Pages that own vertical scroll via `PageShell` (or list `DataTable`).
   * `main` stays `overflow-hidden` so we do not stack an outer scrollbar.
   */
  const isFullBleedListPage =
    isCandidatesTablePage ||
    path === CRM_APP_PATHS.clientsDirectory ||
    path === CRM_APP_PATHS.vacancies ||
    path === CRM_APP_PATHS.leads ||
    path === CRM_APP_PATHS.services ||
    path === CRM_APP_PATHS.invoices ||
    path === CRM_APP_PATHS.tasks ||
    isInboxWorkspacePage ||
    isRecruitmentSearchesWorkspace ||
    isHrWorkspacePage ||
    isHubWorkspacePage ||
    isProfileWorkspacePage ||
    isMyCompanyWorkspacePage ||
    isOrganizationHubPage ||
    isAutomationsWorkspacePage ||
    isCalendarOrDocumentsPage ||
    isSetupFlowPage
  // Settings pages scroll on `main` (content height grows). Do not put them in the
  // full-bleed overflow-hidden chain — it clips long funnels/forms mid-block.
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

  const isSuperAdmin = isPlatformSuperadminRole(me?.role)
  // Trial = full product for the evaluation window (settings included). Do not strip admin nav.
  const shellNavItems = navItems

  if (!isOnboardingPage && !isSuperAdmin && onboardingStatus?.onboarding_required === true) {
    return <Navigate to={CRM_APP_PATHS.platformSetup} replace />
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
            <ImpersonationBanner visible={me?.session_kind === 'impersonation'} />
            <LicenseExpiredBanner visible={licenseExpired && !isSuperAdmin} validUntil={validUntil} />
            <Topbar
              me={me}
              tenant={tenant}
              onLogout={onLogout}
              onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
              compact={isCrmWorkspace}
            />
            <WizardSetupRail hidden={!onboardingWizardEnabled || isOnboardingPage || !me?.tenant_id} />

            <main
              className={
                isSettingsArea
                  ? 'min-h-0 flex-1 overflow-y-auto'
                  : isFullBleedListPage
                    ? 'flex min-h-0 flex-1 flex-col overflow-hidden'
                    : 'min-h-0 flex-1 overflow-y-auto'
              }
            >
              <div
                className={
                  isCrmWorkspace
                    ? clsx(
                        'w-full',
                        isSettingsArea
                          ? 'px-4 pb-10 pt-1 sm:px-6 lg:px-8'
                          : 'flex min-h-0 w-full flex-1 flex-col px-0 py-0',
                        !isSettingsArea && isFullBleedListPage && 'overflow-hidden',
                      )
                    : isFullBleedListPage
                      ? 'flex min-h-0 w-full flex-1 flex-col overflow-hidden px-6 py-6 lg:px-10'
                      : 'w-full px-6 py-6 lg:px-10'
                }
              >
                {isCrmWorkspace && !isSettingsArea && !isOnboardingPage && <WorkspaceBackBar />}
                {isSettingsArea && location.pathname !== CRM_APP_PATHS.settings && (
                  <SettingsChrome pathname={location.pathname} search={location.search} />
                )}
                <div
                  className={clsx(
                    'app-ui min-h-0',
                    isSettingsArea && 'settings-surface',
                    !isSettingsArea && (isCrmWorkspace || isSetupFlowPage) && 'crm-workspace-fill',
                    isCrmWorkspace &&
                      !isSettingsArea &&
                      !isFullBleedListPage &&
                      'crm-page-inset',
                    !isSettingsArea &&
                      isFullBleedListPage &&
                      'flex min-h-0 flex-1 flex-col overflow-hidden',
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
