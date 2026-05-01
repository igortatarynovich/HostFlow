import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { redeemMagicLink } from '../../api/publicIntake'
import { PUBLIC_EMAIL_STORAGE_KEY, PUBLIC_TOKEN_STORAGE_KEY } from './constants'
import { useToast } from '../../components/Toast'
import { useI18n } from '../../i18n'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { useSeoMeta } from '../../hooks/useSeoMeta'

export default function PublicPortalLanding() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { notify } = useToast()
  const { t } = useI18n()
  useSeoMeta({
    title: t('app.seo.public_portal.title', { defaultValue: 'Candidate Portal' }),
    description: t('app.seo.public_portal.description', {
      defaultValue: 'Access your candidate portal, continue onboarding, and track required steps and documents.',
    }),
    canonicalPath: '/public/portal',
  })

  const [tokenInput, setTokenInput] = useState('')
  const [lastEmail, setLastEmail] = useState<string | undefined>()
  const [error, setError] = useState<string | null>(null)
  const [magicRedeemError, setMagicRedeemError] = useState<string | null>(null)
  const [verifyingMagic, setVerifyingMagic] = useState(false)

  useEffect(() => {
    try {
      const cachedToken = window.localStorage.getItem(PUBLIC_TOKEN_STORAGE_KEY)
      if (cachedToken) setTokenInput(cachedToken)
    } catch {
      /* ignore */
    }
    try {
      const cachedEmail = window.localStorage.getItem(PUBLIC_EMAIL_STORAGE_KEY)
      if (cachedEmail) setLastEmail(cachedEmail)
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    const magicToken = searchParams.get('magic')
    if (!magicToken) return
    setVerifyingMagic(true)
    setMagicRedeemError(null)
    const redeem = async () => {
      try {
        const data = await redeemMagicLink(magicToken)
        try {
          window.localStorage.setItem(PUBLIC_TOKEN_STORAGE_KEY, data.token)
        } catch {
          /* ignore */
        }
        navigate(`/public/apply/${data.token}`, { replace: true })
      } catch (err: any) {
        const detail = err?.response?.data?.detail || t('public.portal.errors.redeem_failed')
        setMagicRedeemError(detail)
        notify({ title: t('public.portal.errors.redeem_action'), description: detail, variant: 'error' })
      } finally {
        setVerifyingMagic(false)
      }
    }
    redeem()
  }, [navigate, notify, searchParams, t])

  const handleResume = (e: React.FormEvent) => {
    e.preventDefault()
    const normalized = tokenInput.trim()
    if (!normalized) {
      setError(t('public.portal.errors.access_code_required'))
      return
    }
    setError(null)
    navigate(`/public/apply/${normalized}`)
  }

  const steps = t('public.portal.landing.steps.items').split('\n').filter(Boolean)
  const audience = t('public.portal.landing.audience.items').split('\n').filter(Boolean)
  const whyItems = t('public.portal.landing.why.items').split('\n').filter(Boolean)
  const docsList = t('public.portal.landing.docs.items').split('\n').filter(Boolean)
  return (
    <PublicPageShell maxWidth="5xl" headerExtra={<PublicLocaleSwitcher />}>
      <div className="space-y-16">
        <section className="card overflow-hidden backdrop-blur">
          <div className="grid gap-8 p-6 lg:grid-cols-[1.15fr_0.85fr] lg:p-10">
            <div className="space-y-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{t('public.portal.hero.title')}</p>
              <h1 className="text-3xl font-semibold text-slate-900 lg:text-4xl">{t('public.portal.hero.subtitle')}</h1>
              <p className="text-base text-slate-600">{t('public.portal.hero.note')}</p>
              <div className="flex flex-wrap gap-3 text-sm text-brand-800">
                <span className="rounded-md bg-brand-50 px-4 py-2">{t('public.portal.hero.bullets.presign')}</span>
                <span className="rounded-md bg-brand-50 px-4 py-2">{t('public.portal.hero.bullets.hints')}</span>
                <span className="rounded-md bg-brand-50 px-4 py-2">{t('public.portal.hero.bullets.return')}</span>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  to="/public/intake"
                  className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-6 py-3 text-base font-semibold text-white shadow-lg shadow-brand-500/40 transition hover:bg-brand-700"
                >
                  {t('public.portal.hero.cta')}
                </Link>
                <Link
                  to="#apply"
                  className="inline-flex items-center px-4 py-3 text-sm font-semibold text-brand-700 underline-offset-4 hover:text-brand-900 hover:underline"
                >
                  {t('public.portal.hero.secondary')}
                </Link>
              </div>
              <p className="text-sm text-slate-600">
                {t('public.portal.hero.client_inquiry_prefix')}{' '}
                <Link
                  to="/public/intake?application_kind=client"
                  className="font-semibold text-brand-700 underline-offset-4 hover:text-brand-900 hover:underline"
                >
                  {t('public.portal.hero.client_inquiry_link_label')}
                </Link>{' '}
                {t('public.portal.hero.client_inquiry_suffix')}
              </p>
              {magicRedeemError && (
                <ErrorRecoveryBanner
                  info={{ title: magicRedeemError, hint: t('app.common.retry_hint') }}
                  compact
                />
              )}
              {verifyingMagic && (
                <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">
                  {t('public.portal.loaders.verifying')}
                </div>
              )}
            </div>
            <div className="relative overflow-hidden rounded-xl bg-slate-900 text-white shadow-lg">
              <img
                src="/assets/image_truck.png"
                alt={t('public.portal.hero.image_alt')}
                className="absolute inset-0 h-full w-full object-cover"
                loading="eager"
                fetchPriority="high"
                decoding="async"
              />
              <div className="relative flex h-full flex-col justify-end bg-gradient-to-t from-slate-900/90 via-slate-900/25 to-transparent p-6">
                <p className="text-xs uppercase tracking-wide text-brand-100">{t('public.portal.hero.card_title')}</p>
                <p className="mt-2 text-lg font-semibold">{t('public.portal.hero.card_caption')}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="card cv-auto grid gap-6 bg-white/90 p-6 lg:grid-cols-2">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">{t('public.portal.landing.steps.title')}</h2>
            <ol className="mt-4 space-y-3 text-slate-700">
              {steps.map((item, idx) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">{idx + 1}</span>
                  <span>{item}</span>
                </li>
              ))}
            </ol>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-900">{t('public.portal.landing.audience.title')}</h2>
            <ul className="mt-4 space-y-2 text-slate-700">
              {audience.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-1 h-2 w-2 rounded-full bg-brand-600" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="card cv-auto grid gap-6 bg-white/90 p-6 lg:grid-cols-2">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">{t('public.portal.landing.why.title')}</h2>
            <ul className="mt-4 space-y-2 text-slate-700">
              {whyItems.map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-1 h-2 w-2 rounded-full bg-brand-600" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-slate-900">{t('public.portal.landing.docs.title')}</h2>
            <ul className="mt-4 grid grid-cols-1 gap-3 text-slate-700 sm:grid-cols-2">
              {docsList.map((item) => (
                <li
                  key={item}
                  className="flex h-16 items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 text-center text-sm font-medium text-slate-700"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="apply" className="cv-auto grid gap-6 lg:grid-cols-2">
          <div className="relative overflow-hidden rounded-xl border-2 border-brand-200 bg-gradient-to-br from-brand-50 via-white to-brand-100 p-6 shadow-lg">
            <div className="absolute inset-0 pointer-events-none opacity-30" aria-hidden>
              <div className="absolute -left-10 top-6 h-32 w-32 rounded-full bg-white mix-blend-overlay" />
            </div>
            <div className="relative flex h-full flex-col space-y-2">
              <div className="inline-flex items-center gap-2 rounded-full bg-brand-600/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-900">
                <span>{t('public.portal.cards.new.badge')}</span>
                <span className="text-brand-500">• {t('public.portal.cards.new.highlight')}</span>
              </div>
              <h2 className="text-2xl font-semibold text-slate-900">{t('public.portal.cards.new.title')}</h2>
              <p className="text-sm text-slate-700">{t('public.portal.cards.new.body')}</p>
              <p className="text-sm font-semibold text-brand-900">{t('public.portal.cards.new.focus')}</p>
              <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-slate-600">
                <li>{t('public.portal.cards.new.bullets.autosave')}</li>
                <li>{t('public.portal.cards.new.bullets.checklist')}</li>
                <li>{t('public.portal.cards.new.bullets.reminders')}</li>
              </ul>
              <Link
                to="/public/intake"
                className="mt-auto inline-flex items-center justify-center rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-brand-500/40 transition hover:bg-brand-700"
              >
                {t('public.portal.cards.new.cta')}
              </Link>
            </div>
          </div>

          <div className="card p-6">
            <p className="text-xs uppercase tracking-wide text-emerald-600">{t('public.portal.cards.resume.badge')}</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-900">{t('public.portal.cards.resume.title')}</h2>
            <p className="mt-2 text-sm text-slate-600">
              {t('public.portal.cards.resume.body_prefix')}{' '}
              <code>/public/apply/</code>. {t('public.portal.cards.resume.body_suffix')}
            </p>
            <form className="mt-4 flex h-full flex-col space-y-4" onSubmit={handleResume}>
              <div>
                <label className="text-xs uppercase text-slate-500">{t('public.portal.form.access_code')}</label>
                <input
                  type="text"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 font-mono text-sm tracking-wide text-slate-900 focus:border-brand-400 focus:outline-none focus:ring"
                  placeholder={t('public.portal.cards.resume.placeholder')}
                  autoComplete="off"
                />
              </div>
              {lastEmail && (
                <p className="text-xs text-slate-500">
                  {t('public.portal.cards.resume.last_email')}: <span className="font-medium text-slate-800">{lastEmail}</span>
                </p>
              )}
              {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>}
              <button
                type="submit"
                className="mt-auto w-full rounded-xl border border-brand-200 bg-brand-700 px-4 py-3 text-sm font-semibold text-white shadow-inner shadow-brand-500/30 transition hover:bg-brand-800"
              >
                {t('public.portal.cards.resume.cta')}
              </button>
            </form>
          </div>
        </section>

        <PublicLegalFooter className="mt-16" />
      </div>
    </PublicPageShell>
  )
}
