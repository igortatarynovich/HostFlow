import { useCallback, useMemo, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { PublicBrandingLogo } from '../components/public/PublicLogo'
import { ConsentRow } from '../components/public/ConsentRow'
import { InlineFieldError } from '../components/forms/InlineFieldError'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import TurnstileWidget from '../components/TurnstileWidget'
import { usePublicAuthConfig } from '../hooks/usePublicAuthConfig'
import { usePlanLimitModal } from '../contexts/PlanLimitModalContext'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../utils/friendlyError'
import { fieldControlClass, focusFirstInvalid } from '../utils/formFieldValidation'
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

type FieldKey = 'password' | 'confirm' | 'terms' | 'privacy' | 'captcha'

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
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldKey, string>>>({})
  const [submitError, setSubmitError] = useState<FriendlyErrorInfo | null>(null)

  const passwordRef = useRef<HTMLInputElement>(null)
  const confirmRef = useRef<HTMLInputElement>(null)
  const termsRef = useRef<HTMLInputElement>(null)
  const privacyRef = useRef<HTMLInputElement>(null)
  const captchaRef = useRef<HTMLDivElement>(null)

  const publicAuthConfig = usePublicAuthConfig()
  const captchaRequired = Boolean(
    publicAuthConfig.turnstile_enabled && publicAuthConfig.turnstile_sitekey,
  )
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const handleCaptchaToken = useCallback((token: string | null) => {
    setCaptchaToken(token)
    if (token) {
      setFieldErrors((prev) => {
        if (!prev.captcha) return prev
        const next = { ...prev }
        delete next.captcha
        return next
      })
    }
  }, [])

  const planLabel = useMemo(() => {
    if (!preselectedPlan) return null
    if (preselectedPlan === 'starter') return t('app.signup.plan_labels.solo', { defaultValue: 'Solo' })
    if (preselectedPlan === 'team') return t('app.signup.plan_labels.team', { defaultValue: 'Team' })
    if (preselectedPlan === 'pro') return t('app.signup.plan_labels.business', { defaultValue: 'Business' })
    return preselectedPlan
  }, [preselectedPlan, t])

  function clearFieldError(key: FieldKey) {
    setFieldErrors((prev) => {
      if (!prev[key]) return prev
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  function validateClient(): boolean {
    const next: Partial<Record<FieldKey, string>> = {}
    if (password.length < 8) {
      next.password = t('app.signup.errors.password_short', {
        defaultValue: 'Пароль должен быть не короче 8 символов',
      })
    }
    if (password !== confirm) {
      next.confirm = t('app.signup.errors.password_mismatch', {
        defaultValue: 'Пароли не совпадают — повторите в этом поле',
      })
    }
    if (!acceptTerms) {
      next.terms = t('app.signup.errors.terms_required', {
        defaultValue: 'Отметьте это поле: согласие с Условиями использования',
      })
    }
    if (!acceptPrivacy) {
      next.privacy = t('app.signup.errors.privacy_required', {
        defaultValue: 'Отметьте это поле: согласие с Политикой конфиденциальности',
      })
    }
    if (captchaRequired && !captchaToken) {
      next.captcha = t('app.signup.errors.captcha_required', {
        defaultValue: 'Пройдите проверку ниже, чтобы подтвердить, что вы человек',
      })
    }
    setFieldErrors(next)
    if (Object.keys(next).length === 0) return true

    const focusOrder: FieldKey[] = ['password', 'confirm', 'terms', 'privacy', 'captcha']
    const first = focusOrder.find((key) => next[key])
    const refMap: Record<FieldKey, HTMLElement | null> = {
      password: passwordRef.current,
      confirm: confirmRef.current,
      terms: termsRef.current,
      privacy: privacyRef.current,
      captcha: captchaRef.current,
    }
    if (first) focusFirstInvalid([refMap[first]])
    return false
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitError(null)
    if (!validateClient()) return

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
        setSubmitError(getFriendlyErrorInfo(err, fb, t))
      }
    } finally {
      setLoading(false)
    }
  }

  const inputBase = 'input'

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

          <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
            <div>
              <label className="label" htmlFor="signup-workspace">
                {t('app.signup.fields.workspace', { defaultValue: 'Your company name' })}
              </label>
              <input
                id="signup-workspace"
                className={inputBase}
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
              <label className="label" htmlFor="signup-full-name">
                {t('app.signup.fields.full_name', { defaultValue: 'Your name (optional)' })}
              </label>
              <input
                id="signup-full-name"
                className={inputBase}
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder={t('app.signup.fields.full_name_placeholder', {
                  defaultValue: 'How we should address you',
                })}
              />
            </div>
            <div>
              <label className="label" htmlFor="signup-email">
                {t('app.signup.fields.email', { defaultValue: 'Work email' })}
              </label>
              <input
                id="signup-email"
                className={inputBase}
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
              <label className="label" htmlFor="signup-password">
                {t('app.signup.fields.password', { defaultValue: 'Password for sign-in' })}
              </label>
              <input
                id="signup-password"
                ref={passwordRef}
                className={fieldControlClass(inputBase, Boolean(fieldErrors.password))}
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                aria-invalid={fieldErrors.password ? true : undefined}
                aria-describedby={fieldErrors.password ? 'signup-password-error' : undefined}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  clearFieldError('password')
                  clearFieldError('confirm')
                }}
              />
              <FieldHint>
                {t('app.signup.fields.password_hint', {
                  defaultValue: 'At least 8 characters.',
                })}
              </FieldHint>
              <InlineFieldError id="signup-password-error" message={fieldErrors.password} />
            </div>
            <div>
              <label className="label" htmlFor="signup-confirm">
                {t('app.signup.fields.confirm', { defaultValue: 'Repeat password' })}
              </label>
              <input
                id="signup-confirm"
                ref={confirmRef}
                className={fieldControlClass(inputBase, Boolean(fieldErrors.confirm))}
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                aria-invalid={fieldErrors.confirm ? true : undefined}
                aria-describedby={fieldErrors.confirm ? 'signup-confirm-error' : undefined}
                value={confirm}
                onChange={(e) => {
                  setConfirm(e.target.value)
                  clearFieldError('confirm')
                }}
              />
              <FieldHint>
                {t('app.signup.fields.confirm_hint', {
                  defaultValue: 'Must match the password above.',
                })}
              </FieldHint>
              <InlineFieldError id="signup-confirm-error" message={fieldErrors.confirm} />
            </div>

            <div className="space-y-2">
              <ConsentRow
                id="signup-accept-terms"
                ref={termsRef}
                checked={acceptTerms}
                showError={Boolean(fieldErrors.terms)}
                errorMessage={fieldErrors.terms}
                onChange={(checked) => {
                  setAcceptTerms(checked)
                  if (checked) clearFieldError('terms')
                }}
              >
                {t('app.signup.accept_terms_prefix', { defaultValue: 'I accept the' })}{' '}
                <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                  {t('app.signup.accept_terms_link', { defaultValue: 'Terms of Service' })}
                </a>
                .
              </ConsentRow>
              <ConsentRow
                id="signup-accept-privacy"
                ref={privacyRef}
                checked={acceptPrivacy}
                showError={Boolean(fieldErrors.privacy)}
                errorMessage={fieldErrors.privacy}
                onChange={(checked) => {
                  setAcceptPrivacy(checked)
                  if (checked) clearFieldError('privacy')
                }}
              >
                {t('app.signup.accept_privacy_prefix', { defaultValue: 'I accept the' })}{' '}
                <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="text-brand-700 hover:underline">
                  {t('app.signup.accept_privacy_link', { defaultValue: 'Privacy Policy' })}
                </a>
                .
              </ConsentRow>
            </div>

            {captchaRequired && publicAuthConfig.turnstile_sitekey ? (
              <div
                ref={captchaRef}
                tabIndex={-1}
                data-invalid={fieldErrors.captcha ? 'true' : undefined}
                className={
                  fieldErrors.captcha
                    ? 'rounded-lg border border-rose-400 bg-rose-50/50 p-3 outline outline-2 outline-rose-500 outline-offset-1'
                    : 'pt-1'
                }
              >
                <TurnstileWidget
                  sitekey={publicAuthConfig.turnstile_sitekey}
                  action="signup"
                  onToken={handleCaptchaToken}
                />
                <InlineFieldError id="signup-captcha-error" message={fieldErrors.captcha} />
              </div>
            ) : null}

            {submitError ? (
              <ErrorRecoveryBanner
                info={submitError}
                {...friendlyErrorBannerSecondary(submitError)}
                compact
              />
            ) : null}

            <button
              type="submit"
              className="btn-primary w-full justify-center py-3 text-center text-base font-bold tracking-wide"
              disabled={loading}
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
