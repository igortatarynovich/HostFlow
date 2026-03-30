import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  getMetaIncomingPreview,
  getMetaLeadSettings,
  rotateGenericInboundWebhook,
} from '../../api/metaLeads'
import type {
  GenericInboundWebhookRotateResponse,
  MetaIncomingLeadPreviewItem,
  MetaLeadSettings,
} from '../../api/types'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import { useLicenseStatus } from '../../hooks/useLicenseStatus'
import { ACTIVATION_PATHS } from '../../app/activationRoutes'

const TEAM_BLOCKED = new Set(['solo', 'starter', 'trial', 'free'])

function isTeamTierPlan(plan: string | null | undefined): boolean {
  return !TEAM_BLOCKED.has((plan || 'starter').toLowerCase())
}

/**
 * §2.11: generic JSON inbound webhook (Team+). Same field_mapping as Meta — configure on Meta leads admin.
 */
export default function IntegrationsWebhookPage() {
  const { t } = useI18n()
  const { plan, loading: planLoading } = useLicenseStatus()
  const teamOk = isTeamTierPlan(plan)

  const [settings, setSettings] = useState<MetaLeadSettings | null>(null)
  const [settingsLoading, setSettingsLoading] = useState(true)
  const [rotateLoading, setRotateLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRotate, setLastRotate] = useState<GenericInboundWebhookRotateResponse | null>(null)
  const [previewItems, setPreviewItems] = useState<MetaIncomingLeadPreviewItem[]>([])
  const [previewLoading, setPreviewLoading] = useState(false)

  const load = useCallback(async () => {
    setSettingsLoading(true)
    setError(null)
    try {
      const s = await getMetaLeadSettings()
      setSettings(s)
    } catch {
      setError(t('admin.integrations_webhook.load_error'))
      setSettings(null)
    } finally {
      setSettingsLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (planLoading) return
    let cancelled = false
    setPreviewLoading(true)
    void (async () => {
      try {
        const res = await getMetaIncomingPreview({ limit: 8, source: 'webhook' })
        if (!cancelled) setPreviewItems(Array.isArray(res?.items) ? res.items : [])
      } catch {
        if (!cancelled) setPreviewItems([])
      } finally {
        if (!cancelled) setPreviewLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [planLoading, lastRotate, settings?.generic_inbound_webhook_enabled])

  const onRotate = useCallback(async () => {
    setRotateLoading(true)
    setError(null)
    setLastRotate(null)
    try {
      const r = await rotateGenericInboundWebhook()
      setLastRotate(r)
      await load()
    } catch (e: unknown) {
      const code =
        typeof e === 'object' && e !== null && 'response' in e
          ? (e as { response?: { data?: { detail?: { code?: string } } } }).response?.data?.detail
          : undefined
      if (code && typeof code === 'object' && (code as { code?: string }).code === 'plan_requires_team') {
        setError(t('admin.integrations_webhook.plan_team_required'))
      } else {
        setError(t('admin.integrations_webhook.rotate_error'))
      }
    } finally {
      setRotateLoading(false)
    }
  }, [load, t])

  const onCopy = useCallback(
    async (text: string) => {
      try {
        await navigator.clipboard.writeText(text)
      } catch {
        setError(t('admin.integrations_webhook.copy_failed'))
      }
    },
    [t],
  )

  const apiBase =
    (import.meta.env.VITE_API_URL as string | undefined) ||
    (import.meta.env.VITE_API_BASE as string | undefined) ||
    ''

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 py-6 sm:py-8">
      <header className="space-y-2">
        <Link to={CRM_APP_PATHS.settingsIntegrations} className="text-sm font-medium text-brand-600 hover:underline">
          {t('admin.integrations_hub.back_to_hub')}
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t('admin.integrations_webhook.title')}</h1>
        <p className="text-sm leading-relaxed text-slate-600">{t('admin.integrations_webhook.intro')}</p>
      </header>

      {!planLoading && !teamOk ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          <p>{t('admin.integrations_webhook.plan_gate')}</p>
          <Link
            to={`${ACTIVATION_PATHS.billing}?focus=plan`}
            className="mt-2 inline-block font-medium text-brand-700 hover:underline"
          >
            {t('admin.integrations_webhook.upgrade_cta')}
          </Link>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900" role="alert">
          {error}
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">{t('admin.integrations_webhook.endpoint_title')}</h2>
        <p className="mt-2 text-sm text-slate-600">{t('admin.integrations_webhook.endpoint_desc')}</p>

        {settingsLoading ? (
          <p className="mt-4 text-sm text-slate-500">{t('common.loading')}</p>
        ) : (
          <>
            <p className="mt-3 text-sm text-slate-700">
              <span className="font-medium">{t('admin.integrations_webhook.status_label')}</span>{' '}
              {settings?.generic_inbound_webhook_enabled
                ? t('admin.integrations_webhook.status_on')
                : t('admin.integrations_webhook.status_off')}
            </p>
            <button
              type="button"
              disabled={!teamOk || rotateLoading}
              onClick={() => void onRotate()}
              className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {rotateLoading ? t('common.loading') : t('admin.integrations_webhook.rotate_btn')}
            </button>
            <p className="mt-2 text-xs text-slate-500">{t('admin.integrations_webhook.rotate_hint')}</p>
          </>
        )}
      </div>

      {lastRotate ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/80 p-5 text-sm">
          <p className="font-medium text-emerald-950">{t('admin.integrations_webhook.new_url_title')}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <code className="max-w-full break-all rounded bg-white px-2 py-1 text-xs text-slate-800">
              {lastRotate.ingest_url.startsWith('http')
                ? lastRotate.ingest_url
                : `${apiBase.replace(/\/+$/, '')}${lastRotate.ingest_url}`}
            </code>
            <button
              type="button"
              onClick={() =>
                void onCopy(
                  lastRotate.ingest_url.startsWith('http')
                    ? lastRotate.ingest_url
                    : `${apiBase.replace(/\/+$/, '')}${lastRotate.ingest_url}`,
                )
              }
              className="rounded border border-emerald-300 bg-white px-2 py-1 text-xs font-medium text-emerald-900 hover:bg-emerald-100"
            >
              {t('admin.integrations_webhook.copy_url')}
            </button>
          </div>
          <p className="mt-3 text-xs text-emerald-900">{t('admin.integrations_webhook.secret_once_hint')}</p>
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-5 text-sm text-slate-700">
        <p>{t('admin.integrations_webhook.mapping_hint')}</p>
        <p className="mt-3">
          <Link to={CRM_APP_PATHS.settingsIntegrationsMeta} className="font-medium text-brand-600 hover:underline">
            {t('admin.integrations_webhook.mapping_cta')}
          </Link>
        </p>
        <pre className="mt-4 overflow-x-auto rounded bg-slate-900/90 p-3 text-xs text-slate-100">
          {`POST …/inbound/{secret}
Content-Type: application/json

{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+48123456789",
  "id": "crm-form-123"
}`}
        </pre>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">{t('admin.integrations_webhook.recent_title')}</h2>
        <p className="mt-1 text-sm text-slate-600">{t('admin.integrations_webhook.recent_subtitle')}</p>
        <p className="mt-2">
          <Link
            to={`${CRM_APP_PATHS.settingsIntegrationsMeta}?tab=incoming&incoming_source=webhook`}
            className="text-sm font-medium text-brand-600 hover:underline"
          >
            {t('admin.integrations_webhook.view_all_incoming')}
          </Link>
        </p>
        {previewLoading ? (
          <p className="mt-3 text-sm text-slate-500">{t('common.loading')}</p>
        ) : previewItems.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">{t('admin.integrations_webhook.recent_empty')}</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm">
            {previewItems.map((row) => (
              <li key={row.lead_id} className="rounded border border-slate-100 bg-slate-50/80 px-3 py-2">
                <Link
                  to={`${CRM_APP_PATHS.leads}/${row.lead_id}`}
                  className="font-medium text-brand-600 hover:underline"
                >
                  {row.lead_id.slice(0, 8)}…
                </Link>
                <span className="text-slate-600"> · {row.status}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
