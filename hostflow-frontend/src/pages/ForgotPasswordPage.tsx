import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { requestPasswordReset } from '../api/users'
import { PublicBrandingLogo } from '../components/public/PublicLogo'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { useRobotsMeta } from '../hooks/useRobotsMeta'

export default function ForgotPasswordPage() {
  useRobotsMeta({ index: false, follow: false })
  const { t } = useI18n()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await requestPasswordReset(email)
      setSent(true)
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? t('app.forgot_password.errors.generic', { defaultValue: 'Nie udało się wysłać linku' }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f6fbff] px-4 py-10 flex items-center justify-center">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(94,186,205,0.35),transparent_55%),radial-gradient(circle_at_85%_0%,rgba(25,78,122,0.2),transparent_65%)]" />
      <div className="relative w-full max-w-md">
        <div className="card p-8">
          <PublicBrandingLogo showWordmark />
          <h1 className="mt-6 text-2xl font-semibold text-slate-900">
            {t('app.forgot_password.title', { defaultValue: 'Zapomniałeś hasła?' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.forgot_password.subtitle', { defaultValue: 'Podaj adres e-mail. Wyślemy link do ustawienia nowego hasła.' })}
          </p>

          {sent ? (
            <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              {t('app.forgot_password.sent', { defaultValue: 'Jeśli ten adres jest zarejestrowany, wysłaliśmy link. Sprawdź skrzynkę (i spam).' })}
            </div>
          ) : (
            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <div>
                <label className="label">{t('app.login.fields.email')}</label>
                <input
                  className="input"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t('app.forgot_password.fields.email_placeholder', { defaultValue: 'email@example.com' })}
                />
              </div>
              {error && (
                <ErrorRecoveryBanner
                  info={{ title: error, hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }) }}
                  compact
                />
              )}
              <button type="submit" className="btn-primary w-full py-3" disabled={loading}>
                {loading ? t('common.loading') : t('app.forgot_password.submit', { defaultValue: 'Wyślij link' })}
              </button>
            </form>
          )}

          <Link to="/login" className="mt-6 block text-center text-sm text-brand-600 hover:underline">
            {t('app.forgot_password.back', { defaultValue: 'Wróć do logowania' })}
          </Link>
        </div>
      </div>
    </div>
  )
}
