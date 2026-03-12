import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../store/useAuth'
import { useI18n } from '../i18n'
import { PublicBrandingLogo } from '../components/public/PublicLogo'
import { PublicCookieBanner } from '../components/public/PublicCookieBanner'
import { PublicLegalFooter } from '../components/public/PublicLegalFooter'
import ErrorRecoveryBanner from '../components/ErrorRecoveryBanner'
import { LOGIN_NOTICE_STORAGE_KEY } from '../store/auth'
import { useSeoMeta } from '../hooks/useSeoMeta'

export default function Login(){
  const { login } = useAuth()
  const nav = useNavigate()
  const [searchParams] = useSearchParams()
  const { t } = useI18n()
  useSeoMeta({
    title: t('app.seo.login.title', { defaultValue: 'Sign In to HostFlow' }),
    description: t('app.seo.login.description', {
      defaultValue: 'Sign in to HostFlow CRM to manage candidates, documents, and team operations.',
    }),
    canonicalPath: '/login',
  })
  const [email, setEmail] = useState(() => (searchParams.get('email') || '').trim())
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const valuePropKeys = ['pipeline', 'documents', 'support'] as const
  const valueProps = valuePropKeys.map((key) => ({
    key,
    title: t(`app.login.value_props.items.${key}.title`),
    body: t(`app.login.value_props.items.${key}.body`),
  }))

  async function onSubmit(e: FormEvent){
    e.preventDefault()
    setError(null)
    setLoading(true)
    try{
      await login(email, password)
      nav('/', { replace: true })
    }catch(err:any){
      if(err?.response?.status === 401){
        setError(t('app.login.errors.invalid'))
      }else{
        setError(err?.response?.data?.detail || t('app.login.errors.generic'))
      }
    }finally{
      setLoading(false)
    }
  }

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const notice = window.sessionStorage.getItem(LOGIN_NOTICE_STORAGE_KEY)
      if (notice === 'expired') {
        setError(t('app.login.errors.expired'))
      } else if (notice === 'invite_accepted') {
        setNotice(t('app.login.notices.invite_accepted', { defaultValue: 'Invitation accepted. Sign in to continue.' }))
      }
      if (notice) {
        window.sessionStorage.removeItem(LOGIN_NOTICE_STORAGE_KEY)
      }
    } catch {
      /* ignore */
    }
  }, [t])

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f6fbff] px-4 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(94,186,205,0.35),transparent_55%),radial-gradient(circle_at_85%_0%,rgba(25,78,122,0.2),transparent_65%),linear-gradient(180deg,rgba(255,255,255,0.92)_0%,#f6fbff_50%,#f8fbff_100%)]" />
      <div className="relative mx-auto flex w-full max-w-6xl flex-col gap-12">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-3xl border border-white/20 bg-brand-900/95 p-8 text-white shadow-2xl">
            <PublicBrandingLogo showWordmark />
            <div className="mt-8 space-y-5">
              <h1 className="text-3xl font-semibold">{t('app.login.hero.title', { defaultValue: 'Добро пожаловать' })}</h1>
              <p className="text-white/80">
                {t('app.login.hero.subtitle', { defaultValue: 'Управляйте кандидатами и документами из единого рабочего места.' })}
              </p>
              <ul className="space-y-2 text-sm text-white/80">
                <li>• {t('app.login.hero.points.pipeline', { defaultValue: 'Пайплайн кандидатów и задачи' })}</li>
                <li>• {t('app.login.hero.points.documents', { defaultValue: 'Контроль документов и статусов' })}</li>
                <li>• {t('app.login.hero.points.analytics', { defaultValue: 'Аналитика по вакансиям и источникам' })}</li>
              </ul>
            </div>
          </div>
          <form
            onSubmit={onSubmit}
            className="card w-full space-y-4 rounded-3xl border border-white/70 bg-white/95 p-8 shadow-card backdrop-blur-lg"
          >
            <h2 className="text-2xl font-semibold text-center text-slate-900">{t('app.login.title')}</h2>
            {notice && (
              <div className="alert-success text-sm">
                {notice}
              </div>
            )}
            {error && (
              <ErrorRecoveryBanner
                info={{ title: error, hint: t('app.common.retry_hint', { defaultValue: 'Retry the action or refresh the page.' }) }}
                compact
              />
            )}
            <div>
              <label className="label">{t('app.login.fields.email')}</label>
              <input
                className="input"
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="label">{t('app.login.fields.password')}</label>
              <input
                className="input"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <button className="btn-primary w-full py-3 text-base" disabled={loading}>
              {loading ? t('app.login.actions.submitting') : t('app.login.actions.submit')}
            </button>
            <Link
              to="/forgot-password"
              className="block text-center text-sm text-brand-600 hover:underline mt-2"
            >
              {t('app.login.forgot_password', { defaultValue: 'Zapomniałeś hasła?' })}
            </Link>
            <Link
              to="/signup"
              className="block text-center text-sm text-brand-700 hover:underline mt-1"
            >
              {t('app.login.create_account', { defaultValue: 'Create account' })}
            </Link>
          </form>
        </div>

        <section className="rounded-3xl border border-white/60 bg-white/90 p-6 shadow-card">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <h3 className="text-xl font-semibold text-slate-900">{t('app.login.value_props.title')}</h3>
            <p className="text-sm text-slate-600">{t('app.login.value_props.subtitle')}</p>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {valueProps.map((item, idx) => (
              <div key={item.key} className="rounded-2xl border border-slate-100 bg-white/95 p-5 shadow-sm">
                <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-base font-semibold text-brand-700">
                  {idx + 1}
                </div>
                <div className="text-base font-semibold text-slate-900">{item.title}</div>
                <p className="mt-2 text-sm text-slate-600">{item.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="overflow-hidden rounded-[32px] border border-brand-100 bg-white/95 shadow-card backdrop-blur">
          <div className="grid gap-8 p-6 lg:grid-cols-[1.15fr_0.85fr] lg:p-10">
            <div className="space-y-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                {t('app.login.signup_first.badge', { defaultValue: 'New to HostFlow CRM?' })}
              </p>
              <h1 className="text-3xl font-semibold text-slate-900 lg:text-4xl">
                {t('app.login.signup_first.title', { defaultValue: 'Start with signup, not settings' })}
              </h1>
              <p className="text-base text-slate-600">
                {t('app.login.signup_first.subtitle', { defaultValue: 'Create account, create company, and reach first value in minutes.' })}
              </p>
              <div className="flex flex-wrap gap-3 text-sm text-brand-800">
                <span className="rounded-md bg-brand-50 px-4 py-2">
                  {t('app.login.signup_first.bullets.0', { defaultValue: 'Choose plan and create workspace' })}
                </span>
                <span className="rounded-md bg-brand-50 px-4 py-2">
                  {t('app.login.signup_first.bullets.1', { defaultValue: 'Add first client and lead' })}
                </span>
                <span className="rounded-md bg-brand-50 px-4 py-2">
                  {t('app.login.signup_first.bullets.2', { defaultValue: 'Run daily operations immediately' })}
                </span>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  to="/signup"
                  className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-6 py-3 text-base font-semibold text-white shadow-lg shadow-brand-500/40 transition hover:bg-brand-700"
                >
                  {t('app.login.signup_first.primary_cta', { defaultValue: 'Create account' })}
                </Link>
                <Link
                  to="/pricing"
                  className="inline-flex items-center px-4 py-3 text-sm font-semibold text-brand-700 underline-offset-4 hover:text-brand-900 hover:underline"
                >
                  {t('app.login.signup_first.secondary_cta', { defaultValue: 'View plans' })}
                </Link>
              </div>
            </div>
            <div className="relative overflow-hidden rounded-3xl bg-slate-900 text-white shadow-lg">
              <img
                src="/assets/image_truck.png"
                alt={t('app.login.signup_first.image_alt', { defaultValue: 'CRM onboarding workflow preview' })}
                className="absolute inset-0 h-full w-full object-cover"
                loading="lazy"
              />
              <div className="relative flex h-full flex-col justify-end bg-gradient-to-t from-slate-900/90 via-slate-900/25 to-transparent p-6">
                <p className="text-xs uppercase tracking-wide text-brand-100">
                  {t('app.login.signup_first.card_title', { defaultValue: 'Signup-first journey' })}
                </p>
                <p className="mt-2 text-lg font-semibold">
                  {t('app.login.signup_first.card_caption', { defaultValue: 'Landing -> Signup -> Company -> First Value' })}
                </p>
              </div>
            </div>
          </div>
        </section>

        <PublicLegalFooter className="pb-4" />
      </div>
      <PublicCookieBanner />
    </div>
  )
}
