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
  starter: 'Solo',
  team: 'Team',
  pro: 'Business',
  enterprise: 'Enterprise',
}

const NAVY = '#0B0E14'

function ProductShot({
  caption,
  imageSrc,
  size = 'support',
  focus = 'center',
}: {
  caption: string
  imageSrc: string
  size?: 'hero' | 'support' | 'compact' | 'wide' | 'fragment'
  focus?: 'center' | 'top' | 'left' | 'right'
}) {
  const src = (imageSrc || '').trim()
  if (!(src.startsWith('http://') || src.startsWith('https://') || src.startsWith('/') || src.startsWith('.'))) {
    return (
      <div
        className="flex min-h-[200px] items-center justify-center rounded-2xl border border-white/10 bg-slate-800 p-6 text-center text-sm text-slate-300"
        role="img"
        aria-label={caption}
      >
        {caption}
      </div>
    )
  }

  const isHero = size === 'hero'
  const isFragment = size === 'fragment'
  const imgH = isHero ? 958 : 709
  const imgW = isHero ? 1920 : 1568

  const maxW =
    size === 'hero'
      ? 'max-w-full'
      : size === 'wide'
        ? 'max-w-[1080px]'
        : size === 'compact'
          ? 'max-w-[420px]'
          : size === 'fragment'
            ? 'max-w-[480px]'
            : 'max-w-[560px]'

  const frameH = size === 'fragment' ? 'h-[220px] sm:h-[260px]' : 'h-auto'

  const objectPos =
    focus === 'top' ? 'object-top' : focus === 'left' ? 'object-left' : focus === 'right' ? 'object-right' : 'object-center'

  return (
    <figure
      className={`w-full overflow-hidden ${maxW} ${
        isHero
          ? 'rounded-t-2xl rounded-b-none border border-b-0 border-slate-300/50 bg-[#0F131A]'
          : isFragment
            ? 'rounded-2xl border border-slate-200/90 bg-white'
            : 'rounded-2xl border border-white/10 bg-[#0F131A] ring-1 ring-white/5'
      }`}
    >
      <div className={`relative overflow-hidden ${isFragment ? 'bg-slate-100' : 'bg-slate-200'} ${frameH}`}>
        <img
          src={src}
          alt={caption}
          width={imgW}
          height={imgH}
          className={
            isFragment
              ? `absolute inset-0 h-[150%] w-[150%] max-w-none ${objectPos} object-cover`
              : 'block h-auto w-full'
          }
          style={
            isFragment
              ? {
                  left: focus === 'right' ? 'auto' : focus === 'left' ? '-6%' : '-16%',
                  right: focus === 'right' ? '-6%' : 'auto',
                  top: focus === 'top' ? '0%' : '-10%',
                }
              : undefined
          }
          loading={isHero ? 'eager' : 'lazy'}
          decoding="async"
        />
        {caption && !isHero && !isFragment ? (
          <figcaption className="absolute inset-x-0 bottom-0 bg-slate-900/80 px-3 pb-2.5 pt-8 text-xs text-slate-200 sm:px-4 sm:text-sm">
            {caption}
          </figcaption>
        ) : null}
      </div>
      {caption && (isHero || isFragment) ? <figcaption className="sr-only">{caption}</figcaption> : null}
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
    ? t('app.seo.pricing.title', {
        defaultValue: 'HostFlow Pricing — Recruitment Plans for Transport Teams',
      })
    : t('app.seo.landing.title', {
        defaultValue: 'HostFlow — Recruitment & Workforce Operations for Transport Companies',
      })
  const seoDescription = isPricingRoute
    ? t('app.seo.pricing.description', {
        defaultValue:
          'Compare HostFlow plans. Every plan includes the core recruitment workflow and document control.',
      })
    : t('app.seo.landing.description', {
        defaultValue:
          'Manage candidates, recruitment pipelines, ownership and documents in one system built for transport operations.',
      })

  const problemItems = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.problem.items.${i}`)), [t])
  const howSteps = useMemo(
    () =>
      [0, 1, 2, 3, 4].map((i) => ({
        title: t(`public.crm_landing.how.steps.${i}.title`),
        body: t(`public.crm_landing.how.steps.${i}.body`),
      })),
    [t],
  )
  const productBlocks = useMemo(
    () =>
      [0, 1, 2, 3, 4].map((i) => ({
        title: t(`public.crm_landing.product.blocks.${i}.title`),
        body: t(`public.crm_landing.product.blocks.${i}.body`),
        caption: t(`public.crm_landing.product.blocks.${i}.caption`),
        imageSrc: t(`public.crm_landing.product.blocks.${i}.screenshot_src`, { defaultValue: '' }),
      })),
    [t],
  )
  const includedAll = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.pricing.included.${i}`)), [t])
  const faq = useMemo(
    () =>
      ['distribution', 'documents', 'meta', 'data', 'plan_change', 'demo', 'ats'].map((key) => ({
        q: t(`public.crm_landing.faq.${key}_q`),
        a: t(`public.crm_landing.faq.${key}_a`),
      })),
    [t],
  )

  const plans = useMemo(
    () =>
      (
        [
          { key: 'starter' as const, featured: false, ctaHref: '/signup?plan=starter' },
          { key: 'team' as const, featured: true, ctaHref: '/signup?plan=team' },
          { key: 'pro' as const, featured: false, ctaHref: '/signup?plan=pro' },
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

  useSeoMeta({
    title: seoTitle,
    description: seoDescription,
    canonicalPath,
    structuredData: [
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
            priceCurrency: 'EUR',
            description: 'Custom configuration; contact sales',
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
          acceptedAnswer: { '@type': 'Answer', text: item.a },
        })),
      },
    ],
  })

  const practiceShot = t('public.crm_landing.practice.screenshot_src', {
    defaultValue: '/landing/shots/hero-pipeline.jpg',
  })
  const heroShot = t('public.crm_landing.hero.screenshot_src', {
    defaultValue: '/landing/shots/hero-pipeline.jpg',
  })

  const navLinks = [
    { href: '/#problem', id: 'problem', label: t('public.crm_landing.nav.problem') },
    { href: '/#how', id: 'how', label: t('public.crm_landing.nav.how') },
    { href: '/#product', id: 'product', label: t('public.crm_landing.nav.product') },
    { href: '/#transport', id: 'transport', label: t('public.crm_landing.nav.transport') },
    { href: '/#practice', id: 'practice', label: t('public.crm_landing.nav.practice') },
    { href: '/#pricing', id: 'pricing', label: t('public.crm_landing.nav.pricing') },
    { href: '/#faq', id: 'faq', label: t('public.crm_landing.nav.faq') },
  ]

  const scrollToId = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="min-h-screen bg-[#F7F8FA] text-slate-900 antialiased">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-[#0B0E14]/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 sm:gap-4 sm:px-6 sm:py-3">
          <a
            href="/#top"
            className="shrink-0"
            aria-label="HostFlow"
            onClick={(e) => {
              if (location.pathname === '/' || location.pathname === '/pricing') {
                e.preventDefault()
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }
            }}
          >
            <PublicLogo showWordmark white size={34} />
          </a>
          <nav
            className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto text-[12px] font-medium text-slate-400 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden sm:gap-4 sm:text-[13px]"
            aria-label="Primary"
          >
            {navLinks.map((link) => (
              <a
                key={link.id}
                href={link.href}
                className="shrink-0 rounded-md px-2 py-1.5 transition hover:bg-white/5 hover:text-white"
                onClick={(e) => {
                  if (location.pathname === '/' || location.pathname === '/pricing') {
                    e.preventDefault()
                    scrollToId(link.id)
                    trackCta(`nav_anchor_${link.id}`, link.href)
                    window.history.replaceState?.(null, '', `#${link.id}`)
                  }
                }}
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <div className="hidden md:block">
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
              to="/signup"
              onClick={() => trackCta('nav_signup', '/signup')}
              className="inline-flex items-center justify-center rounded-lg bg-[#00C2A8] px-3 py-2 text-[12px] font-semibold text-[#04201C] transition hover:bg-[#1ad4bb] sm:px-3.5 sm:text-[13px]"
            >
              {t('public.crm_landing.nav.demo')}
            </Link>
          </div>
        </div>
      </header>

      <section id="top" className="relative overflow-hidden pt-14 sm:pt-16">
        <div className="bg-[#0B0E14] text-white">
          <div className="mx-auto flex max-w-3xl flex-col items-center space-y-5 px-4 pb-16 pt-10 text-center sm:px-6 sm:pb-20 sm:pt-14 lg:pb-24 lg:pt-16">
            <p className="inline-flex rounded-full border border-[#00C2A8]/35 bg-white/[0.04] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#00C2A8]">
              {t('public.crm_landing.hero.badge')}
            </p>
            <h1 className="text-balance text-4xl font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl lg:text-[3.05rem]">
              {t('public.crm_landing.hero.title')}
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-slate-300 sm:text-[17px]">
              {t('public.crm_landing.hero.lead')}
            </p>
            <p className="max-w-2xl text-sm font-medium leading-relaxed text-[#B8FFF3] sm:text-base">
              {t('public.crm_landing.hero.platform_line')}
            </p>
            <div className="flex flex-col items-center gap-3 pt-1 sm:flex-row">
              <Link
                to="/signup"
                onClick={() => trackCta('hero_signup', '/signup')}
                className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-7 py-3.5 text-base font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
              >
                {t('public.crm_landing.hero.primary_cta')}
              </Link>
              <Link
                to="/demo"
                onClick={() => trackCta('hero_demo', '/demo')}
                className="inline-flex items-center justify-center rounded-xl border border-white/15 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/5"
              >
                {t('public.crm_landing.hero.secondary_cta')}
              </Link>
            </div>
          </div>
          <svg
            className="block h-[64px] w-full text-[#F7F8FA] sm:h-[88px] lg:h-[112px]"
            viewBox="0 0 1440 180"
            preserveAspectRatio="none"
            aria-hidden
          >
            <path fill="currentColor" d="M0 180V150C200 150 320 20 720 20C1120 20 1240 150 1440 150V180H0Z" />
          </svg>
        </div>

        <div className="relative z-10 -mt-1 bg-[#F7F8FA]">
          <div className="mx-auto flex max-w-6xl justify-center px-4 sm:px-6">
            <div className="w-full max-w-[1000px] leading-none">
              <ProductShot
                size="hero"
                caption={t('public.crm_landing.hero.screenshot_caption')}
                imageSrc={heroShot}
              />
            </div>
          </div>
        </div>
      </section>

      <section id="problem" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-3xl space-y-4 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2E6F74]">
              {t('public.crm_landing.problem.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.problem.title')}
            </h2>
            <p className="text-base leading-relaxed text-slate-600 sm:text-lg">{t('public.crm_landing.problem.lead')}</p>
          </div>
          <ul className="mx-auto grid max-w-4xl gap-3">
            {problemItems.map((item) => (
              <li
                key={item}
                className="rounded-2xl border border-slate-200 bg-[#F7F8FA] px-5 py-4 text-left text-sm font-medium leading-relaxed text-slate-800 sm:text-base"
              >
                {item}
              </li>
            ))}
          </ul>
          <p className="mx-auto max-w-3xl text-center text-base font-semibold leading-relaxed text-slate-900 sm:text-lg">
            {t('public.crm_landing.problem.closing')}
          </p>
        </div>
      </section>

      <section id="how" className="scroll-mt-20 bg-[#F7F8FA] sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-2xl space-y-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2E6F74]">
              {t('public.crm_landing.how.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.how.title')}
            </h2>
          </div>
          <ol className="grid gap-4 md:grid-cols-5">
            {howSteps.map((step, idx) => (
              <li key={step.title} className="rounded-3xl border border-slate-200 bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">0{idx + 1}</p>
                <p className="mt-3 text-lg font-semibold tracking-tight text-[#0B0E14]">{step.title}</p>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="product" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-14 px-4 py-16 sm:px-6 lg:space-y-20 lg:py-24">
          <div className="mx-auto max-w-2xl space-y-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t('public.crm_landing.product.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.product.title')}
            </h2>
          </div>

          <div className="space-y-16 lg:space-y-24">
            {productBlocks.map((block, idx) => {
              const visualLeft = idx % 2 === 0
              const focus = idx === 0 ? 'left' : idx === 2 ? 'top' : 'center'
              const copy = (
                <div className="space-y-4">
                  <h3 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{block.title}</h3>
                  <p className="max-w-md text-base leading-relaxed text-slate-600">{block.body}</p>
                </div>
              )
              const visual = (
                <div className={`flex ${visualLeft ? 'justify-start lg:justify-center' : 'justify-start lg:justify-end'}`}>
                  <ProductShot size="fragment" focus={focus} caption={block.caption} imageSrc={block.imageSrc} />
                </div>
              )
              return (
                <article key={block.title} className="grid items-center gap-8 lg:grid-cols-2 lg:gap-14">
                  <div className={visualLeft ? 'order-2 lg:order-1' : 'order-2'}>{visual}</div>
                  <div className={visualLeft ? 'order-1 lg:order-2' : 'order-1'}>{copy}</div>
                </article>
              )
            })}
          </div>
        </div>
      </section>

      <section id="transport" className="scroll-mt-20 bg-[#0B0E14] text-white sm:scroll-mt-24">
        <div className="mx-auto max-w-3xl space-y-5 px-4 py-16 text-center sm:px-6 lg:py-24">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#00C2A8]">
            {t('public.crm_landing.transport.badge')}
          </p>
          <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl sm:leading-[1.1]">
            {t('public.crm_landing.transport.title')}
          </h2>
          <p className="text-lg font-medium text-[#B8FFF3]">{t('public.crm_landing.transport.lead')}</p>
          <p className="text-base leading-relaxed text-slate-300 sm:text-lg">{t('public.crm_landing.transport.body')}</p>
          <p className="text-base font-semibold leading-relaxed text-white sm:text-lg">
            {t('public.crm_landing.transport.closing')}
          </p>
        </div>
      </section>

      <section id="origin" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-16 text-center sm:px-6 lg:py-20">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2E6F74]">
            {t('public.crm_landing.origin.badge')}
          </p>
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            {t('public.crm_landing.origin.title')}
          </h2>
          <p className="text-base font-medium text-slate-800 sm:text-lg">{t('public.crm_landing.origin.lead')}</p>
          <p className="text-base leading-relaxed text-slate-600">{t('public.crm_landing.origin.body')}</p>
        </div>
      </section>

      <section id="practice" className="scroll-mt-20 bg-[#F7F8FA] sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-16 sm:px-6 lg:py-20">
          <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-12">
            <div className="space-y-4">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#2E6F74]">
                {t('public.crm_landing.practice.badge')}
              </p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
                {t('public.crm_landing.practice.title')}
              </h2>
              <p className="text-base leading-relaxed text-slate-700">{t('public.crm_landing.practice.lead')}</p>
              <p className="text-base leading-relaxed text-slate-600">{t('public.crm_landing.practice.body')}</p>
            </div>
            <div className="flex justify-center lg:justify-end">
              <ProductShot
                size="fragment"
                focus="left"
                caption={t('public.crm_landing.practice.screenshot_caption')}
                imageSrc={practiceShot}
              />
            </div>
          </div>
        </div>
      </section>

      <section id="platform" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-16 text-center sm:px-6 lg:py-20">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2E6F74]">
            {t('public.crm_landing.platform.badge')}
          </p>
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            {t('public.crm_landing.platform.title')}
          </h2>
          <p className="text-base leading-relaxed text-slate-600 sm:text-lg">{t('public.crm_landing.platform.lead')}</p>
          <p className="text-base leading-relaxed text-slate-600">{t('public.crm_landing.platform.body')}</p>
          <p className="text-base font-semibold text-slate-900">{t('public.crm_landing.platform.today')}</p>
          <p className="text-base leading-relaxed text-slate-600">{t('public.crm_landing.platform.closing')}</p>
        </div>
      </section>

      <section id="trust" className="scroll-mt-20 bg-[#0B0E14] text-white sm:scroll-mt-24">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-16 text-center sm:px-6 lg:py-20">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#00C2A8]">
            {t('public.crm_landing.trust.badge')}
          </p>
          <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            {t('public.crm_landing.trust.title')}
          </h2>
          <p className="text-base leading-relaxed text-slate-300 sm:text-lg">{t('public.crm_landing.trust.body')}</p>
        </div>
      </section>

      <section id="demo" className="scroll-mt-20 bg-[#F7F8FA] sm:scroll-mt-24">
        <div className="mx-auto max-w-3xl space-y-5 px-4 py-16 text-center sm:px-6 lg:py-20">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2E6F74]">
            {t('public.crm_landing.demo.badge')}
          </p>
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            {t('public.crm_landing.demo.title')}
          </h2>
          <p className="text-base leading-relaxed text-slate-600 sm:text-lg">{t('public.crm_landing.demo.body')}</p>
          <p className="text-sm leading-relaxed text-slate-500">{t('public.crm_landing.demo.note')}</p>
          <div className="flex flex-col items-center justify-center gap-3 pt-2 sm:flex-row">
            <Link
              to="/signup"
              onClick={() => trackCta('demo_signup', '/signup')}
              className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-7 py-3.5 text-base font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
            >
              {t('public.crm_landing.demo.primary_cta')}
            </Link>
            <Link
              to="/demo"
              onClick={() => trackCta('demo_explore', '/demo')}
              className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-50"
            >
              {t('public.crm_landing.demo.secondary_cta')}
            </Link>
          </div>
        </div>
      </section>

      <section id="pricing" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-16 sm:px-6 lg:py-24">
          <div className="flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-end">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                {t('public.crm_landing.pricing.badge')}
              </p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
                {t('public.crm_landing.pricing.title')}
              </h2>
              <p className="max-w-xl text-sm text-slate-600">{t('public.crm_landing.pricing.note')}</p>
            </div>
            <div className="inline-flex items-center rounded-full border border-slate-200 bg-[#F7F8FA] p-1 text-sm font-semibold">
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
                    className={`flex flex-col rounded-3xl border bg-[#F7F8FA] p-5 ${
                      plan.featured ? 'border-[#00C2A8]' : 'border-slate-200'
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
                        className="mt-6 inline-flex w-full items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-slate-50"
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
            <aside className="rounded-3xl border border-slate-200 bg-[#F7F8FA] p-6 lg:w-64">
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

      <section id="faq" className="scroll-mt-20 bg-[#F7F8FA] sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-16 sm:px-6 lg:py-24">
          <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            {t('public.crm_landing.faq.title')}
          </h2>
          <div className="grid gap-3 lg:grid-cols-2">
            {faq.map((item, idx) => {
              const open = openFaq === idx
              return (
                <article key={item.q} className="rounded-2xl border border-slate-200 bg-white">
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
                  {open ? (
                    <p className="border-t border-slate-200 px-5 py-4 text-sm leading-relaxed text-slate-600">{item.a}</p>
                  ) : null}
                </article>
              )
            })}
          </div>
        </div>
      </section>

      <section className="px-4 py-20 sm:px-6" style={{ background: NAVY }}>
        <div className="mx-auto max-w-3xl space-y-6 text-center">
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl sm:leading-[1.15]">
            {t('public.crm_landing.final_cta.title')}
          </h2>
          <p className="text-base leading-relaxed text-slate-300 sm:text-lg">
            {t('public.crm_landing.final_cta.subtitle')}
          </p>
          <div className="flex flex-col items-center justify-center gap-3 pt-2 sm:flex-row">
            <Link
              to="/signup"
              onClick={() => trackCta('final_signup_primary', '/signup')}
              className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-8 py-3.5 text-base font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
            >
              {t('public.crm_landing.final_cta.button')}
            </Link>
            <Link
              to="/demo"
              onClick={() => trackCta('final_demo', '/demo')}
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
