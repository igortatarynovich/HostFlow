import { useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { PublicBrandingLogo } from '../components/public/PublicLogo'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { registerSelfService } from '../api/users'
import { useAuth } from '../store/useAuth'

export default function SignupPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()
  const preselectedPlan = (searchParams.get('plan') || '').trim().toLowerCase()

  const [workspaceName, setWorkspaceName] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const planLabel = useMemo(() => {
    if (!preselectedPlan) return null
    if (preselectedPlan === 'starter') return 'Starter'
    if (preselectedPlan === 'team') return 'Team'
    if (preselectedPlan === 'pro') return 'Pro'
    return preselectedPlan
  }, [preselectedPlan])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError(t('app.signup.errors.password_mismatch', { defaultValue: 'Passwords do not match' }))
      return
    }
    if (password.length < 8) {
      setError(t('app.signup.errors.password_short', { defaultValue: 'Password must be at least 8 characters' }))
      return
    }
    setLoading(true)
    try {
      await registerSelfService({
        email: email.trim(),
        password,
        workspace_name: workspaceName.trim(),
        full_name: fullName.trim() || undefined,
        plan_code: preselectedPlan || undefined,
      })
      await login(email.trim(), password)
      navigate('/app/onboarding/company', { replace: true })
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || t('app.signup.errors.generic', { defaultValue: 'Registration failed' }))
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
            {t('app.signup.title', { defaultValue: 'Create your CRM workspace' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.signup.subtitle', { defaultValue: 'Start with a trial and invite your team later.' })}
          </p>
          {planLabel && (
            <p className="mt-2 text-xs text-brand-700">
              {t('app.signup.selected_plan', { defaultValue: 'Selected plan: {plan}', values: { plan: planLabel } })}
            </p>
          )}

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="label">{t('app.signup.fields.workspace', { defaultValue: 'Workspace name' })}</label>
              <input
                className="input"
                type="text"
                required
                minLength={2}
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                placeholder={t('app.signup.fields.workspace_placeholder', { defaultValue: 'Acme Recruiting' })}
              />
            </div>
            <div>
              <label className="label">{t('app.signup.fields.full_name', { defaultValue: 'Full name (optional)' })}</label>
              <input
                className="input"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
            <div>
              <label className="label">{t('app.login.fields.email')}</label>
              <input
                className="input"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="label">{t('app.signup.fields.password', { defaultValue: 'Password' })}</label>
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
              <label className="label">{t('app.signup.fields.confirm', { defaultValue: 'Confirm password' })}</label>
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
              {loading ? t('common.loading') : t('app.signup.submit', { defaultValue: 'Create account' })}
            </button>
          </form>

          <p className="mt-4 text-center text-sm text-slate-600">
            {t('app.signup.have_account', { defaultValue: 'Already have an account?' })}{' '}
            <Link to="/login" className="text-brand-600 hover:underline">
              {t('app.signup.sign_in', { defaultValue: 'Sign in' })}
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
