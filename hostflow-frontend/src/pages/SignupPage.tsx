import { useCallback, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { PublicBrandingLogo } from '../components/public/PublicLogo'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import TurnstileWidget from '../components/TurnstileWidget'
import { usePublicAuthConfig } from '../hooks/usePublicAuthConfig'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import {
  friendlyErrorBannerSecondary,
  friendlyFormHintError,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../utils/friendlyError'
import { registerSelfService } from '../api/users'
import { useAuth } from '../store/useAuth'
import { useSeoMeta } from '../hooks/useSeoMeta'
import {
  buildSignupSuccessContext,
  SIGNUP_SUCCESS_CONTEXT_KEY,
  signupContextToSearchParams,
} from '../constants/signupContext'
import { recordTtvStepCompleted } from '../api/analytics'
import { CRM_APP_PATHS } from '../app/crmAppPaths'

export default function SignupPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  useSeoMeta({
    title: t('app.seo.signup.title', { defaultValue: 'Create CRM Workspace' }),
    description: t('app.seo.signup.description', {
      defaultValue: 'Create your HostFlow account, start trial, and launch your recruiting workflow quickly.',
    }),
    canonicalPath: '/signup',
  })
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
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const publicAuthConfig = usePublicAuthConfig()
  const captchaRequired = Boolean(
    publicAuthConfig.turnstile_enabled && publicAuthConfig.turnstile_sitekey,
  )
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const handleCaptchaToken = useCallback((token: string | null) => {
    setCaptchaToken(token)
  }, [])

  const planLabel = useMemo(() => {
    if (!preselectedPlan) return null
    if (preselectedPlan === 'starter') return t('app.signup.plan_labels.solo', { defaultValue: 'Solo' })
    if (preselectedPlan === 'team') return t('app.signup.plan_labels.team', { defaultValue: 'Team' })
    if (preselectedPlan === 'pro') return t('app.signup.plan_labels.business', { defaultValue: 'Business' })
    return preselectedPlan
  }, [preselectedPlan, t])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError(friendlyFormHintError(t('app.signup.errors.password_mismatch', { defaultValue: 'Passwords do not match' }), t))
      return
    }
    if (password.length < 8) {
      setError(
        friendlyFormHintError(t('app.signup.errors.password_short', { defaultValue: 'Password must be at least 8 characters' }), t),
      )
      return
    }
    if (!acceptTerms || !acceptPrivacy) {
      setError(
        friendlyFormHintError(
          t('app.signup.errors.consent_required', { defaultValue: 'You must accept Terms and Privacy Policy to continue.' }),
          t,
        ),
      )
      return
    }
    if (captchaRequired && !captchaToken) {
      setError(
        friendlyFormHintError(
          t('app.signup.errors.captcha_required', {
            defaultValue: 'Please complete the challenge to verify you are human.',
          }),
          t,
        ),
      )
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
        turnstile_token: captchaToken,
      })
      const signupContext = buildSignupSuccessContext(
        registration.meta?.welcome_email_sent !== false,
        registration.tenant?.trial_ends_at || null,
      )
      if (typeof window !== 'undefined') {
        try {
          window.sessionStorage.setItem(SIGNUP_SUCCESS_CONTEXT_KEY, JSON.stringify(signupContext))
        } catch {
          // ignore storage errors
        }
      }
      void recordTtvStepCompleted({ event: 'ttv_step', action: 'completed', step_key: 'signup' })
      await login(email.trim(), password)
      const params = signupContextToSearchParams(signupContext)
      navigate(`${CRM_APP_PATHS.onboardingCompany}?${params.toString()}`, { replace: true })
    } catch (err: any) {
      if (typeof window !== 'undefined') {
        try {
          window.sessionStorage.removeItem(SIGNUP_SUCCESS_CONTEXT_KEY)
        } catch {
          // ignore storage errors
        }
      }
      const fb = t('app.signup.errors.generic', { defaultValue: 'Registration failed' })
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
            'radial-gradient(ellipse 80% 50% at 10% 0%, rgba(0,194,168,0.08), transparent 50%), radial-gradient(ellipse 60% 40% at 90% 10%, rgba(11,14,20,0.06), transparent 55%)',
        }}
      />
      <div className="relative w-full max-w-md">
        <div className="rounded-2xl border border-slate-200/80 bg-white p-8 shadow-[0_20px_50px_-36px_rgba(15,23,42,0.35)]">
          <PublicBrandingLogo showWordmark />
          <h1 className="mt-6 text-2xl font-semibold text-slate-900">
            {t('app.signup.title', { defaultValue: 'Create your CRM workspace' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.signup.subtitle', { defaultValue: 'Start with a trial and invite your team later.' })}
          </p>
          {planLabel && (
            <p className="mt-2 text-xs text-[#0F766E]">
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
                info={error}
                {...friendlyErrorBannerSecondary(error, '/login', t('app.login.title', { defaultValue: 'Sign in' }))}
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
            {captchaRequired && publicAuthConfig.turnstile_sitekey && (
              <div className="pt-1">
                <TurnstileWidget
                  sitekey={publicAuthConfig.turnstile_sitekey}
                  action="signup"
                  onToken={handleCaptchaToken}
                />
              </div>
            )}
            <button
              type="submit"
              className="inline-flex w-full items-center justify-center rounded-xl bg-[#00C2A8] px-4 py-3 text-base font-semibold text-[#04201C] shadow-[0_12px_40px_-12px_rgba(0,194,168,0.55)] transition hover:bg-[#1ad4bb] disabled:opacity-60"
              disabled={loading || (captchaRequired && !captchaToken)}
            >
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
            <Link to="/login" className="font-medium text-[#0F766E] hover:text-[#0B0E14] hover:underline">
              {t('app.signup.sign_in', { defaultValue: 'Sign in' })}
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
