import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import {
  completeCommunicationAccountOAuth,
  createCommunicationAccount,
  listCommunicationAccounts,
  refreshCommunicationAccountOAuth,
  startCommunicationAccountOAuth,
  type CommunicationChannelAccount,
} from '../../api/communications'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { clearPendingGmailOAuthCode, readPendingGmailOAuthCode } from '../../utils/oauthRedirectBridge'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'

function oauthBlock(account: CommunicationChannelAccount | null) {
  const settings = account?.settings_json && typeof account.settings_json === 'object' ? account.settings_json : {}
  const oauth = settings.oauth && typeof settings.oauth === 'object' ? settings.oauth : {}
  const sync = settings.sync && typeof settings.sync === 'object' ? settings.sync : {}
  return { settings, oauth, sync }
}

function defaultRedirectUri(): string {
  if (typeof window === 'undefined') return 'https://hostflow.cc/app/email'
  return `${window.location.origin}/app/email`
}

export function EmailGmailOAuthSection() {
  const { t } = useI18n()
  const { notify } = useToast()
  const [accounts, setAccounts] = useState<CommunicationChannelAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [selectedId, setSelectedId] = useState('')
  const [clientId, setClientId] = useState('')
  const [redirectUri, setRedirectUri] = useState(defaultRedirectUri)
  const [pendingCode, setPendingCode] = useState<string | null>(() => readPendingGmailOAuthCode())
  const [oauthState, setOauthState] = useState('')

  const selected = useMemo(
    () => accounts.find((row) => row.id === selectedId) ?? accounts[0] ?? null,
    [accounts, selectedId],
  )
  const { oauth, sync } = oauthBlock(selected)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listCommunicationAccounts({ channel: 'email' })
      const items = (res.items || []).filter((row) => {
        const provider = String(row.settings_json?.provider || row.settings_json?.oauth?.provider || '').toLowerCase()
        return provider === 'gmail' || provider === 'google'
      })
      setAccounts(items)
      if (!selectedId && items[0]?.id) setSelectedId(items[0].id)
      const active = items.find((row) => row.id === selectedId) ?? items[0] ?? null
      if (active) {
        const block = oauthBlock(active)
        setClientId(String(block.oauth.client_id || ''))
        setRedirectUri(String(block.oauth.redirect_uri || defaultRedirectUri()))
        setOauthState(String(block.oauth.state || ''))
      }
    } finally {
      setLoading(false)
    }
  }, [selectedId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const code = readPendingGmailOAuthCode()
    if (code) setPendingCode(code)
  }, [])

  const ensureAccount = async (): Promise<CommunicationChannelAccount> => {
    if (selected) return selected
    if (!clientId.trim()) {
      throw new Error(t('admin.email.gmail_oauth.client_id_required', { defaultValue: 'Укажите OAuth Client ID' }))
    }
    const created = await createCommunicationAccount({
      channel: 'email',
      account_label: t('admin.email.gmail_oauth.default_label', { defaultValue: 'Gmail inbox' }),
      inbox_address: '',
      settings_json: {
        provider: 'gmail',
        oauth: {
          provider: 'gmail',
          client_id: clientId.trim(),
          redirect_uri: redirectUri.trim() || defaultRedirectUri(),
        },
      },
    })
    setAccounts((prev) => [...prev, created])
    setSelectedId(created.id)
    return created
  }

  const handleStartOAuth = async (forceConsent = false) => {
    setBusy(true)
    try {
      const account = await ensureAccount()
      const res = await startCommunicationAccountOAuth(account.id, {
        client_id: clientId.trim() || undefined,
        redirect_uri: redirectUri.trim() || defaultRedirectUri(),
        force_consent: forceConsent,
      })
      setOauthState(res.state)
      window.location.assign(res.auth_url)
    } catch (err: unknown) {
      const info = getFriendlyErrorInfo(err, t('admin.email.gmail_oauth.start_failed', { defaultValue: 'Не удалось начать OAuth' }), t)
      notify({ title: info.title, description: info.detail, variant: 'error' })
    } finally {
      setBusy(false)
    }
  }

  const handleCompleteOAuth = async () => {
    const code = String(pendingCode || readPendingGmailOAuthCode() || '').trim()
    const state = String(oauthState || oauth.state || '').trim()
    if (!code) {
      notify({
        title: t('admin.email.gmail_oauth.code_required', { defaultValue: 'Нет кода авторизации' }),
        variant: 'error',
      })
      return
    }
    if (!state) {
      notify({
        title: t('admin.email.gmail_oauth.state_required', { defaultValue: 'Нет OAuth state — сначала нажмите «Подключить Gmail»' }),
        variant: 'error',
      })
      return
    }
    setBusy(true)
    try {
      const account = await ensureAccount()
      await completeCommunicationAccountOAuth(account.id, {
        state,
        code,
        client_id: clientId.trim() || undefined,
        redirect_uri: redirectUri.trim() || defaultRedirectUri(),
      })
      clearPendingGmailOAuthCode()
      setPendingCode(null)
      notify({
        title: t('admin.email.gmail_oauth.complete_ok', { defaultValue: 'Gmail подключён' }),
        variant: 'success',
      })
      await load()
    } catch (err: unknown) {
      const info = getFriendlyErrorInfo(err, t('admin.email.gmail_oauth.complete_failed', { defaultValue: 'Не удалось завершить OAuth' }), t)
      notify({ title: info.title, description: info.detail, variant: 'error' })
    } finally {
      setBusy(false)
    }
  }

  const handleRefresh = async () => {
    if (!selected) return
    setBusy(true)
    try {
      await refreshCommunicationAccountOAuth(selected.id)
      notify({
        title: t('admin.email.gmail_oauth.refresh_ok', { defaultValue: 'Токен обновлён' }),
        variant: 'success',
      })
      await load()
    } catch (err: unknown) {
      const info = getFriendlyErrorInfo(err, t('admin.email.gmail_oauth.refresh_failed', { defaultValue: 'Не удалось обновить токен' }), t)
      notify({ title: info.title, description: info.detail, variant: 'error' })
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading')}</p>
  }

  const oauthStatus = String(oauth.oauth_status || 'unknown')
  const lastError = String(sync.last_error || oauth.last_error || '').trim()
  const needsReconnect = oauthStatus !== 'connected' || Boolean(lastError)

  return (
    <div className="mt-8 space-y-4 border-t border-slate-200 pt-6 max-w-2xl">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">
          {t('admin.email.gmail_oauth.title', { defaultValue: 'Gmail OAuth (входящая почта)' })}
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          {t('admin.email.gmail_oauth.subtitle', {
            defaultValue: 'Подключение Gmail для Communications inbox. SMTP выше — только для исходящих уведомлений CRM.',
          })}
        </p>
      </div>

      {pendingCode ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {t('app.communications.setup.notices.oauth_code_prefilled')}
        </div>
      ) : null}

      {needsReconnect && lastError ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p>{t('app.communications.email.poll.reconnect_oauth_hint')}</p>
          {lastError ? <p className="mt-2 font-mono text-xs text-amber-800">{lastError}</p> : null}
        </div>
      ) : null}

      {accounts.length > 1 ? (
        <div>
          <label className="label">{t('admin.email.gmail_oauth.account', { defaultValue: 'Почтовый аккаунт' })}</label>
          <select className="input mt-1" value={selected?.id || ''} onChange={(e) => setSelectedId(e.target.value)}>
            {accounts.map((row) => (
              <option key={row.id} value={row.id}>
                {row.account_label || row.inbox_address || row.id}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="label">OAuth Client ID</label>
          <input className="input mt-1" value={clientId} onChange={(e) => setClientId(e.target.value)} placeholder="xxxx.apps.googleusercontent.com" />
        </div>
        <div className="sm:col-span-2">
          <label className="label">Redirect URI</label>
          <input className="input mt-1" value={redirectUri} onChange={(e) => setRedirectUri(e.target.value)} />
          <p className="mt-1 text-xs text-slate-500">{t('app.communications.setup.oauth_google_js_origin_hint')}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span
          className={clsx(
            'rounded-full px-3 py-0.5 text-xs font-semibold',
            oauthStatus === 'connected' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800',
          )}
        >
          {oauthStatus}
        </span>
        {oauth.has_refresh_token === false ? (
          <span className="text-xs text-amber-700">
            {t('admin.email.gmail_oauth.no_refresh_token', { defaultValue: 'Refresh token отсутствует' })}
          </span>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-primary" disabled={busy} onClick={() => void handleStartOAuth(false)}>
          {t('app.communications.setup.actions.connect_email')}
        </button>
        <button type="button" className="btn-secondary" disabled={busy} onClick={() => void handleCompleteOAuth()}>
          OAuth complete
        </button>
        <button type="button" className="btn-secondary" disabled={busy || !selected} onClick={() => void handleRefresh()}>
          {t('admin.email.gmail_oauth.refresh_token', { defaultValue: 'Обновить токен' })}
        </button>
        <button type="button" className="btn-secondary" disabled={busy} onClick={() => void handleStartOAuth(true)}>
          {t('app.communications.email.poll.reconnect_email_setup')}
        </button>
      </div>
    </div>
  )
}
