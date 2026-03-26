import { Link, Navigate, useLocation } from 'react-router-dom'

import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

type PlaceholderSource = 'google' | 'webhook'

function sourceFromPathname(pathname: string): PlaceholderSource | null {
  const seg = pathname.replace(/\/+$/, '').split('/').pop() || ''
  if (seg === 'google' || seg === 'webhook') return seg
  return null
}

/**
 * §2.11: per-source shell for lead integrations not yet implemented (Google Ads, Webhook).
 * Same entry pattern as Meta — full product pages replace this later.
 */
export default function IntegrationsSourcePlaceholderPage() {
  const { t } = useI18n()
  const { pathname } = useLocation()
  const source = sourceFromPathname(pathname)
  if (!source) return <Navigate to={CRM_APP_PATHS.settingsIntegrations} replace />

  const titleKey =
    source === 'google' ? 'app.admin.integrations_hub.google_title' : 'app.admin.integrations_hub.webhook_title'
  const descKey =
    source === 'google' ? 'app.admin.integrations_hub.google_desc' : 'app.admin.integrations_hub.webhook_desc'

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <div>
        <Link to={CRM_APP_PATHS.settingsIntegrations} className="text-sm font-medium text-brand-600 hover:underline">
          {t('app.admin.integrations_hub.back_to_hub')}
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-slate-900">{t(titleKey)}</h1>
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-900">
            {t('app.admin.integrations_placeholder.badge')}
          </span>
        </div>
        <p className="mt-2 text-sm text-slate-600">{t(descKey)}</p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-5 text-sm text-slate-700">
        <p>{t('app.admin.integrations_placeholder.body')}</p>
        <p className="mt-3 text-slate-600">{t('app.admin.integrations_placeholder.roadmap')}</p>
        <p className="mt-4">
          <Link to={CRM_APP_PATHS.settingsIntegrationsMeta} className="font-medium text-brand-600 hover:underline">
            {t('app.admin.integrations_placeholder.meta_cta')}
          </Link>
        </p>
      </div>
    </div>
  )
}
