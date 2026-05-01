import { useEffect, useMemo, useState } from 'react'
import { useLocation, Navigate, Link } from 'react-router-dom'
import {
  IconBrandGoogle,
  IconBrandInstagram,
  IconBrandMeta,
  IconBrandMessenger,
  IconBrandTelegram,
  IconBrandWhatsapp,
  IconMail,
  IconMessageCircle,
  IconWebhook,
} from '@tabler/icons-react'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { listMetaLeadCredentials } from '../../api/metaLeads'
import { usePermissions } from '../../hooks/usePermissions'
import { useCommunicationsAccess, type CommunicationsFeatureKey } from '../../hooks/useCommunicationsAccess'
import { MESSENGER_CHANNELS, type MessengerChannel } from './communicationsMessengerChannels'

type ConnectionTile = {
  key: string
  titleKey: string
  descKey: string
  to: string
  Icon: TablerIcon
  permission?: 'admin.metaLeads' | 'admin.users'
  commFeatureAny?: CommunicationsFeatureKey[]
  /** Show Meta connected / not connected badge */
  showMetaStatus?: boolean
}

const MESSENGER_INTEGRATION_ICONS: Record<MessengerChannel, TablerIcon> = {
  telegram: IconBrandTelegram,
  whatsapp: IconBrandWhatsapp,
  viber: IconMessageCircle,
  messenger: IconBrandMessenger,
  instagram: IconBrandInstagram,
}

const MESSENGER_INTEGRATION_PATHS: Record<MessengerChannel, keyof typeof CRM_APP_PATHS> = {
  telegram: 'settingsIntegrationsMessengerTelegram',
  whatsapp: 'settingsIntegrationsMessengerWhatsapp',
  viber: 'settingsIntegrationsMessengerViber',
  messenger: 'settingsIntegrationsMessengerFacebook',
  instagram: 'settingsIntegrationsMessengerInstagram',
}

export default function IntegrationsHubPage() {
  const { t } = useI18n()
  const { can } = usePermissions()
  const { canUseCommunicationsFeature } = useCommunicationsAccess()
  const location = useLocation()
  const sp = new URLSearchParams(location.search || '')
  const redirectToMeta = sp.has('tab')

  const [metaCredCount, setMetaCredCount] = useState<number | null>(null)
  useEffect(() => {
    let cancelled = false
    if (!can('admin.metaLeads')) {
      setMetaCredCount(null)
      return
    }
    listMetaLeadCredentials()
      .then((rows) => {
        if (!cancelled) setMetaCredCount(Array.isArray(rows) ? rows.length : 0)
      })
      .catch(() => {
        if (!cancelled) setMetaCredCount(null)
      })
    return () => {
      cancelled = true
    }
  }, [can])

  const connectionTiles: ConnectionTile[] = useMemo(() => {
    const messengerTiles: ConnectionTile[] = MESSENGER_CHANNELS.map((ch) => ({
      key: `messenger-${ch}`,
      titleKey: `admin.communications_messengers.channels.${ch}.title`,
      descKey: `admin.communications_messengers.channels.${ch}.subtitle`,
      to: CRM_APP_PATHS[MESSENGER_INTEGRATION_PATHS[ch]],
      Icon: MESSENGER_INTEGRATION_ICONS[ch],
      permission: 'admin.users',
      commFeatureAny: ['communicationsAdmin'],
    }))
    return [
      {
        key: 'meta',
        titleKey: 'admin.integrations_hub.meta_title',
        descKey: 'admin.integrations_hub.meta_desc_short',
        to: CRM_APP_PATHS.settingsIntegrationsMeta,
        Icon: IconBrandMeta,
        permission: 'admin.metaLeads',
        showMetaStatus: true,
      },
      {
        key: 'email',
        titleKey: 'admin.integrations_hub.email_title',
        descKey: 'admin.integrations_hub.email_desc_short',
        to: CRM_APP_PATHS.settingsEmail,
        Icon: IconMail,
        permission: 'admin.users',
      },
      ...messengerTiles,
      {
        key: 'webhook',
        titleKey: 'admin.integrations_hub.webhook_title',
        descKey: 'admin.integrations_hub.webhook_desc_short',
        to: CRM_APP_PATHS.settingsIntegrationsWebhook,
        Icon: IconWebhook,
        permission: 'admin.metaLeads',
      },
      {
        key: 'google',
        titleKey: 'admin.integrations_hub.google_title',
        descKey: 'admin.integrations_hub.google_desc',
        to: CRM_APP_PATHS.settingsIntegrationsGoogle,
        Icon: IconBrandGoogle,
        permission: 'admin.users',
      },
    ]
  }, [])

  const visibleConnections = useMemo(
    () =>
      connectionTiles.filter((tile) => {
        if (tile.permission && !can(tile.permission)) return false
        if (tile.commFeatureAny?.length) {
          const ok = tile.commFeatureAny.some((f) => canUseCommunicationsFeature(f))
          if (!ok) return false
        }
        return true
      }),
    [can, canUseCommunicationsFeature, connectionTiles],
  )

  if (redirectToMeta) {
    return <Navigate to={`${CRM_APP_PATHS.settingsIntegrationsMeta}${location.search}`} replace />
  }

  return (
    <div className="settings-page-shell py-6 sm:py-8">
      <SettingsSubpageHeader
        backHref={CRM_APP_PATHS.settings}
        backLabel={t('admin.settings.subpage.back_all', { defaultValue: '← All settings' })}
        kicker={t('admin.integrations_hub.header_kicker', { defaultValue: 'Integrations' })}
        title={t('admin.integrations_hub.title')}
        subtitle={t('admin.integrations_hub.subtitle_v3')}
      />

      <section aria-labelledby="integrations-hub-connections-heading">
        <h2 id="integrations-hub-connections-heading" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('admin.integrations_hub.section_connections')}
        </h2>
        <ul className="mt-4 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {visibleConnections.map((tile) => {
            const metaActive = tile.showMetaStatus && metaCredCount !== null && metaCredCount > 0
            const metaUnknown = tile.showMetaStatus && metaCredCount === null && can('admin.metaLeads')
            return (
              <li key={tile.key}>
                <Link
                  to={tile.to}
                  className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-400 hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <span
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-100 bg-slate-50 text-brand-700"
                        aria-hidden
                      >
                        <tile.Icon size={22} stroke={1.75} aria-hidden />
                      </span>
                      <span className="text-lg font-semibold leading-snug text-slate-900">
                        {t(tile.titleKey as any)}
                      </span>
                    </div>
                    {tile.showMetaStatus && can('admin.metaLeads') ? (
                      <span
                        className={[
                          'shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                          metaActive ? 'bg-emerald-100 text-emerald-800' : metaUnknown ? 'bg-slate-100 text-slate-600' : 'bg-amber-50 text-amber-800',
                        ].join(' ')}
                        title={t('admin.integrations_hub.status_hint')}
                      >
                        {metaActive
                          ? t('admin.integrations_hub.status_active')
                          : metaUnknown
                            ? t('admin.integrations_hub.status_unknown')
                            : t('admin.integrations_hub.status_setup')}
                      </span>
                    ) : (
                      <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                        {t('admin.integrations_hub.screen_badge')}
                      </span>
                    )}
                  </div>
                  <span className="mt-3 flex-1 text-sm text-slate-600">{t(tile.descKey as any)}</span>
                  <span className="mt-4 text-sm font-medium text-brand-600">{t('admin.integrations_hub.open')} →</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </section>

      
    </div>
  )
}
