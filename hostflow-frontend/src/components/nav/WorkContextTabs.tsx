import clsx from 'clsx'
import { useMemo } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

import { useTeamOverviewNav } from '../../contexts/TeamOverviewNavContext'
import { useBusinessTerminology } from '../../hooks/useBusinessTerminology'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'
import {
  type BusinessTypeNav,
  resolveNavPlanFromTeamOverview,
  shouldShowFinanceNavSection,
} from '../../nav/financeNavVisibility'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

function workShellActive(pathname: string): boolean {
  const p = CRM_APP_PATHS
  if (pathname === p.workHub) return true
  if (pathname.startsWith(`${p.workHub}/`)) return true
  if (pathname.startsWith(p.candidatesList)) return true
  if (pathname.startsWith(p.agencyClients)) return true
  if (pathname.startsWith(p.doProcesowania)) return true
  if (pathname.startsWith(p.vacanciesList)) return true
  if (pathname.startsWith(p.leadsWorkspace)) return true
  if (pathname === p.ordersEntry) return true
  if (pathname.startsWith(p.servicesWorkspace)) return true
  if (pathname.startsWith(p.invoices)) return true
  if (pathname.startsWith(p.documentsRegistry)) return true
  return false
}

type TabDef = {
  key: string
  to: string
  label: string
  isActive: (pathname: string, servicesTab: string | null) => boolean
}

export type WorkContextTabsProps = {
  businessType?: BusinessTypeNav
}

export default function WorkContextTabs({ businessType = 'agency' }: WorkContextTabsProps) {
  const { pathname, search } = useLocation()
  const { t } = useI18n()
  const { can, isClientTenant } = usePermissions()
  const { entityPlural: companiesLabel } = useBusinessTerminology()
  const { teamOverview, canLoadTeamOverview } = useTeamOverviewNav()

  const resolvedNavPlan = useMemo(
    () => resolveNavPlanFromTeamOverview(canLoadTeamOverview, teamOverview),
    [canLoadTeamOverview, teamOverview],
  )

  const showFinanceSplit = useMemo(
    () =>
      shouldShowFinanceNavSection({
        isClientTenant,
        businessType,
        resolvedNavPlan,
      }),
    [businessType, isClientTenant, resolvedNavPlan],
  )

  const servicesTab = useMemo(() => {
    try {
      return new URLSearchParams(search).get('tab')
    } catch {
      return null
    }
  }, [search])

  const showShell =
    can('candidates.view') ||
    can('companies.view') ||
    can('leads.view') ||
    can('vacancies.view') ||
    can('services.view') ||
    can('documents.manage')

  const { coreTabs, financeTabs } = useMemo(() => {
    const core: TabDef[] = []
    const finance: TabDef[] = []

    const financeDefs: TabDef[] = []
    if (can('services.view')) {
      financeDefs.push(
        {
          key: 'orders',
          to: CRM_APP_PATHS.orders,
          label: t('app.nav.items.orders'),
          isActive: (p, tab) =>
            p === CRM_APP_PATHS.orders ||
            (p.startsWith(CRM_APP_PATHS.services) && tab === 'orders'),
        },
        {
          key: 'services',
          to: CRM_APP_PATHS.services,
          label: t('app.nav.items.services'),
          isActive: (p, tab) => p.startsWith(CRM_APP_PATHS.services) && tab !== 'orders',
        },
        {
          key: 'invoices',
          to: CRM_APP_PATHS.invoices,
          label: t('app.nav.items.invoices'),
          isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.invoices),
        },
      )
    }

    if (showShell) {
      core.push({
        key: 'hub',
        to: CRM_APP_PATHS.work,
        label: t('app.nav.items.work'),
        isActive: (p, _tab) => p === CRM_APP_PATHS.work,
      })
    }
    if (can('candidates.view')) {
      core.push({
        key: 'candidates',
        to: CRM_APP_PATHS.candidates,
        label: t('app.nav.items.candidates'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.candidates),
      })
    }
    if (can('companies.view')) {
      core.push(
        {
          key: 'clients',
          to: CRM_APP_PATHS.clientsDirectory,
          label: companiesLabel,
          isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.agencyClients),
        },
        {
          key: 'processed',
          to: CRM_APP_PATHS.procesowani,
          label: t('app.nav.items.do_procesowania'),
          isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.procesowani),
        },
      )
    }
    if (can('vacancies.view')) {
      core.push({
        key: 'vacancies',
        to: CRM_APP_PATHS.vacancies,
        label: t('app.nav.items.vacancies'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.vacancies),
      })
    }
    if (can('documents.manage')) {
      core.push({
        key: 'documents',
        to: CRM_APP_PATHS.documents,
        label: t('app.nav.items.documents'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.documents),
      })
    }
    if (can('leads.view')) {
      core.push({
        key: 'leads',
        to: CRM_APP_PATHS.leads,
        label: t('app.nav.items.leads'),
        isActive: (p, _tab) => p.startsWith(CRM_APP_PATHS.leads),
      })
    }

    if (financeDefs.length > 0) {
      if (showFinanceSplit) {
        finance.push(...financeDefs)
      } else {
        core.push(...financeDefs)
      }
    }

    return { coreTabs: core, financeTabs: finance }
  }, [can, companiesLabel, showFinanceSplit, showShell, t])

  const allTabs = useMemo(() => [...coreTabs, ...financeTabs], [coreTabs, financeTabs])

  if (!workShellActive(pathname) || allTabs.length === 0) return null

  const renderTab = (tab: TabDef) => {
    const active = tab.isActive(pathname, servicesTab)
    return (
      <NavLink
        key={tab.key}
        to={tab.to}
        className={clsx(
          'shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition',
          active ? 'bg-white text-brand-800 shadow-sm ring-1 ring-slate-200' : 'text-slate-600 hover:bg-white/80 hover:text-slate-900',
        )}
      >
        {tab.label}
      </NavLink>
    )
  }

  return (
    <div className="sticky top-0 z-20 border-b border-slate-200 bg-slate-50/95 px-2 py-2 backdrop-blur supports-[backdrop-filter]:bg-slate-50/80">
      <nav
        className="flex max-w-full flex-wrap items-center gap-x-1 gap-y-1 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        aria-label={t('app.work.context_tabs.aria')}
      >
        {coreTabs.map(renderTab)}
        {showFinanceSplit && financeTabs.length > 0 ? (
          <>
            <span
              className="mx-1 inline-block h-4 w-px shrink-0 self-center bg-slate-200"
              role="separator"
              aria-orientation="vertical"
              aria-label={t('app.work.context_tabs.finance_group_aria')}
            />
            {financeTabs.map(renderTab)}
          </>
        ) : null}
      </nav>
    </div>
  )
}
