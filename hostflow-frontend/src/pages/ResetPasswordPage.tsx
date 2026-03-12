import { useState, useEffect, type FormEvent } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import { resetPasswordWithToken } from '../api/users'
import { PublicBrandingLogo } from '../components/public/PublicLogo'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'

export default function ResetPasswordPage() {
  const { t } = useI18n()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [noToken, setNoToken] = useState(false)

  useEffect(() => {
    if (!token || token.length < 20) {
      setNoToken(true)
    }
  }, [token])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError(t('app.reset_password.errors.mismatch', { defaultValue: 'Hasła nie są identyczne' }))
      return
    }
    if (password.length < 8) {
      setError(t('app.reset_password.errors.too_short', { defaultValue: 'Hasło musi mieć minimum 8 znaków' }))
      return
    }
    setLoading(true)
    try {
      await resetPasswordWithToken(token, password)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? t('app.reset_password.errors.generic', { defaultValue: 'Token nieprawidłowy lub wygasł' }))
    } finally {
      setLoading(false)
    }
  }

  if (noToken) {
    return (
      <div className="relative min-h-screen overflow-hidden bg-[#f6fbff] px-4 py-10 flex items-center justify-center">
        <div className="card p-8 max-w-md">
          <PublicBrandingLogo showWordmark />
          <h1 className="mt-6 text-xl font-semibold text-slate-900">
            {t('app.reset_password.no_token', { defaultValue: 'Brak tokenu' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.reset_password.no_token_hint', { defaultValue: 'Użyj linku z e-maila lub poproś o nowy link do resetu.' })}
          </p>
          <Link to="/forgot-password" className="btn-primary mt-6 inline-block w-full text-center">
            {t('app.forgot_password.submit', { defaultValue: 'Wyślij link' })}
          </Link>
          <Link to="/login" className="mt-4 block text-center text-sm text-brand-600 hover:underline">
            {t('app.forgot_password.back', { defaultValue: 'Wróć do logowania' })}
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f6fbff] px-4 py-10 flex items-center justify-center">
      <div className="relative w-full max-w-md">
        <div className="card p-8">
          <PublicBrandingLogo showWordmark />
          <h1 className="mt-6 text-2xl font-semibold text-slate-900">
            {t('app.reset_password.title', { defaultValue: 'Ustaw nowe hasło' })}
          </h1>

          {success ? (
            <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              {t('app.reset_password.success', { defaultValue: 'Hasło zaktualizowane. Przekierowanie do logowania...' })}
            </div>
          ) : (
            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <div>
                <label className="label">{t('app.reset_password.new_password', { defaultValue: 'Nowe hasło' })}</label>
                <input
                  className="input"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div>
                <label className="label">{t('app.reset_password.confirm', { defaultValue: 'Potwierdź hasło' })}</label>
                <input
                  className="input"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </div>
              {error && (
                <ErrorRecoveryBanner
                  info={{ title: error, hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }) }}
                  compact
                />
              )}
              <button type="submit" className="btn-primary w-full py-3" disabled={loading}>
                {loading ? t('common.loading') : t('app.reset_password.submit', { defaultValue: 'Zapisz hasło' })}
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
