import clsx from 'clsx'
import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import {
  IconBell,
  IconBolt,
  IconBriefcase,
  IconBuilding,
  IconBuildingStore,
  IconChartBar,
  IconCalendarEvent,
  IconCalendarOff,
  IconChecklist,
  IconClipboardList,
  IconClock,
  IconCreditCard,
  IconDashboard,
  IconFileText,
  IconFilter,
  IconHome,
  IconInbox,
  IconLayoutKanban,
  IconMail,
  IconMessageCircle,
  IconPlugConnected,
  IconRoute,
  IconSearch,
  IconSettings,
  IconShield,
  IconUsers,
  IconUser,
  IconUserQuestion,
  IconUsersGroup,
  IconBrandMeta,
  IconBrandGoogle,
  IconWebhook,
} from '@tabler/icons-react'
import type { TenantSummary } from '../../api/types'
import type { NavItem } from '../../app/routes'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { useCommunicationsAccess } from '../../hooks/useCommunicationsAccess'
import { getTenantModules } from '../../api/tenants'
import type { TenantModuleSettings } from '../../api/types'
import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'
import { useTeamOverviewNav } from '../../contexts/TeamOverviewNavContext'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { navigateToModuleHost } from '../../api/client'
import { APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS } from '../../nav/appShellNav'
import {
  SIDEBAR_AGENCY_ANALYTICS_ORDER,
  SIDEBAR_AGENCY_AUTOMATIONS_ORDER,
  SIDEBAR_AGENCY_DASHBOARD_ORDER,
  SIDEBAR_AGENCY_DOCUMENTS_ORDER,
  SIDEBAR_AGENCY_INBOX_ORDER,
  SIDEBAR_AGENCY_INTEGRATIONS_ORDER,
  SIDEBAR_AGENCY_ORGANIZATION_ORDER,
  SIDEBAR_AGENCY_PROCESSING_ORDER,
  SIDEBAR_AGENCY_PROFILE_ORDER,
  SIDEBAR_AGENCY_FINANCE_ORDER,
  SIDEBAR_AGENCY_HR_ORDER,
  SIDEBAR_AGENCY_MARKETING_ORDER,
  SIDEBAR_AGENCY_RECRUITMENT_ORDER,
  SIDEBAR_AGENCY_SALES_ORDER,
  SIDEBAR_AGENCY_SERVICES_ORDER,
  SIDEBAR_AGENCY_SETTINGS_HUB_ORDER,
  SIDEBAR_AGENCY_TASKS_ORDER,
  SIDEBAR_AGENCY_TEAM_ORDER,
  SIDEBAR_AGENCY_WORK_HUB_ORDER,
  SIDEBAR_CLIENT_FLAT_ORDER,
} from '../../nav/sidebarRailBuckets'
import { SidebarOwnCompanySection } from './SidebarOwnCompanySection'

type SidebarProps = {
  items: NavItem[]
  tenant: TenantSummary | null
  businessType?: 'agency' | 'employer' | 'services'
  open: boolean
  onClose: () => void
  pendingHandoffsCount?: number
}

const DEFAULT_ICON: TablerIcon = IconChecklist

/** Canonical list: `nav/appShellNav.ts` */
const SIDEBAR_HIDDEN_ITEM_KEYS = new Set<string>(APP_SHELL_SIDEBAR_HIDDEN_ITEM_KEYS)

const ITEM_ICONS: Partial<Record<string, TablerIcon>> = {
  overview: IconDashboard,
  analytics: IconChartBar,
  'work-hub': IconBriefcase,
  'recruitment-searches': IconSearch,
  'recruitment-inbox': IconInbox,
  'hr-workspace': IconUsersGroup,
  sales: IconBuildingStore,
  'sales-orders': IconClipboardList,
  candidates: IconUsers,
  'candidates-no-next-action': IconUserQuestion,
  clients: IconBuilding,
  'do-procesowania': IconFilter,
  vacancies: IconLayoutKanban,
  documents: IconFileText,
  'service-orders': IconClipboardList,
  services: IconChecklist,
  invoices: IconFileText,
  inbox: IconInbox,
  tasks: IconChecklist,
  'notification-alerts': IconBell,
  calendar: IconCalendarEvent,
  'sla-incidents': IconBell,
  'command-audit': IconShield,
  'leads-distribution': IconRoute,
  'leads-distribution-rules': IconRoute,
  'automation-rules': IconBolt,
  'automation-log': IconChecklist,
  'acquisition-activity': IconChecklist,
  'marketing-sources': IconChecklist,
  'marketing-diagnostics': IconChecklist,
  automations: IconBolt,
  'integrations-meta': IconBrandMeta,
  'integrations-google': IconBrandGoogle,
  'integrations-webhook': IconWebhook,
  'settings-communications-messengers': IconMessageCircle,
  'settings-communications-queue': IconFilter,
  'settings-communications-sla': IconBell,
  'team-availability': IconUsersGroup,
  'my-availability': IconClock,
  'time-off': IconCalendarOff,
  leads: IconInbox,
  'my-company': IconHome,
  organization: IconBuilding,
  settings: IconSettings,
  'settings-users': IconUsersGroup,
  'settings-billing': IconCreditCard,
  'settings-tenants': IconBuilding,
  'settings-funnels': IconLayoutKanban,
  'settings-docs': IconFileText,
  'settings-candidate-profiles': IconUsers,
  'settings-custom-fields': IconFilter,
  'settings-legal': IconShield,
  'settings-company-access': IconUsersGroup,
  'settings-email': IconMail,
  'settings-tenant-links': IconUsers,
  'settings-integrations': IconPlugConnected,
  'settings-ruleset': IconShield,
  'settings-audit': IconShield,
  'settings-communications': IconMessageCircle,
  profile: IconUser,
}

export function Sidebar({
  items,
  tenant,
  businessType = 'agency',
  open,
  onClose,
  pendingHandoffsCount = 0,
}: SidebarProps) {
  const { t } = useI18n()
  const location = useLocation()
  const p = CRM_APP_PATHS
  const inboxNavActive =
    location.pathname.startsWith(p.inbox) ||
    location.pathname.startsWith(p.messages) ||
    location.pathname.startsWith(p.email) ||
    location.pathname.startsWith(p.inboxThreadsBase)
  const clientsNavActive = location.pathname.startsWith(p.agencyClients)
  const servicesWorkspacePath = location.pathname === p.services
  const ordersStandalonePath = location.pathname === p.orders
  const servicesTabParam = useMemo(() => {
    const sp = new URLSearchParams(location.search)
    return (sp.get('tab') || 'overview').trim().toLowerCase()
  }, [location.search])
  const inboxChannelParam = useMemo(() => {
    const sp = new URLSearchParams(location.search)
    return (sp.get('channel') || '').trim().toLowerCase()
  }, [location.search])
  const ordersNavActive = ordersStandalonePath || (servicesWorkspacePath && servicesTabParam === 'orders')
  const servicesModuleNavActive = servicesWorkspacePath && servicesTabParam !== 'orders'
  const { isClientTenant, can } = usePermissions()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const [modules, setModules] = useState<TenantModuleSettings | null>(null)
  const { teamOverview, canLoadTeamOverview: canLoadTeamOverviewCtx } = useTeamOverviewNav()

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        if (!tenant?.id) {
          if (mounted) setModules(null)
          return
        }
        const modulesData = await getTenantModules({ tenantId: tenant.id })
        if (mounted) setModules(modulesData)
      } catch {
        if (mounted) setModules(null)
      }
    })()
    return () => {
      mounted = false
    }
  }, [tenant?.id])

  void businessType
  void canLoadTeamOverviewCtx

  const isSoloWorkspace = useMemo(() => {
    const membersCount = Array.isArray(teamOverview?.members) ? teamOverview!.members.length : null
    if (typeof membersCount === 'number') return membersCount <= 1
    const usage = teamOverview?.usage
    if (!usage) return false
    const total =
      Number(usage.administrator_count ?? usage.supervisor_count ?? 0) +
      Number(usage.employee_count ?? usage.recruiter_count ?? 0) +
      Number(usage.viewer_count || 0)
    // Portal guests are non-billable and do not count toward workspace team size.
    return total <= 1
  }, [teamOverview])

  const visibleItems = useMemo(() => {
    const moduleByItemKey: Partial<Record<string, keyof TenantModuleSettings>> = {
      'recruitment-searches': 'vacancies',
      'recruitment-inbox': 'leads',
      candidates: 'candidates',
      'candidates-no-next-action': 'candidates',
      'hr-workspace': 'hr',
      /** Growth / Campaigns share vacancy module gate until a dedicated Acquisition entitlement exists. */
      marketing: 'vacancies',
      'acquisition-activity': 'vacancies',
      sales: 'companies',
      'sales-orders': 'companies',
      clients: 'companies',
      vacancies: 'vacancies',
      documents: 'documents',
      leads: 'leads',
      'leads-distribution': 'leads',
      'leads-distribution-rules': 'leads',
      'integrations-meta': 'leads',
      'integrations-google': 'leads',
      'integrations-webhook': 'leads',
      'service-orders': 'services',
      services: 'services',
      invoices: 'services',
      tasks: 'candidates',
      communications: 'candidates',
      inbox: 'candidates',
      'settings-integrations': 'candidates',
      calendar: 'candidates',
      'team-availability': 'candidates',
      'my-availability': 'candidates',
      'time-off': 'candidates',
      'command-audit': 'candidates',
      'sla-incidents': 'candidates',
      'do-procesowania': 'candidates',
    }

    const commFeatureByItemKey: Partial<Record<string, Parameters<typeof canUseCommunicationsFeature>[0]>> = {
      calendar: 'calendar',
      'team-availability': 'teamAvailability',
      'my-availability': 'myAvailability',
      'time-off': 'timeOffRequests',
      'command-audit': 'communicationsAdmin',
      'settings-communications': 'communicationsAdmin',
      'settings-communications-messengers': 'communicationsAdmin',
      'settings-communications-queue': 'communicationsAdmin',
      'settings-communications-sla': 'communicationsAdmin',
    }

    const moduleFiltered = items.filter((item) => {
      if (SIDEBAR_HIDDEN_ITEM_KEYS.has(item.key)) return false
      if (item.key === 'work-hub') {
        return (
          can('candidates.view') ||
          can('companies.view') ||
          can('leads.view') ||
          can('vacancies.view') ||
          can('services.view') ||
          can('documents.manage')
        )
      }
      if (item.key === 'communications') return false
      if (item.key === 'team-availability' && isSoloWorkspace) return false
      if (item.key === 'settings-integrations') {
        if (can('admin.metaLeads') || can('admin.users') || can('settings.view')) return true
        return (
          can('notifications.view') &&
          (canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email'))
        )
      }
      if (item.key === 'inbox') {
        return canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email')
      }
      const commFeature = commFeatureByItemKey[item.key]
      if (commFeature && !canUseCommunicationsFeature(commFeature)) return false
      const moduleKey = moduleByItemKey[item.key]
      if (!moduleKey) return true
      if (!modules) return true
      return Boolean(modules[moduleKey])
    })

    if (!isClientTenant) return moduleFiltered
    const allowed = new Set([
      'overview',
      'work-hub',
      'candidates',
      'tasks',
      'inbox',
      'settings-integrations',
      'profile',
    ])
    return moduleFiltered.filter((item) => allowed.has(item.key))
  }, [can, canUseCommunicationsFeature, isClientTenant, isSoloWorkspace, items, modules])

  /** ADR-023 + Acquisition UI Cutover C-1: … → HR → Marketing → Sales → Services → Finance → … */
  const {
    dashboardNavItems,
    workHubNavItems,
    inboxNavItems,
    recruitmentNavItems,
    hrNavItems,
    marketingNavItems,
    salesNavItems,
    servicesNavItems,
    financeNavItems,
    tasksNavItems,
    processingNavItems,
    teamNavItems,
    documentsNavItems,
    automationsNavItems,
    integrationsNavItems,
    analyticsNavItems,
    coreNavItems,
    organizationNavItems,
    settingsHubNavItems,
    profileNavItems,
    sidebarBucketed,
  } = useMemo(() => {
    const pickOrdered = (order: string[]) => {
      const idx = new Map(order.map((k, i) => [k, i]))
      return visibleItems
        .filter((item) => item.path && idx.has(item.key))
        .sort((a, b) => (idx.get(a.key) ?? 0) - (idx.get(b.key) ?? 0))
    }

    if (isClientTenant) {
      const flat = pickOrdered([...SIDEBAR_CLIENT_FLAT_ORDER])
      return {
        dashboardNavItems: [] as NavItem[],
        workHubNavItems: [] as NavItem[],
        inboxNavItems: [] as NavItem[],
        recruitmentNavItems: [] as NavItem[],
        hrNavItems: [] as NavItem[],
        marketingNavItems: [] as NavItem[],
        salesNavItems: [] as NavItem[],
        servicesNavItems: [] as NavItem[],
        financeNavItems: [] as NavItem[],
        tasksNavItems: [] as NavItem[],
        processingNavItems: [] as NavItem[],
        teamNavItems: [] as NavItem[],
        documentsNavItems: [] as NavItem[],
        automationsNavItems: [] as NavItem[],
        integrationsNavItems: [] as NavItem[],
        analyticsNavItems: [] as NavItem[],
        coreNavItems: flat,
        organizationNavItems: [] as NavItem[],
        settingsHubNavItems: [] as NavItem[],
        profileNavItems: [] as NavItem[],
        sidebarBucketed: false,
      }
    }

    const dashboardNavItems = pickOrdered([...SIDEBAR_AGENCY_DASHBOARD_ORDER])
    const workHubNavItems = pickOrdered([...SIDEBAR_AGENCY_WORK_HUB_ORDER])
    const inboxNavItems = pickOrdered([...SIDEBAR_AGENCY_INBOX_ORDER])
    const recruitmentNavItems = pickOrdered([...SIDEBAR_AGENCY_RECRUITMENT_ORDER])
    const hrNavItems = pickOrdered([...SIDEBAR_AGENCY_HR_ORDER])
    const marketingNavItems = pickOrdered([...SIDEBAR_AGENCY_MARKETING_ORDER])
    const salesNavItems = pickOrdered([...SIDEBAR_AGENCY_SALES_ORDER])
    const servicesNavItems = pickOrdered([...SIDEBAR_AGENCY_SERVICES_ORDER])
    const financeNavItems = pickOrdered([...SIDEBAR_AGENCY_FINANCE_ORDER])
    const tasksNavItems = pickOrdered([...SIDEBAR_AGENCY_TASKS_ORDER])
    const processingNavItems = pickOrdered([...SIDEBAR_AGENCY_PROCESSING_ORDER])
    const teamNavItems = pickOrdered([...SIDEBAR_AGENCY_TEAM_ORDER])
    const documentsNavItems = pickOrdered([...SIDEBAR_AGENCY_DOCUMENTS_ORDER])
    const automationsNavItems = pickOrdered([...SIDEBAR_AGENCY_AUTOMATIONS_ORDER])
    const integrationsNavItems = pickOrdered([...SIDEBAR_AGENCY_INTEGRATIONS_ORDER])
    const analyticsNavItems = pickOrdered([...SIDEBAR_AGENCY_ANALYTICS_ORDER])
    const coreNavItems: NavItem[] = []
    const organizationNavItems = pickOrdered([...SIDEBAR_AGENCY_ORGANIZATION_ORDER])
    const settingsHubNavItems = pickOrdered([...SIDEBAR_AGENCY_SETTINGS_HUB_ORDER])
    const profileNavItems = pickOrdered([...SIDEBAR_AGENCY_PROFILE_ORDER])
    return {
      dashboardNavItems,
      workHubNavItems,
      inboxNavItems,
      recruitmentNavItems,
      hrNavItems,
      marketingNavItems,
      salesNavItems,
      servicesNavItems,
      financeNavItems,
      tasksNavItems,
      processingNavItems,
      teamNavItems,
      documentsNavItems,
      automationsNavItems,
      integrationsNavItems,
      analyticsNavItems,
      coreNavItems,
      organizationNavItems,
      settingsHubNavItems,
      profileNavItems,
      sidebarBucketed: true,
    }
  }, [isClientTenant, visibleItems])

  const automationsRailActive = useMemo(() => {
    const path = location.pathname
    return (
      path === p.automations ||
      path === p.automationRules ||
      path === p.automationLog ||
      path === p.leadsDistribution ||
      path.startsWith(`${p.leadsDistribution}/`)
    )
  }, [location.pathname, p])

  const marketingRailActive = useMemo(() => {
    const path = location.pathname
    return path === p.marketing || path.startsWith(`${p.marketing}/`)
  }, [location.pathname, p])

  const acquisitionActivityRailActive = useMemo(() => {
    const path = location.pathname
    return path === p.acquisitionActivity || path.startsWith(`${p.acquisitionActivity}/`)
  }, [location.pathname, p])

  const integrationsRailActive = useMemo(() => {
    const path = location.pathname
    return (
      path.startsWith(`${p.settingsIntegrations}`) ||
      path === p.settingsEmail ||
      path.startsWith(`${p.settingsCommunications}`)
    )
  }, [location.pathname, p])

  const navItemActive = (item: NavItem, isActive: boolean): boolean => {
    if (item.key === 'clients') return clientsNavActive
    if (item.key === 'sales') {
      const path = location.pathname
      if (path === p.salesOrders || path.startsWith(`${p.salesOrders}/`)) return false
      return path === p.sales || path.startsWith(`${p.sales}/`)
    }
    if (item.key === 'sales-orders') {
      const path = location.pathname
      return path === p.salesOrders || path.startsWith(`${p.salesOrders}/`)
    }
    if (item.key === 'marketing') return marketingRailActive
    if (item.key === 'acquisition-activity') return acquisitionActivityRailActive
    if (item.key === 'recruitment-searches') {
      return location.pathname.startsWith(p.recruitmentSearches)
    }
    if (item.key === 'work-hub') return location.pathname.startsWith(p.work) || location.pathname.startsWith(`${p.work}/`)
    if (item.key === 'hr-workspace') return location.pathname === p.hr || location.pathname.startsWith(`${p.hr}/`)
    if (
      item.key === 'automations' ||
      item.key === 'automation-rules' ||
      item.key === 'automation-log' ||
      item.key === 'leads-distribution' ||
      item.key === 'leads-distribution-rules'
    ) {
      return automationsRailActive
    }
    if (
      item.key === 'settings-integrations' ||
      item.key === 'integrations-meta' ||
      item.key === 'integrations-google' ||
      item.key === 'integrations-webhook' ||
      item.key === 'settings-email'
    ) {
      return integrationsRailActive
    }
    if (item.key === 'service-orders') return ordersNavActive
    if (item.key === 'services') return servicesModuleNavActive
    if (item.key === 'organization') return location.pathname === p.organization || location.pathname.startsWith(`${p.organization}/`)
    if (item.key === 'my-company') return location.pathname.startsWith(p.myCompany)
    if (item.key === 'profile') return location.pathname.startsWith(p.profile)
    if (item.key === 'settings') {
      if (!location.pathname.startsWith(p.settings)) return false
      if (integrationsRailActive) return false
      return true
    }
    return isActive
  }

  const handleNavigate = () => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      onClose()
    }
  }

  const tenantLabel = tenant?.workspace_label?.trim() || tenant?.name || 'HostFlow'
  const { entityPlural: clientsNavLabel } = useBusinessTerminology()
  const getItemLabel = (item: NavItem): string => {
    const translated = t(item.labelKey, { defaultValue: '' }).trim()
    if (translated && translated !== item.labelKey) return translated
    const fallbackFromKey = item.key
      .replace(/[-_]+/g, ' ')
      .trim()
      .replace(/\b\w/g, (m) => m.toUpperCase())
    return fallbackFromKey || item.key
  }

  const renderPrimaryNavItem = (item: NavItem) => {
    const itemPath = String(item.path || '')
    const crossHost = /^https?:\/\//i.test(itemPath)
    const navClass = (active: boolean) =>
      clsx(
        'block rounded-lg px-3 py-3 text-sm font-medium transition',
        active ? 'bg-white text-brand-900 shadow-sm' : 'text-white hover:bg-white/15 hover:text-white',
      )

    if (item.key === 'inbox') {
      const ItemIcon = ITEM_ICONS.inbox || DEFAULT_ICON
      const showMessagesChild = canUseCommunicationsFeature('messages')
      const showEmailChild = canUseCommunicationsFeature('email')
      return (
        <div key={item.key} className="space-y-1">
          <NavLink
            to={item.path!}
            title={getItemLabel(item)}
            onClick={handleNavigate}
            className={() => navClass(inboxNavActive)}
          >
            <span className="flex items-center justify-between gap-2">
              <span className="inline-flex items-center gap-2">
                <ItemIcon size={16} stroke={1.8} />
                <span>{getItemLabel(item)}</span>
              </span>
            </span>
          </NavLink>
          {(showMessagesChild || showEmailChild) && (
            <div className="ml-7 flex flex-wrap gap-1 pt-0.5">
              {showMessagesChild && (
                <NavLink
                  to={p.inboxMessagesScoped}
                  title={t('app.nav.items.messages_inbox', { defaultValue: 'Messages' })}
                  onClick={handleNavigate}
                  className={() =>
                    clsx(
                      'inline-flex items-center gap-2 rounded-lg px-2 py-1 text-[11px] font-medium transition',
                      location.pathname.startsWith(p.messages) ||
                        (location.pathname.startsWith(p.inbox) && inboxChannelParam === 'messages')
                        ? 'bg-white/20 text-white'
                        : 'text-white/80 hover:bg-white/10 hover:text-white',
                    )
                  }
                >
                  <IconMessageCircle size={13} stroke={1.8} />
                  {t('app.nav.items.messages_inbox', { defaultValue: 'Messages' })}
                </NavLink>
              )}
              {showEmailChild && (
                <NavLink
                  to={p.inboxEmailScoped}
                  title={t('app.nav.items.email_inbox', { defaultValue: 'Email' })}
                  onClick={handleNavigate}
                  className={() =>
                    clsx(
                      'inline-flex items-center gap-2 rounded-lg px-2 py-1 text-[11px] font-medium transition',
                      location.pathname.startsWith(p.email) ||
                        (location.pathname.startsWith(p.inbox) && inboxChannelParam === 'email')
                        ? 'bg-white/20 text-white'
                        : 'text-white/80 hover:bg-white/10 hover:text-white',
                    )
                  }
                >
                  <IconMail size={13} stroke={1.8} />
                  {t('app.nav.items.email_inbox', { defaultValue: 'Email' })}
                </NavLink>
              )}
            </div>
          )}
        </div>
      )
    }

    const label = item.key === 'clients' ? clientsNavLabel : getItemLabel(item)
    const ItemIcon = ITEM_ICONS[item.key] || DEFAULT_ICON
    const inner = (
      <span className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-2">
          <ItemIcon size={16} stroke={1.8} />
          <span>{label}</span>
        </span>
      </span>
    )

    // Foreign modules are absolute https://sales.hostflow.cc/... — must be <a>, not React Router.
    // Sync Domain cookies before leaving the shell, otherwise the module host has no session → /login.
    if (crossHost) {
      return (
        <a
          key={item.key}
          href={itemPath}
          title={getItemLabel(item)}
          onClick={(event) => {
            event.preventDefault()
            handleNavigate()
            void navigateToModuleHost(itemPath)
          }}
          className={navClass(false)}
        >
          {inner}
        </a>
      )
    }

    return (
      <NavLink
        key={item.key}
        to={item.path!}
        title={getItemLabel(item)}
        onClick={handleNavigate}
        className={({ isActive }) => navClass(navItemActive(item, isActive))}
      >
        {inner}
      </NavLink>
    )
  }

  return (
    <>
      <div
        className={clsx(
          'relative z-[100] bg-brand-900 transition-[width] duration-300',
          open ? 'w-screen max-w-sm lg:w-72 lg:max-w-none' : 'w-0'
        )}
        aria-hidden={!open}
      >
        <div
          className={clsx(
            'fixed inset-y-0 left-0 flex h-full flex-col bg-brand-900 text-white transition-transform duration-300',
            open ? 'translate-x-0' : '-translate-x-full',
            'w-screen max-w-sm lg:max-w-none lg:w-72'
          )}
        >
          <div className="px-4 py-3">
            <div className="min-w-0">
              <div className="text-xs font-medium text-white/65" title={t('app.shell.sidebar.workspace')}>
                {t('app.shell.sidebar.workspace')}
              </div>
              <div className="truncate text-base font-semibold leading-tight text-white" title={tenantLabel}>
                {tenantLabel}
              </div>
            </div>
          </div>

          <SidebarOwnCompanySection />

          <nav className="flex-1 overflow-y-auto px-3 pb-6">
            {sidebarBucketed ? (
              <>
                {dashboardNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                      {t('app.shell.sidebar.section_dashboard')}
                    </div>
                    <div className="space-y-1">{dashboardNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {workHubNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                      {t('app.shell.sidebar.work')}
                    </div>
                    <div className="space-y-1">{workHubNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {inboxNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                      {t('app.shell.sidebar.section_communications')}
                    </div>
                    <div className="space-y-1">{inboxNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {recruitmentNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_recruitment')}
                      </div>
                      <div className="space-y-1">{recruitmentNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {hrNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_hr')}
                      </div>
                      <div className="space-y-1">{hrNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {marketingNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3" data-testid="sidebar-section-marketing">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_marketing')}
                      </div>
                      <div className="space-y-1">{marketingNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {salesNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3" data-testid="sidebar-section-sales">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_sales')}
                      </div>
                      <div className="space-y-1">{salesNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {servicesNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_services')}
                      </div>
                      <div className="space-y-1">{servicesNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {financeNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_finance')}
                      </div>
                      <div className="space-y-1">{financeNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {tasksNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_tasks_calendar')}
                      </div>
                      <div className="space-y-1">{tasksNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {processingNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_processing')}
                      </div>
                      <div className="space-y-1">{processingNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {teamNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_team')}
                      </div>
                      <div className="space-y-1">{teamNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {documentsNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_documents')}
                      </div>
                      <div className="space-y-1">{documentsNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {automationsNavItems.length > 0 && (
                  <>
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="mb-3">
                      <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                        {t('app.shell.sidebar.section_automations')}
                      </div>
                      <div className="space-y-1">{automationsNavItems.map(renderPrimaryNavItem)}</div>
                    </div>
                  </>
                )}
                {integrationsNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                      {t('app.shell.sidebar.section_integrations')}
                    </div>
                    <div className="space-y-1">{integrationsNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {analyticsNavItems.length > 0 && (
                  <div className="mb-4">
                    <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                    <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                      {t('app.shell.sidebar.section_analytics')}
                    </div>
                    <div className="space-y-1">{analyticsNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {(organizationNavItems.length > 0 || settingsHubNavItems.length > 0 || profileNavItems.length > 0) && (
                  <div className="mx-3 my-2 border-t border-white/10" role="separator" />
                )}
                {organizationNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                      {t('app.shell.sidebar.section_organization')}
                    </div>
                    <div className="space-y-1">{organizationNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {settingsHubNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                      {t('app.shell.sidebar.section_settings')}
                    </div>
                    <div className="space-y-1">{settingsHubNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {profileNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                      {t('app.shell.sidebar.section_personal')}
                    </div>
                    <div className="space-y-1">{profileNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
              </>
            ) : (
              <div className="mb-4">
                <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-white/45">
                  {t('app.shell.sidebar.section_menu')}
                </div>
                <div className="space-y-1">{coreNavItems.map(renderPrimaryNavItem)}</div>
              </div>
            )}
          </nav>
        </div>
      </div>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onClose} role="presentation" />
      )}
    </>
  )
}
