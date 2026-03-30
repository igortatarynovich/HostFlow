import { useEffect, useMemo, useState } from 'react'
import { useLocation, Navigate, Link } from 'react-router-dom'
import {
  IconBell,
  IconBrandGoogle,
  IconBrandMeta,
  IconFilter,
  IconInbox,
  IconMail,
  IconMessageCircle,
  IconMessages,
  IconWebhook,
} from '@tabler/icons-react'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { listMetaLeadCredentials } from '../../api/metaLeads'
import { usePermissions } from '../../hooks/usePermissions'
import { useCommunicationsAccess, type CommunicationsFeatureKey } from '../../hooks/useCommunicationsAccess'

type IntegrationTile = {
  key: string
  titleKey: string
  descKey: string
  to: string
  Icon: TablerIcon
  /** When set, tile is shown only if `can(permission)` */
  permission?: 'admin.metaLeads' | 'admin.users' | 'notifications.view'
  /** When set, require at least one comm feature (in addition to permission, if any) */
  commFeatureAny?: CommunicationsFeatureKey[]
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

  const tiles: IntegrationTile[] = useMemo(
    () => [
      {
        key: 'inbox',
        titleKey: 'admin.integrations_hub.tile_inbox_title',
        descKey: 'admin.integrations_hub.tile_inbox_desc',
        to: CRM_APP_PATHS.inbox,
        Icon: IconInbox,
        permission: 'notifications.view',
        commFeatureAny: ['messages', 'email'],
      },
      {
        key: 'meta',
        titleKey: 'admin.integrations_hub.meta_title',
        descKey: 'admin.integrations_hub.meta_desc',
        to: CRM_APP_PATHS.settingsIntegrationsMeta,
        Icon: IconBrandMeta,
        permission: 'admin.metaLeads',
      },
      {
        key: 'google',
        titleKey: 'admin.integrations_hub.google_title',
        descKey: 'admin.integrations_hub.google_desc',
        to: CRM_APP_PATHS.settingsIntegrationsGoogle,
        Icon: IconBrandGoogle,
        permission: 'admin.metaLeads',
      },
      {
        key: 'webhook',
        titleKey: 'admin.integrations_hub.webhook_title',
        descKey: 'admin.integrations_hub.webhook_desc',
        to: CRM_APP_PATHS.settingsIntegrationsWebhook,
        Icon: IconWebhook,
        permission: 'admin.metaLeads',
      },
      {
        key: 'email',
        titleKey: 'admin.integrations_hub.email_title',
        descKey: 'admin.integrations_hub.email_desc',
        to: CRM_APP_PATHS.settingsEmail,
        Icon: IconMail,
        permission: 'admin.users',
      },
      {
        key: 'comms',
        titleKey: 'admin.integrations_hub.comms_title',
        descKey: 'admin.integrations_hub.comms_desc',
        to: CRM_APP_PATHS.settingsCommunications,
        Icon: IconMessageCircle,
        permission: 'admin.users',
      },
      {
        key: 'messengers',
        titleKey: 'admin.settings.cards.communications_messengers.label',
        descKey: 'admin.settings.cards.communications_messengers.description',
        to: CRM_APP_PATHS.settingsCommunicationsMessengers,
        Icon: IconMessages,
        permission: 'admin.users',
      },
      {
        key: 'queue',
        titleKey: 'admin.settings.cards.communications_queue.label',
        descKey: 'admin.settings.cards.communications_queue.description',
        to: CRM_APP_PATHS.settingsCommunicationsQueue,
        Icon: IconFilter,
        permission: 'admin.users',
      },
      {
        key: 'sla',
        titleKey: 'admin.settings.cards.communications_sla.label',
        descKey: 'admin.settings.cards.communications_sla.description',
        to: CRM_APP_PATHS.settingsCommunicationsSla,
        Icon: IconBell,
        permission: 'admin.users',
      },
    ],
    [],
  )

  const visibleTiles = useMemo(
    () =>
      tiles.filter((tile) => {
        if (tile.permission && !can(tile.permission)) return false
        if (tile.commFeatureAny?.length) {
          const ok = tile.commFeatureAny.some((f) => canUseCommunicationsFeature(f))
          if (!ok) return false
        }
        return true
      }),
    [can, canUseCommunicationsFeature, tiles],
  )

  if (redirectToMeta) {
    return <Navigate to={`${CRM_APP_PATHS.settingsIntegrationsMeta}${location.search}`} replace />
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 py-6 sm:py-8">
      <header className="max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t('admin.integrations_hub.title')}</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{t('admin.integrations_hub.subtitle_v2')}</p>
      </header>

      <ul className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {visibleTiles.map((tile) => {
          const metaActive = tile.key === 'meta' && metaCredCount !== null && metaCredCount > 0
          const metaUnknown = tile.key === 'meta' && metaCredCount === null && can('admin.metaLeads')
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
                  {tile.key === 'meta' && can('admin.metaLeads') ? (
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
    </div>
  )
}
