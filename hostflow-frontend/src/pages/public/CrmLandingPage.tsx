import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { PublicCookieBanner } from '../../components/public/PublicCookieBanner'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { PublicLocaleSwitcher } from '../../components/public/PublicLocaleSwitcher'
import { PublicLogo } from '../../components/public/PublicLogo'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

type PlanKey = 'starter' | 'team' | 'pro' | 'enterprise'

const PLAN_NAME_DEFAULT: Record<PlanKey, string> = {
  starter: 'Starter',
  team: 'Growth',
  pro: 'Business',
  enterprise: 'Enterprise',
}

const TEAL = '#00C2A8'
const NAVY = '#0B0E14'
const NAVY_SOFT = '#12151C'

function ProductShot({
  caption,
  imageSrc,
  size = 'feature',
}: {
  caption: string
  imageSrc: string
  size?: 'hero' | 'feature'
}) {
  const src = (imageSrc || '').trim()
  const frame =
    size === 'hero'
      ? 'min-h-[300px] sm:min-h-[440px] lg:min-h-[520px]'
      : 'min-h-[260px] sm:min-h-[340px] lg:min-h-[400px]'

  if (!(src.startsWith('http://') || src.startsWith('https://') || src.startsWith('/') || src.startsWith('.'))) {
    return (
      <div
        className={`flex ${frame} items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-slate-800 to-[#0B0E14] p-6 text-center text-sm text-slate-300`}
        role="img"
        aria-label={caption}
      >
        {caption}
      </div>
    )
  }

  return (
    <figure className="overflow-hidden rounded-2xl border border-white/10 bg-[#0F131A] shadow-[0_40px_100px_-40px_rgba(0,0,0,0.85)] ring-1 ring-white/5">
      <div className={`relative bg-slate-100 ${frame}`}>
        <img
          src={src}
          alt={caption}
          className="absolute inset-0 h-full w-full object-contain object-top p-1.5 sm:p-2"
          loading={size === 'hero' ? 'eager' : 'lazy'}
          decoding="async"
        />
      </div>
      {caption ? (
        <figcaption className="border-t border-white/10 px-4 py-2.5 text-sm text-slate-400">{caption}</figcaption>
      ) : null}
    </figure>
  )
}

export default function CrmLandingPage() {
  const { t } = useI18n()
  const location = useLocation()
  const { trackCta } = useSeoTracking({
    pageType: 'landing',
    pageKey: location.pathname === '/pricing' ? 'pricing' : 'landing',
  })
  const [billing, setBilling] = useState<'monthly' | 'yearly'>('monthly')
  const [openFaq, setOpenFaq] = useState<number | null>(0)

  const isPricingRoute = location.pathname === '/pricing'
  const canonicalPath = isPricingRoute ? '/pricing' : '/'
  const seoTitle = isPricingRoute
    ? t('app.seo.pricing.title', { defaultValue: 'Pricing — HostFlow' })
    : t('app.seo.landing.title', {
        defaultValue: 'Close vacancies faster — HostFlow',
      })
  const seoDescription = isPricingRoute
    ? t('app.seo.pricing.description', {
        defaultValue: 'Simple plans for teams that need to close vacancies faster.',
      })
    : t('app.seo.landing.description', {
        defaultValue:
          'Built by recruiters with 10+ years in international hiring. Close vacancies faster with one process from Meta and WhatsApp to hire.',
      })

  const proofChips = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.hero.proof.${i}`)), [t])
  const problemItems = useMemo(
    () =>
      [0, 1, 2, 3, 4].map((i) => ({
        icon: t(`public.crm_landing.problem.items.${i}.icon`),
        title: t(`public.crm_landing.problem.items.${i}.title`),
      })),
    [t],
  )
  const authorityPoints = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.authority.points.${i}`)), [t])
  const flowSteps = useMemo(() => [0, 1, 2, 3, 4, 5, 6, 7].map((i) => t(`public.crm_landing.flow.steps.${i}`)), [t])
  const todayItems = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.outcome.today.${i}`)), [t])
  const monthItems = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.outcome.month.${i}`)), [t])
  const productBlocks = useMemo(
    () =>
      [0, 1, 2, 3].map((i) => ({
        title: t(`public.crm_landing.product.blocks.${i}.title`),
        body: t(`public.crm_landing.product.blocks.${i}.body`),
        caption: t(`public.crm_landing.product.blocks.${i}.caption`),
        imageSrc: t(`public.crm_landing.product.blocks.${i}.screenshot_src`, { defaultValue: '' }),
      })),
    [t],
  )
  const caseBefore = useMemo(() => [0, 1, 2].map((i) => t(`public.crm_landing.case.before.${i}`)), [t])
  const caseAfter = useMemo(() => [0, 1, 2].map((i) => t(`public.crm_landing.case.after.${i}`)), [t])
  const segmentItems = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.segments.items.${i}`)), [t])
  const includedAll = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.pricing.included.${i}`)), [t])

  const faq = useMemo(
    () =>
      ['crm_vs_ats', 'meta', 'whatsapp', 'data', 'rodo', 'recruiters', 'launch', 'plan_change'].map((key) => ({
        q: t(`public.crm_landing.faq.${key}_q`),
        a: t(`public.crm_landing.faq.${key}_a`),
      })),
    [t],
  )

  const plans = useMemo(
    () =>
      (
        [
          {
            key: 'starter' as const,
            featured: false,
            ctaHref: '/signup?plan=starter',
          },
          {
            key: 'team' as const,
            featured: true,
            ctaHref: '/signup?plan=team',
          },
          {
            key: 'pro' as const,
            featured: false,
            ctaHref: '/signup?plan=pro',
          },
          {
            key: 'enterprise' as const,
            featured: false,
            ctaHref: 'mailto:info@hostflow.cc?subject=' + encodeURIComponent('HostFlow Enterprise'),
            external: true,
          },
        ] as const
      ).map((plan) => ({
        ...plan,
        name: t(`public.crm_landing.pricing.${plan.key}.name`, { defaultValue: PLAN_NAME_DEFAULT[plan.key] }),
        priceMonthly: t(`public.crm_landing.pricing.${plan.key}.price_monthly`),
        priceYearly: t(`public.crm_landing.pricing.${plan.key}.price_yearly`),
        audience: t(`public.crm_landing.pricing.${plan.key}.audience`),
        seats: t(`public.crm_landing.pricing.${plan.key}.seats`),
        line: t(`public.crm_landing.pricing.${plan.key}.line`),
      })),
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
        name: 'HostFlow',
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        url: `https://hostflow.cc${canonicalPath}`,
        description: seoDescription,
      },
      {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: faq.map((item) => ({
          '@type': 'Question',
          name: item.q,
          acceptedAnswer: { '@type': 'Answer', text: item.a },
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

  const heroShot = t('public.crm_landing.hero.screenshot_src', {
    defaultValue: '/landing/shots/hero-pipeline.jpg',
  })

  const navLinks = [
    { href: '#problem', label: t('public.crm_landing.nav.problem') },
    { href: '#authority', label: t('public.crm_landing.nav.authority') },
    { href: '#product', label: t('public.crm_landing.nav.product') },
    { href: '#pricing', label: t('public.crm_landing.nav.pricing') },
    { href: '#faq', label: t('public.crm_landing.nav.faq') },
  ]

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#F7F8FA] text-slate-900 antialiased">
      {/* NAV */}
      <header className="sticky top-0 z-40 border-b border-white/8 bg-[#0B0E14]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <a href="/" className="shrink-0" aria-label="HostFlow">
            <PublicLogo showWordmark white size={34} />
          </a>
          <nav className="hidden items-center gap-7 text-[13px] font-medium text-slate-400 lg:flex" aria-label="Primary">
            {navLinks.map((link) => (
              <a key={link.href} href={link.href} className="transition hover:text-white">
                {link.label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <div className="hidden sm:block">
              <PublicLocaleSwitcher className="text-slate-400" />
            </div>
            <Link
              to="/login"
              onClick={() => trackCta('nav_login', '/login')}
              className="hidden text-[13px] font-semibold text-slate-300 transition hover:text-white sm:inline"
            >
              {t('public.crm_landing.nav.login')}
            </Link>
            <Link
              to="/demo"
              onClick={() => trackCta('nav_demo', '/demo')}
              className="inline-flex items-center justify-center rounded-lg bg-[#00C2A8] px-3.5 py-2 text-[13px] font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
            >
              {t('public.crm_landing.nav.demo')}
            </Link>
          </div>
        </div>
      </header>

      {/* SCREEN 1 — We solve the problem */}
      <section
        className="relative overflow-hidden"
        style={{ background: `radial-gradient(ellipse 80% 60% at 70% 20%, rgba(0,194,168,0.12), transparent 55%), linear-gradient(180deg, ${NAVY} 0%, ${NAVY_SOFT} 100%)` }}
      >
        <div className="mx-auto grid max-w-6xl gap-12 px-4 pb-10 pt-14 sm:px-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:items-center lg:gap-10 lg:pb-12 lg:pt-20">
          <div className="space-y-6">
            <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]">
              {t('public.crm_landing.hero.title')}
              <span className="mt-2 block text-[#00C2A8]">{t('public.crm_landing.hero.title_accent')}</span>
            </h1>
            <div className="max-w-xl space-y-3 text-base leading-relaxed text-slate-300 sm:text-[17px]">
              <p>{t('public.crm_landing.hero.lead')}</p>
              <p className="font-medium text-white/90">{t('public.crm_landing.hero.system_line')}</p>
            </div>
            <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:items-center">
              <Link
                to="/demo"
                onClick={() => trackCta('hero_demo', '/demo')}
                className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-7 py-3.5 text-base font-semibold text-[#04201C] shadow-[0_12px_40px_-12px_rgba(0,194,168,0.7)] transition hover:bg-[#1ad4bb]"
              >
                {t('public.crm_landing.hero.primary_cta')}
              </Link>
              <a
                href="#flow"
                onClick={() => trackCta('hero_flow', '#flow')}
                className="inline-flex items-center justify-center gap-2 px-2 py-3 text-sm font-semibold text-slate-300 transition hover:text-white"
              >
                <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/20 text-[10px]" aria-hidden>
                  ▶
                </span>
                {t('public.crm_landing.hero.secondary_cta')}
              </a>
            </div>
            <ul className="flex flex-wrap gap-x-4 gap-y-2 pt-2 text-sm text-slate-300">
              {proofChips.map((chip) => (
                <li key={chip} className="inline-flex items-center gap-1.5">
                  <span className="text-[#00C2A8]" aria-hidden>
                    ✓
                  </span>
                  {chip}
                </li>
              ))}
            </ul>
          </div>
          <div className="relative lg:-mr-4">
            <div
              className="pointer-events-none absolute -inset-6 rounded-[2rem] opacity-70 blur-3xl"
              style={{ background: 'radial-gradient(circle at 50% 40%, rgba(0,194,168,0.22), transparent 65%)' }}
              aria-hidden
            />
            <div className="relative origin-center lg:rotate-[-1.5deg] lg:scale-[1.02]">
              <ProductShot
                size="hero"
                caption={t('public.crm_landing.hero.screenshot_caption')}
                imageSrc={heroShot}
              />
            </div>
          </div>
        </div>
      </section>

      {/* SCREEN 2 — Why vacancies don’t close */}
      <section id="problem" className="scroll-mt-24 bg-white">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1.15fr_0.85fr] lg:gap-12 lg:py-24">
          <div className="space-y-8">
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                {t('public.crm_landing.problem.badge')}
              </p>
              <h2 className="max-w-xl text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
                {t('public.crm_landing.problem.title')}
              </h2>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {problemItems.map((item) => (
                <li
                  key={item.title}
                  className="flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-[#F7F8FA] px-4 py-4"
                >
                  <span className="text-xl leading-none" aria-hidden>
                    {item.icon}
                  </span>
                  <span className="text-sm font-medium leading-snug text-slate-800">{item.title}</span>
                </li>
              ))}
            </ul>
          </div>
          <aside className="flex flex-col justify-between rounded-3xl border border-rose-200/70 bg-gradient-to-br from-rose-50 to-orange-50 p-7 sm:p-8">
            <div className="space-y-4">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-rose-500">
                {t('public.crm_landing.problem.cost_badge')}
              </p>
              <h3 className="text-2xl font-semibold tracking-tight text-slate-900">
                {t('public.crm_landing.problem.cost_title')}
              </h3>
              <p className="text-4xl font-bold tracking-tight text-rose-600 sm:text-5xl">
                {t('public.crm_landing.problem.cost_value')}
              </p>
              <p className="text-sm leading-relaxed text-slate-600">{t('public.crm_landing.problem.cost_note')}</p>
            </div>
            <p className="mt-8 text-sm font-semibold text-slate-800">{t('public.crm_landing.problem.cost_closing')}</p>
          </aside>
        </div>
      </section>

      {/* SCREEN 3 — Why we can do this (authority) */}
      <section
        id="authority"
        className="scroll-mt-24"
        style={{ background: `linear-gradient(180deg, ${NAVY} 0%, #10141C 100%)` }}
      >
        <div className="mx-auto max-w-3xl space-y-8 px-4 py-20 text-center sm:px-6 lg:py-28">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#00C2A8]">
            {t('public.crm_landing.authority.badge')}
          </p>
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-5xl sm:leading-[1.1]">
            {t('public.crm_landing.authority.title')}
          </h2>
          <p className="mx-auto max-w-2xl text-lg leading-relaxed text-slate-300">
            {t('public.crm_landing.authority.body')}
          </p>
          <ul className="mx-auto grid max-w-2xl gap-3 text-left sm:grid-cols-1">
            {authorityPoints.map((point) => (
              <li
                key={point}
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 text-sm leading-relaxed text-slate-200"
              >
                {point}
              </li>
            ))}
          </ul>
          <p className="mx-auto max-w-2xl text-base font-medium leading-relaxed text-[#B8FFF3]">
            {t('public.crm_landing.authority.closing')}
          </p>
        </div>
      </section>

      {/* SCREEN 4 — How it works */}
      <section id="flow" className="scroll-mt-24 bg-[#F7F8FA]">
        <div className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-2xl space-y-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t('public.crm_landing.flow.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.flow.title')}
            </h2>
          </div>
          <ol className="flex flex-col items-center gap-2 md:flex-row md:flex-wrap md:justify-center md:gap-x-2 md:gap-y-3">
            {flowSteps.map((step, idx) => (
              <li key={step} className="flex flex-col items-center gap-2 md:flex-row md:gap-2">
                <div
                  className={`min-w-[8.5rem] rounded-2xl border px-4 py-3 text-center text-sm font-semibold shadow-sm ${
                    step === 'HostFlow'
                      ? 'border-[#00C2A8]/40 bg-[#0B0E14] text-white'
                      : 'border-slate-200 bg-white text-slate-900'
                  }`}
                >
                  {step}
                </div>
                {idx < flowSteps.length - 1 ? (
                  <>
                    <span className="text-[#00C2A8] md:hidden" aria-hidden>
                      ↓
                    </span>
                    <span className="hidden text-[#00C2A8] md:inline" aria-hidden>
                      →
                    </span>
                  </>
                ) : null}
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* SCREEN 5 — What the client gets */}
      <section className="bg-white">
        <div className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-2xl space-y-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t('public.crm_landing.outcome.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.outcome.title')}
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-slate-200 bg-[#F7F8FA] p-6 sm:p-8">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">
                {t('public.crm_landing.outcome.today_title')}
              </p>
              <ul className="mt-5 space-y-3">
                {todayItems.map((item) => (
                  <li key={item} className="flex gap-3 text-sm text-slate-600">
                    <span className="text-rose-500" aria-hidden>
                      ✕
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-3xl border border-[#00C2A8]/30 bg-[#0B0E14] p-6 text-white sm:p-8">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#00C2A8]">
                {t('public.crm_landing.outcome.month_title')}
              </p>
              <ul className="mt-5 space-y-3">
                {monthItems.map((item) => (
                  <li key={item} className="flex gap-3 text-sm text-slate-200">
                    <span className="text-[#00C2A8]" aria-hidden>
                      ✓
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* SCREEN 6 — Product */}
      <section id="product" className="scroll-mt-24 bg-[#F7F8FA]">
        <div className="mx-auto max-w-6xl space-y-16 px-4 py-16 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-2xl space-y-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t('public.crm_landing.product.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.product.title')}
            </h2>
            <p className="text-base text-slate-500">{t('public.crm_landing.product.lead')}</p>
          </div>
          <div className="space-y-20">
            {productBlocks.map((block, idx) => (
              <article
                key={block.title}
                className={`grid items-center gap-8 lg:grid-cols-2 lg:gap-12 ${
                  idx % 2 === 1 ? 'lg:[&>*:first-child]:order-2' : ''
                }`}
              >
                <div className="space-y-3">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#2E6F74]">
                    {String(idx + 1).padStart(2, '0')}
                  </p>
                  <h3 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{block.title}</h3>
                  <p className="max-w-md text-base leading-relaxed text-slate-600">{block.body}</p>
                </div>
                <ProductShot caption={block.caption} imageSrc={block.imageSrc} />
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* SCREEN 7 — Case */}
      <section
        id="case"
        className="scroll-mt-24"
        style={{ background: `linear-gradient(135deg, ${NAVY} 0%, #151A24 55%, #0E2A2A 100%)` }}
      >
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-24">
          <div className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/[0.03]">
            <div className="grid lg:grid-cols-[0.9fr_1.1fr]">
              <div
                className="relative min-h-[240px] bg-cover bg-center lg:min-h-full"
                style={{
                  backgroundImage:
                    'linear-gradient(90deg, rgba(11,14,20,0.15), rgba(11,14,20,0.75)), url(/landing/shots/step-vacancy.jpg)',
                }}
                role="img"
                aria-label={t('public.crm_landing.case.image_alt')}
              />
              <div className="space-y-6 p-7 sm:p-10">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">
                  {t('public.crm_landing.case.badge')}
                </p>
                <h2 className="text-3xl font-semibold tracking-tight text-white">{t('public.crm_landing.case.title')}</h2>
                <p className="text-base leading-relaxed text-slate-300">{t('public.crm_landing.case.body')}</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                      {t('public.crm_landing.case.before_title')}
                    </p>
                    <ul className="mt-3 space-y-2 text-sm text-slate-300">
                      {caseBefore.map((item) => (
                        <li key={item}>— {item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-[#00C2A8]">
                      {t('public.crm_landing.case.after_title')}
                    </p>
                    <ul className="mt-3 space-y-2 text-sm text-slate-200">
                      {caseAfter.map((item) => (
                        <li key={item}>— {item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                <p className="text-sm font-medium text-[#B8FFF3]">{t('public.crm_landing.case.result')}</p>
                <Link
                  to="/use-cases/transport-companies"
                  onClick={() => trackCta('case_read', '/use-cases/transport-companies')}
                  className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-5 py-2.5 text-sm font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
                >
                  {t('public.crm_landing.case.cta')}
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SCREEN 8 — For whom */}
      <section className="bg-white">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-16 sm:px-6 lg:py-20">
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            {t('public.crm_landing.segments.title')}
          </h2>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {segmentItems.map((item, idx) => (
              <li
                key={item}
                className={`rounded-2xl border px-5 py-6 text-sm font-semibold ${
                  idx === 0
                    ? 'border-[#00C2A8]/35 bg-[#0B0E14] text-white'
                    : 'border-slate-200 bg-[#F7F8FA] text-slate-800'
                }`}
              >
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* SCREEN 9 — Pricing */}
      <section id="pricing" className="scroll-mt-24 bg-[#F7F8FA]">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-16 sm:px-6 lg:py-24">
          <div className="flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                {t('public.crm_landing.pricing.badge')}
              </p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
                {t('public.crm_landing.pricing.title')}
              </h2>
            </div>
            <div className="inline-flex items-center rounded-full border border-slate-200 bg-white p-1 text-sm font-semibold shadow-sm">
              <button
                type="button"
                onClick={() => setBilling('monthly')}
                className={`rounded-full px-4 py-2 transition ${
                  billing === 'monthly' ? 'bg-[#0B0E14] text-white' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {t('public.crm_landing.pricing.billing_monthly')}
              </button>
              <button
                type="button"
                onClick={() => setBilling('yearly')}
                className={`rounded-full px-4 py-2 transition ${
                  billing === 'yearly' ? 'bg-[#0B0E14] text-white' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                {t('public.crm_landing.pricing.billing_yearly')}
              </button>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {plans.map((plan) => {
                const price = billing === 'yearly' ? plan.priceYearly : plan.priceMonthly
                return (
                  <article
                    key={plan.key}
                    className={`flex flex-col rounded-3xl border bg-white p-5 ${
                      plan.featured ? 'border-[#00C2A8] shadow-[0_0_0_1px_rgba(0,194,168,0.25)]' : 'border-slate-200'
                    }`}
                  >
                    {plan.featured ? (
                      <span className="mb-3 w-fit rounded-full bg-[#00C2A8]/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#0F766E]">
                        {t('public.crm_landing.pricing.featured_badge')}
                      </span>
                    ) : (
                      <span className="mb-3 block h-[18px]" aria-hidden />
                    )}
                    <p className="text-sm font-semibold text-slate-500">{plan.name}</p>
                    <p className="mt-3 text-3xl font-bold tracking-tight text-slate-900">{price}</p>
                    <p className="mt-3 text-sm font-medium text-slate-800">{plan.audience}</p>
                    <p className="mt-1 text-xs text-slate-500">{plan.seats}</p>
                    <p className="mt-4 flex-1 text-sm leading-relaxed text-slate-600">{plan.line}</p>
                    {'external' in plan && plan.external ? (
                      <a
                        href={plan.ctaHref}
                        onClick={() => trackCta(`pricing_${plan.key}`, plan.ctaHref)}
                        className="mt-6 inline-flex w-full items-center justify-center rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-slate-50"
                      >
                        {t('public.crm_landing.pricing.contact_sales_cta')}
                      </a>
                    ) : (
                      <Link
                        to={plan.ctaHref}
                        onClick={() => trackCta(`pricing_${plan.key}`, plan.ctaHref)}
                        className={`mt-6 inline-flex w-full items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
                          plan.featured
                            ? 'bg-[#00C2A8] text-[#04201C] hover:bg-[#1ad4bb]'
                            : 'bg-[#0B0E14] text-white hover:bg-black'
                        }`}
                      >
                        {t('public.crm_landing.pricing.select_cta')}
                      </Link>
                    )}
                  </article>
                )
              })}
            </div>
            <aside className="rounded-3xl border border-slate-200 bg-white p-6 lg:w-64">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">
                {t('public.crm_landing.pricing.included_title')}
              </p>
              <ul className="mt-4 space-y-3 text-sm text-slate-700">
                {includedAll.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-[#00C2A8]" aria-hidden>
                      ✓
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </aside>
          </div>
        </div>
      </section>

      {/* SCREEN 10 — FAQ */}
      <section id="faq" className="scroll-mt-24 bg-white">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-16 sm:px-6 lg:py-24">
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            {t('public.crm_landing.faq.title')}
          </h2>
          <div className="grid gap-3 lg:grid-cols-2">
            {faq.map((item, idx) => {
              const open = openFaq === idx
              return (
                <article key={item.q} className="rounded-2xl border border-slate-200 bg-[#F7F8FA]">
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                    aria-expanded={open}
                    onClick={() => setOpenFaq(open ? null : idx)}
                  >
                    <span className="text-sm font-semibold text-slate-900">{item.q}</span>
                    <span className="text-slate-400" aria-hidden>
                      {open ? '−' : '+'}
                    </span>
                  </button>
                  {open ? <p className="border-t border-slate-200 px-5 py-4 text-sm leading-relaxed text-slate-600">{item.a}</p> : null}
                </article>
              )
            })}
          </div>
        </div>
      </section>

      {/* SCREEN 11 — Final CTA */}
      <section
        className="px-4 py-20 sm:px-6"
        style={{ background: `radial-gradient(ellipse 70% 80% at 50% 0%, rgba(0,194,168,0.16), transparent 55%), ${NAVY}` }}
      >
        <div className="mx-auto max-w-3xl space-y-6 text-center">
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-5xl sm:leading-[1.1]">
            {t('public.crm_landing.final_cta.title')}
          </h2>
          <p className="text-base text-slate-300 sm:text-lg">{t('public.crm_landing.final_cta.subtitle')}</p>
          <div className="flex flex-col items-center justify-center gap-3 pt-2 sm:flex-row">
            <Link
              to="/demo"
              onClick={() => trackCta('final_demo', '/demo')}
              className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-8 py-3.5 text-base font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
            >
              {t('public.crm_landing.final_cta.button')}
            </Link>
            <Link
              to="/signup?plan=team"
              onClick={() => trackCta('final_signup', '/signup?plan=team')}
              className="inline-flex items-center justify-center rounded-xl border border-white/15 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/5"
            >
              {t('public.crm_landing.final_cta.secondary')}
            </Link>
          </div>
        </div>
      </section>

      <div className="bg-[#F7F8FA] px-4 pb-10 sm:px-6">
        <div className="mx-auto max-w-6xl">
          <PublicLegalFooter />
        </div>
      </div>
      <PublicCookieBanner />
    </div>
  )
}
