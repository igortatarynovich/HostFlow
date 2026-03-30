import { Link } from 'react-router-dom'
import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useCommunicationsAccess } from '../../hooks/useCommunicationsAccess'
import { usePermissions } from '../../hooks/usePermissions'
import { useI18n } from '../../i18n'

/** Shortcuts previously on the standalone Analytics hub (for workspaces without lead analytics). */
export function DashboardAnalyticsHubLinks() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()

  const showWorkHub =
    can('candidates.view') ||
    can('companies.view') ||
    can('vacancies.view') ||
    can('services.view') ||
    can('documents.manage')
  const showTtv = can('admin.users')
  const showCandidates = can('candidates.view')
  const showSlaIncidents =
    can('notifications.view') &&
    (canUseCommunicationsFeature('messages') || canUseCommunicationsFeature('email'))

  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {showWorkHub ? (
        <li>
          <Link
            to={CRM_APP_PATHS.work}
            className="block rounded-lg border border-slate-100 bg-slate-50/80 p-3 text-sm transition hover:border-brand-200 hover:bg-white"
          >
            <div className="font-semibold text-slate-900">{t('app.analytics.hub.card_work_title')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.analytics.hub.card_work_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showCandidates ? (
        <li>
          <Link
            to={CRM_APP_DRILLDOWN_HREFS.candidatesQueueNoNextAction}
            className="block rounded-lg border border-slate-100 bg-slate-50/80 p-3 text-sm transition hover:border-brand-200 hover:bg-white"
          >
            <div className="font-semibold text-slate-900">{t('app.nav.items.no_next_action')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_no_next_action_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showSlaIncidents ? (
        <li>
          <Link
            to={CRM_APP_PATHS.slaIncidents}
            className="block rounded-lg border border-slate-100 bg-slate-50/80 p-3 text-sm transition hover:border-brand-200 hover:bg-white"
          >
            <div className="font-semibold text-slate-900">{t('app.nav.items.sla_incidents')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.work.hub.card_sla_incidents_desc')}</p>
          </Link>
        </li>
      ) : null}
      {showTtv ? (
        <li>
          <Link
            to={CRM_APP_PATHS.settingsTtvReport}
            className="block rounded-lg border border-slate-100 bg-slate-50/80 p-3 text-sm transition hover:border-brand-200 hover:bg-white"
          >
            <div className="font-semibold text-slate-900">{t('app.analytics.hub.card_ttv_title')}</div>
            <p className="mt-1 text-xs text-slate-600">{t('app.analytics.hub.card_ttv_desc')}</p>
          </Link>
        </li>
      ) : null}
    </ul>
  )
}
