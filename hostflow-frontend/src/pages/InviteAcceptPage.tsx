import { useState, useEffect, type FormEvent } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import { acceptInvite } from '../api/users'
import { PublicBrandingLogo } from '../components/public/PublicLogo'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import {
  friendlyErrorBannerSecondary,
  friendlyFormHintError,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../utils/friendlyError'
import { useAuth } from '../store/useAuth'
import { useRobotsMeta } from '../hooks/useRobotsMeta'
import { rememberLoginNotice } from '../store/auth'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'

export default function InviteAcceptPage() {
  useRobotsMeta({ index: false, follow: false })
  const { t } = useI18n()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const planLimitModal = usePlanLimitModal()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fullName, setFullName] = useState('')
  const [shortId, setShortId] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [noToken, setNoToken] = useState(false)

  useEffect(() => {
    if (!token || token.length < 16) {
      setNoToken(true)
    }
  }, [token])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError(friendlyFormHintError(t('app.invite_accept.errors.mismatch', { defaultValue: 'Passwords do not match' }), t))
      return
    }
    if (password.length < 8) {
      setError(friendlyFormHintError(t('app.invite_accept.errors.too_short', { defaultValue: 'Password must be at least 8 characters' }), t))
      return
    }
    setLoading(true)
    try {
      const result = await acceptInvite({
        token,
        password,
        full_name: fullName.trim() || undefined,
        short_id: shortId.trim() || undefined,
      }) as { email?: string }
      setSuccess(true)
      const userEmail = result?.email
      if (userEmail) {
        try {
          await login(userEmail, password)
          navigate('/', { replace: true })
          return
        } catch {
          // fallback to login page
        }
        rememberLoginNotice('invite_accepted')
        navigate(`/login?email=${encodeURIComponent(userEmail)}`, { replace: true })
        return
      }
      rememberLoginNotice('invite_accepted')
      navigate('/login', { replace: true })
    } catch (err: unknown) {
      if (
        planLimitModal?.showPlanLimitIfNeeded(
          err,
          t('app.invite_accept.errors.generic', { defaultValue: 'Invalid or expired invitation' }),
        )
      ) {
        return
      }
      setError(getFriendlyErrorInfo(err, t('app.invite_accept.errors.generic', { defaultValue: 'Invalid or expired invitation' }), t))
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
            {t('app.invite_accept.no_token', { defaultValue: 'Brak tokenu zaproszenia' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.invite_accept.no_token_hint', { defaultValue: 'Użyj linku z zaproszenia e-mail.' })}
          </p>
          <Link to="/login" className="btn-primary mt-6 inline-block w-full text-center">
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
            {t('app.invite_accept.title', { defaultValue: 'Przyjmij zaproszenie' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.invite_accept.subtitle', { defaultValue: 'Ustaw hasło i uzupełnij dane.' })}
          </p>

          {success ? (
            <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              {t('app.invite_accept.success', { defaultValue: 'Konto aktywowane. Przekierowanie...' })}
            </div>
          ) : (
            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <div>
                <label className="label">{t('app.invite_accept.full_name', { defaultValue: 'Imię i nazwisko' })}</label>
                <input
                  className="input"
                  type="text"
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
              <div>
                <label className="label">{t('app.invite_accept.short_id', { defaultValue: 'Short ID (opcjonalnie)' })}</label>
                <input
                  className="input"
                  type="text"
                  value={shortId}
                  onChange={(e) => setShortId(e.target.value)}
                />
              </div>
              <div>
                <label className="label">{t('app.invite_accept.password', { defaultValue: 'Hasło' })} *</label>
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
                <label className="label">{t('app.invite_accept.confirm', { defaultValue: 'Potwierdź hasło' })} *</label>
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
                  info={error}
                  {...friendlyErrorBannerSecondary(error, '/login', t('app.forgot_password.back', { defaultValue: 'Back to sign in' }))}
                  compact
                />
              )}
              <button type="submit" className="btn-primary w-full py-3" disabled={loading}>
                {loading ? t('common.loading') : t('app.invite_accept.submit', { defaultValue: 'Akceptuj i zaloguj' })}
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
