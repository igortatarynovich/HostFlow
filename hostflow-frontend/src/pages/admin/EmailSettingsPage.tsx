import { useCallback, useEffect, useState } from 'react'
import { useI18n } from '../../i18n'
import { getEmailConfig, sendTestEmail, upsertEmailConfig, type EmailConfig, type EmailConfigUpdate } from '../../api/emailSettings'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useToast } from '../../components/Toast'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { recordTtvStepCompleted } from '../../api/analytics'

export default function EmailSettingsPage() {
  const { t } = useI18n()
  const { notify } = useToast()
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
      setPageError(
        getFriendlyErrorInfo(
          err,
          t('admin.email.load_error', { defaultValue: 'Failed to load email settings' }),
        ),
      )
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

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
      setPageError(
        getFriendlyErrorInfo(
          e,
          t('admin.email.save_error', { defaultValue: 'Failed to save email settings' }),
        ),
      )
      notify({ title: e?.response?.data?.detail ?? 'Error', variant: 'error' })
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
      setPageError(
        getFriendlyErrorInfo(
          e,
          t('admin.email.test_error', { defaultValue: 'Failed to send test email' }),
        ),
      )
      notify({ title: e?.response?.data?.detail ?? 'Error', variant: 'error' })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <p className="text-slate-500">{t('common.loading', { defaultValue: 'Loading...' })}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {pageError && (
        <ErrorRecoveryBanner
          info={pageError}
          onRetry={() => void load()}
          retryLabel={t('common.actions.refresh', { defaultValue: 'Refresh' })}
          secondaryTo="/app/settings/team"
          secondaryLabel={t('common.navigation.settings', { defaultValue: 'Settings' })}
        />
      )}

      <section className="card p-6">
        <header className="mb-4">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('admin.email.title', { defaultValue: 'Poczta (SMTP)' })}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {t('admin.email.description', {
              defaultValue: 'Skonfiguruj SMTP, aby wysyłać maile do kandydatów (RODO, powiadomienia). Dla Google Workspace użyj: smtp.gmail.com, port 587, App Password.',
            })}
          </p>
        </header>

        <div className="space-y-4 max-w-xl">
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
      </section>

      {config && (
        <section className="card p-6">
          <h3 className="text-lg font-medium text-slate-900 mb-4">
            {t('admin.email.test_title', { defaultValue: 'Wyślij testową wiadomość' })}
          </h3>
          <div className="flex gap-2 max-w-md">
            <input
              type="email"
              value={testTo}
              onChange={(e) => setTestTo(e.target.value)}
              placeholder={t('admin.email.placeholders.test_to', { defaultValue: 'test@example.com' })}
              className="input flex-1"
            />
            <button
              type="button"
              onClick={handleTest}
              disabled={testing}
              className="btn-secondary"
            >
              {testing ? t('common.sending', { defaultValue: 'Wysyłanie...' }) : t('admin.email.send_test', { defaultValue: 'Wyślij test' })}
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
