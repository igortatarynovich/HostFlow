import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { useI18n } from '../../i18n'
import { getEmailConfig, sendTestEmail, upsertEmailConfig, type EmailConfig, type EmailConfigUpdate } from '../../api/emailSettings'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useToast } from '../../components/Toast'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { recordTtvStepCompleted } from '../../api/analytics'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { usePlanLimitModal } from '../../contexts/PlanLimitModalContext'

export default function EmailSettingsPage() {
  const { t } = useI18n()
  const { notify } = useToast()
  const planLimitModal = usePlanLimitModal()
  const [config, setConfig] = useState<EmailConfig | null | undefined>(undefined)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)

  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState(587)
  const [smtpUser, setSmtpUser] = useState('')
  const [smtpPassword, setSmtpPassword] = useState('')
  const [fromEmail, setFromEmail] = useState('')
  const [fromName, setFromName] = useState('')
  const [useTls, setUseTls] = useState(true)
  const [isActive, setIsActive] = useState(true)
  const [testTo, setTestTo] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setPageError(null)
      const c = await getEmailConfig()
      setConfig(c)
      if (c) {
        setSmtpHost(c.smtp_host ?? '')
        setSmtpPort(c.smtp_port ?? 587)
        setSmtpUser(c.smtp_user ?? '')
        setFromEmail(c.from_email)
        setFromName(c.from_name ?? '')
        setUseTls(c.use_tls)
        setIsActive(c.is_active)
      } else {
        setSmtpHost('')
        setSmtpPort(587)
        setSmtpUser('')
        setSmtpPassword('')
        setFromEmail('')
        setFromName('')
        setUseTls(true)
        setIsActive(true)
      }
    } catch (err: any) {
      setConfig(null)
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('admin.email.load_error', { defaultValue: 'Failed to load email settings' }),
        )
      ) {
        setPageError(
          getFriendlyErrorInfo(
            err,
            t('admin.email.load_error', { defaultValue: 'Failed to load email settings' }),
            t,
          ),
        )
      }
    } finally {
      setLoading(false)
    }
  }, [planLimitModal, t])

  useEffect(() => {
    void load()
  }, [load])

  const emailHubStatus = useMemo(() => {
    if (loading || config === undefined) return 'loading' as const
    if (config === null) return 'no_config' as const
    if (!config.is_active) return 'paused' as const
    return 'live' as const
  }, [config, loading])

  const emailStatusHeadline = useMemo(() => {
    switch (emailHubStatus) {
      case 'loading':
        return t('common.loading')
      case 'no_config':
        return t('admin.email.integration_wizard.status_no_config')
      case 'paused':
        return t('admin.email.integration_wizard.status_paused')
      case 'live':
        return t('admin.email.integration_wizard.status_live')
      default:
        return ''
    }
  }, [emailHubStatus, t])

  const emailStepHighlight = useMemo(() => {
    if (emailHubStatus === 'loading') return 1
    if (emailHubStatus === 'live') return 3
    if (emailHubStatus === 'paused') return 2
    return 1
  }, [emailHubStatus])

  const handleSave = async () => {
    if (!fromEmail.trim()) {
      notify({ title: t('admin.email.validation.from_required', { defaultValue: 'Podaj adres nadawcy' }), variant: 'error' })
      return
    }
    if (!smtpHost.trim()) {
      notify({ title: t('admin.email.validation.host_required', { defaultValue: 'Podaj serwer SMTP' }), variant: 'error' })
      return
    }
    setSaving(true)
    try {
      setPageError(null)
      const payload: EmailConfigUpdate = {
        smtp_host: smtpHost.trim(),
        smtp_port: smtpPort,
        smtp_user: smtpUser.trim() || undefined,
        from_email: fromEmail.trim(),
        from_name: fromName.trim() || undefined,
        use_tls: useTls,
        is_active: isActive,
      }
      if (smtpPassword) payload.smtp_password = smtpPassword
      const updated = await upsertEmailConfig(payload)
      setConfig(updated)
      setSmtpPassword('')
      notify({ title: t('admin.email.saved', { defaultValue: 'Ustawienia zapisane' }), variant: 'success' })
      // Если email был неактивен и стал активен — считаем шаг email_connected завершённым для TTV.
      if (!config?.is_active && updated.is_active) {
        void recordTtvStepCompleted({ event: 'ttv_step', action: 'completed', step_key: 'email_connected' })
      }
    } catch (e: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('admin.email.save_error', { defaultValue: 'Failed to save email settings' }),
        )
      ) {
        setPageError(
          getFriendlyErrorInfo(
            e,
            t('admin.email.save_error', { defaultValue: 'Failed to save email settings' }),
            t,
          ),
        )
        notify({ title: e?.response?.data?.detail ?? 'Error', variant: 'error' })
      }
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    if (!testTo.trim()) {
      notify({ title: t('admin.email.validation.test_to_required', { defaultValue: 'Podaj adres do testu' }), variant: 'error' })
      return
    }
    setTesting(true)
    try {
      setPageError(null)
      await sendTestEmail(testTo.trim())
      notify({ title: t('admin.email.test_sent', { defaultValue: 'Testowa wiadomość wysłana' }), variant: 'success' })
    } catch (e: any) {
      if (
        !planLimitModal?.showPlanLimitIfNeeded(
          e,
          t('admin.email.test_error', { defaultValue: 'Failed to send test email' }),
        )
      ) {
        setPageError(
          getFriendlyErrorInfo(
            e,
            t('admin.email.test_error', { defaultValue: 'Failed to send test email' }),
            t,
          ),
        )
        notify({ title: e?.response?.data?.detail ?? 'Error', variant: 'error' })
      }
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <p className="text-slate-500">{t('common.loading')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {pageError && (
        <ErrorRecoveryBanner
          info={pageError}
          onRetry={() => void load()}
          retryLabel={t('common.actions.refresh')}
          {...friendlyErrorBannerSecondary(
            pageError,
            CRM_APP_PATHS.settingsIntegrations,
            t('admin.integrations_hub.title', { defaultValue: 'Integration hub' }),
          )}
        />
      )}

      <section className="settings-panel">
        <SettingsSubpageHeader
          className="mb-4"
          backHref={CRM_APP_PATHS.settingsIntegrations}
          backLabel={t('admin.integrations_hub.back_to_hub')}
          kicker={t('admin.integrations_hub.integration_kicker', { defaultValue: 'Integration' })}
          title={t('admin.email.title', { defaultValue: 'Email (SMTP)' })}
          subtitle={t('admin.email.description_short', {
            defaultValue: 'Outbound SMTP for CRM notifications. Google Workspace: smtp.gmail.com, port 587, App Password.',
          })}
        />

        <div className="mt-4 flex justify-end">
          <button type="button" className="btn-secondary btn-sm" onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced
              ? t('admin.calendar_integrations.actions.hide_advanced', { defaultValue: 'Hide advanced' })
              : t('admin.calendar_integrations.actions.show_advanced', { defaultValue: 'Show advanced' })}
          </button>
        </div>

        <div className="mt-6 space-y-4 max-w-xl">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('admin.email.integration_wizard.step_smtp')}
          </h2>
          <div>
            <label className="label">{t('admin.email.smtp_host', { defaultValue: 'Serwer SMTP' })}</label>
            <input
              type="text"
              value={smtpHost}
              onChange={(e) => setSmtpHost(e.target.value)}
              placeholder="smtp.gmail.com"
              className="input mt-1"
            />
          </div>
          <div>
            <label className="label">{t('admin.email.smtp_port', { defaultValue: 'Port' })}</label>
            <input
              type="number"
              value={smtpPort}
              onChange={(e) => setSmtpPort(parseInt(e.target.value, 10) || 587)}
              className="input mt-1 max-w-[120px]"
            />
          </div>
          <div>
            <label className="label">{t('admin.email.smtp_user', { defaultValue: 'Użytkownik SMTP' })}</label>
            <input
              type="text"
              value={smtpUser}
              onChange={(e) => setSmtpUser(e.target.value)}
              placeholder={t('admin.email.placeholders.smtp_user', { defaultValue: 'email@example.com' })}
              className="input mt-1"
            />
          </div>
          <div>
            <label className="label">{t('admin.email.smtp_password', { defaultValue: 'Hasło (App Password)' })}</label>
            <input
              type="password"
              value={smtpPassword}
              onChange={(e) => setSmtpPassword(e.target.value)}
              placeholder={config?.has_password ? '••••••••' : ''}
              className="input mt-1"
            />
            {config?.has_password && !smtpPassword && (
              <p className="mt-1 text-xs text-slate-500">
                {t('admin.email.password_hint', { defaultValue: 'Pozostaw puste, aby zachować obecne hasło' })}
              </p>
            )}
          </div>
          <div>
            <label className="label">{t('admin.email.from_email', { defaultValue: 'Adres nadawcy' })} *</label>
            <input
              type="email"
              value={fromEmail}
              onChange={(e) => setFromEmail(e.target.value)}
              placeholder={t('admin.email.placeholders.from_email', { defaultValue: 'info@hostflow.cc' })}
              className="input mt-1"
            />
          </div>
          <div>
            <label className="label">{t('admin.email.from_name', { defaultValue: 'Nazwa nadawcy' })}</label>
            <input
              type="text"
              value={fromName}
              onChange={(e) => setFromName(e.target.value)}
              placeholder={t('admin.email.placeholders.from_name', { defaultValue: 'HostFlow' })}
              className="input mt-1"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="use_tls"
              checked={useTls}
              onChange={(e) => setUseTls(e.target.checked)}
            />
            <label htmlFor="use_tls" className="text-sm text-slate-700">
              {t('admin.email.use_tls', { defaultValue: 'Użyj TLS (port 587)' })}
            </label>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            <label htmlFor="is_active" className="text-sm text-slate-700">
              {t('admin.email.is_active', { defaultValue: 'Włącz wysyłkę maili' })}
            </label>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="btn-primary"
            >
              {saving ? t('common.saving', { defaultValue: 'Zapisywanie...' }) : t('common.save', { defaultValue: 'Zapisz' })}
            </button>
          </div>
        </div>

        {showAdvanced ? (
          <>
            <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('admin.email.integration_wizard.connection_status')}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span
                  className={clsx(
                    'badge',
                    emailHubStatus === 'live' && 'border-emerald-200 bg-emerald-50 text-emerald-800',
                    emailHubStatus === 'paused' && 'border-amber-200 bg-amber-50 text-amber-900',
                    emailHubStatus === 'no_config' && 'border-slate-200 bg-slate-100 text-slate-600',
                    emailHubStatus === 'loading' && 'border-slate-200 bg-slate-100 text-slate-500',
                  )}
                >
                  {emailHubStatus === 'live'
                    ? t('admin.communications_messengers.integration_wizard.tech_status.connected', { defaultValue: 'Connected' })
                    : emailHubStatus === 'paused'
                      ? t('admin.communications_messengers.states.disabled', { defaultValue: 'disabled' })
                      : emailHubStatus === 'loading'
                        ? t('common.loading')
                        : t('admin.communications_messengers.integration_wizard.tech_status.none', { defaultValue: 'Not configured' })}
                </span>
                <span className="text-sm text-slate-700">{emailStatusHeadline}</span>
              </div>
            </div>

            <ol className="mt-6 grid gap-2 sm:grid-cols-3">
              {[
                { n: 1, label: t('admin.email.integration_wizard.step_smtp') },
                { n: 2, label: t('admin.email.integration_wizard.step_test') },
                { n: 3, label: t('admin.communications_messengers.integration_wizard.step_active') },
              ].map(({ n, label }) => (
                <li
                  key={n}
                  className={clsx(
                    'rounded-lg border px-3 py-2 text-center text-sm font-medium',
                    emailStepHighlight === n ? 'border-brand-500 bg-brand-50 text-brand-900' : 'border-slate-200 text-slate-500',
                  )}
                >
                  <span className="mr-1 font-normal text-slate-400">{n}.</span>
                  {label}
                </li>
              ))}
            </ol>

            <div className="mt-8 border-t border-slate-200 pt-6 max-w-xl">
              <h2 className="text-sm font-semibold text-slate-900">{t('admin.email.integration_wizard.step_test')}</h2>
              {config ? (
                <>
                  <p className="mt-1 text-xs text-slate-500">{t('admin.email.test_title', { defaultValue: 'Send a test message' })}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <input
                      type="email"
                      value={testTo}
                      onChange={(e) => setTestTo(e.target.value)}
                      placeholder={t('admin.email.placeholders.test_to', { defaultValue: 'test@example.com' })}
                      className="input min-w-[200px] flex-1"
                    />
                    <button
                      type="button"
                      onClick={handleTest}
                      disabled={testing}
                      className="btn-secondary"
                    >
                      {testing ? t('common.sending', { defaultValue: 'Sending...' }) : t('admin.email.send_test', { defaultValue: 'Send test' })}
                    </button>
                  </div>
                </>
              ) : (
                <p className="mt-2 text-sm text-slate-500">{t('admin.email.integration_wizard.test_locked')}</p>
              )}
            </div>
          </>
        ) : null}
      </section>
    </div>
  )
}
