import clsx from 'clsx'
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import {
  createCommunicationAccount,
  completeCommunicationAccountOAuth,
  deleteCommunicationAccount,
  getCommunicationSchedulerStatus,
  getCommunicationsSettings,
  listCommunicationAccounts,
  listCommunicationThreads,
  patchCommunicationAccount,
  patchCommunicationsSettings,
  runCommunicationEmailPollWorker,
  simulateTelegramWebhook,
  startCommunicationAccountOAuth,
  testCommunicationAccountConnection,
  type CommunicationChannelAccount,
  type CommunicationSchedulerStatus,
  type CommunicationThread,
} from '../api/communications'
import { useI18n } from '../i18n'
import { clearPendingGmailOAuthCode, peekPendingGmailOAuthCode } from '../utils/oauthRedirectBridge'

type EmailFormState = {
  accountLabel: string
  provider: string
  inboxAddress: string
  clientId: string
  clientSecret: string
  redirectUri: string
}

function buildDefaultEmailForm(): EmailFormState {
  const origin =
    typeof window !== 'undefined' && window.location?.origin ? String(window.location.origin).replace(/\/$/, '') : ''
  return {
    accountLabel: '',
    provider: 'gmail',
    inboxAddress: '',
    clientId: '',
    clientSecret: '',
    redirectUri: origin ? `${origin}/app/email` : 'https://hostflow.cc/app/email',
  }
}

type SetupState = {
  channelsEnabled: boolean
  emailConnected: boolean
  messengerConnected: boolean
  emailInboundSeen: boolean
  messengerInboundSeen: boolean
}

function parseOAuthAuthUrlForDebug(authUrl: string): { client_id: string | null; redirect_uri: string | null } {
  try {
    const u = new URL(authUrl)
    return {
      client_id: u.searchParams.get('client_id'),
      redirect_uri: u.searchParams.get('redirect_uri'),
    }
  } catch {
    return { client_id: null, redirect_uri: null }
  }
}

function errorTextFrom(err: any, fallback: string): string {
  const status = err?.response?.status as number | undefined
  const data = err?.response?.data
  const detail = data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const lines = detail
      .map((x: any) => {
        const m = typeof x?.msg === 'string' ? x.msg : typeof x?.message === 'string' ? x.message : ''
        if (!m) return null
        const loc = Array.isArray(x?.loc) ? x.loc.filter((p: unknown) => p !== 'body').join('.') : ''
        return loc ? `${loc}: ${m}` : m
      })
      .filter(Boolean)
    if (lines.length) return lines.join('; ')
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string' && detail.msg.trim()) return detail.msg
    try {
      return JSON.stringify(detail)
    } catch {
      // ignore
    }
  }
  if (typeof data?.message === 'string' && data.message.trim()) return data.message
  if (typeof err?.message === 'string' && err.message.trim()) return err.message
  return fallback
}

function SetupStepCard(props: {
  stepId: string
  stepNo: string
  title: string
  hint: string
  done: boolean
  focused?: boolean
  children: ReactNode
}) {
  const { t } = useI18n()
  const { stepId, stepNo, title, hint, done, focused, children } = props
  return (
    <section
      id={stepId}
      className={clsx(
        'rounded-xl border p-4 shadow-sm scroll-mt-24',
        done ? 'border-emerald-200 bg-emerald-50/60' : 'border-amber-200 bg-amber-50/60',
        focused && 'ring-2 ring-brand-500',
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={clsx('inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold', done ? 'bg-emerald-600 text-white' : 'bg-amber-600 text-white')}>
              {stepNo}
            </span>
            <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          </div>
          <p className="mt-1 text-xs text-slate-600">{hint}</p>
        </div>
        <span className={clsx('badge border text-[11px] font-medium', done ? 'border-emerald-300 bg-white text-emerald-700' : 'border-amber-300 bg-white text-amber-700')}>
          {done
            ? t('app.communications.setup.states.done', { defaultValue: 'Done' })
            : t('app.communications.setup.states.required', { defaultValue: 'Required' })}
        </span>
      </div>
      {children}
    </section>
  )
}

export default function CommunicationsSetupPage() {
  const { t } = useI18n()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [errorText, setErrorText] = useState<string | null>(null)
  const [opsNotice, setOpsNotice] = useState<string | null>(null)
  const [busyKey, setBusyKey] = useState<string | null>(null)

  const [accounts, setAccounts] = useState<CommunicationChannelAccount[]>([])
  const [threads, setThreads] = useState<CommunicationThread[]>([])
  const [settings, setSettings] = useState<any | null>(null)
  const [schedulerStatus, setSchedulerStatus] = useState<CommunicationSchedulerStatus | null>(null)
  const [oauthStartByAccountId, setOauthStartByAccountId] = useState<Record<string, { state: string; authUrl: string } | undefined>>({})
  const [oauthCodeByAccountId, setOauthCodeByAccountId] = useState<Record<string, string | undefined>>({})

  const [selectedEmailAccountId, setSelectedEmailAccountId] = useState<string | null>(null)
  const emailInitialSelectRef = useRef(false)

  const [emailForm, setEmailForm] = useState<EmailFormState>(() => buildDefaultEmailForm())
  const [telegramForm, setTelegramForm] = useState({
    accountLabel: '',
    botToken: '',
    externalRef: '',
  })
  const [telegramInboundTest, setTelegramInboundTest] = useState({
    chatId: '',
    text: '',
  })

  const reloadAll = useCallback(async () => {
    const [cfg, acc, th, sched] = await Promise.all([
      getCommunicationsSettings(),
      listCommunicationAccounts(),
      listCommunicationThreads({ limit: 300 }).catch(() => ({ items: [] as CommunicationThread[] })),
      getCommunicationSchedulerStatus().catch(() => null),
    ])
    setSettings(cfg)
    setAccounts(Array.isArray(acc?.items) ? acc.items : [])
    setThreads(Array.isArray(th?.items) ? th.items : [])
    setSchedulerStatus(sched)
  }, [])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      setLoading(true)
      setErrorText(null)
      try {
        await reloadAll()
      } catch (err: any) {
        if (mounted) {
          setErrorText(
            errorTextFrom(
              err,
              t('app.communications.setup.errors.load_status_failed', {
                defaultValue: 'Failed to load communications setup status',
              }),
            ),
          )
        }
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => {
      mounted = false
    }
  }, [reloadAll, t])

  useEffect(() => {
    if (loading) return
    const raw = location.hash.replace(/^#/, '').trim()
    if (!raw) return
    const stepId =
      raw === 'email' || raw === 'email-oauth' || raw === 'step-email'
        ? 'step-2'
        : raw.startsWith('step-')
          ? raw
          : null
    if (!stepId) return
    const node = document.getElementById(stepId)
    if (!node) return
    const timer = window.setTimeout(() => {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 80)
    return () => window.clearTimeout(timer)
  }, [loading, location.hash])

  const emailAccountsAll = useMemo(() => {
    return accounts
      .filter((x) => String(x.channel || '').toLowerCase() === 'email')
      .slice()
      .sort((a, b) => String(a.account_label || '').localeCompare(String(b.account_label || ''), undefined, { sensitivity: 'base' }))
  }, [accounts])

  const emailAccounts = useMemo(() => emailAccountsAll.filter((x) => Boolean(x.is_active)), [emailAccountsAll])

  const selectedEmailAccount = useMemo(
    () => (selectedEmailAccountId ? emailAccountsAll.find((a) => a.id === selectedEmailAccountId) ?? null : null),
    [emailAccountsAll, selectedEmailAccountId],
  )
  const messengerAccounts = useMemo(() => accounts.filter((x) => String(x.channel || '').toLowerCase() !== 'email' && Boolean(x.is_active)), [accounts])
  const telegramAccounts = useMemo(() => accounts.filter((x) => String(x.channel || '').toLowerCase() === 'telegram' && Boolean(x.is_active)), [accounts])
  const oauthEmailAccounts = useMemo(
    () =>
      emailAccounts.filter((acc) => {
        const provider = String(acc.settings_json?.provider || '').toLowerCase()
        return provider === 'gmail' || provider === 'microsoft_graph'
      }),
    [emailAccounts],
  )

  const primaryOAuthEmailAccount = useMemo(() => {
    if (selectedEmailAccountId) {
      const sel = emailAccountsAll.find((a) => a.id === selectedEmailAccountId)
      if (sel) {
        const p = String(sel.settings_json?.provider || '').toLowerCase()
        if (p === 'gmail' || p === 'microsoft_graph') return sel
      }
    }
    return oauthEmailAccounts[0]
  }, [emailAccountsAll, oauthEmailAccounts, selectedEmailAccountId])

  useEffect(() => {
    if (loading || emailInitialSelectRef.current) return
    if (emailAccountsAll.length === 0) return
    emailInitialSelectRef.current = true
    const oauthFirst = emailAccountsAll.find((a) => {
      const p = String(a.settings_json?.provider || '').toLowerCase()
      return p === 'gmail' || p === 'microsoft_graph'
    })
    setSelectedEmailAccountId(oauthFirst?.id ?? emailAccountsAll[0]!.id)
  }, [loading, emailAccountsAll])

  useEffect(() => {
    if (loading) return
    if (selectedEmailAccountId === null) {
      setEmailForm(buildDefaultEmailForm())
      return
    }
    const acc = emailAccountsAll.find((a) => a.id === selectedEmailAccountId)
    if (!acc) {
      setSelectedEmailAccountId(null)
      return
    }
    const oauth = (acc.settings_json as { oauth?: Record<string, unknown> } | undefined)?.oauth ?? {}
    const provider = String((acc.settings_json as { provider?: string } | undefined)?.provider || 'gmail').toLowerCase()
    setEmailForm({
      accountLabel: acc.account_label || '',
      inboxAddress: acc.inbox_address || '',
      provider: provider === 'microsoft_graph' ? 'microsoft_graph' : 'gmail',
      clientId: String(oauth.client_id || ''),
      clientSecret: '',
      redirectUri: String(oauth.redirect_uri || '').trim() || buildDefaultEmailForm().redirectUri,
    })
  }, [loading, selectedEmailAccountId, emailAccountsAll])

  const oauthAccountMissingToken = useMemo(
    () => oauthEmailAccounts.some((acc) => !acc.settings_json?.oauth?.has_access_token),
    [oauthEmailAccounts],
  )

  /** Prefill authorization code from `/app/email?code=...` redirect or sessionStorage. */
  useEffect(() => {
    if (loading) return
    const first = primaryOAuthEmailAccount
    if (!first?.id) return
    const fromUrl = searchParams.get('code')?.trim() || ''
    const pending = peekPendingGmailOAuthCode() || ''
    const code = fromUrl || pending
    if (!code) return
    let applied = false
    setOauthCodeByAccountId((prev) => {
      if (prev[first.id] === code) return prev
      applied = true
      return { ...prev, [first.id]: code }
    })
    if (fromUrl) {
      const next = new URLSearchParams(searchParams)
      next.delete('code')
      next.delete('state')
      next.delete('scope')
      setSearchParams(next, { replace: true })
    }
    if (applied) {
      setOpsNotice(
        t('app.communications.setup.notices.oauth_code_prefilled', {
          defaultValue: 'Authorization code loaded — click «OAuth complete» to exchange it for tokens.',
        }),
      )
    }
  }, [loading, primaryOAuthEmailAccount, searchParams, setSearchParams, t])

  const state = useMemo<SetupState>(() => {
    const enabledChannels = Array.isArray(settings?.channels?.channels)
      ? settings.channels.channels.filter((x: any) => x?.enabled)
      : []
    const channelsEnabled = enabledChannels.length > 0

    const emailThreads = threads.filter((x) => String(x.channel || '').toLowerCase() === 'email')
    const messengerThreads = threads.filter((x) => String(x.channel || '').toLowerCase() !== 'email')

    const emailInboundSeen = emailThreads.some((x) => Boolean(x.last_inbound_at))
    const messengerInboundSeen = messengerThreads.some((x) => Boolean(x.last_inbound_at))

    return {
      channelsEnabled,
      emailConnected: emailAccounts.length > 0,
      messengerConnected: messengerAccounts.length > 0,
      emailInboundSeen,
      messengerInboundSeen,
    }
  }, [emailAccounts.length, messengerAccounts.length, settings, threads])

  const doneCount = useMemo(() => {
    const checks = [
      state.channelsEnabled,
      state.emailConnected,
      state.messengerConnected,
      state.emailInboundSeen,
      state.messengerInboundSeen,
    ]
    return checks.filter(Boolean).length
  }, [state])

  const missingItems = useMemo(() => {
    const items: string[] = []
    if (!state.channelsEnabled) {
      items.push(
        t('app.communications.setup.missing.enable_baseline_channels', { defaultValue: 'Enable baseline channels' }),
      )
    }
    if (!state.emailConnected) {
      items.push(
        t('app.communications.setup.missing.create_email_account', {
          defaultValue: 'Create at least one email account',
        }),
      )
    }
    if (!state.messengerConnected) {
      items.push(
        t('app.communications.setup.missing.create_messenger_account', {
          defaultValue: 'Create at least one messenger account',
        }),
      )
    }
    if (!state.emailInboundSeen) {
      items.push(
        t('app.communications.setup.missing.verify_email_inbound', {
          defaultValue: 'Run and verify inbound email check',
        }),
      )
    }
    if (!state.messengerInboundSeen) {
      items.push(
        t('app.communications.setup.missing.verify_messenger_inbound', {
          defaultValue: 'Run and verify inbound messenger check',
        }),
      )
    }
    return items
  }, [state, t])

  const nextStepKey = useMemo(() => {
    if (!state.channelsEnabled) return 'step-1'
    if (!state.emailConnected) return 'step-2'
    if (!state.messengerConnected) return 'step-3'
    if (!state.emailInboundSeen) return 'step-4'
    if (!state.messengerInboundSeen) return 'step-5'
    return null
  }, [state])

  const nextStepLabel = useMemo(() => {
    if (nextStepKey === 'step-1') return t('app.communications.setup.steps.channels', { defaultValue: 'Enable baseline channels' })
    if (nextStepKey === 'step-2') return t('app.communications.setup.steps.email_connect_short', { defaultValue: 'Connect email mailbox' })
    if (nextStepKey === 'step-3') return t('app.communications.setup.steps.messenger_connect_short', { defaultValue: 'Connect Telegram bot' })
    if (nextStepKey === 'step-4') return t('app.communications.setup.steps.email_inbound_short', { defaultValue: 'Verify incoming email' })
    if (nextStepKey === 'step-5') return t('app.communications.setup.steps.messenger_inbound_short', { defaultValue: 'Verify incoming messenger messages' })
    return null
  }, [nextStepKey, t])

  const emailInboundReasons = useMemo(() => {
    if (state.emailInboundSeen) return []
    const reasons: string[] = []
    if (emailAccounts.length === 0) {
      reasons.push(t('app.communications.setup.email_reasons.no_active_account', { defaultValue: 'No active email account connected' }))
      return reasons
    }
    const oauthWithoutToken = oauthEmailAccounts.filter((acc) => !acc.settings_json?.oauth?.has_access_token)
    if (oauthWithoutToken.length > 0) {
      reasons.push(
        t('app.communications.setup.email_reasons.oauth_incomplete', {
          defaultValue: 'OAuth is not completed for {count} email account(s)',
          values: { count: oauthWithoutToken.length },
        }),
      )
    }
    const connectionErrors = emailAccounts.filter(
      (acc) =>
        String(acc.settings_json?.connection?.status || '').toLowerCase() === 'error' ||
        String(acc.settings_json?.sync?.status || '').toLowerCase() === 'error',
    )
    if (connectionErrors.length > 0) {
      reasons.push(
        t('app.communications.setup.email_reasons.connection_errors', {
          defaultValue: 'Connection/sync errors detected on {count} email account(s)',
          values: { count: connectionErrors.length },
        }),
      )
    }
    if (!schedulerStatus?.active) {
      reasons.push(
        t('app.communications.setup.email_reasons.scheduler_inactive', {
          defaultValue: 'Email scheduler is not active (poll/dispatch loop)',
        }),
      )
    }
    reasons.push(
      t('app.communications.setup.email_reasons.no_inbound_seen', {
        defaultValue: 'No inbound email seen yet in threads; run inbound check and send a test email to connected mailbox',
      }),
    )
    return reasons
  }, [emailAccounts, oauthEmailAccounts, schedulerStatus?.active, state.emailInboundSeen, t])

  const messengerInboundReasons = useMemo(() => {
    if (state.messengerInboundSeen) return []
    const reasons: string[] = []
    if (telegramAccounts.length === 0) {
      reasons.push(
        t('app.communications.setup.messenger_reasons.no_active_account', {
          defaultValue: 'No active Telegram account connected',
        }),
      )
      return reasons
    }
    const tokenMissing = telegramAccounts.filter((acc) => !acc.settings_json?.telegram?.has_bot_token)
    if (tokenMissing.length > 0) {
      reasons.push(
        t('app.communications.setup.messenger_reasons.bot_token_missing', {
          defaultValue: 'Bot token is missing for {count} Telegram account(s)',
          values: { count: tokenMissing.length },
        }),
      )
    }
    const webhookMissing = telegramAccounts.filter((acc) => !String(acc.settings_json?.telegram?.webhook_secret || '').trim())
    if (webhookMissing.length > 0) {
      reasons.push(
        t('app.communications.setup.messenger_reasons.webhook_missing', {
          defaultValue: 'Webhook secret is missing for {count} Telegram account(s)',
          values: { count: webhookMissing.length },
        }),
      )
    }
    reasons.push(
      t('app.communications.setup.messenger_reasons.no_inbound_seen', {
        defaultValue: 'No inbound messenger message seen yet in threads; run inbound simulation or send a real Telegram message to bot',
      }),
    )
    return reasons
  }, [state.messengerInboundSeen, telegramAccounts, t])

  const runAction = useCallback(async <T,>(key: string, action: () => Promise<T>, okText: string | ((result: T) => string)) => {
    setBusyKey(key)
    setOpsNotice(null)
    setErrorText(null)
    try {
      const result = await action()
      if (key === 'oauth-complete') {
        clearPendingGmailOAuthCode()
      }
      await reloadAll()
      setOpsNotice(typeof okText === 'function' ? okText(result) : okText)
    } catch (err: any) {
      const msg = errorTextFrom(err, t('common.errors.operation_failed', { defaultValue: 'Operation failed' }))
      setErrorText(msg)
      requestAnimationFrame(() => {
        document.getElementById('communications-setup-error')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      })
    } finally {
      setBusyKey(null)
    }
  }, [reloadAll])

  const enableBaseline = useCallback(async () => {
    if (!settings) return
    const channels = Array.isArray(settings?.channels?.channels) ? settings.channels.channels : []
    const patchChannels = channels.map((x: any) => {
      const key = String(x?.key || '').toLowerCase()
      if (key === 'email' || key === 'telegram') {
        return { ...x, enabled: true, inboundEnabled: true, outboundEnabled: true }
      }
      return x
    })
    await patchCommunicationsSettings({
      channels: {
        ...(settings.channels || {}),
        channels: patchChannels,
      },
      email: {
        ...(settings.email || {}),
        incomingEnabled: true,
        syncIntervalMinutes: settings.email?.syncIntervalMinutes ?? 5,
      },
      entitlements: {
        modules: {
          ...(settings.entitlements?.modules || {}),
          messages: { ...(settings.entitlements?.modules?.messages || {}), enabled: true },
          email: { ...(settings.entitlements?.modules?.email || {}), enabled: true },
        },
      },
    })
  }, [settings])

  const saveEmailAccount = useCallback(async () => {
    const label =
      emailForm.accountLabel.trim() ||
      t('app.communications.setup.defaults.main_mailbox', { defaultValue: 'Main mailbox' })
    const provider = String(emailForm.provider || 'gmail').toLowerCase()
    const cid = emailForm.clientId.trim()
    const ruri = emailForm.redirectUri.trim()
    const cs = emailForm.clientSecret.trim()
    const oauth: Record<string, string> = { provider }
    if (cid) oauth.client_id = cid
    if (ruri) oauth.redirect_uri = ruri
    // Persist secret via top-level oauth_client_secret (server merges into oauth); avoids nested JSON loss.

    if (selectedEmailAccountId) {
      await patchCommunicationAccount(selectedEmailAccountId, {
        account_label: label,
        inbox_address: emailForm.inboxAddress.trim() || null,
        settings_json: {
          provider,
          oauth,
        },
        ...(cs ? { oauth_client_secret: cs } : {}),
      })
      return
    }

    const created = await createCommunicationAccount({
      channel: 'email',
      account_label: label,
      inbox_address: emailForm.inboxAddress.trim() || undefined,
      settings_json: {
        provider,
        oauth,
      },
      ...(cs ? { oauth_client_secret: cs } : {}),
    })
    setSelectedEmailAccountId(created.id)
    const latest = await getCommunicationsSettings()
    await patchCommunicationsSettings({
      email: {
        ...(latest.email || {}),
        incomingEnabled: true,
        syncIntervalMinutes: latest.email?.syncIntervalMinutes ?? 5,
      },
    })
  }, [emailForm, selectedEmailAccountId, t])

  const disableSelectedEmailAccount = useCallback(async () => {
    if (!selectedEmailAccountId) return
    await patchCommunicationAccount(selectedEmailAccountId, { is_active: false })
    setSelectedEmailAccountId(null)
  }, [selectedEmailAccountId])

  const enableSelectedEmailAccount = useCallback(async () => {
    if (!selectedEmailAccountId) return
    await patchCommunicationAccount(selectedEmailAccountId, { is_active: true })
  }, [selectedEmailAccountId])

  const deleteSelectedEmailAccount = useCallback(async () => {
    if (!selectedEmailAccountId) return
    await deleteCommunicationAccount(selectedEmailAccountId)
    setSelectedEmailAccountId(null)
    emailInitialSelectRef.current = false
  }, [selectedEmailAccountId])

  const connectTelegramAccount = useCallback(async () => {
    await createCommunicationAccount({
      channel: 'telegram',
      account_label:
        telegramForm.accountLabel.trim() ||
        t('app.communications.setup.defaults.main_telegram_bot', { defaultValue: 'Main Telegram bot' }),
      external_account_ref: telegramForm.externalRef.trim() || undefined,
      settings_json: {
        provider: 'telegram_bot',
        telegram: {
          bot_token: telegramForm.botToken.trim() || undefined,
        },
      },
    })
  }, [telegramForm])

  const runEmailInboundCheck = useCallback(async () => {
    const first = emailAccounts[0]
    return await runCommunicationEmailPollWorker(first ? { only_account_id: first.id, limit_per_account: 20 } : { limit_per_account: 20 })
  }, [emailAccounts])

  const runTelegramInboundCheck = useCallback(async () => {
    const first = telegramAccounts[0]
    if (!first) throw new Error(t('app.communications.setup.errors.no_active_telegram', { defaultValue: 'No active Telegram account' }))
    const now = Math.floor(Date.now() / 1000)
    const chatId = Number(telegramInboundTest.chatId || '0') || now
    await simulateTelegramWebhook({
      channel_account_id: first.id,
      auto_assign: true,
      update: {
        update_id: now,
        message: {
          message_id: now,
          date: now,
          chat: { id: chatId, type: 'private' },
          from: { id: chatId, is_bot: false, first_name: 'QuickSetup' },
          text:
            telegramInboundTest.text ||
            t('app.communications.setup.defaults.test_inbound_text', { defaultValue: 'Test inbound from Quick Setup' }),
        },
      },
    })
  }, [telegramAccounts, telegramInboundTest.chatId, telegramInboundTest.text])

  const testFirstEmailConnection = useCallback(async () => {
    const id = selectedEmailAccountId || emailAccounts[0]?.id
    if (!id) throw new Error(t('app.communications.setup.errors.no_active_email', { defaultValue: 'No active email account' }))
    const res = await testCommunicationAccountConnection(id)
    if (!res.ok) {
      throw new Error(
        res.detail ||
          t('app.communications.setup.errors.email_connection_test_failed', {
            defaultValue: 'Email connection test failed',
          }),
      )
    }
    return res
  }, [emailAccounts, selectedEmailAccountId, t])

  const testFirstTelegramConnection = useCallback(async () => {
    const first = telegramAccounts[0]
    if (!first) throw new Error(t('app.communications.setup.errors.no_active_telegram', { defaultValue: 'No active Telegram account' }))
    const res = await testCommunicationAccountConnection(first.id)
    if (!res.ok) {
      throw new Error(
        res.detail ||
          t('app.communications.setup.errors.telegram_connection_test_failed', {
            defaultValue: 'Telegram connection test failed',
          }),
      )
    }
    return res
  }, [telegramAccounts])

  const startOAuthForFirstEmailAccount = useCallback(async () => {
    const target = primaryOAuthEmailAccount
    if (!target) throw new Error(t('app.communications.setup.errors.no_oauth_email', { defaultValue: 'No OAuth email account available' }))
    if (!target.is_active) {
      throw new Error(
        t('app.communications.setup.errors.oauth_mailbox_inactive', {
          defaultValue: 'Turn this mailbox on before starting OAuth.',
        }),
      )
    }
    const redirect_uri = emailForm.redirectUri.trim() || undefined
    const client_id = emailForm.clientId.trim() || undefined
    const res = await startCommunicationAccountOAuth(target.id, {
      force_consent: true,
      ...(redirect_uri ? { redirect_uri } : {}),
      ...(client_id ? { client_id } : {}),
    })
    setOauthStartByAccountId((p) => ({ ...p, [target.id]: { state: res.state, authUrl: res.auth_url } }))
  }, [emailForm.clientId, emailForm.redirectUri, primaryOAuthEmailAccount, t])

  const completeOAuthForFirstEmailAccount = useCallback(async () => {
    const target = primaryOAuthEmailAccount
    if (!target) throw new Error(t('app.communications.setup.errors.no_oauth_email', { defaultValue: 'No OAuth email account available' }))
    if (!target.is_active) {
      throw new Error(
        t('app.communications.setup.errors.oauth_mailbox_inactive', {
          defaultValue: 'Turn this mailbox on before completing OAuth.',
        }),
      )
    }
    const state = String(oauthStartByAccountId[target.id]?.state || target.settings_json?.oauth?.state || '').trim()
    if (!state) throw new Error(t('app.communications.setup.errors.oauth_start_first', { defaultValue: 'Run OAuth start first' }))
    const code = String(oauthCodeByAccountId[target.id] || '').trim()
    if (!code) {
      throw new Error(
        t('app.communications.setup.errors.oauth_code_required', { defaultValue: 'Paste authorization code first' }),
      )
    }
    const redirect_uri = emailForm.redirectUri.trim() || undefined
    const client_id = emailForm.clientId.trim() || undefined
    await completeCommunicationAccountOAuth(target.id, {
      state,
      code,
      simulate_exchange: false,
      ...(redirect_uri ? { redirect_uri } : {}),
      ...(client_id ? { client_id } : {}),
    })
    setOauthCodeByAccountId((p) => ({ ...p, [target.id]: '' }))
  }, [emailForm.clientId, emailForm.redirectUri, oauthCodeByAccountId, oauthStartByAccountId, primaryOAuthEmailAccount, t])

  const goToNextStep = useCallback(() => {
    if (!nextStepKey) return
    const node = document.getElementById(nextStepKey)
    if (!node) return
    node.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [nextStepKey])

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-brand-50 to-brand-100 p-5 shadow-sm">
        <h1 className="text-2xl font-semibold text-slate-900">
          {t('app.communications.setup.title', { defaultValue: 'Communications Quick Setup' })}
        </h1>
        <p className="mt-1 text-sm text-slate-700">
          {t('app.communications.setup.subtitle', { defaultValue: 'Connect channels, confirm incoming messages, and start operations from one guided flow.' })}
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-sm text-slate-700">
            {t('app.communications.setup.progress', { defaultValue: 'Setup progress' })}: <strong>{doneCount}/5</strong>
          </div>
          <div className="flex items-center gap-2">
            <div className={clsx('badge border px-3 py-1 text-xs font-medium', doneCount === 5 ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-amber-200 bg-amber-50 text-amber-800')}>
              {doneCount === 5
                ? t('app.communications.setup.ready', { defaultValue: 'Ready for operations' })
                : t('app.communications.setup.incomplete', { defaultValue: 'Configuration required' })}
            </div>
            {nextStepKey && (
              <button
                type="button"
                onClick={goToNextStep}
                className="btn-secondary btn-xs"
              >
                {t('app.communications.setup.next_step', { defaultValue: 'Continue setup' })}: {nextStepLabel}
              </button>
            )}
          </div>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${Math.max(0, Math.min(100, (doneCount / 5) * 100))}%` }}
          />
        </div>
      </div>

      {missingItems.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-sm font-semibold text-slate-900">
            {t('app.communications.setup.remaining', { defaultValue: 'Remaining to complete setup' })}
          </div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {missingItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {errorText && (
        <div id="communications-setup-error">
          <ErrorRecoveryBanner
            info={{
              title: errorText,
              hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }),
            }}
            onRetry={() => void reloadAll()}
            retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
            secondaryTo="/app/settings/communications"
            secondaryLabel={t('app.communications.setup.actions.open_settings', { defaultValue: 'Open settings' })}
            compact
          />
        </div>
      )}
      {opsNotice && <div className="alert-success">{opsNotice}</div>}

      <div className="space-y-3">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600">
          <span className="font-semibold text-slate-700">{t('app.communications.setup.phases.phase_1', { defaultValue: 'Phase 1:' })}</span>{' '}
          {t('app.communications.setup.phases.phase_1_body', { defaultValue: 'Connect channels and accounts' })}
          <span className="ml-3 font-semibold text-slate-700">{t('app.communications.setup.phases.phase_2', { defaultValue: 'Phase 2:' })}</span>{' '}
          {t('app.communications.setup.phases.phase_2_body', { defaultValue: 'Verify incoming flow' })}
          <span className="ml-3 font-semibold text-slate-700">{t('app.communications.setup.phases.phase_3', { defaultValue: 'Phase 3:' })}</span>{' '}
          {t('app.communications.setup.phases.phase_3_body', { defaultValue: 'Start daily work' })}
        </div>
        <SetupStepCard
          stepId="step-1"
          stepNo="1"
          focused={nextStepKey === 'step-1'}
          done={state.channelsEnabled}
          title={t('app.communications.setup.steps.channels', { defaultValue: 'Enable baseline channels' })}
          hint={t('app.communications.setup.steps.channels_hint', { defaultValue: 'Enable Email + Telegram channels for immediate start.' })}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs text-slate-600">
                {t('app.communications.setup.baseline_hint', { defaultValue: 'Applies a default production-safe starter config.' })}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() =>
                  void runAction(
                    'baseline',
                    enableBaseline,
                    t('app.communications.setup.notices.baseline_enabled', { defaultValue: 'Baseline enabled' }),
                  )
                }
                disabled={busyKey !== null}
                className="btn-primary btn-sm disabled:opacity-60"
              >
                {busyKey === 'baseline' ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.communications.setup.actions.enable_baseline', { defaultValue: 'Enable baseline' })}
              </button>
              <Link to="/app/settings/communications" className="btn-secondary btn-sm">
                {t('app.communications.setup.actions.open_settings', { defaultValue: 'Open settings' })}
              </Link>
            </div>
          </div>
        </SetupStepCard>

        <SetupStepCard
          stepId="step-2"
          stepNo="2"
          focused={nextStepKey === 'step-2'}
          done={state.emailConnected}
          title={t('app.communications.setup.steps.email_connect', { defaultValue: 'Connect email mailbox (OAuth)' })}
          hint={t('app.communications.setup.steps.email_connect_hint', { defaultValue: 'Create mailbox account and complete OAuth token exchange.' })}
        >
          {emailAccountsAll.length > 0 && (
            <div className="mb-3 flex flex-wrap items-end gap-2">
              <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-xs font-medium text-slate-600">
                {t('app.communications.setup.fields.mailbox_select', { defaultValue: 'Mailbox' })}
                <select
                  className="input text-sm"
                  value={selectedEmailAccountId ?? ''}
                  onChange={(e) => {
                    const v = e.target.value
                    setSelectedEmailAccountId(v === '' ? null : v)
                  }}
                >
                  <option value="">{t('app.communications.setup.mailbox_new', { defaultValue: '+ New mailbox' })}</option>
                  {emailAccountsAll.map((a) => (
                    <option key={a.id} value={a.id}>
                      {(a.account_label || a.inbox_address || a.id).trim()}
                      {!a.is_active ? ` (${t('app.communications.setup.mailbox_inactive', { defaultValue: 'off' })})` : ''}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={() => setSelectedEmailAccountId(null)}
                className="btn-secondary btn-sm"
                disabled={busyKey !== null}
              >
                {t('app.communications.setup.actions.mailbox_new', { defaultValue: 'New mailbox' })}
              </button>
            </div>
          )}
          {selectedEmailAccount && !selectedEmailAccount.is_active && (
            <div className="mb-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
              {t('app.communications.setup.mailbox_disabled_hint', {
                defaultValue: 'This mailbox is turned off. Enable it to use email sync and OAuth, or edit and save settings.',
              })}
              <button
                type="button"
                className="btn-secondary btn-xs ml-2"
                disabled={busyKey !== null}
                onClick={() =>
                  void runAction(
                    'email-enable',
                    enableSelectedEmailAccount,
                    t('app.communications.setup.notices.mailbox_enabled', { defaultValue: 'Mailbox enabled' }),
                  )
                }
              >
                {t('app.communications.setup.actions.mailbox_enable', { defaultValue: 'Enable mailbox' })}
              </button>
            </div>
          )}
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <input value={emailForm.accountLabel} onChange={(e) => setEmailForm((p) => ({ ...p, accountLabel: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.account_label', { defaultValue: 'Account label' })} />
            <input value={emailForm.inboxAddress} onChange={(e) => setEmailForm((p) => ({ ...p, inboxAddress: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.mailbox_address', { defaultValue: 'Mailbox address' })} />
            <select value={emailForm.provider} onChange={(e) => setEmailForm((p) => ({ ...p, provider: e.target.value }))} className="input">
              <option value="gmail">{t('app.communications.setup.providers.gmail', { defaultValue: 'Gmail OAuth' })}</option>
              <option value="microsoft_graph">{t('app.communications.setup.providers.microsoft', { defaultValue: 'Microsoft OAuth' })}</option>
            </select>
            <input value={emailForm.clientId} onChange={(e) => setEmailForm((p) => ({ ...p, clientId: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.oauth_client_id', { defaultValue: 'OAuth client_id' })} />
            <div className="md:col-span-2">
              <input type="password" value={emailForm.clientSecret} onChange={(e) => setEmailForm((p) => ({ ...p, clientSecret: e.target.value }))} className="input w-full" placeholder={t('app.communications.setup.fields.oauth_client_secret', { defaultValue: 'OAuth client_secret' })} />
              {Boolean(selectedEmailAccount?.settings_json?.oauth?.has_client_secret) && (
                <p className="mt-1 text-[11px] text-slate-500">
                  {t('app.communications.setup.oauth_secret_unchanged_hint', {
                    defaultValue: 'A secret is already stored. Leave this field empty to keep it; enter a new value only if you want to replace it.',
                  })}
                </p>
              )}
            </div>
            <input value={emailForm.redirectUri} onChange={(e) => setEmailForm((p) => ({ ...p, redirectUri: e.target.value }))} className="input md:col-span-2" placeholder={t('app.communications.setup.fields.redirect_uri', { defaultValue: 'Redirect URI' })} />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() =>
                void runAction(
                  'email-connect',
                  saveEmailAccount,
                  selectedEmailAccountId
                    ? t('app.communications.setup.notices.email_account_saved', { defaultValue: 'Mailbox settings saved' })
                    : t('app.communications.setup.notices.email_account_created', { defaultValue: 'Email account created' }),
                )
              }
              disabled={busyKey !== null || !emailForm.accountLabel.trim()}
              className="btn-primary btn-sm disabled:opacity-60"
            >
              {busyKey === 'email-connect'
                ? t('common.loading', { defaultValue: 'Loading...' })
                : selectedEmailAccountId
                  ? t('app.communications.setup.actions.save_email_account', { defaultValue: 'Save mailbox' })
                  : t('app.communications.setup.actions.connect_email', { defaultValue: 'Create email account' })}
            </button>
            {selectedEmailAccountId && selectedEmailAccount?.is_active ? (
              <button
                type="button"
                onClick={() =>
                  void runAction(
                    'email-disable',
                    disableSelectedEmailAccount,
                    t('app.communications.setup.notices.mailbox_disabled', { defaultValue: 'Mailbox turned off' }),
                  )
                }
                disabled={busyKey !== null}
                className="btn-secondary btn-sm disabled:opacity-60"
              >
                {t('app.communications.setup.actions.mailbox_disable', { defaultValue: 'Turn off mailbox' })}
              </button>
            ) : null}
            {selectedEmailAccountId ? (
              <button
                type="button"
                disabled={busyKey !== null}
                className="btn-secondary btn-sm text-red-700 hover:bg-red-50 disabled:opacity-60"
                onClick={() => {
                  const ok = window.confirm(
                    t('app.communications.setup.confirm_delete_mailbox', {
                      defaultValue:
                        'Delete this mailbox from HostFlow? Existing email threads remain, but will no longer be tied to this mailbox.',
                    }),
                  )
                  if (!ok) return
                  void runAction(
                    'email-delete',
                    deleteSelectedEmailAccount,
                    t('app.communications.setup.notices.mailbox_deleted', { defaultValue: 'Mailbox deleted' }),
                  )
                }}
              >
                {t('app.communications.setup.actions.mailbox_delete', { defaultValue: 'Delete mailbox' })}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() =>
                void runAction('email-test', testFirstEmailConnection, (res) => {
                  const d = String(res.detail || '').trim()
                  return d
                    ? t('app.communications.setup.notices.email_connection_test_detail', {
                        defaultValue: 'Email connection test: {detail}',
                        values: { detail: d },
                      })
                    : t('app.communications.setup.notices.email_connection_test_completed', {
                        defaultValue: 'Email connection test completed',
                      })
                })
              }
              disabled={busyKey !== null || (!selectedEmailAccountId && emailAccounts.length === 0)}
              className="btn-secondary btn-sm disabled:opacity-60"
            >
              {busyKey === 'email-test' ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.communications.email.test_connection', { defaultValue: 'Test connection' })}
            </button>
            <Link to="/app/email" className="btn-secondary btn-sm">
              {t('app.nav.items.email_inbox', { defaultValue: 'Email inbox' })}
            </Link>
          </div>
          {oauthEmailAccounts.length > 0 && oauthAccountMissingToken && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
              <p className="font-semibold text-amber-950">
                {t('app.communications.setup.oauth_token_required_title', {
                  defaultValue: 'Client ID and Secret are not enough for Gmail',
                })}
              </p>
              <p className="mt-1 text-amber-900/95">
                {t('app.communications.setup.oauth_token_required_intro', {
                  defaultValue:
                    'Google only accepts requests that include a valid OAuth access token. You get that token after you sign in with Google and exchange the one-time authorization code.',
                })}
              </p>
              <ol className="mt-2 list-decimal space-y-1 pl-4 text-amber-900/95">
                <li>
                  {t('app.communications.setup.oauth_token_required_step_consent', {
                    defaultValue: 'Click «OAuth start», then «Open consent URL», and sign in with the Google account for this mailbox.',
                  })}
                </li>
                <li>
                  {t('app.communications.setup.oauth_token_required_step_redirect', {
                    defaultValue:
                      'After Google redirects you back (usually to /app/email), the code is saved automatically — return here and click «OAuth complete».',
                  })}
                </li>
                <li>
                  {t('app.communications.setup.oauth_token_required_step_complete', {
                    defaultValue: 'Or paste the `code` from the browser address bar into the field below, then «OAuth complete».',
                  })}
                </li>
              </ol>
              <details className="mt-2 rounded border border-amber-200/80 bg-amber-50/80 px-2 py-1.5 text-amber-950">
                <summary className="cursor-pointer text-xs font-medium text-amber-950">
                  {t('app.communications.setup.oauth_troubleshoot_google_console', {
                    defaultValue: 'If Google shows an error (400, Testing mode, redirect)',
                  })}
                </summary>
                <p className="mt-2 text-amber-900/95">
                  {t('app.communications.setup.oauth_google_testing_hint', {
                    defaultValue:
                      'If the consent screen is in «Testing», add this Google user under Test users in Google Cloud Console — otherwise Google will refuse access.',
                  })}
                </p>
                <p className="mt-2 text-amber-900/95">
                  {t('app.communications.setup.oauth_google_js_origin_hint', {
                    defaultValue:
                      'If Google shows «400 / invalid_request»: in Google Cloud → Credentials → your Web client → Authorized JavaScript origins must match your app host (e.g. https://hostflow.cc). Redirect URI must match exactly what you saved on this mailbox (e.g. https://hostflow.cc/app/email).',
                  })}
                </p>
              </details>
            </div>
          )}
          {primaryOAuthEmailAccount && !primaryOAuthEmailAccount.settings_json?.oauth?.has_access_token && (
            <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold text-slate-800">
                {t('app.communications.setup.oauth_connect_mailbox', { defaultValue: 'Sign in with Google' })}
              </div>
              {!primaryOAuthEmailAccount.is_active ? (
                <p className="mt-2 text-xs text-slate-600">
                  {t('app.communications.setup.oauth_requires_active_mailbox', {
                    defaultValue: 'Turn the mailbox on above to run OAuth for this account.',
                  })}
                </p>
              ) : null}
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() =>
                    void runAction(
                      'oauth-start',
                      startOAuthForFirstEmailAccount,
                      t('app.communications.setup.notices.oauth_url_generated', { defaultValue: 'OAuth consent URL generated' }),
                    )
                  }
                  disabled={busyKey !== null || !primaryOAuthEmailAccount.is_active}
                  className="btn-secondary btn-xs disabled:opacity-60"
                >
                  {busyKey === 'oauth-start'
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.setup.actions.oauth_start', { defaultValue: 'OAuth start' })}
                </button>
                {oauthStartByAccountId[primaryOAuthEmailAccount.id]?.authUrl && (
                  <a
                    href={oauthStartByAccountId[primaryOAuthEmailAccount.id]?.authUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary btn-xs"
                  >
                    {t('app.communications.setup.actions.open_consent_url', { defaultValue: 'Open consent URL' })}
                  </a>
                )}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  value={oauthCodeByAccountId[primaryOAuthEmailAccount.id] || ''}
                  onChange={(e) =>
                    setOauthCodeByAccountId((p) => ({ ...p, [primaryOAuthEmailAccount.id]: e.target.value }))
                  }
                  className="input w-full max-w-md text-xs"
                  placeholder={t('app.communications.setup.fields.paste_oauth_code', { defaultValue: 'Paste OAuth authorization code' })}
                />
                <button
                  type="button"
                  onClick={() =>
                    void runAction(
                      'oauth-complete',
                      completeOAuthForFirstEmailAccount,
                      t('app.communications.setup.notices.oauth_completed', { defaultValue: 'OAuth completed' }),
                    )
                  }
                  disabled={busyKey !== null || !primaryOAuthEmailAccount.is_active}
                  className="btn-secondary btn-xs disabled:opacity-60"
                >
                  {busyKey === 'oauth-complete'
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.setup.actions.oauth_complete', { defaultValue: 'OAuth complete' })}
                </button>
              </div>
              <details className="mt-3 rounded border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-600">
                <summary className="cursor-pointer font-medium text-slate-700">
                  {t('app.communications.setup.oauth_diagnostics_summary', {
                    defaultValue: 'Diagnostics (redirect / client_id mismatch)',
                  })}
                </summary>
                <div className="mt-2 space-y-2">
                  {oauthStartByAccountId[primaryOAuthEmailAccount.id]?.authUrl ? (
                    <>
                      <p className="font-medium text-slate-700">
                        {t('app.communications.setup.oauth_verify_request', {
                          defaultValue: 'Parameters sent to Google with the last OAuth start',
                        })}
                      </p>
                      {(() => {
                        const raw = oauthStartByAccountId[primaryOAuthEmailAccount.id]!.authUrl
                        const q = parseOAuthAuthUrlForDebug(raw)
                        return (
                          <>
                            <dl className="space-y-1 break-all font-mono text-[11px] text-slate-800">
                              <div>
                                <dt className="text-slate-500">client_id</dt>
                                <dd>{q.client_id || '—'}</dd>
                              </div>
                              <div>
                                <dt className="text-slate-500">redirect_uri</dt>
                                <dd>{q.redirect_uri || '—'}</dd>
                              </div>
                            </dl>
                            <p className="text-[11px] text-slate-600">
                              {t('app.communications.setup.oauth_error_url_note', {
                                defaultValue:
                                  'Compare redirect_uri with Authorized redirect URIs in Google Cloud (exact match). Google’s error page may show a redacted client_id.',
                              })}
                            </p>
                          </>
                        )
                      })()}
                    </>
                  ) : (
                    <p className="text-slate-600">
                      {t('app.communications.setup.oauth_diagnostics_run_start_first', {
                        defaultValue: 'Click OAuth start above; request details will appear here.',
                      })}
                    </p>
                  )}
                </div>
              </details>
            </div>
          )}
          {primaryOAuthEmailAccount && primaryOAuthEmailAccount.settings_json?.oauth?.has_access_token && (
            <p className="mt-2 text-xs text-emerald-800">
              {t('app.communications.setup.oauth_mailbox_connected', {
                defaultValue: 'This mailbox is connected via Google — no further OAuth steps needed here.',
              })}
            </p>
          )}
        </SetupStepCard>

        <SetupStepCard
          stepId="step-3"
          stepNo="3"
          focused={nextStepKey === 'step-3'}
          done={state.messengerConnected}
          title={t('app.communications.setup.steps.messenger_connect', { defaultValue: 'Connect Telegram bot' })}
          hint={t('app.communications.setup.steps.messenger_connect_hint', { defaultValue: 'Add bot account for inbound/outbound messaging.' })}
        >
          <div className="mt-3 grid gap-2 md:grid-cols-3">
            <input value={telegramForm.accountLabel} onChange={(e) => setTelegramForm((p) => ({ ...p, accountLabel: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.bot_label', { defaultValue: 'Bot label' })} />
            <input type="password" value={telegramForm.botToken} onChange={(e) => setTelegramForm((p) => ({ ...p, botToken: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.bot_token', { defaultValue: 'Bot token' })} />
            <input value={telegramForm.externalRef} onChange={(e) => setTelegramForm((p) => ({ ...p, externalRef: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.external_ref_optional', { defaultValue: 'External ref (optional)' })} />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() =>
                void runAction(
                  'tg-connect',
                  connectTelegramAccount,
                  t('app.communications.setup.notices.telegram_account_created', { defaultValue: 'Telegram account created' }),
                )
              }
              disabled={busyKey !== null || !telegramForm.accountLabel.trim()}
              className="btn-primary btn-sm disabled:opacity-60"
            >
              {busyKey === 'tg-connect' ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.communications.setup.actions.connect_telegram', { defaultValue: 'Create Telegram account' })}
            </button>
            <button
              type="button"
              onClick={() =>
                void runAction('tg-test', testFirstTelegramConnection, (res) => {
                  const d = String(res.detail || '').trim()
                  return d
                    ? t('app.communications.setup.notices.telegram_connection_test_detail', {
                        defaultValue: 'Telegram connection test: {detail}',
                        values: { detail: d },
                      })
                    : t('app.communications.setup.notices.telegram_connection_test_completed', {
                        defaultValue: 'Telegram connection test completed',
                      })
                })
              }
              disabled={busyKey !== null || telegramAccounts.length === 0}
              className="btn-secondary btn-sm disabled:opacity-60"
            >
              {busyKey === 'tg-test' ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.communications.email.test_connection', { defaultValue: 'Test connection' })}
            </button>
            <Link to="/app/messages" className="btn-secondary btn-sm">
              {t('app.nav.items.messages_inbox', { defaultValue: 'Messages inbox' })}
            </Link>
          </div>
        </SetupStepCard>

        <SetupStepCard
          stepId="step-4"
          stepNo="4"
          focused={nextStepKey === 'step-4'}
          done={state.emailInboundSeen}
          title={t('app.communications.setup.steps.email_inbound', { defaultValue: 'Verify incoming email' })}
          hint={t('app.communications.setup.steps.email_inbound_hint', { defaultValue: 'Run inbound poll and confirm a real incoming message appears.' })}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-xs text-slate-600">
                {t('app.communications.setup.email_inbound_hint_2', {
                  defaultValue: 'Use this after mailbox connection/OAuth.',
                })}
              </div>
            </div>
            <button
              type="button"
              onClick={() =>
                void runAction(
                  'email-inbound',
                  runEmailInboundCheck,
                  (res) =>
                    t('app.communications.setup.notices.email_inbound_check', {
                      defaultValue:
                        'Email inbound check: ingested {ingested}, created threads {threads}, skipped {skipped}',
                      values: {
                        ingested: Number(res.ingested_messages || 0),
                        threads: Number(res.created_threads || 0),
                        skipped: Number(res.skipped_messages || 0),
                      },
                    }),
                )
              }
              disabled={busyKey !== null}
              className="btn-secondary btn-sm disabled:opacity-60"
            >
              {busyKey === 'email-inbound' ? t('common.loading', { defaultValue: 'Loading...' }) : t('common.actions.check', { defaultValue: 'Check' })}
            </button>
          </div>
          {!state.emailInboundSeen && emailInboundReasons.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-700">
              {emailInboundReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
        </SetupStepCard>

        <SetupStepCard
          stepId="step-5"
          stepNo="5"
          focused={nextStepKey === 'step-5'}
          done={state.messengerInboundSeen}
          title={t('app.communications.setup.steps.messenger_inbound', { defaultValue: 'Verify incoming messenger messages' })}
          hint={t('app.communications.setup.steps.messenger_inbound_hint', { defaultValue: 'Simulate webhook and confirm inbound thread appears.' })}
        >
          <div>
            <div className="text-xs text-slate-600">
              {t('app.communications.setup.messenger_inbound_hint_2', {
                defaultValue: 'Run once now and later verify with real inbound chat.',
              })}
            </div>
          </div>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <input value={telegramInboundTest.chatId} onChange={(e) => setTelegramInboundTest((p) => ({ ...p, chatId: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.chat_id_optional', { defaultValue: 'chat_id (optional)' })} />
            <input value={telegramInboundTest.text} onChange={(e) => setTelegramInboundTest((p) => ({ ...p, text: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.test_inbound_message', { defaultValue: 'Test inbound message' })} />
          </div>
          <div className="mt-3">
            <button
              type="button"
              onClick={() =>
                void runAction(
                  'tg-inbound',
                  runTelegramInboundCheck,
                  t('app.communications.setup.notices.telegram_inbound_check_executed', {
                    defaultValue: 'Telegram inbound check executed',
                  }),
                )
              }
              disabled={busyKey !== null || telegramAccounts.length === 0}
              className="btn-secondary btn-sm disabled:opacity-60"
            >
              {busyKey === 'tg-inbound' ? t('common.loading', { defaultValue: 'Loading...' }) : t('common.actions.check', { defaultValue: 'Check' })}
            </button>
          </div>
          {!state.messengerInboundSeen && messengerInboundReasons.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-700">
              {messengerInboundReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
        </SetupStepCard>

      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="text-sm font-semibold text-slate-900">{t('app.communications.setup.next_title', { defaultValue: 'Start daily work' })}</div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link to="/app/messages" className="btn-secondary">
            {t('app.nav.items.messages_inbox', { defaultValue: 'Messages inbox' })}
          </Link>
          <Link to="/app/email" className="btn-secondary">
            {t('app.nav.items.email_inbox', { defaultValue: 'Email inbox' })}
          </Link>
          <Link to="/app/tasks" className="btn-secondary">
            {t('app.nav.items.tasks', { defaultValue: 'Tasks' })}
          </Link>
          <Link to="/app/calendar" className="btn-secondary">
            {t('app.nav.items.calendar', { defaultValue: 'Calendar' })}
          </Link>
        </div>
      </div>

      {loading && <div className="text-sm text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</div>}
    </div>
  )
}
