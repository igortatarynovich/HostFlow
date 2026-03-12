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
  const [acceptTerms, setAcceptTerms] = useState(false)
  const [acceptPrivacy, setAcceptPrivacy] = useState(false)
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
    if (!acceptTerms || !acceptPrivacy) {
      setError(t('app.signup.errors.consent_required', { defaultValue: 'You must accept Terms and Privacy Policy to continue.' }))
      return
    }
    setLoading(true)
    try {
      const registration = await registerSelfService({
        email: email.trim(),
        password,
        workspace_name: workspaceName.trim(),
        full_name: fullName.trim() || undefined,
        plan_code: preselectedPlan || undefined,
        accept_terms: acceptTerms,
        accept_privacy: acceptPrivacy,
      })
      await login(email.trim(), password)
      const params = new URLSearchParams()
      params.set('signup', 'success')
      if (registration.tenant?.trial_ends_at) {
        params.set('trial_ends_at', registration.tenant.trial_ends_at)
      }
      navigate(`/app/onboarding/company?${params.toString()}`, { replace: true })
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
            <label className="flex items-start gap-2 text-xs text-slate-600">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                checked={acceptTerms}
                onChange={(e) => setAcceptTerms(e.target.checked)}
              />
              <span>
                {t('app.signup.accept_terms_prefix', { defaultValue: 'I accept the' })}{' '}
                <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                  {t('app.signup.accept_terms_link', { defaultValue: 'Terms of Service' })}
                </a>
                .
              </span>
            </label>
            <label className="flex items-start gap-2 text-xs text-slate-600">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                checked={acceptPrivacy}
                onChange={(e) => setAcceptPrivacy(e.target.checked)}
              />
              <span>
                {t('app.signup.accept_privacy_prefix', { defaultValue: 'I accept the' })}{' '}
                <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                  {t('app.signup.accept_privacy_link', { defaultValue: 'Privacy Policy' })}
                </a>
                .
              </span>
            </label>
            <button type="submit" className="btn-primary w-full py-3" disabled={loading}>
              {loading ? t('common.loading') : t('app.signup.submit', { defaultValue: 'Create account' })}
            </button>
            <p className="text-xs leading-relaxed text-slate-500">
              {t('app.signup.legal_notice', { defaultValue: 'By creating an account, you confirm that you reviewed:' })}{' '}
              <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                {t('app.signup.legal_notice_terms', { defaultValue: 'Terms of Service' })}
              </a>
              {', '}
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                {t('app.signup.legal_notice_privacy', { defaultValue: 'Privacy Policy' })}
              </a>
              {', '}
              <a href="/legal/cookies.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                {t('app.signup.legal_notice_cookies', { defaultValue: 'Cookie Policy' })}
              </a>
              .
            </p>
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
