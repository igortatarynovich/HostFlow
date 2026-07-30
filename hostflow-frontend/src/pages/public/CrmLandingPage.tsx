import { useMemo } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

type PlanCard = {
  /** Billing `plan_code` for self-service signup; `enterprise` is contact-only. */
  key: 'starter' | 'team' | 'pro' | 'enterprise'
  price: string
  seats: string
  features: string[]
  bestFor: string
  ctaHref: string
  ctaIsExternal?: boolean
}

const PLAN_NAME_DEFAULT: Record<PlanCard['key'], string> = {
  starter: 'Solo',
  team: 'Team',
  pro: 'Business',
  enterprise: 'Enterprise',
}

function ProductShotPlaceholder({ caption, badge }: { caption: string; badge: string }) {
  return (
    <div
      className="relative aspect-[16/10] w-full overflow-hidden rounded-2xl border border-slate-200/80 bg-gradient-to-br from-slate-100 via-white to-brand-50 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]"
      role="img"
      aria-label={caption}
    >
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage: `linear-gradient(rgba(15,23,42,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(15,23,42,0.06) 1px, transparent 1px)`,
          backgroundSize: '24px 24px',
        }}
      />
      <div className="relative flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <span className="rounded-full border border-slate-200 bg-white/95 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-slate-500 shadow-sm">
          {badge}
        </span>
        <p className="max-w-sm text-sm font-medium leading-relaxed text-slate-600">{caption}</p>
      </div>
    </div>
  )
}

/** `imageSrc` from i18n (e.g. `/landing/hero.webp`); empty → gradient placeholder. */
function ProductShot({ caption, badge, imageSrc }: { caption: string; badge: string; imageSrc: string }) {
  const src = (imageSrc || '').trim()
  if (src.startsWith('http://') || src.startsWith('https://') || src.startsWith('/') || src.startsWith('.')) {
    return (
      <figure className="space-y-2">
        <div className="relative aspect-[16/10] w-full overflow-hidden rounded-2xl border border-slate-200/80 bg-slate-100 shadow-sm">
          <img
            src={src}
            alt={caption}
            className="h-full w-full object-cover object-top"
            loading="lazy"
            decoding="async"
          />
        </div>
        <figcaption className="flex flex-wrap items-center gap-2 text-xs leading-snug text-slate-500">
          <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 font-semibold uppercase tracking-wide text-slate-500">
            {badge}
          </span>
          <span>{caption}</span>
        </figcaption>
      </figure>
    )
  }
  return <ProductShotPlaceholder caption={caption} badge={badge} />
}

export default function CrmLandingPage() {
  const { t } = useI18n()
  const location = useLocation()
  const { trackCta } = useSeoTracking({
    pageType: 'landing',
    pageKey: location.pathname === '/pricing' ? 'pricing' : 'landing',
  })

  const isPricingRoute = location.pathname === '/pricing'
  const canonicalPath = isPricingRoute ? '/pricing' : '/'
  const seoTitle = isPricingRoute
    ? t('app.seo.pricing.title', { defaultValue: 'Pricing for Recruitment CRM' })
    : t('app.seo.landing.title', { defaultValue: 'HostFlow — recruitment operations in one system' })
  const seoDescription = isPricingRoute
    ? t('app.seo.pricing.description', {
        defaultValue: 'Compare HostFlow plans and start your recruitment CRM trial in minutes.',
      })
    : t('app.seo.landing.description', {
        defaultValue:
          'Control hiring from first lead to hire: pipeline, ownership, documents — without losing candidates to spreadsheet chaos.',
      })

  const painItems = useMemo(
    () => [0, 1, 2, 3, 4, 5].map((i) => t(`public.crm_landing.pain.items.${i}`)),
    [t],
  )
  const roiHidden = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.roi.hidden_items.${i}`)), [t])
  const solutionSee = useMemo(() => [0, 1, 2].map((i) => t(`public.crm_landing.solution.see_items.${i}`)), [t])
  const howSteps = useMemo(
    () =>
      [0, 1, 2, 3, 4].map((i) => ({
        title: t(`public.crm_landing.how.steps.${i}.title`),
        caption: t(`public.crm_landing.how.steps.${i}.caption`),
        imageSrc: t(`public.crm_landing.how.steps.${i}.screenshot_src`, { defaultValue: '' }),
      })),
    [t],
  )
  const heroAnswers = useMemo(
    () =>
      (['what', 'who', 'get', 'why'] as const).map((key) => ({
        key,
        label: t(`public.crm_landing.hero.answers.${key}.label`),
        body: t(`public.crm_landing.hero.answers.${key}.body`),
      })),
    [t],
  )
  const pricingClarity = useMemo(
    () => ({
      includes: [0, 1, 2, 3].map((i) => t(`public.crm_landing.pricing.clarity.includes.${i}`)),
      excludes: [0, 1, 2].map((i) => t(`public.crm_landing.pricing.clarity.excludes.${i}`)),
      limits: [0, 1, 2].map((i) => t(`public.crm_landing.pricing.clarity.limits.${i}`)),
      afterTrial: t('public.crm_landing.pricing.clarity.after_trial'),
    }),
    [t],
  )

  const heroShotSrc = t('public.crm_landing.hero.screenshot_src', { defaultValue: '' })
  const benefitItems = useMemo(() => [0, 1, 2, 3, 4, 5].map((i) => t(`public.crm_landing.benefits.items.${i}`)), [t])
  const beforeItems = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.before_after.before_items.${i}`)), [t])
  const afterItems = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.before_after.after_items.${i}`)), [t])
  const segmentItems = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.segments.items.${i}`)), [t])
  const convictionSteps = useMemo(() => [0, 1, 2].map((i) => t(`public.crm_landing.conviction.steps.${i}`)), [t])

  const faq = useMemo(
    () => [
      {
        q: t('public.crm_landing.faq.launch_q'),
        a: t('public.crm_landing.faq.launch_a'),
      },
      {
        q: t('public.crm_landing.faq.training_q'),
        a: t('public.crm_landing.faq.training_a'),
      },
      {
        q: t('public.crm_landing.faq.processes_q'),
        a: t('public.crm_landing.faq.processes_a'),
      },
    ],
    [t],
  )

  const structuredData = useMemo(
    () => [
      {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'HostFlow',
        url: 'https://hostflow.cc',
        logo: 'https://hostflow.cc/logo_hf.svg',
      },
      {
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        name: 'HostFlow CRM',
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        offers: [
          {
            '@type': 'Offer',
            name: 'Solo',
            price: '29',
            priceCurrency: 'EUR',
            description: 'Per month when billed monthly; yearly billing from €24/mo equivalent (see pricing)',
          },
          {
            '@type': 'Offer',
            name: 'Team',
            price: '129',
            priceCurrency: 'EUR',
            description: 'Per month when billed monthly; yearly billing from €109/mo equivalent',
          },
          {
            '@type': 'Offer',
            name: 'Business',
            price: '249',
            priceCurrency: 'EUR',
            description: 'Per month when billed monthly; yearly billing from €219/mo equivalent',
          },
          {
            '@type': 'Offer',
            name: 'Enterprise',
            price: '499',
            priceCurrency: 'EUR',
            description: 'From €499/mo or custom; contact sales',
          },
        ],
        url: `https://hostflow.cc${canonicalPath}`,
        description: seoDescription,
      },
      {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: faq.map((item) => ({
          '@type': 'Question',
          name: item.q,
          acceptedAnswer: {
            '@type': 'Answer',
            text: item.a,
          },
        })),
      },
    ],
    [canonicalPath, faq, seoDescription],
  )

  useSeoMeta({
    title: seoTitle,
    description: seoDescription,
    canonicalPath,
    structuredData,
  })

  const shotBadge = t('public.crm_landing.shot.placeholder_badge', { defaultValue: 'Product screenshot' })

  const plans: PlanCard[] = [
    {
      key: 'starter',
      price: t('public.crm_landing.pricing.starter.price', {
        defaultValue: '€29/mo · €24/mo billed yearly',
      }),
      seats: t('public.crm_landing.pricing.starter.seats', { defaultValue: '1 user · 1 workspace' }),
      features: [
        t('public.crm_landing.pricing.starter.features.0'),
        t('public.crm_landing.pricing.starter.features.1'),
        t('public.crm_landing.pricing.starter.features.2'),
      ],
      bestFor: t('public.crm_landing.pricing.starter.best_for'),
      ctaHref: '/signup?plan=starter',
    },
    {
      key: 'team',
      price: t('public.crm_landing.pricing.team.price', {
        defaultValue: '€129/mo · €109/mo billed yearly',
      }),
      seats: t('public.crm_landing.pricing.team.seats', { defaultValue: 'Up to 3 users · 1 workspace' }),
      features: [
        t('public.crm_landing.pricing.team.features.0'),
        t('public.crm_landing.pricing.team.features.1'),
        t('public.crm_landing.pricing.team.features.2'),
      ],
      bestFor: t('public.crm_landing.pricing.team.best_for'),
      ctaHref: '/signup?plan=team',
    },
    {
      key: 'pro',
      price: t('public.crm_landing.pricing.pro.price', {
        defaultValue: '€249/mo · €219/mo billed yearly',
      }),
      seats: t('public.crm_landing.pricing.pro.seats', { defaultValue: 'Up to 10 users · up to 3 workspaces' }),
      features: [
        t('public.crm_landing.pricing.pro.features.0'),
        t('public.crm_landing.pricing.pro.features.1'),
        t('public.crm_landing.pricing.pro.features.2'),
      ],
      bestFor: t('public.crm_landing.pricing.pro.best_for'),
      ctaHref: '/signup?plan=pro',
    },
    {
      key: 'enterprise',
      price: t('public.crm_landing.pricing.enterprise.price', {
        defaultValue: 'From €499/mo or custom',
      }),
      seats: t('public.crm_landing.pricing.enterprise.seats', {
        defaultValue: 'Custom seats, workspaces, storage, and SLAs',
      }),
      features: [
        t('public.crm_landing.pricing.enterprise.features.0'),
        t('public.crm_landing.pricing.enterprise.features.1'),
        t('public.crm_landing.pricing.enterprise.features.2'),
      ],
      bestFor: t('public.crm_landing.pricing.enterprise.best_for'),
      ctaHref:
        'mailto:info@hostflow.cc?subject=' + encodeURIComponent('HostFlow Enterprise'),
      ctaIsExternal: true,
    },
  ]

  const comparisonRows = useMemo(
    () => [
      {
        key: 'users',
        label: t('public.crm_landing.compare.rows.users.label', { defaultValue: 'Users (included)' }),
        starter: t('public.crm_landing.compare.rows.users.starter', { defaultValue: '1' }),
        team: t('public.crm_landing.compare.rows.users.team', { defaultValue: 'Up to 3' }),
        pro: t('public.crm_landing.compare.rows.users.pro', { defaultValue: 'Up to 10' }),
        enterprise: t('public.crm_landing.compare.rows.users.enterprise', { defaultValue: 'Custom' }),
      },
      {
        key: 'workspaces',
        label: t('public.crm_landing.compare.rows.workspaces.label', { defaultValue: 'Workspaces / companies' }),
        starter: t('public.crm_landing.compare.rows.workspaces.starter', { defaultValue: '1' }),
        team: t('public.crm_landing.compare.rows.workspaces.team', { defaultValue: '1 (add-ons available)' }),
        pro: t('public.crm_landing.compare.rows.workspaces.pro', { defaultValue: 'Up to 3 included' }),
        enterprise: t('public.crm_landing.compare.rows.workspaces.enterprise', { defaultValue: 'Custom' }),
      },
      {
        key: 'automation',
        label: t('public.crm_landing.compare.rows.automation.label', { defaultValue: 'Automation & distribution' }),
        starter: t('public.crm_landing.compare.rows.automation.starter', { defaultValue: 'Assisted only' }),
        team: t('public.crm_landing.compare.rows.automation.team', { defaultValue: 'Rules, auto-distribution' }),
        pro: t('public.crm_landing.compare.rows.automation.pro', { defaultValue: 'Extended rules & workflows' }),
        enterprise: t('public.crm_landing.compare.rows.automation.enterprise', { defaultValue: 'Custom' }),
      },
      {
        key: 'portals',
        label: t('public.crm_landing.compare.rows.portals.label', { defaultValue: 'Candidate & client portals' }),
        starter: t('public.crm_landing.compare.rows.portals.starter', { defaultValue: 'Not included' }),
        team: t('public.crm_landing.compare.rows.portals.team', { defaultValue: 'Included (plan limits)' }),
        pro: t('public.crm_landing.compare.rows.portals.pro', { defaultValue: 'Extended limits + branded basics' }),
        enterprise: t('public.crm_landing.compare.rows.portals.enterprise', { defaultValue: 'Custom' }),
      },
      {
        key: 'finance',
        label: t('public.crm_landing.compare.rows.finance.label', { defaultValue: 'Services, orders & invoicing' }),
        starter: t('public.crm_landing.compare.rows.finance.starter', { defaultValue: 'Not included' }),
        team: t('public.crm_landing.compare.rows.finance.team', { defaultValue: 'Not included' }),
        pro: t('public.crm_landing.compare.rows.finance.pro', { defaultValue: 'Included' }),
        enterprise: t('public.crm_landing.compare.rows.finance.enterprise', { defaultValue: 'Custom' }),
      },
      {
        key: 'analytics',
        label: t('public.crm_landing.compare.rows.analytics.label', { defaultValue: 'Analytics' }),
        starter: t('public.crm_landing.compare.rows.analytics.starter', { defaultValue: 'Basic funnel' }),
        team: t('public.crm_landing.compare.rows.analytics.team', { defaultValue: 'Funnel, sources, team' }),
        pro: t('public.crm_landing.compare.rows.analytics.pro', { defaultValue: 'Advanced slices & reporting' }),
        enterprise: t('public.crm_landing.compare.rows.analytics.enterprise', { defaultValue: 'Custom' }),
      },
    ],
    [t],
  )

  const sectionTitle = (k: string) => (
    <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{t(`public.crm_landing.${k}.badge`)}</p>
  )

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-16 md:space-y-20">
        {/* HERO */}
        <section className="card cv-auto overflow-hidden p-6 sm:p-8 lg:p-10">
          <div className="grid gap-10 lg:grid-cols-[1.05fr_1fr] lg:items-center">
            <div className="space-y-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                {t('public.crm_landing.hero.badge')}
              </p>
              <h1 className="text-balance text-3xl font-semibold leading-tight text-slate-900 sm:text-4xl lg:text-[2.65rem] lg:leading-[1.12]">
                {t('public.crm_landing.hero.title')}
              </h1>
              <p className="text-pretty text-base leading-relaxed text-slate-600 lg:text-lg">
                {t('public.crm_landing.hero.subtitle')}
              </p>
              <dl className="grid gap-3 sm:grid-cols-2">
                {heroAnswers.map((item) => (
                  <div
                    key={item.key}
                    className="rounded-xl border border-slate-200/90 bg-slate-50/80 px-3.5 py-3"
                  >
                    <dt className="text-[11px] font-bold uppercase tracking-wide text-brand-700">{item.label}</dt>
                    <dd className="mt-1 text-sm font-medium leading-snug text-slate-800">{item.body}</dd>
                  </div>
                ))}
              </dl>
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                <Link
                  to="/signup"
                  onClick={() => trackCta('hero_primary_signup', '/signup')}
                  className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-brand-500/30 transition hover:bg-brand-700"
                >
                  {t('public.crm_landing.hero.primary_cta')}
                </Link>
                <Link
                  to="/login"
                  onClick={() => trackCta('hero_secondary_login', '/login')}
                  className="inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-semibold text-slate-600 underline-offset-4 hover:text-slate-900 hover:underline"
                >
                  {t('public.crm_landing.hero.secondary_cta')}
                </Link>
              </div>
              <p className="text-sm font-medium text-slate-500">{t('public.crm_landing.hero.cta_subline')}</p>
            </div>
            <div className="space-y-3">
              <ProductShot
                badge={shotBadge}
                caption={t('public.crm_landing.hero.screenshot_caption')}
                imageSrc={heroShotSrc}
              />
            </div>
          </div>
        </section>

        {/* PAIN */}
        <section className="cv-auto space-y-6">
          {sectionTitle('pain')}
          <h2 className="text-balance text-2xl font-semibold text-slate-900 sm:text-3xl">{t('public.crm_landing.pain.title')}</h2>
          <div className="space-y-3 text-base leading-relaxed text-slate-600">
            {t('public.crm_landing.pain.lead')
              .split('\n')
              .map((line) => (
                <p key={line}>{line}</p>
              ))}
          </div>
          <ul className="grid gap-3 sm:grid-cols-2">
            {painItems.map((item) => (
              <li
                key={item}
                className="rounded-2xl border border-rose-100 bg-rose-50/50 px-4 py-3 text-sm font-medium text-slate-800"
              >
                — {item}
              </li>
            ))}
          </ul>
          <p className="text-base font-semibold text-slate-900">{t('public.crm_landing.pain.closing')}</p>
        </section>

        {/* ROI */}
        <section className="cv-auto overflow-hidden rounded-xl border border-amber-200/80 bg-gradient-to-br from-amber-50/90 via-white to-orange-50/50 p-6 shadow-sm sm:p-8">
          {sectionTitle('roi')}
          <h2 className="mt-2 text-balance text-2xl font-semibold text-slate-900 sm:text-3xl">{t('public.crm_landing.roi.title')}</h2>
          <div className="mt-4 space-y-4 text-base leading-relaxed text-slate-700">
            <p>{t('public.crm_landing.roi.intro')}</p>
            {t('public.crm_landing.roi.loss_setup').trim() ? (
              <p className="text-lg font-semibold text-slate-900">{t('public.crm_landing.roi.loss_setup')}</p>
            ) : null}
            <p className="text-2xl font-bold tracking-tight text-amber-900 sm:text-3xl">{t('public.crm_landing.roi.loss_range')}</p>
            <p className="text-sm text-slate-600">{t('public.crm_landing.roi.loss_note')}</p>
            <div>
              <p className="font-semibold text-slate-900">{t('public.crm_landing.roi.hidden_title')}</p>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                {roiHidden.map((line) => (
                  <li key={line}>— {line}</li>
                ))}
              </ul>
            </div>
            <p className="rounded-xl border border-amber-200/80 bg-white/90 px-4 py-3 text-base font-semibold text-brand-800">
              {t('public.crm_landing.roi.highlight')}
            </p>
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{t('public.crm_landing.roi.pilot_badge')}</p>
              <p className="mt-2 text-sm text-slate-600">{t('public.crm_landing.roi.pilot_note')}</p>
              <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium text-slate-500">{t('public.crm_landing.roi.pilot_m1_label')}</dt>
                  <dd className="mt-1 text-lg font-semibold text-slate-900">{t('public.crm_landing.roi.pilot_m1_value')}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-slate-500">{t('public.crm_landing.roi.pilot_m2_label')}</dt>
                  <dd className="mt-1 text-lg font-semibold text-slate-900">{t('public.crm_landing.roi.pilot_m2_value')}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs font-medium text-slate-500">{t('public.crm_landing.roi.pilot_m3_label')}</dt>
                  <dd className="mt-1 text-lg font-semibold text-slate-900">{t('public.crm_landing.roi.pilot_m3_value')}</dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        {/* SOLUTION */}
        <section className="card cv-auto space-y-5 p-6 sm:p-8">
          {sectionTitle('solution')}
          <h2 className="text-2xl font-semibold text-slate-900 sm:text-3xl">{t('public.crm_landing.solution.title')}</h2>
          <p className="max-w-3xl text-base leading-relaxed text-slate-600">{t('public.crm_landing.solution.body')}</p>
          <div>
            <p className="font-semibold text-slate-900">{t('public.crm_landing.solution.see_title')}</p>
            <ul className="mt-2 space-y-2 text-sm text-slate-700">
              {solutionSee.map((line) => (
                <li key={line}>— {line}</li>
              ))}
            </ul>
            <p className="mt-3 text-sm font-medium text-slate-800">{t('public.crm_landing.solution.footer')}</p>
          </div>
        </section>

        {/* HOW */}
        <section id="how-it-works" className="cv-auto space-y-8 scroll-mt-8">
          {sectionTitle('how')}
          <h2 className="text-2xl font-semibold text-slate-900 sm:text-3xl">{t('public.crm_landing.how.title')}</h2>
          <p className="max-w-2xl text-base text-slate-600">{t('public.crm_landing.how.lead')}</p>
          <ol className="grid gap-6 md:grid-cols-2 xl:grid-cols-5 xl:gap-4">
            {howSteps.map((step, idx) => (
              <li key={step.title} className="relative space-y-3">
                {idx < howSteps.length - 1 ? (
                  <span
                    className="pointer-events-none absolute -right-3 top-5 hidden text-brand-400 xl:block"
                    aria-hidden
                  >
                    →
                  </span>
                ) : null}
                <p className="text-xs font-bold uppercase tracking-widest text-brand-600">
                  {t('public.crm_landing.how.step_label', { values: { n: idx + 1 } })}
                </p>
                <h3 className="text-base font-semibold text-slate-900 xl:text-sm xl:leading-snug">{step.title}</h3>
                <p className="text-sm text-slate-600">{step.caption}</p>
                <ProductShot badge={shotBadge} caption={step.caption} imageSrc={step.imageSrc} />
              </li>
            ))}
          </ol>
        </section>

        {/* BENEFITS */}
        <section className="cv-auto space-y-5">
          {sectionTitle('benefits')}
          <h2 className="text-2xl font-semibold text-slate-900 sm:text-3xl">{t('public.crm_landing.benefits.title')}</h2>
          <ul className="grid gap-2 sm:grid-cols-2">
            {benefitItems.map((item) => (
              <li key={item} className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-800 shadow-sm">
                — {item}
              </li>
            ))}
          </ul>
          <p className="text-base font-semibold text-slate-900">{t('public.crm_landing.benefits.closing')}</p>
        </section>

        {/* BEFORE / AFTER */}
        <section className="cv-auto grid gap-6 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-6">
            {sectionTitle('before_after')}
            <h2 className="mt-2 text-xl font-semibold text-slate-900 sm:text-2xl">{t('public.crm_landing.before_after.title')}</h2>
            <p className="mt-4 text-sm font-bold uppercase tracking-wide text-slate-500">{t('public.crm_landing.before_after.before_title')}</p>
            <ul className="mt-2 space-y-2 text-sm text-slate-700">
              {beforeItems.map((item) => (
                <li key={item}>— {item}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">{t('public.crm_landing.before_after.after_badge')}</p>
            <p className="mt-2 text-sm font-bold uppercase tracking-wide text-emerald-800">{t('public.crm_landing.before_after.after_title')}</p>
            <ul className="mt-2 space-y-2 text-sm text-slate-800">
              {afterItems.map((item) => (
                <li key={item}>— {item}</li>
              ))}
            </ul>
          </div>
        </section>

        {/* SEGMENTS */}
        <section className="cv-auto rounded-xl border border-brand-100 bg-brand-50/40 p-6 sm:p-8">
          {sectionTitle('segments')}
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">{t('public.crm_landing.segments.title')}</h2>
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {segmentItems.map((item) => (
              <li key={item} className="text-sm font-medium text-slate-800">
                — {item}
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-slate-600">{t('public.crm_landing.segments.footnote')}</p>
        </section>

        {/* PRICING */}
        <section id="pricing" className="cv-auto space-y-5 scroll-mt-8">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              {sectionTitle('pricing')}
              <h2 className="mt-2 text-2xl font-semibold text-slate-900">{t('public.crm_landing.pricing.title')}</h2>
            </div>
            <p className="max-w-md text-sm text-slate-600">{t('public.crm_landing.pricing.note')}</p>
          </div>
          <div className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                {t('public.crm_landing.pricing.clarity.includes_title')}
              </p>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                {pricingClarity.includes.map((line) => (
                  <li key={line}>• {line}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                {t('public.crm_landing.pricing.clarity.excludes_title')}
              </p>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                {pricingClarity.excludes.map((line) => (
                  <li key={line}>• {line}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                {t('public.crm_landing.pricing.clarity.limits_title')}
              </p>
              <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                {pricingClarity.limits.map((line) => (
                  <li key={line}>• {line}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                {t('public.crm_landing.pricing.clarity.after_trial_title')}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">{pricingClarity.afterTrial}</p>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {plans.map((plan) => {
              const featured = plan.key === 'team'
              return (
                <article
                  key={plan.key}
                  className={`relative flex flex-col rounded-2xl border bg-white p-5 shadow-sm ${
                    featured
                      ? 'border-brand-400 ring-2 ring-brand-500/30 ring-offset-2 ring-offset-[#f6fbff] xl:scale-[1.02]'
                      : 'border-slate-200'
                  }`}
                >
                  {featured ? (
                    <span className="absolute -top-3 left-4 rounded-full bg-brand-600 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                      {t('public.crm_landing.pricing.featured_badge')}
                    </span>
                  ) : null}
                  <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                    {t(`public.crm_landing.pricing.${plan.key}.name`, { defaultValue: PLAN_NAME_DEFAULT[plan.key] })}
                  </p>
                  <p className="mt-3 text-2xl font-semibold leading-snug text-slate-900 lg:text-[1.65rem]">{plan.price}</p>
                  <p className="mt-1 text-sm text-slate-600">{plan.seats}</p>
                  <p className="mt-2 rounded-lg bg-slate-50 px-2 py-1 text-xs text-slate-700">{plan.bestFor}</p>
                  <ul className="mt-4 flex-1 space-y-2 text-sm text-slate-700">
                    {plan.features.map((feature) => (
                      <li key={feature}>• {feature}</li>
                    ))}
                  </ul>
                  {plan.ctaIsExternal ? (
                    <a
                      href={plan.ctaHref}
                      onClick={() => trackCta(`pricing_select_${plan.key}`, plan.ctaHref)}
                      className="mt-5 inline-flex w-full items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-slate-50"
                    >
                      {t('public.crm_landing.pricing.contact_sales_cta')}
                    </a>
                  ) : (
                    <Link
                      to={plan.ctaHref}
                      onClick={() => trackCta(`pricing_select_${plan.key}`, plan.ctaHref)}
                      className={`mt-5 inline-flex w-full items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition ${
                        featured ? 'bg-brand-600 hover:bg-brand-700' : 'bg-slate-900 hover:bg-slate-800'
                      }`}
                    >
                      {t('public.crm_landing.pricing.select_cta')}
                    </Link>
                  )}
                </article>
              )
            })}
          </div>
        </section>

        {/* COMPARISON TABLE */}
        <section className="cv-auto space-y-4">
          <h2 className="text-2xl font-semibold text-slate-900">{t('public.crm_landing.compare.title')}</h2>
          <div className="space-y-3 md:hidden">
            {comparisonRows.map((row) => (
              <article key={row.key} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-900">{row.label}</h3>
                <dl className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-700">
                  {(['starter', 'team', 'pro', 'enterprise'] as const).map((col) => (
                    <div key={col} className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                      <dt className="font-medium text-slate-600">
                        {t(`public.crm_landing.pricing.${col}.name`, { defaultValue: PLAN_NAME_DEFAULT[col] })}
                      </dt>
                      <dd className="text-right">{row[col]}</dd>
                    </div>
                  ))}
                </dl>
              </article>
            ))}
          </div>
          <div className="hidden overflow-x-auto rounded-2xl border border-slate-200 bg-white md:block">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-700">
                <tr>
                  <th className="px-4 py-3 text-left">{t('public.crm_landing.compare.feature')}</th>
                  {(['starter', 'team', 'pro', 'enterprise'] as const).map((col) => (
                    <th key={col} className="px-4 py-3 text-left">
                      {t(`public.crm_landing.pricing.${col}.name`, { defaultValue: PLAN_NAME_DEFAULT[col] })}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row) => (
                  <tr key={row.key} className="border-t border-slate-100 text-slate-700">
                    <td className="px-4 py-3 font-medium text-slate-900">{row.label}</td>
                    <td className="px-4 py-3">{row.starter}</td>
                    <td className="px-4 py-3">{row.team}</td>
                    <td className="px-4 py-3">{row.pro}</td>
                    <td className="px-4 py-3">{row.enterprise}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* CONVICTION */}
        <section className="card cv-auto p-6 sm:p-8">
          {sectionTitle('conviction')}
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">{t('public.crm_landing.conviction.title')}</h2>
          <p className="mt-3 max-w-3xl text-base leading-relaxed text-slate-600">{t('public.crm_landing.conviction.body')}</p>
          <p className="mt-4 text-sm font-semibold text-slate-900">{t('public.crm_landing.conviction.list_intro')}</p>
          <ul className="mt-2 space-y-2 text-sm text-slate-700">
            {convictionSteps.map((line) => (
              <li key={line}>— {line}</li>
            ))}
          </ul>
          <p className="mt-4 text-sm font-medium text-slate-800">{t('public.crm_landing.conviction.closing')}</p>
        </section>

        {/* FAQ */}
        <section className="cv-auto rounded-xl border border-brand-200 bg-brand-50/60 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.crm_landing.faq.title')}</h2>
          <div className="mt-4 space-y-3">
            {faq.map((item) => (
              <article key={item.q} className="rounded-xl border border-brand-100 bg-white px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-900">{item.q}</h3>
                <p className="mt-1 text-sm text-slate-700">{item.a}</p>
              </article>
            ))}
          </div>
        </section>

        {/* GUIDES */}
        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.crm_landing.guides.title')}</h2>
          <p className="mt-2 text-sm text-slate-600">{t('public.crm_landing.guides.subtitle')}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to="/faq" className="btn-secondary btn-sm" onClick={() => trackCta('guide_faq', '/faq')}>
              {t('public.marketing.common.related.faq', { defaultValue: 'FAQ' })}
            </Link>
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm" onClick={() => trackCta('guide_pipeline', '/features/candidate-pipeline')}>
              {t('public.marketing.common.related.candidate_pipeline', { defaultValue: 'Candidate pipeline' })}
            </Link>
            <Link to="/features/document-control" className="btn-secondary btn-sm" onClick={() => trackCta('guide_document_control', '/features/document-control')}>
              {t('public.marketing.common.related.document_control', { defaultValue: 'Document control' })}
            </Link>
            <Link to="/use-cases/trucking-recruitment" className="btn-secondary btn-sm" onClick={() => trackCta('guide_trucking', '/use-cases/trucking-recruitment')}>
              {t('public.marketing.common.related.trucking_recruitment_use_case', { defaultValue: 'Trucking recruitment use-case' })}
            </Link>
            <Link to="/use-cases/high-volume-onboarding" className="btn-secondary btn-sm" onClick={() => trackCta('guide_high_volume', '/use-cases/high-volume-onboarding')}>
              {t('public.marketing.common.related.high_volume_onboarding', { defaultValue: 'High-volume onboarding' })}
            </Link>
            <Link to="/comparison/hostflow-vs-spreadsheets" className="btn-secondary btn-sm" onClick={() => trackCta('guide_vs_spreadsheets', '/comparison/hostflow-vs-spreadsheets')}>
              {t('public.marketing.common.related.hostflow_vs_spreadsheets', { defaultValue: 'HostFlow vs spreadsheets' })}
            </Link>
            <Link to="/comparison/recruitment-crm-vs-ats" className="btn-secondary btn-sm" onClick={() => trackCta('guide_crm_vs_ats', '/comparison/recruitment-crm-vs-ats')}>
              {t('public.marketing.common.related.crm_vs_ats', { defaultValue: 'Recruitment CRM vs ATS' })}
            </Link>
            <Link to="/use-cases/recruitment-agencies" className="btn-secondary btn-sm" onClick={() => trackCta('guide_recruitment_agencies', '/use-cases/recruitment-agencies')}>
              {t('public.marketing.common.related.recruitment_agencies', { defaultValue: 'Recruitment agencies' })}
            </Link>
            <Link to="/use-cases/transport-companies" className="btn-secondary btn-sm" onClick={() => trackCta('guide_transport_companies', '/use-cases/transport-companies')}>
              {t('public.marketing.common.related.transport_companies', { defaultValue: 'Transport companies' })}
            </Link>
            <Link to="/features/meta-ads-recruitment" className="btn-secondary btn-sm" onClick={() => trackCta('guide_meta_ads', '/features/meta-ads-recruitment')}>
              {t('public.marketing.common.related.meta_ads_recruitment', { defaultValue: 'Meta ads recruitment' })}
            </Link>
            <Link to="/features/whatsapp-recruitment" className="btn-secondary btn-sm" onClick={() => trackCta('guide_whatsapp', '/features/whatsapp-recruitment')}>
              {t('public.marketing.common.related.whatsapp_recruitment', { defaultValue: 'WhatsApp recruitment' })}
            </Link>
            <Link to="/use-cases/ats-for-drivers" className="btn-secondary btn-sm" onClick={() => trackCta('guide_ats_drivers', '/use-cases/ats-for-drivers')}>
              {t('public.marketing.common.related.ats_for_drivers', { defaultValue: 'ATS for drivers' })}
            </Link>
          </div>
        </section>

        {/* FINAL CTA */}
        <section className="card cv-auto p-8 text-center">
          <h2 className="text-balance text-2xl font-semibold text-slate-900 sm:text-3xl">{t('public.crm_landing.final_cta.title')}</h2>
          <p className="mt-3 text-sm text-slate-600 sm:text-base">{t('public.crm_landing.final_cta.subtitle')}</p>
          <div className="mt-6 flex justify-center">
            <Link
              to="/signup?plan=team"
              onClick={() => trackCta('final_cta_signup_team', '/signup?plan=team')}
              className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-brand-500/30 transition hover:bg-brand-700"
            >
              {t('public.crm_landing.final_cta.button')}
            </Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
