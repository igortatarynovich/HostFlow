import clsx from 'clsx'
import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import {
  IconBell,
  IconBolt,
  IconBriefcase,
  IconBuilding,
  IconChartBar,
  IconCalendarEvent,
  IconCalendarOff,
  IconChevronDown,
  IconChecklist,
  IconClipboardList,
  IconClock,
  IconCreditCard,
  IconDashboard,
  IconFileText,
  IconFilter,
  IconInbox,
  IconLayoutKanban,
  IconLogout,
  IconMail,
  IconMessageCircle,
  IconPlugConnected,
  IconRoute,
  IconSettings,
  IconShield,
  IconUsers,
  IconUser,
  IconUserQuestion,
  IconUsersGroup,
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
import {
  FINANCE_NAV_ORDER,
  resolveNavPlanFromTeamOverview,
  shouldShowFinanceNavSection,
} from '../../nav/financeNavVisibility'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

type SidebarProps = {
  items: NavItem[]
  tenant: TenantSummary | null
  businessType?: 'agency' | 'employer' | 'services'
  open: boolean
  onClose: () => void
  onLogout: () => void
  pendingHandoffsCount?: number
}

const GROUP_STORAGE_KEY = 'hf:ui:sidebar-groups'
const DEFAULT_ICON: TablerIcon = IconChecklist

/** SSOT §2.13: stateful queues — primary entry via Dashboard / Work / Inbox / notifications; keep routes + `NAV_ITEMS` for deep links. */
const SIDEBAR_HIDDEN_ITEM_KEYS = new Set<string>(['candidates-no-next-action', 'sla-incidents'])

const ITEM_ICONS: Partial<Record<string, TablerIcon>> = {
  overview: IconDashboard,
  analytics: IconChartBar,
  'work-hub': IconBriefcase,
  candidates: IconUsers,
  'candidates-no-next-action': IconUserQuestion,
  clients: IconBuilding,
  'do-procesowania': IconFilter,
  vacancies: IconLayoutKanban,
  documents: IconFileText,
  'service-orders': IconClipboardList,
  services: IconChecklist,
  invoices: IconFileText,
  'communications-setup': IconPlugConnected,
  inbox: IconInbox,
  tasks: IconChecklist,
  calendar: IconCalendarEvent,
  'sla-incidents': IconBell,
  'command-audit': IconShield,
  'leads-distribution': IconRoute,
  automations: IconBolt,
  'team-availability': IconUsersGroup,
  'my-availability': IconClock,
  'time-off': IconCalendarOff,
  leads: IconInbox,
  settings: IconSettings,
  'settings-users': IconUsersGroup,
  'settings-billing': IconCreditCard,
  'settings-tenants': IconBuilding,
  'settings-funnels': IconLayoutKanban,
  'settings-docs': IconFileText,
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
  onLogout,
  pendingHandoffsCount = 0,
}: SidebarProps) {
  const { t } = useI18n()
  const location = useLocation()
  const p = CRM_APP_PATHS
  const inboxNavActive =
    location.pathname.startsWith(p.communicationsInbox) ||
    location.pathname.startsWith(p.communicationsMessages) ||
    location.pathname.startsWith(p.communicationsEmail) ||
    location.pathname.startsWith(p.communicationsAppThreadsBase)
  const clientsNavActive = location.pathname.startsWith(p.agencyClients)
  const automationsNavActive = location.pathname.startsWith(p.appAutomationsAreaPrefix)
  const servicesWorkspacePath = location.pathname === p.servicesWorkspace
  const ordersStandalonePath = location.pathname === p.ordersEntry
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
  const { isClientTenant, role, can } = usePermissions()
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

  const resolvedNavPlan = useMemo(
    () => resolveNavPlanFromTeamOverview(canLoadTeamOverviewCtx, teamOverview),
    [canLoadTeamOverviewCtx, teamOverview],
  )

  const showFinanceSidebarSection = useMemo(
    () =>
      shouldShowFinanceNavSection({
        isClientTenant,
        businessType,
        resolvedNavPlan,
      }),
    [businessType, isClientTenant, resolvedNavPlan],
  )

  const isSoloWorkspace = useMemo(() => {
    const membersCount = Array.isArray(teamOverview?.members) ? teamOverview!.members.length : null
    if (typeof membersCount === 'number') return membersCount <= 1
    const usage = teamOverview?.usage
    if (!usage) return false
    const total =
      Number(usage.recruiter_count || 0) +
      Number(usage.supervisor_count || 0) +
      Number(usage.client_manager_count || 0) +
      Number(usage.viewer_count || 0)
    return total <= 1
  }, [teamOverview])

  const visibleItems = useMemo(() => {
    const moduleByItemKey: Partial<Record<string, keyof TenantModuleSettings>> = {
      candidates: 'candidates',
      'candidates-no-next-action': 'candidates',
      clients: 'companies',
      vacancies: 'vacancies',
      documents: 'documents',
      leads: 'leads',
      'leads-distribution': 'leads',
      'service-orders': 'services',
      services: 'services',
      invoices: 'services',
      tasks: 'candidates',
      communications: 'candidates',
      'communications-setup': 'candidates',
      inbox: 'candidates',
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
      if (item.key === 'communications-setup') {
        return canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email')
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
    const allowed = new Set(['work-hub', 'candidates', 'do-procesowania', 'tasks', 'inbox', 'analytics'])
    return moduleFiltered.filter((item) => allowed.has(item.key))
  }, [can, canUseCommunicationsFeature, isClientTenant, isSoloWorkspace, items, modules])

  /** SSOT §2.13: Dashboard / Inbox / Tasks / Work / System — Work row order below. */
  const {
    dashboardNavItems,
    inboxNavItems,
    tasksNavItems,
    analyticsNavItems,
    coreNavItems,
    businessNavItems,
    financeNavItems,
    systemNavItems,
    primaryNavItems,
    sidebarBucketed,
  } = useMemo(() => {
    const dashboardOrder = ['overview']
    const inboxOrder = ['inbox']
    const tasksOrder = ['tasks', 'calendar']
    const analyticsOrder = ['analytics']
    const businessOrderSsot = [
      'work-hub',
      'candidates',
      'clients',
      'do-procesowania',
      'vacancies',
      'service-orders',
      'services',
      'invoices',
      'documents',
      'leads',
      'leads-distribution',
    ]
    const workCoreOrderSsot = businessOrderSsot.filter((k) => !FINANCE_NAV_ORDER.includes(k as (typeof FINANCE_NAV_ORDER)[number]))
    const systemOrder = ['automations']

    const pickOrdered = (order: string[]) => {
      const idx = new Map(order.map((k, i) => [k, i]))
      return visibleItems
        .filter((item) => item.path && idx.has(item.key))
        .sort((a, b) => (idx.get(a.key) ?? 0) - (idx.get(b.key) ?? 0))
    }

    if (isClientTenant) {
      const order = ['inbox', 'tasks', 'analytics', 'candidates', 'do-procesowania']
      const flat = pickOrdered(order)
      return {
        dashboardNavItems: [] as NavItem[],
        inboxNavItems: [] as NavItem[],
        tasksNavItems: [] as NavItem[],
        analyticsNavItems: [] as NavItem[],
        coreNavItems: flat,
        businessNavItems: [] as NavItem[],
        financeNavItems: [] as NavItem[],
        systemNavItems: [] as NavItem[],
        primaryNavItems: flat,
        sidebarBucketed: false,
      }
    }

    const dashboardNavItems = pickOrdered(dashboardOrder)
    const inboxNavItems = pickOrdered(inboxOrder)
    const tasksNavItems = pickOrdered(tasksOrder)
    const analyticsNavItems = pickOrdered(analyticsOrder)
    const businessNavItems = pickOrdered(showFinanceSidebarSection ? workCoreOrderSsot : businessOrderSsot)
    const financeNavItems = showFinanceSidebarSection ? pickOrdered([...FINANCE_NAV_ORDER]) : []
    const systemNavItems = pickOrdered(systemOrder)
    const coreNavItems = [...dashboardNavItems, ...inboxNavItems, ...tasksNavItems, ...analyticsNavItems]
    const primaryNavItems = [...coreNavItems, ...businessNavItems, ...financeNavItems, ...systemNavItems]
    return {
      dashboardNavItems,
      inboxNavItems,
      tasksNavItems,
      analyticsNavItems,
      coreNavItems,
      businessNavItems,
      financeNavItems,
      systemNavItems,
      primaryNavItems,
      sidebarBucketed: true,
    }
  }, [isClientTenant, showFinanceSidebarSection, visibleItems])

  const sections = useMemo(() => {
    const sectionDefs: {
      key: string
      label: string
      itemKeys: string[]
      collapsible?: boolean
    }[] = isClientTenant
      ? []
      : [
          {
            key: 'account',
            label: t('app.shell.sidebar.account', { defaultValue: 'Account' }),
            itemKeys: ['profile'],
            collapsible: false,
          },
          {
            key: 'settings',
            label: t('app.nav.groups.admin'),
            itemKeys: [
              'settings',
              'settings-legal',
              'settings-users',
              'settings-company-access',
              'settings-funnels',
              'settings-docs',
              'settings-billing',
              'settings-communications',
              'communications-setup',
              'command-audit',
              'settings-email',
              'settings-integrations',
              'settings-tenant-links',
              'settings-tenants',
              'settings-ruleset',
              'settings-audit',
            ],
          },
        ]

    const byKey = new Map(visibleItems.filter((item) => Boolean(item.path)).map((item) => [item.key, item]))
    const usedKeys = new Set(primaryNavItems.map((item) => item.key))
    const mapped = sectionDefs
      .map((section) => {
        const sectionItems = section.itemKeys
          .map((itemKey) => byKey.get(itemKey))
          .filter((item): item is NavItem => Boolean(item))
        sectionItems.forEach((item) => usedKeys.add(item.key))
        return {
          key: section.key,
          label: section.label,
          items: sectionItems,
          collapsible: section.collapsible !== false,
        }
      })
      .filter((section) => section.items.length > 0)

    const leftovers = visibleItems.filter((item) => item.path && !usedKeys.has(item.key))
    if (leftovers.length > 0) {
      mapped.push({
        key: 'more',
        label: t('app.shell.sidebar.more', { defaultValue: 'More' }),
        items: leftovers,
      })
    }
    return mapped
  }, [isClientTenant, primaryNavItems, t, visibleItems])

  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(() => {
    if (typeof window === 'undefined') {
      return Object.fromEntries(sections.map((section) => [section.key, true]))
    }
    try {
      const raw = window.localStorage.getItem(GROUP_STORAGE_KEY)
      if (!raw) throw new Error('no-cache')
      const parsed = JSON.parse(raw)
      return { ...Object.fromEntries(sections.map((section) => [section.key, true])), ...parsed }
    } catch {
      return Object.fromEntries(sections.map((section) => [section.key, true]))
    }
  })

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(GROUP_STORAGE_KEY, JSON.stringify(expandedGroups))
  }, [expandedGroups])

  useEffect(() => {
    setExpandedGroups((prev) => {
      const next = { ...prev }
      sections.forEach((section) => {
        if (!(section.key in next)) {
          next[section.key] = true
        }
      })
      return next
    })
  }, [sections])

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
            className={() =>
              clsx(
                'block rounded-md px-3 py-2.5 text-sm font-medium transition',
                inboxNavActive
                  ? 'bg-white text-brand-900 shadow-sm'
                  : 'text-white hover:bg-white/15 hover:text-white',
              )
            }
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
                  to={p.communicationsInboxMessages}
                  title={t('app.nav.items.messages_inbox', { defaultValue: 'Messages' })}
                  onClick={handleNavigate}
                  className={() =>
                    clsx(
                      'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium transition',
                      location.pathname.startsWith(p.communicationsMessages) ||
                        (location.pathname.startsWith(p.communicationsInbox) && inboxChannelParam === 'messages')
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
                  to={p.communicationsInboxEmail}
                  title={t('app.nav.items.email_inbox', { defaultValue: 'Email' })}
                  onClick={handleNavigate}
                  className={() =>
                    clsx(
                      'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium transition',
                      location.pathname.startsWith(p.communicationsEmail) ||
                        (location.pathname.startsWith(p.communicationsInbox) && inboxChannelParam === 'email')
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
    return (
      <NavLink
        key={item.key}
        to={item.path!}
        title={getItemLabel(item)}
        onClick={handleNavigate}
        className={({ isActive }) =>
          clsx(
            'block rounded-md px-3 py-2.5 text-sm font-medium transition',
            (item.key === 'clients'
              ? clientsNavActive
              : item.key === 'work-hub'
                ? location.pathname.startsWith(p.workHub) || location.pathname.startsWith(`${p.workHub}/`)
                : item.key === 'automations'
                  ? automationsNavActive
                  : item.key === 'service-orders'
                    ? ordersNavActive
                    : item.key === 'services'
                      ? servicesModuleNavActive
                      : isActive)
              ? 'bg-white text-brand-900 shadow-sm'
              : 'text-white hover:bg-white/15 hover:text-white',
          )
        }
      >
        {(() => {
          const ItemIcon = ITEM_ICONS[item.key] || DEFAULT_ICON
          return (
            <span className="flex items-center justify-between gap-2">
              <span className="inline-flex items-center gap-2">
                <ItemIcon size={16} stroke={1.8} />
                <span>{item.key === 'clients' ? clientsNavLabel : getItemLabel(item)}</span>
              </span>
              {item.key === 'do-procesowania' && pendingHandoffsCount > 0 && (
                <span
                  className="inline-flex h-5 min-w-[20px] shrink-0 items-center justify-center rounded-full bg-rose-500 px-1.5 text-[11px] font-semibold text-white"
                  aria-label={t('app.handoff.badge_new', { count: pendingHandoffsCount })}
                >
                  {pendingHandoffsCount}
                </span>
              )}
            </span>
          )
        })()}
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
          <div className="px-4 py-4">
            <div className="text-xs uppercase tracking-[0.3em] text-white/60">
              {t('app.shell.sidebar.workspace')}
            </div>
            <div className="text-lg font-semibold">{tenantLabel}</div>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 pb-6">
            {sidebarBucketed ? (
              <>
                {dashboardNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">
                      {t('app.shell.sidebar.section_dashboard')}
                    </div>
                    <div className="space-y-1">{dashboardNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {inboxNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">
                      {t('app.shell.sidebar.section_inbox')}
                    </div>
                    <div className="space-y-1">{inboxNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {tasksNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">
                      {t('app.shell.sidebar.section_tasks')}
                    </div>
                    <div className="space-y-1">{tasksNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {analyticsNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">
                      {t('app.shell.sidebar.section_analytics')}
                    </div>
                    <div className="space-y-1">{analyticsNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {businessNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">
                      {t('app.shell.sidebar.work')}
                    </div>
                    <div className="space-y-1">{businessNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {financeNavItems.length > 0 && (
                  <div className="mb-3">
                    <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">
                      {t('app.shell.sidebar.section_finance', { defaultValue: 'Finance' })}
                    </div>
                    <div className="space-y-1">{financeNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
                {systemNavItems.length > 0 && (
                  <div className="mb-4">
                    <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">
                      {t('app.shell.sidebar.system')}
                    </div>
                    <div className="space-y-1">{systemNavItems.map(renderPrimaryNavItem)}</div>
                  </div>
                )}
              </>
            ) : (
              <div className="mb-4 space-y-1">{coreNavItems.map(renderPrimaryNavItem)}</div>
            )}

            {sections.length > 0 && primaryNavItems.length > 0 && (
              <div className="mx-4 my-4 border-t border-white/15" />
            )}

            {sections.map((section, index) => {
              const expanded = expandedGroups[section.key] ?? true
              const linkRow = (item: NavItem) => (
                <NavLink
                  key={item.key}
                  to={item.path!}
                  title={getItemLabel(item)}
                  onClick={handleNavigate}
                  className={({ isActive }) =>
                    clsx(
                      'block rounded-md px-3 py-2 text-sm transition',
                      (item.key === 'clients'
                        ? clientsNavActive
                        : item.key === 'work-hub'
                          ? location.pathname.startsWith(p.workHub) || location.pathname.startsWith(`${p.workHub}/`)
                          : item.key === 'automations'
                            ? automationsNavActive
                            : item.key === 'service-orders'
                              ? ordersNavActive
                              : item.key === 'services'
                                ? servicesModuleNavActive
                                : isActive)
                        ? 'bg-white text-brand-900'
                        : 'text-white/90 hover:bg-white/10',
                    )
                  }
                >
                  <span className="inline-flex items-center gap-2">
                    {(() => {
                      const ItemIcon = ITEM_ICONS[item.key] || DEFAULT_ICON
                      return <ItemIcon size={15} stroke={1.8} />
                    })()}
                    <span>{item.key === 'clients' ? clientsNavLabel : getItemLabel(item)}</span>
                  </span>
                </NavLink>
              )

              return (
                <div key={section.key} className="space-y-2">
                  <div>
                    {section.collapsible ? (
                      <>
                        <button
                          type="button"
                          className="flex w-full items-center justify-between rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-widest text-white/60 hover:bg-white/5"
                          onClick={() =>
                            setExpandedGroups((prev) => ({ ...prev, [section.key]: !expanded }))
                          }
                        >
                          <span>{section.label}</span>
                          <span
                            className={clsx(
                              'inline-flex transition-transform',
                              expanded ? 'rotate-0' : '-rotate-90'
                            )}
                          >
                            <IconChevronDown size={16} stroke={2} />
                          </span>
                        </button>
                        <div className={clsx('mt-2 space-y-1', !expanded && 'hidden')}>
                          {section.items.map(linkRow)}
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/45">
                          {section.label}
                        </div>
                        <div className="space-y-1">{section.items.map(linkRow)}</div>
                      </>
                    )}
                  </div>
                  {index < sections.length - 1 && (
                    <div className="mx-4 my-3 border-t border-white/15" />
                  )}
                </div>
              )
            })}
          </nav>

          <div className="border-t border-white/10 px-3 py-3 text-sm">
            <button
              type="button"
              className="flex w-full items-center justify-center gap-2 rounded-md border border-white/20 px-3 py-2 text-white/90 transition hover:bg-white/10"
              onClick={onLogout}
            >
              <IconLogout size={16} stroke={1.9} />
              {t('app.shell.actions.logout')}
            </button>
          </div>
        </div>
      </div>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onClose} role="presentation" />
      )}
    </>
  )
}
