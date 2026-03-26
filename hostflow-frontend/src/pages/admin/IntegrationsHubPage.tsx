import { useLocation, Navigate, Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

/**
 * §2.11 v0: product shell for lead sources. Per-source pages live under
 * `/app/settings/integrations/<source>` (Meta first).
 */
export default function IntegrationsHubPage() {
  const { t } = useI18n()
  const location = useLocation()
  const sp = new URLSearchParams(location.search || '')
  if (sp.has('tab')) {
    return <Navigate to={`${CRM_APP_PATHS.settingsIntegrationsMeta}${location.search}`} replace />
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-semibold text-slate-900">{t('app.admin.integrations_hub.title')}</h1>
      <p className="mt-2 text-sm text-slate-600">{t('app.admin.integrations_hub.subtitle')}</p>

      <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <li>
          <Link
            to={CRM_APP_PATHS.settingsIntegrationsMeta}
            className="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-400 hover:shadow"
          >
            <span className="text-lg font-semibold text-slate-900">{t('app.admin.integrations_hub.meta_title')}</span>
            <span className="mt-2 flex-1 text-sm text-slate-600">{t('app.admin.integrations_hub.meta_desc')}</span>
            <span className="mt-4 text-sm font-medium text-brand-600">{t('app.admin.integrations_hub.open')} →</span>
          </Link>
        </li>
        <li>
          <Link
            to={CRM_APP_PATHS.settingsIntegrationsGoogle}
            className="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-400 hover:shadow"
          >
            <span className="text-lg font-semibold text-slate-900">{t('app.admin.integrations_hub.google_title')}</span>
            <span className="mt-2 flex-1 text-sm text-slate-600">{t('app.admin.integrations_hub.google_desc')}</span>
            <span className="mt-4 text-sm font-medium text-brand-600">{t('app.admin.integrations_hub.open')} →</span>
          </Link>
        </li>
        <li className="sm:col-span-2 lg:col-span-1">
          <Link
            to={CRM_APP_PATHS.settingsIntegrationsWebhook}
            className="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-400 hover:shadow"
          >
            <span className="text-lg font-semibold text-slate-900">{t('app.admin.integrations_hub.webhook_title')}</span>
            <span className="mt-2 flex-1 text-sm text-slate-600">{t('app.admin.integrations_hub.webhook_desc')}</span>
            <span className="mt-4 text-sm font-medium text-brand-600">{t('app.admin.integrations_hub.open')} →</span>
          </Link>
        </li>
      </ul>
    </div>
  )
}
