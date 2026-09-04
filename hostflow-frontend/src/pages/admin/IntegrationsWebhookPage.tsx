import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
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
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'
import { useLicenseStatus } from '../../hooks/useLicenseStatus'
import { ACTIVATION_PATHS } from '../../app/activationRoutes'

const TEAM_BLOCKED = new Set(['solo', 'starter', 'free'])

function isTeamTierPlan(plan: string | null | undefined): boolean {
  const p = (plan || 'starter').toLowerCase()
  if (p === 'trial') return true
  return !TEAM_BLOCKED.has(p)
}

/**
 * §2.11: generic JSON inbound webhook (Team+). Mapping is edited in Mapping workspace.
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
  const [showAdvanced, setShowAdvanced] = useState(false)

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

  const webhookStepHighlight = useMemo(() => {
    if (settingsLoading) return 1
    if (settings?.generic_inbound_webhook_enabled) return previewItems.length > 0 ? 3 : 2
    return 1
  }, [previewItems.length, settings?.generic_inbound_webhook_enabled, settingsLoading])

  return (
    <SettingsSubpageHeader
      backHref={CRM_APP_PATHS.settingsIntegrations}
      backLabel={t('admin.integrations_hub.back_to_hub')}
      kicker={t('admin.integrations_hub.integration_kicker', { defaultValue: 'Integration' })}
      title={t('admin.integrations_webhook.title')}
      subtitle={t('admin.integrations_webhook.intro')}
      contentClassName="mx-auto w-full max-w-4xl gap-8"
    >

      <div className="flex justify-end">
        <button type="button" className="btn-secondary btn-sm" onClick={() => setShowAdvanced((v) => !v)}>
          {showAdvanced
            ? t('admin.calendar_integrations.actions.hide_advanced', { defaultValue: 'Hide advanced' })
            : t('admin.calendar_integrations.actions.show_advanced', { defaultValue: 'Show advanced' })}
        </button>
      </div>

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
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900" role="alert">
          {error}
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
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
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/80 p-4 text-sm">
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

      {showAdvanced ? (
        <>
          <ol className="grid gap-2 sm:grid-cols-3">
            {[
              { n: 1, label: t('admin.integrations_webhook.step_endpoint') },
              { n: 2, label: t('admin.integrations_webhook.step_verify') },
              { n: 3, label: t('admin.integrations_webhook.step_mapping') },
            ].map(({ n, label }) => (
              <li
                key={n}
                className={clsx(
                  'rounded-lg border px-3 py-2 text-center text-sm font-medium',
                  webhookStepHighlight === n ? 'border-brand-500 bg-brand-50 text-brand-900' : 'border-slate-200 text-slate-500',
                )}
              >
                <span className="mr-1 font-normal text-slate-400">{n}.</span>
                {label}
              </li>
            ))}
          </ol>

          <details className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
            <summary className="cursor-pointer text-sm font-semibold text-slate-900">
              {t('admin.integrations_webhook.advanced_mapping_toggle')}
            </summary>
            <p className="mt-3">{t('admin.integrations_webhook.mapping_hint')}</p>
            <p className="mt-3">
              <Link to={CRM_APP_PATHS.marketingSources} className="font-medium text-brand-600 hover:underline">
                {t('admin.integrations_webhook.mapping_cta')}
              </Link>
            </p>
            <p className="mt-3 text-xs font-medium text-slate-600">{t('admin.integrations_webhook.sample_payload_title')}</p>
            <pre className="mt-2 overflow-x-auto rounded bg-slate-900/90 p-3 text-xs text-slate-100">
              {`POST …/inbound/{secret}
Content-Type: application/json

{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+48123456789",
  "id": "crm-form-123"
}`}
            </pre>
          </details>

          <details className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <summary className="cursor-pointer text-sm font-semibold text-slate-900">
              {t('admin.integrations_webhook.recent_title')}
            </summary>
            <p className="mt-2 text-sm text-slate-600">{t('admin.integrations_webhook.recent_subtitle')}</p>
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
          </details>
        </>
      ) : null}
    </SettingsSubpageHeader>
  )
}
