import clsx from 'clsx'
import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import {
  IconBell,
  IconBuilding,
  IconCalendarEvent,
  IconCalendarOff,
  IconChevronDown,
  IconChecklist,
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
  IconSettings,
  IconShield,
  IconUsers,
  IconUser,
  IconUsersGroup,
} from '@tabler/icons-react'
import type { TenantSummary } from '../../api/types'
import type { NavItem } from '../../app/routes'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import { useCommunicationsAccess } from '../../hooks/useCommunicationsAccess'
import { getTeamOverview, getTenantModules } from '../../api/tenants'
import type { TeamOverviewResponse, TenantModuleSettings } from '../../api/types'
import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'

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

const ITEM_ICONS: Partial<Record<string, TablerIcon>> = {
  overview: IconDashboard,
  candidates: IconUsers,
  clients: IconBuilding,
  'do-procesowania': IconFilter,
  vacancies: IconLayoutKanban,
  documents: IconFileText,
  services: IconChecklist,
  invoices: IconFileText,
  'communications-setup': IconPlugConnected,
  inbox: IconInbox,
  tasks: IconChecklist,
  calendar: IconCalendarEvent,
  'sla-incidents': IconBell,
  'command-audit': IconShield,
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

export function Sidebar({ items, tenant, businessType = 'agency', open, onClose, onLogout, pendingHandoffsCount = 0 }: SidebarProps) {
  const { t } = useI18n()
  const location = useLocation()
  const inboxNavActive =
    location.pathname.startsWith('/app/messages') || location.pathname.startsWith('/app/email')
  const { isClientTenant, role } = usePermissions()
  /** Matches backend `GET /settings/team` (administrator | supervisor only). */
  const canLoadTeamOverview = role === 'administrator' || role === 'supervisor'
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const [modules, setModules] = useState<TenantModuleSettings | null>(null)
  const [teamOverview, setTeamOverview] = useState<TeamOverviewResponse | null>(null)

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        if (!tenant?.id) {
          if (mounted) {
            setModules(null)
            setTeamOverview(null)
          }
          return
        }
        const [modulesData, teamData] = await Promise.all([
          getTenantModules({ tenantId: tenant.id }),
          canLoadTeamOverview
            ? getTeamOverview({ tenantId: tenant.id }).catch(() => null)
            : Promise.resolve(null),
        ])
        if (mounted) {
          setModules(modulesData)
          setTeamOverview(teamData)
        }
      } catch {
        if (mounted) {
          setModules(null)
          setTeamOverview(null)
        }
      }
    })()
    return () => {
      mounted = false
    }
  }, [tenant?.id, canLoadTeamOverview])

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
      clients: 'companies',
      vacancies: 'vacancies',
      documents: 'documents',
      leads: 'leads',
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
      if (item.key === 'communications') return false
      if (item.key === 'team-availability' && isSoloWorkspace) return false
      if (item.key === 'communications-setup') {
        return canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email')
      }
      if (item.key === 'inbox') {
        return canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email')
      }
      if (item.key === 'sla-incidents') {
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
    const allowed = new Set(['candidates', 'do-procesowania', 'tasks', 'sla-incidents', 'inbox'])
    return moduleFiltered.filter((item) => allowed.has(item.key))
  }, [canUseCommunicationsFeature, isClientTenant, isSoloWorkspace, items, modules])

  // Основные элементы, которые выносим наверх (business-type order: services = client-first, employer = vacancy-first, agency = candidate-first)
  const mainItems = useMemo(() => {
    const order = isClientTenant
      ? ['candidates', 'do-procesowania', 'inbox', 'tasks', 'sla-incidents']
      : businessType === 'services'
        ? [
            'inbox',
            'tasks',
            'calendar',
            'sla-incidents',
            'clients',
            'candidates',
            'services',
            'invoices',
            'overview',
            'vacancies',
            'leads',
          ]
        : businessType === 'employer'
          ? [
              'inbox',
              'tasks',
              'calendar',
              'sla-incidents',
              'overview',
              'vacancies',
              'candidates',
              'clients',
              'do-procesowania',
              'services',
              'invoices',
              'leads',
            ]
          : [
              'inbox',
              'tasks',
              'calendar',
              'sla-incidents',
              'overview',
              'candidates',
              'clients',
              'do-procesowania',
              'vacancies',
              'services',
              'invoices',
              'leads',
            ]
    const mainKeys = new Set(order)
    const filtered = visibleItems.filter(
      (item) =>
        item.path &&
        (isClientTenant
          ? item.key === 'candidates' ||
            item.key === 'do-procesowania' ||
            item.key === 'inbox' ||
            item.key === 'tasks' ||
            item.key === 'sla-incidents'
          : mainKeys.has(item.key))
    )
    return filtered.sort((a, b) => {
      const indexA = order.indexOf(a.key)
      const indexB = order.indexOf(b.key)
      return indexA - indexB
    })
  }, [isClientTenant, businessType, visibleItems])

  const sections = useMemo(() => {
    const sectionDefs = isClientTenant
      ? [
          {
            key: 'client-workflow',
            label: t('app.shell.sidebar.client_workflow', { defaultValue: 'Client Workflow' }),
            itemKeys: ['sla-incidents'],
          },
        ]
      : [
          {
            key: 'operations',
            label: t('app.shell.sidebar.operations', { defaultValue: 'Operations' }),
            itemKeys: ['documents', 'services', 'invoices', 'sla-incidents'],
          },
          {
            key: 'communications',
            label: t('app.shell.sidebar.communications_workspace', { defaultValue: 'Communications Workspace' }),
            itemKeys: ['communications-setup', 'calendar', 'command-audit', 'team-availability', 'my-availability', 'time-off'],
          },
          {
            key: 'leads',
            label: t('app.nav.groups.leads'),
            itemKeys: ['leads'],
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
    const usedKeys = new Set(mainItems.map((item) => item.key))
    const mapped = sectionDefs
      .map((section) => {
        const sectionItems = section.itemKeys
          .map((itemKey) => byKey.get(itemKey))
          .filter((item): item is NavItem => Boolean(item))
        sectionItems.forEach((item) => usedKeys.add(item.key))
        return { key: section.key, label: section.label, items: sectionItems }
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
  }, [isClientTenant, mainItems, t, visibleItems])

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
            {/* Основные элементы - всегда видны, выделены */}
            <div className="mb-4 space-y-1">
              {mainItems.map((item) => (
                <NavLink
                  key={item.key}
                  to={item.path!}
                  title={getItemLabel(item)}
                  onClick={handleNavigate}
                  className={({ isActive }) =>
                    clsx(
                      'block rounded-md px-3 py-2.5 text-sm font-medium transition',
                      (item.key === 'inbox' ? inboxNavActive : isActive)
                        ? 'bg-white text-brand-900 shadow-sm'
                        : 'text-white hover:bg-white/15 hover:text-white'
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
              ))}
            </div>

            {/* Разделитель перед остальными секциями */}
            {sections.length > 0 && mainItems.length > 0 && (
              <div className="mx-4 my-4 border-t border-white/15" />
            )}

            {/* Остальные секции - раздвижные */}
            {sections.map((section, index) => {
              const expanded = expandedGroups[section.key] ?? true
              return (
                <div key={section.key} className="space-y-2">
                  <div>
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
                      {section.items.map((item) => (
                        <NavLink
                          key={item.key}
                          to={item.path!}
                          title={getItemLabel(item)}
                          onClick={handleNavigate}
                          className={({ isActive }) =>
                            clsx(
                              'block rounded-md px-3 py-2 text-sm transition',
                              isActive ? 'bg-white text-brand-900' : 'text-white/90 hover:bg-white/10'
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
                      ))}
                    </div>
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
