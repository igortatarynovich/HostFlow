import clsx from 'clsx'
import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import {
  createCommunicationAccount,
  completeCommunicationAccountOAuth,
  getCommunicationSchedulerStatus,
  getCommunicationsSettings,
  listCommunicationAccounts,
  listCommunicationThreads,
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

type SetupState = {
  channelsEnabled: boolean
  emailConnected: boolean
  messengerConnected: boolean
  emailInboundSeen: boolean
  messengerInboundSeen: boolean
}

function errorTextFrom(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const msg = detail.map((x) => (typeof x?.msg === 'string' ? x.msg : null)).filter(Boolean).join('; ')
    if (msg) return msg
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.msg === 'string' && detail.msg.trim()) return detail.msg
    try {
      return JSON.stringify(detail)
    } catch {
      // ignore
    }
  }
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

  const [emailForm, setEmailForm] = useState({
    accountLabel: '',
    provider: 'gmail',
    inboxAddress: '',
    clientId: '',
    clientSecret: '',
    redirectUri: 'https://hostflow.cc/app/email',
  })
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

  const emailAccounts = useMemo(() => accounts.filter((x) => String(x.channel || '').toLowerCase() === 'email' && Boolean(x.is_active)), [accounts])
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
      await reloadAll()
      setOpsNotice(typeof okText === 'function' ? okText(result) : okText)
    } catch (err: any) {
      setErrorText(errorTextFrom(err, t('common.errors.operation_failed', { defaultValue: 'Operation failed' })))
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

  const connectEmailAccount = useCallback(async () => {
    const provider = String(emailForm.provider || 'gmail').toLowerCase()
    await createCommunicationAccount({
      channel: 'email',
      account_label: emailForm.accountLabel.trim() || t('app.communications.setup.defaults.main_mailbox', { defaultValue: 'Main mailbox' }),
      inbox_address: emailForm.inboxAddress.trim() || undefined,
      settings_json: {
        provider,
        oauth: {
          provider,
          client_id: emailForm.clientId.trim() || undefined,
          client_secret: emailForm.clientSecret.trim() || undefined,
          redirect_uri: emailForm.redirectUri.trim() || undefined,
        },
      },
    })
    const latest = await getCommunicationsSettings()
    await patchCommunicationsSettings({
      email: {
        ...(latest.email || {}),
        incomingEnabled: true,
        syncIntervalMinutes: latest.email?.syncIntervalMinutes ?? 5,
      },
    })
  }, [emailForm, t])

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
    const first = emailAccounts[0]
    if (!first) throw new Error(t('app.communications.setup.errors.no_active_email', { defaultValue: 'No active email account' }))
    const res = await testCommunicationAccountConnection(first.id)
    if (!res.ok) {
      throw new Error(
        res.detail ||
          t('app.communications.setup.errors.email_connection_test_failed', {
            defaultValue: 'Email connection test failed',
          }),
      )
    }
    return res
  }, [emailAccounts])

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
    const first = oauthEmailAccounts[0]
    if (!first) throw new Error(t('app.communications.setup.errors.no_oauth_email', { defaultValue: 'No OAuth email account available' }))
    const res = await startCommunicationAccountOAuth(first.id, { force_consent: true })
    setOauthStartByAccountId((p) => ({ ...p, [first.id]: { state: res.state, authUrl: res.auth_url } }))
  }, [oauthEmailAccounts])

  const completeOAuthForFirstEmailAccount = useCallback(async () => {
    const first = oauthEmailAccounts[0]
    if (!first) throw new Error(t('app.communications.setup.errors.no_oauth_email', { defaultValue: 'No OAuth email account available' }))
    const state = String(oauthStartByAccountId[first.id]?.state || first.settings_json?.oauth?.state || '').trim()
    if (!state) throw new Error(t('app.communications.setup.errors.oauth_start_first', { defaultValue: 'Run OAuth start first' }))
    const code = String(oauthCodeByAccountId[first.id] || '').trim()
    if (!code) {
      throw new Error(
        t('app.communications.setup.errors.oauth_code_required', { defaultValue: 'Paste authorization code first' }),
      )
    }
    await completeCommunicationAccountOAuth(first.id, {
      state,
      code,
      simulate_exchange: false,
    })
    setOauthCodeByAccountId((p) => ({ ...p, [first.id]: '' }))
  }, [oauthEmailAccounts, oauthCodeByAccountId, oauthStartByAccountId])

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
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <input value={emailForm.accountLabel} onChange={(e) => setEmailForm((p) => ({ ...p, accountLabel: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.account_label', { defaultValue: 'Account label' })} />
            <input value={emailForm.inboxAddress} onChange={(e) => setEmailForm((p) => ({ ...p, inboxAddress: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.mailbox_address', { defaultValue: 'Mailbox address' })} />
            <select value={emailForm.provider} onChange={(e) => setEmailForm((p) => ({ ...p, provider: e.target.value }))} className="input">
              <option value="gmail">{t('app.communications.setup.providers.gmail', { defaultValue: 'Gmail OAuth' })}</option>
              <option value="microsoft_graph">{t('app.communications.setup.providers.microsoft', { defaultValue: 'Microsoft OAuth' })}</option>
            </select>
            <input value={emailForm.clientId} onChange={(e) => setEmailForm((p) => ({ ...p, clientId: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.oauth_client_id', { defaultValue: 'OAuth client_id' })} />
            <input type="password" value={emailForm.clientSecret} onChange={(e) => setEmailForm((p) => ({ ...p, clientSecret: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.oauth_client_secret', { defaultValue: 'OAuth client_secret' })} />
            <input value={emailForm.redirectUri} onChange={(e) => setEmailForm((p) => ({ ...p, redirectUri: e.target.value }))} className="input" placeholder={t('app.communications.setup.fields.redirect_uri', { defaultValue: 'Redirect URI' })} />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() =>
                void runAction(
                  'email-connect',
                  connectEmailAccount,
                  t('app.communications.setup.notices.email_account_created', { defaultValue: 'Email account created' }),
                )
              }
              disabled={busyKey !== null || !emailForm.accountLabel.trim()}
              className="btn-primary btn-sm disabled:opacity-60"
            >
              {busyKey === 'email-connect' ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.communications.setup.actions.connect_email', { defaultValue: 'Create email account' })}
            </button>
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
              disabled={busyKey !== null || emailAccounts.length === 0}
              className="btn-secondary btn-sm disabled:opacity-60"
            >
              {busyKey === 'email-test' ? t('common.loading', { defaultValue: 'Loading...' }) : t('app.communications.email.test_connection', { defaultValue: 'Test connection' })}
            </button>
            <Link to="/app/email" className="btn-secondary btn-sm">
              {t('app.nav.items.email_inbox', { defaultValue: 'Email inbox' })}
            </Link>
          </div>
          {oauthEmailAccounts.length > 0 && (
            <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-3">
              <div className="text-xs font-semibold text-slate-700">
                {t('app.communications.setup.oauth_quick_connect', { defaultValue: 'OAuth quick connect' })}
              </div>
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
                  disabled={busyKey !== null}
                  className="btn-secondary btn-xs disabled:opacity-60"
                >
                  {busyKey === 'oauth-start'
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.setup.actions.oauth_start', { defaultValue: 'OAuth start' })}
                </button>
                {oauthStartByAccountId[oauthEmailAccounts[0].id]?.authUrl && (
                  <a
                    href={oauthStartByAccountId[oauthEmailAccounts[0].id]?.authUrl}
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
                  value={oauthCodeByAccountId[oauthEmailAccounts[0].id] || ''}
                  onChange={(e) => setOauthCodeByAccountId((p) => ({ ...p, [oauthEmailAccounts[0].id]: e.target.value }))}
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
                  disabled={busyKey !== null}
                  className="btn-secondary btn-xs disabled:opacity-60"
                >
                  {busyKey === 'oauth-complete'
                    ? t('common.loading', { defaultValue: 'Loading...' })
                    : t('app.communications.setup.actions.oauth_complete', { defaultValue: 'OAuth complete' })}
                </button>
              </div>
            </div>
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
