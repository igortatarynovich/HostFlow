import clsx from 'clsx'
import { useMemo } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { RECRUITMENT_INBOX_PATH } from '../../app/recruitmentInboxPaths'

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
  if (pathname.startsWith(p.recruitmentSearches)) return true
  if (pathname.startsWith(RECRUITMENT_INBOX_PATH)) return true
  if (pathname.startsWith(p.sales)) return true

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

export default function WorkContextTabs({ businessType = 'agency' }: WorkContextTabsProps) {
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
    if (can('leads.view')) {
      out.push({
        key: 'recruitment-inbox',
        to: RECRUITMENT_INBOX_PATH,
        label: t('app.nav.items.recruitment_inbox', { defaultValue: 'Отклики' }),
        isActive: (p, _tab) => p.startsWith(RECRUITMENT_INBOX_PATH),
      })
      if (businessType === 'services') {
        out.push({
          key: 'sales',
          to: CRM_APP_PATHS.sales,
          label: t('app.nav.items.sales', { defaultValue: 'Обращения' }),
          isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.sales),
        })
      }
    }
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
    if (can('documents.manage')) {
      out.push({
        key: 'documents',
        to: CRM_APP_PATHS.documents,
        label: t('app.nav.items.documents'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.documents),
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
  }, [can, companiesLabel, t, businessType])

  if (!globalWorkStripVisible(pathname) || tabs.length === 0) return null

  return (
    <div className="sticky top-0 z-20 border-b border-slate-200 bg-slate-50/95 px-3 py-0.5 backdrop-blur supports-[backdrop-filter]:bg-slate-50/80 sm:px-4 lg:px-6">
      <nav
        className="flex max-w-full flex-nowrap items-center gap-x-0.5 overflow-x-auto py-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        aria-label={t('app.work.context_strip.aria', { defaultValue: 'Operational sections' })}
      >
        {tabs.map((tab) => {
          const active = tab.isActive(pathname, servicesTab)
          return (
            <NavLink
              key={tab.key}
              to={tab.to}
              className={clsx(
                'shrink-0 rounded-md px-2.5 py-1 text-xs font-medium transition',
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
