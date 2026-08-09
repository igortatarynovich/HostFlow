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

function FieldHint({ children }: { children: string }) {
  if (!children.trim()) return null
  return <p className="mt-1 text-xs leading-relaxed text-slate-500">{children}</p>
}

export default function SignupPage() {
  const { t } = useI18n()
  const planLimitModal = usePlanLimitModal()
  useSeoMeta({
    title: t('app.seo.signup.title', { defaultValue: 'Create HostFlow account' }),
    description: t('app.seo.signup.description', {
      defaultValue: 'Create a HostFlow account, set up your company, and start hiring workflows.',
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
    } catch (err: unknown) {
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
    <div className="relative min-h-screen overflow-hidden bg-[#f6fbff] px-4 py-10 flex items-center justify-center">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(94,186,205,0.35),transparent_55%),radial-gradient(circle_at_85%_0%,rgba(25,78,122,0.2),transparent_65%)]" />
      <div className="relative w-full max-w-md">
        <div className="card p-8">
          <PublicBrandingLogo showWordmark />
          <h1 className="mt-6 text-2xl font-semibold text-slate-900">
            {t('app.signup.title', { defaultValue: 'Sign up for HostFlow' })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {planLabel
              ? t('app.signup.subtitle_with_plan', {
                  defaultValue:
                    'Plan {plan} was selected on Pricing. After this form you will describe your company, then you can confirm payment in Billing.',
                  values: { plan: planLabel },
                })
              : t('app.signup.subtitle', {
                  defaultValue:
                    'Create login access so you can run vacancies, applications, and candidates in one place.',
                })}
          </p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="label">
                {t('app.signup.fields.workspace', { defaultValue: 'Your company name' })}
              </label>
              <input
                className="input"
                type="text"
                required
                minLength={2}
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                placeholder={t('app.signup.fields.workspace_placeholder', {
                  defaultValue: 'e.g. Acme Recruiting',
                })}
              />
              <FieldHint>
                {t('app.signup.fields.workspace_hint', {
                  defaultValue: 'Shown in the product as your organization name.',
                })}
              </FieldHint>
            </div>
            <div>
              <label className="label">
                {t('app.signup.fields.full_name', { defaultValue: 'Your name (optional)' })}
              </label>
              <input
                className="input"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder={t('app.signup.fields.full_name_placeholder', {
                  defaultValue: 'How we should address you',
                })}
              />
            </div>
            <div>
              <label className="label">
                {t('app.signup.fields.email', { defaultValue: 'Work email' })}
              </label>
              <input
                className="input"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('app.signup.fields.email_placeholder', {
                  defaultValue: 'you@company.com',
                })}
              />
              <FieldHint>
                {t('app.signup.fields.email_hint', {
                  defaultValue: 'Used to sign in and receive important account messages.',
                })}
              </FieldHint>
            </div>
            <div>
              <label className="label">
                {t('app.signup.fields.password', { defaultValue: 'Password for sign-in' })}
              </label>
              <input
                className="input"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <FieldHint>
                {t('app.signup.fields.password_hint', {
                  defaultValue: 'At least 8 characters.',
                })}
              </FieldHint>
            </div>
            <div>
              <label className="label">
                {t('app.signup.fields.confirm', { defaultValue: 'Repeat password' })}
              </label>
              <input
                className="input"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
              <FieldHint>
                {t('app.signup.fields.confirm_hint', {
                  defaultValue: 'Must match the password above.',
                })}
              </FieldHint>
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
              className="btn-primary w-full justify-center py-3 text-center text-base font-bold tracking-wide"
              disabled={loading || (captchaRequired && !captchaToken)}
            >
              {loading
                ? t('common.loading')
                : t('app.signup.submit', { defaultValue: 'Create account and continue' })}
            </button>
            <p className="text-xs leading-relaxed text-slate-500">
              {t('app.signup.legal_notice', {
                defaultValue: 'Cookie use is described in the',
              })}{' '}
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
