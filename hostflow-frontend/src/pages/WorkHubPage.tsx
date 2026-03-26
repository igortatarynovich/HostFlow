import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { getOnboardingStatus } from '../api/client'
import { useTeamOverviewNav } from '../contexts/TeamOverviewNavContext'
import { useBusinessTerminology } from '../hooks/useBusinessTerminology'
import { useCommunicationsAccess } from '../hooks/useCommunicationsAccess'
import { usePermissions } from '../hooks/usePermissions'
import { useI18n } from '../i18n'
import {
  type BusinessTypeNav,
  resolveNavPlanFromTeamOverview,
  shouldShowFinanceNavSection,
} from '../nav/financeNavVisibility'
import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../app/crmAppPaths'
import { useAuth } from '../store/useAuth'

export default function WorkHubPage() {
  const { t } = useI18n()
  const { me } = useAuth()
  const { can, isClientTenant } = usePermissions()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const { entityPlural: companiesLabel } = useBusinessTerminology()
  const { teamOverview, canLoadTeamOverview } = useTeamOverviewNav()
  const [businessType, setBusinessType] = useState<BusinessTypeNav>('agency')

  useEffect(() => {
    if (!me?.tenant_id) return
    let cancelled = false
    getOnboardingStatus()
      .then((r) => {
        if (!cancelled && r?.business_type) setBusinessType(r.business_type)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [me?.tenant_id])

  const resolvedNavPlan = useMemo(
    () => resolveNavPlanFromTeamOverview(canLoadTeamOverview, teamOverview),
    [canLoadTeamOverview, teamOverview],
  )

  const showFinanceHubSection = useMemo(
    () =>
      shouldShowFinanceNavSection({
        isClientTenant,
        businessType,
        resolvedNavPlan,
      }),
    [businessType, isClientTenant, resolvedNavPlan],
  )

  const showCandidates = can('candidates.view')
  const showCompanies = can('companies.view')
  const showLeads = can('leads.view')
  const showVacancies = can('vacancies.view')
  const showServices = can('services.view')
  const showDocuments = can('documents.manage')
  const showSlaIncidents =
    can('notifications.view') &&
    (canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email'))

  const cardClass =
    'block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300 hover:shadow-md'

  const coreCards = (
    <>
      {showCandidates ? (
        <li>
          <Link to={CRM_APP_PATHS.candidates} className={cardClass}>
            <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.candidates')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_candidates_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showCandidates ? (
        <li>
          <Link to={CRM_APP_PATHS.candidatesNoNextActionPage} className={cardClass}>
            <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.no_next_action')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_no_next_action_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showSlaIncidents ? (
        <li>
          <Link to={CRM_APP_PATHS.slaIncidents} className={cardClass}>
            <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.sla_incidents')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_sla_incidents_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showCompanies ? (
        <li>
          <Link to={CRM_APP_PATHS.clientsDirectory} className={cardClass}>
            <div className="text-sm font-semibold text-slate-900">{companiesLabel}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_companies_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showCompanies ? (
        <li>
          <Link to={CRM_APP_PATHS.procesowani} className={cardClass}>
            <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.do_procesowania')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_processed_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showVacancies ? (
        <li>
          <Link to={CRM_APP_PATHS.vacancies} className={cardClass}>
            <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.vacancies')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_vacancies_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showDocuments ? (
        <li>
          <Link to={CRM_APP_PATHS.documents} className={cardClass}>
            <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.documents')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_documents_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showLeads ? (
        <li>
          <Link to={CRM_APP_PATHS.leads} className={cardClass}>
            <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.leads')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_leads_desc')}</p>
          </Link>
        </li>
      ) : null}
    </>
  )

  const financeCards = showServices ? (
    <>
      <li>
        <Link to={CRM_APP_DRILLDOWN_HREFS.ordersOpen} className={cardClass}>
          <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.orders')}</div>
          <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_orders_desc')}</p>
        </Link>
      </li>
      <li>
        <Link to={CRM_APP_PATHS.services} className={cardClass}>
          <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.services')}</div>
          <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_services_desc')}</p>
        </Link>
      </li>
      <li>
        <Link to={CRM_APP_PATHS.invoices} className={cardClass}>
          <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.invoices')}</div>
          <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_invoices_desc')}</p>
        </Link>
      </li>
    </>
  ) : null

  const hasFinance = Boolean(showServices)
  const hasCore =
    showCandidates ||
    showCompanies ||
    showLeads ||
    showVacancies ||
    showDocuments ||
    showSlaIncidents
  const hasAny = hasCore || hasFinance

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="text-xl font-semibold text-slate-900">{t('app.work.hub.title')}</h1>
      <p className="mt-1 text-sm text-slate-600">{t('app.work.hub.subtitle')}</p>

      {showFinanceHubSection && hasFinance && hasCore ? (
        <>
          <h2 className="mt-10 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            {t('app.work.hub.section_core')}
          </h2>
          <ul className="mt-3 grid gap-4 sm:grid-cols-2">{coreCards}</ul>
          <h2 className="mt-10 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            {t('app.shell.sidebar.section_finance')}
          </h2>
          <ul className="mt-3 grid gap-4 sm:grid-cols-2">{financeCards}</ul>
        </>
      ) : showFinanceHubSection && hasFinance && !hasCore ? (
        <>
          <h2 className="mt-10 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            {t('app.shell.sidebar.section_finance')}
          </h2>
          <ul className="mt-3 grid gap-4 sm:grid-cols-2">{financeCards}</ul>
        </>
      ) : (
        <ul className="mt-8 grid gap-4 sm:grid-cols-2">
          {coreCards}
          {financeCards}
        </ul>
      )}

      {!hasAny ? <p className="mt-8 text-sm text-slate-500">{t('app.work.hub.empty')}</p> : null}
    </div>
  )
}
