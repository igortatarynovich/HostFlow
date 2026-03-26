import { Link } from 'react-router-dom'

import { useCommunicationsAccess } from '../hooks/useCommunicationsAccess'
import { usePermissions } from '../hooks/usePermissions'
import { useI18n } from '../i18n'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

export default function AnalyticsHubPage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const showWorkHub =
    can('candidates.view') ||
    can('companies.view') ||
    can('leads.view') ||
    can('vacancies.view') ||
    can('services.view') ||
    can('documents.manage')
  const showLeads = can('leads.view')
  const showTtv = can('admin.users')
  const showCandidates = can('candidates.view')
  const showSlaIncidents =
    can('notifications.view') &&
    (canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email'))

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="text-xl font-semibold text-slate-900">{t('app.analytics.hub.title')}</h1>
      <p className="mt-1 text-sm text-slate-600">{t('app.analytics.hub.subtitle')}</p>

      <ul className="mt-8 grid gap-4 sm:grid-cols-2">
        <li>
          <Link
            to={CRM_APP_PATHS.overview}
            className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300 hover:shadow-md"
          >
            <div className="text-sm font-semibold text-slate-900">{t('app.analytics.hub.card_dashboard_title')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.analytics.hub.card_dashboard_desc')}</p>
          </Link>
        </li>
        {showWorkHub ? (
          <li>
            <Link
              to={CRM_APP_PATHS.work}
              className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300 hover:shadow-md"
            >
              <div className="text-sm font-semibold text-slate-900">{t('app.analytics.hub.card_work_title')}</div>
              <p className="mt-1 text-xs text-slate-600">{t('app.analytics.hub.card_work_desc')}</p>
            </Link>
          </li>
        ) : null}
        {showLeads ? (
          <li>
            <Link
              to={CRM_APP_PATHS.leads}
              className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300 hover:shadow-md"
            >
              <div className="text-sm font-semibold text-slate-900">{t('app.analytics.hub.card_leads_title')}</div>
              <p className="mt-1 text-xs text-slate-600">{t('app.analytics.hub.card_leads_desc')}</p>
            </Link>
          </li>
        ) : null}
        {showCandidates ? (
          <li>
            <Link
              to={CRM_APP_PATHS.candidatesNoNextActionPage}
              className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300 hover:shadow-md"
            >
              <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.no_next_action')}</div>
              <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_no_next_action_desc')}</p>
            </Link>
          </li>
        ) : null}
        {showSlaIncidents ? (
          <li>
            <Link
              to={CRM_APP_PATHS.slaIncidents}
              className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300 hover:shadow-md"
            >
              <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.sla_incidents')}</div>
              <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_sla_incidents_desc')}</p>
            </Link>
          </li>
        ) : null}
        {showLeads ? (
          <li>
            <Link
              to={CRM_APP_PATHS.leadsDistribution}
              className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300 hover:shadow-md"
            >
              <div className="text-sm font-semibold text-slate-900">{t('app.nav.items.leads_distribution')}</div>
              <p className="mt-1 text-xs text-slate-600">{t('app.analytics.hub.card_leads_distribution_desc')}</p>
            </Link>
          </li>
        ) : null}
        {showTtv ? (
          <li>
            <Link
              to={CRM_APP_PATHS.settingsTtvReport}
              className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-brand-300 hover:shadow-md"
            >
              <div className="text-sm font-semibold text-slate-900">{t('app.analytics.hub.card_ttv_title')}</div>
              <p className="mt-1 text-xs text-slate-600">{t('app.analytics.hub.card_ttv_desc')}</p>
            </Link>
          </li>
        ) : null}
      </ul>
    </div>
  )
}
