import clsx from 'clsx'
import { useMemo } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

/**
 * §2.13 ТЗ: глобальная горизонтальная полоса под top bar для быстрого переключения
 * между операционными разделами (не навигация «Работа» в узком смысле).
 */
function globalWorkStripVisible(pathname: string): boolean {
  const p = CRM_APP_PATHS
  if (pathname.startsWith(p.overview)) return false
  if (pathname.startsWith(p.inbox)) return false
  if (pathname.startsWith(p.tasks)) return false
  if (pathname.startsWith(p.calendar)) return false
  if (pathname.startsWith(p.workCalendar)) return false
  if (pathname.startsWith(p.procesowani)) return false
  if (pathname.startsWith(p.teamAvailability)) return false
  if (pathname.startsWith(p.myAvailability)) return false
  if (pathname.startsWith(p.timeOff)) return false
  if (pathname.startsWith(p.analytics)) return false
  if (pathname.startsWith(p.automations)) return false
  if (pathname.startsWith(p.automationAreaPrefix)) return false
  if (pathname === p.automationRules || pathname.startsWith(`${p.automationRules}/`)) return false
  if (pathname === p.automationLog || pathname.startsWith(`${p.automationLog}/`)) return false
  if (pathname.startsWith(p.leadsDistribution)) return false
  if (pathname.startsWith(p.setupCommunications)) return false
  if (pathname.startsWith(p.settingsIntegrations)) return false
  if (pathname.startsWith(p.settings)) return false
  if (pathname.startsWith(p.profile)) return false
  if (pathname.startsWith(p.myCompany)) return false
  if (pathname.startsWith(p.onboarding)) return false

  if (pathname === p.work || pathname.startsWith(`${p.work}/`)) return false
  if (pathname.startsWith(p.candidates)) return true
  if (pathname.startsWith(p.agencyClients)) return true
  if (pathname.startsWith(p.vacancies)) return true
  if (pathname.startsWith(p.documents)) return true
  if (pathname.startsWith(p.leads)) return true
  if (pathname === p.orders || pathname.startsWith(`${p.orders}/`)) return true
  if (pathname.startsWith(p.services)) return true
  if (pathname.startsWith(p.invoices)) return true
  return false
}

type TabDef = {
  key: string
  to: string
  label: string
  isActive: (pathname: string, servicesTab: string | null) => boolean
}

export type WorkContextTabsProps = {
  /** @deprecated kept for AppShell API compatibility */
  businessType?: 'agency' | 'employer' | 'services'
}

export default function WorkContextTabs(_props: WorkContextTabsProps) {
  const { pathname, search } = useLocation()
  const { t } = useI18n()
  const { can } = usePermissions()
  const { entityPlural: companiesLabel } = useBusinessTerminology()

  const servicesTab = useMemo(() => {
    try {
      return new URLSearchParams(search).get('tab')
    } catch {
      return null
    }
  }, [search])

  const tabs = useMemo(() => {
    const out: TabDef[] = []
    if (can('candidates.view')) {
      out.push({
        key: 'candidates',
        to: CRM_APP_PATHS.candidates,
        label: t('app.nav.items.candidates'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.candidates),
      })
    }
    if (can('companies.view')) {
      out.push({
        key: 'clients',
        to: CRM_APP_PATHS.clientsDirectory,
        label: companiesLabel,
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.agencyClients),
      })
    }
    if (can('vacancies.view')) {
      out.push({
        key: 'vacancies',
        to: CRM_APP_PATHS.vacancies,
        label: t('app.nav.items.vacancies'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.vacancies),
      })
    }
    if (can('documents.manage')) {
      out.push({
        key: 'documents',
        to: CRM_APP_PATHS.documents,
        label: t('app.nav.items.documents'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.documents),
      })
    }
    if (can('leads.view')) {
      out.push({
        key: 'leads',
        to: CRM_APP_PATHS.leads,
        label: t('app.nav.items.leads'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.leads),
      })
    }
    if (can('services.view')) {
      out.push(
        {
          key: 'orders',
          to: CRM_APP_PATHS.orders,
          label: t('app.nav.items.orders'),
          isActive: (p, tab) =>
            p === CRM_APP_PATHS.orders || (p.startsWith(CRM_APP_PATHS.services) && tab === 'orders'),
        },
        {
          key: 'invoices',
          to: CRM_APP_PATHS.invoices,
          label: t('app.nav.items.invoices'),
          isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.invoices),
        },
      )
    }
    return out
  }, [can, companiesLabel, t])

  if (!globalWorkStripVisible(pathname) || tabs.length === 0) return null

  return (
    <div className="sticky top-0 z-20 border-b border-slate-200 bg-slate-50/95 px-4 py-2 backdrop-blur supports-[backdrop-filter]:bg-slate-50/80 sm:px-5 lg:px-8">
      <nav
        className="flex max-w-full flex-wrap items-center gap-x-1 gap-y-1 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        aria-label={t('app.work.context_strip.aria', { defaultValue: 'Operational sections' })}
      >
        {tabs.map((tab) => {
          const active = tab.isActive(pathname, servicesTab)
          return (
            <NavLink
              key={tab.key}
              to={tab.to}
              className={clsx(
                'shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition',
                active
                  ? 'bg-white text-brand-800 shadow-sm ring-1 ring-slate-200'
                  : 'text-slate-600 hover:bg-white/80 hover:text-slate-900',
              )}
            >
              {tab.label}
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}
