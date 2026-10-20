import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'

import {
  connectTikTokAccount,
  disconnectTikTokAccount,
  getTikTokConnection,
  importTikTokLeads,
  type TikTokConnection,
} from '../../api/tiktokLeads'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'

/**
 * TikTok ad account connection. Step 1 collects the account, step 2 checks it
 * with TikTok, step 3 is the finished state: connected, with forms ready for flights.
 */
export default function IntegrationsTikTokPage() {
  const { t } = useI18n()
  const [connection, setConnection] = useState<TikTokConnection | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [advertiserId, setAdvertiserId] = useState('')
  const [accessToken, setAccessToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [importNote, setImportNote] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const row = await getTikTokConnection()
      setConnection(row)
      if (row.advertiser_id) setAdvertiserId(row.advertiser_id)
    } catch {
      setError(t('admin.integrations_tiktok.load_error'))
      setConnection(null)
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const connected = Boolean(connection?.connected)
  const step = submitting ? 2 : connected ? 3 : 1

  async function onConnect() {
    setSubmitting(true)
    setError(null)
    setImportNote(null)
    try {
      const row = await connectTikTokAccount({
        advertiser_id: advertiserId.trim(),
        access_token: accessToken.trim(),
      })
      setConnection(row)
      setAccessToken('')
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      setError(typeof detail === 'string' && detail ? detail : t('admin.integrations_tiktok.connect_error'))
    } finally {
      setSubmitting(false)
    }
  }

  async function onImport() {
    setSubmitting(true)
    setError(null)
    setImportNote(null)
    try {
      const row = await importTikTokLeads()
      setConnection(row)
      setImportNote(
        t('admin.integrations_tiktok.imported', {
          values: { count: String(row.imported ?? 0) },
        }),
      )
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      setError(typeof detail === 'string' && detail ? detail : t('admin.integrations_tiktok.import_error'))
    } finally {
      setSubmitting(false)
    }
  }

  async function onDisconnect() {
    setSubmitting(true)
    setError(null)
    setImportNote(null)
    try {
      const row = await disconnectTikTokAccount()
      setConnection(row)
      setAccessToken('')
    } catch {
      setError(t('admin.integrations_tiktok.disconnect_error'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <SettingsSubpageHeader
      backHref={CRM_APP_PATHS.settingsIntegrations}
      backLabel={t('admin.integrations_hub.back_to_hub')}
      kicker={t('admin.integrations_hub.integration_kicker', { defaultValue: 'Integration' })}
      title={t('admin.integrations_tiktok.title')}
      subtitle={t('admin.integrations_tiktok.intro')}
      contentClassName="mx-auto w-full max-w-3xl gap-6"
    >
      <ol className="grid gap-2 sm:grid-cols-3">
        {[
          { n: 1, label: t('admin.integrations_tiktok.step_account') },
          { n: 2, label: t('admin.integrations_tiktok.step_check') },
          { n: 3, label: t('admin.integrations_tiktok.step_done') },
        ].map(({ n, label }) => (
          <li
            key={n}
            className={clsx(
              'rounded-lg border px-3 py-2 text-center text-sm font-medium',
              step === n ? 'border-brand-500 bg-brand-50 text-brand-900' : 'border-slate-200 text-slate-500',
            )}
          >
            <span className="mr-1 font-normal text-slate-400">{n}.</span>
            {label}
          </li>
        ))}
      </ol>

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900" role="alert">
          {error}
        </div>
      ) : null}

      {loading ? <p className="text-sm text-slate-500">{t('common.loading')}</p> : null}

      {!loading && !connected ? (
        <form
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
          onSubmit={(event) => {
            event.preventDefault()
            void onConnect()
          }}
        >
          <h2 className="text-sm font-semibold text-slate-900">{t('admin.integrations_tiktok.account_title')}</h2>
          <p className="mt-2 text-sm text-slate-600">{t('admin.integrations_tiktok.account_body')}</p>
          <label className="mt-4 block text-sm">
            <span className="font-medium text-slate-800">{t('admin.integrations_tiktok.advertiser_label')}</span>
            <input
              className="input mt-1 w-full"
              value={advertiserId}
              onChange={(event) => setAdvertiserId(event.target.value)}
              autoComplete="off"
              required
            />
          </label>
          <label className="mt-3 block text-sm">
            <span className="font-medium text-slate-800">{t('admin.integrations_tiktok.token_label')}</span>
            <input
              className="input mt-1 w-full"
              type="password"
              value={accessToken}
              onChange={(event) => setAccessToken(event.target.value)}
              autoComplete="off"
              required
            />
          </label>
          <p className="mt-2 text-xs text-slate-500">{t('admin.integrations_tiktok.token_hint')}</p>
          <button type="submit" className="btn-primary mt-4" disabled={submitting}>
            {submitting ? t('common.loading') : t('admin.integrations_tiktok.connect_btn')}
          </button>
        </form>
      ) : null}

      {!loading && connected ? (
        <section className="rounded-lg border border-emerald-200 bg-emerald-50/70 p-4">
          <p className="text-sm font-semibold text-emerald-950">{t('admin.integrations_tiktok.connected_title')}</p>
          <p className="mt-1 text-sm text-emerald-900">
            {t('admin.integrations_tiktok.connected_body', {
              values: { advertiser: connection?.advertiser_id || '' },
            })}
          </p>
          {connection?.forms?.length ? (
            <ul className="mt-3 space-y-2">
              {connection.forms.map((form) => (
                <li key={form.intake_source_profile_id} className="rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm">
                  <span className="font-medium text-slate-900">{form.name}</span>
                  <span className="mt-0.5 block text-xs text-slate-500">{form.page_id}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-emerald-900">{t('admin.integrations_tiktok.no_forms')}</p>
          )}
          {importNote ? <p className="mt-3 text-sm text-emerald-950">{importNote}</p> : null}
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to={CRM_APP_PATHS.marketing} className="btn-primary btn-sm">
              {t('admin.integrations_tiktok.open_flights')}
            </Link>
            <button type="button" className="btn-secondary btn-sm" disabled={submitting} onClick={() => void onImport()}>
              {t('admin.integrations_tiktok.import_btn')}
            </button>
            <button type="button" className="btn-secondary btn-sm" disabled={submitting} onClick={() => void onDisconnect()}>
              {t('admin.integrations_tiktok.disconnect_btn')}
            </button>
          </div>
        </section>
      ) : null}
    </SettingsSubpageHeader>
  )
}
