import { useCallback, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { requestPasswordReset } from '../api/users'
import { PublicBrandingLogo } from '../components/public/PublicLogo'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import TurnstileWidget from '../components/TurnstileWidget'
import { usePublicAuthConfig } from '../hooks/usePublicAuthConfig'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../utils/friendlyError'
import { useRobotsMeta } from '../hooks/useRobotsMeta'

export default function ForgotPasswordPage() {
  useRobotsMeta({ index: false, follow: false })
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const publicAuthConfig = usePublicAuthConfig()
  const captchaRequired = Boolean(
    publicAuthConfig.turnstile_enabled && publicAuthConfig.turnstile_sitekey,
  )
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const handleCaptchaToken = useCallback((token: string | null) => {
    setCaptchaToken(token)
  }, [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await requestPasswordReset(email, captchaToken)
      setSent(true)
    } catch (err: unknown) {
      const fb = t('app.forgot_password.errors.generic', { defaultValue: 'Could not send reset link' })
      if (!planLimitModal?.showPlanLimitIfNeeded(err, fb)) {
        setError(getFriendlyErrorInfo(err, fb, t))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#F7F8FA] px-4 py-10 flex items-center justify-center text-slate-900 antialiased">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 70% 50% at 15% 10%, rgba(0,194,168,0.12), transparent 55%), linear-gradient(180deg, #F7F8FA 0%, #EEF1F4 100%)',
        }}
      />
      <div className="relative w-full max-w-md">
        <div className="rounded-2xl border border-slate-200/80 bg-white p-8 shadow-[0_20px_50px_-36px_rgba(15,23,42,0.35)]">
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
                  info={error}
                  {...friendlyErrorBannerSecondary(error, '/login', t('app.forgot_password.back', { defaultValue: 'Back to sign in' }))}
                  compact
                />
              )}
              {captchaRequired && publicAuthConfig.turnstile_sitekey && (
                <div className="pt-1">
                  <TurnstileWidget
                    sitekey={publicAuthConfig.turnstile_sitekey}
                    action="password_reset"
                    onToken={handleCaptchaToken}
                  />
                </div>
              )}
              <button
                type="submit"
                className="inline-flex w-full items-center justify-center rounded-xl bg-[#00C2A8] px-4 py-3 text-base font-semibold text-[#04201C] transition hover:bg-[#1ad4bb] disabled:opacity-60"
                disabled={loading || (captchaRequired && !captchaToken)}
              >
                {loading ? t('common.loading') : t('app.forgot_password.submit', { defaultValue: 'Wyślij link' })}
              </button>
            </form>
          )}

          <Link
            to="/login"
            className="mt-6 block text-center text-sm font-medium text-[#0F766E] hover:text-[#0B0E14] hover:underline"
          >
            {t('app.forgot_password.back', { defaultValue: 'Wróć do logowania' })}
          </Link>
        </div>
      </div>
    </div>
  )
}
