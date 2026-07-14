import { Link, Navigate, useLocation } from 'react-router-dom'

import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'

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
    source === 'google' ? 'admin.integrations_hub.google_title' : 'admin.integrations_hub.webhook_title'
  const descKey =
    source === 'google' ? 'admin.integrations_hub.google_desc' : 'admin.integrations_hub.webhook_desc'

  return (
    <SettingsSubpageHeader
      backHref={CRM_APP_PATHS.settingsIntegrations}
      backLabel={t('admin.integrations_hub.back_to_hub')}
      kicker={t('admin.integrations_hub.integration_kicker', { defaultValue: 'Integration' })}
      title={
        <span className="inline-flex flex-wrap items-center gap-3">
          {t(titleKey)}
          <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-900">
            {t('admin.integrations_placeholder.badge')}
          </span>
        </span>
      }
      subtitle={t(descKey)}
      contentClassName="mx-auto w-full max-w-4xl gap-8"
    >

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-sm leading-relaxed text-slate-700 shadow-sm">
        <p>{t('admin.integrations_placeholder.body')}</p>
        <p className="mt-3 text-slate-600">{t('admin.integrations_placeholder.roadmap')}</p>
        <p className="mt-4">
          <Link to={CRM_APP_PATHS.settingsIntegrationsMeta} className="font-medium text-brand-600 hover:underline">
            {t('admin.integrations_placeholder.meta_cta')}
          </Link>
        </p>
      </div>
    </SettingsSubpageHeader>
  )
}
