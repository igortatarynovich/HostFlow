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

const NAVY = '#0B0E14'
const NAVY_SOFT = '#12151C'

function ProductShot({
  caption,
  imageSrc,
  size = 'support',
  focus = 'center',
}: {
  caption: string
  imageSrc: string
  /** hero = landing hero only; others are supporting UI inside story blocks */
  size?: 'hero' | 'support' | 'compact' | 'wide' | 'fragment'
  focus?: 'center' | 'top' | 'left' | 'right'
}) {
  const src = (imageSrc || '').trim()
  if (!(src.startsWith('http://') || src.startsWith('https://') || src.startsWith('/') || src.startsWith('.'))) {
    return (
      <div
        className="flex min-h-[200px] items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-slate-800 to-[#0B0E14] p-6 text-center text-sm text-slate-300"
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
            ? 'rounded-2xl border border-slate-200/90 bg-white shadow-[0_18px_50px_-28px_rgba(15,23,42,0.35)]'
            : 'rounded-2xl border border-white/10 bg-[#0F131A] shadow-[0_24px_60px_-36px_rgba(0,0,0,0.55)] ring-1 ring-white/5'
      }`}
      style={
        isHero
          ? {
              // Soft feathered rim — outside overflow so it doesn't harden into a strip
              boxShadow:
                '-2px -3px 8px rgba(15,23,42,0.16), 2px -3px 8px rgba(15,23,42,0.16), 0 -4px 14px rgba(15,23,42,0.12)',
            }
          : undefined
      }
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
          <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/50 to-transparent px-3 pb-2.5 pt-8 text-xs text-slate-200 sm:px-4 sm:text-sm">
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
    ? t('app.seo.pricing.title')
    : t('app.seo.landing.title')
  const seoDescription = isPricingRoute
    ? t('app.seo.pricing.description')
    : t('app.seo.landing.description')

  const heroProof = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.hero.proof.${i}`)), [t])
  const trustPoints = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.trust.points.${i}`)), [t])
  const team = useMemo(
    () =>
      [0, 1, 2].map((i) => ({
        initials: t(`public.crm_landing.team.members.${i}.initials`),
        name: t(`public.crm_landing.team.members.${i}.name`),
        role: t(`public.crm_landing.team.members.${i}.role`),
        line: t(`public.crm_landing.team.members.${i}.line`),
      })),
    [t],
  )
  const moatItems = useMemo(() => [0, 1, 2, 3].map((i) => t(`public.crm_landing.moat.items.${i}`)), [t])
  const storySteps = useMemo(
    () =>
      [0, 1, 2, 3, 4].map((i) => ({
        value: t(`public.crm_landing.story.steps.${i}.value`),
        label: t(`public.crm_landing.story.steps.${i}.label`),
      })),
    [t],
  )
  const productBlocks = useMemo(
    () =>
      [0, 1, 2].map((i) => ({
        why: t(`public.crm_landing.product.blocks.${i}.why`),
        title: t(`public.crm_landing.product.blocks.${i}.title`),
        body: t(`public.crm_landing.product.blocks.${i}.body`),
        quote: t(`public.crm_landing.product.blocks.${i}.quote`),
        caption: t(`public.crm_landing.product.blocks.${i}.caption`),
        imageSrc: t(`public.crm_landing.product.blocks.${i}.screenshot_src`, { defaultValue: '' }),
      })),
    [t],
  )
  const compareThem = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.compare.them.${i}`)), [t])
  const compareUs = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.compare.us.${i}`)), [t])

  const caseSteps = useMemo(
    () =>
      [0, 1, 2, 3].map((i) => ({
        label: t(`public.crm_landing.case.steps.${i}.label`),
        body: t(`public.crm_landing.case.steps.${i}.body`),
      })),
    [t],
  )
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

  const caseShot = t('public.crm_landing.case.screenshot_src', {
    defaultValue: '/landing/shots/hero-pipeline.jpg',
  })
  const heroShot = t('public.crm_landing.hero.screenshot_src', {
    defaultValue: '/landing/shots/hero-pipeline.jpg',
  })

  const navLinks = [
    { href: '/#trust', id: 'trust', label: t('public.crm_landing.nav.trust') },
    { href: '/#problem', id: 'problem', label: t('public.crm_landing.nav.problem') },
    { href: '/#story', id: 'story', label: t('public.crm_landing.nav.story') },
    { href: '/#case', id: 'case', label: t('public.crm_landing.nav.case') },
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
              to="/demo"
              onClick={() => trackCta('nav_demo', '/demo')}
              className="inline-flex items-center justify-center rounded-lg bg-[#00C2A8] px-3 py-2 text-[12px] font-semibold text-[#04201C] transition hover:bg-[#1ad4bb] sm:px-3.5 sm:text-[13px]"
            >
              {t('public.crm_landing.nav.demo')}
            </Link>
          </div>
        </div>
      </header>

      {/* 1. HERO — dark zone (headline+CTA); curve lowered; tight light zone around shot */}
      <section id="top" className="relative overflow-hidden pt-14 sm:pt-16">
        {/* Dark header — extra space under CTA so the curve sits lower */}
        <div className="bg-[#0B0E14] text-white">
          <div className="mx-auto flex max-w-3xl flex-col items-center space-y-5 px-4 pb-16 pt-10 text-center sm:px-6 sm:pb-20 sm:pt-14 lg:pb-24 lg:pt-16">
            <p className="inline-flex rounded-full border border-[#00C2A8]/35 bg-white/[0.04] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#00C2A8]">
              {t('public.crm_landing.hero.badge')}
            </p>
            <h1 className="text-balance text-4xl font-semibold leading-[1.08] tracking-tight text-white sm:text-5xl lg:text-[3.05rem]">
              {t('public.crm_landing.hero.title_line1')}{' '}
              <span className="whitespace-pre-line text-[#00C2A8]">{t('public.crm_landing.hero.title_accent')}</span>
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-slate-300 sm:text-[17px]">
              {t('public.crm_landing.hero.lead')}
            </p>
            <div className="pt-1">
              <Link
                to="/demo"
                onClick={() => trackCta('hero_demo', '/demo')}
                className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-7 py-3.5 text-base font-semibold text-[#04201C] shadow-[0_12px_40px_-12px_rgba(0,194,168,0.45)] transition hover:bg-[#1ad4bb]"
              >
                {t('public.crm_landing.hero.primary_cta')}
              </Link>
            </div>
          </div>

          {/* Symmetrical curve — sits lower after CTA padding */}
          <svg
            className="block h-[64px] w-full text-[#F7F8FA] sm:h-[88px] lg:h-[112px]"
            viewBox="0 0 1440 180"
            preserveAspectRatio="none"
            aria-hidden
          >
            <path
              fill="currentColor"
              d="M0 180V150C200 150 320 20 720 20C1120 20 1240 150 1440 150V180H0Z"
            />
          </svg>
        </div>

        {/* Light zone — pull up into curve valley; height ≈ screenshot */}
        <div className="relative z-10 -mt-1 bg-[#F7F8FA]">
          <div className="mx-auto grid max-w-6xl items-center gap-6 px-4 sm:gap-8 sm:px-6 lg:grid-cols-[minmax(0,0.72fr)_minmax(0,1.28fr)] lg:gap-10">
            <div className="relative z-10 space-y-4">
              <p className="max-w-md text-base font-medium leading-relaxed text-slate-800 sm:text-[17px]">
                {t('public.crm_landing.hero.system_line')}
              </p>
              <ul className="space-y-3 text-sm text-slate-600 sm:text-[15px]">
                {heroProof.map((chip) => (
                  <li key={chip} className="flex items-start gap-2.5">
                    <span className="mt-0.5 text-[#00C2A8]" aria-hidden>
                      ✓
                    </span>
                    <span>{chip}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative z-10 flex w-full justify-center leading-none lg:justify-end">
              <div className="w-full max-w-[1000px] leading-none lg:max-w-none lg:w-[156%] lg:origin-bottom-right">
                <ProductShot
                  size="hero"
                  caption={t('public.crm_landing.hero.screenshot_caption')}
                  imageSrc={heroShot}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. TRUST FIRST — why you can trust us */}
      <section id="trust" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-12 px-4 py-16 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-3xl space-y-5 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2E6F74]">
              {t('public.crm_landing.trust.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-5xl sm:leading-[1.1]">
              {t('public.crm_landing.trust.title')}
            </h2>
            <p className="text-lg leading-relaxed text-slate-600">{t('public.crm_landing.trust.lead')}</p>
          </div>

          <ul className="mx-auto grid max-w-4xl gap-3">
            {trustPoints.map((point) => (
              <li
                key={point}
                className="rounded-2xl border border-slate-200 bg-[#F7F8FA] px-5 py-4 text-left text-sm font-medium leading-relaxed text-slate-800 sm:text-base"
              >
                {point}
              </li>
            ))}
          </ul>

          <p className="mx-auto max-w-3xl text-center text-base font-semibold leading-relaxed text-slate-900 sm:text-lg">
            {t('public.crm_landing.trust.closing')}
          </p>

          {/* People — CRM is sold by people */}
          <div className="space-y-6 rounded-[1.75rem] border border-slate-200 bg-[#0B0E14] p-6 text-white sm:p-10">
            <div className="max-w-2xl space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">
                {t('public.crm_landing.team.badge')}
              </p>
              <h3 className="text-2xl font-semibold tracking-tight sm:text-3xl">{t('public.crm_landing.team.title')}</h3>
              <p className="text-sm leading-relaxed text-slate-300 sm:text-base">{t('public.crm_landing.team.body')}</p>
            </div>
            <ul className="grid gap-4 md:grid-cols-3">
              {team.map((member) => (
                <li key={member.name} className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#00C2A8]/15 text-sm font-bold text-[#00C2A8]">
                    {member.initials}
                  </div>
                  <p className="mt-4 text-base font-semibold">{member.name}</p>
                  <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-[#00C2A8]">{member.role}</p>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">{member.line}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* 3. COMPARE — show only the argument, no screenshots */}
      <section id="problem" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6 lg:py-20">
          <h2 className="mx-auto max-w-3xl text-balance text-center text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            {t('public.crm_landing.compare.title')}
          </h2>
          <div className="grid gap-4 lg:grid-cols-2 lg:gap-6">
            <article className="rounded-3xl border border-slate-200 bg-[#F7F8FA] p-6 sm:p-8">
              <h3 className="text-center text-lg font-semibold text-slate-900 sm:text-xl">
                {t('public.crm_landing.compare.them_title')}
              </h3>
              <ul className="mt-6 space-y-4">
                {compareThem.map((item) => (
                  <li key={item} className="flex gap-3 text-sm leading-relaxed text-slate-600 sm:text-base">
                    <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-rose-100 text-xs font-bold text-rose-600">
                      ×
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </article>
            <article className="rounded-3xl bg-[#0B0E14] p-6 text-white sm:p-8">
              <h3 className="text-center text-lg font-semibold sm:text-xl">
                {t('public.crm_landing.compare.us_title')}
              </h3>
              <ul className="mt-6 space-y-4">
                {compareUs.map((item) => (
                  <li key={item} className="flex gap-3 text-sm leading-relaxed text-slate-200 sm:text-base">
                    <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#00C2A8] text-[11px] font-bold text-[#04201C]">
                      ✓
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </article>
          </div>
          <div className="flex justify-center">
            <Link
              to="/demo"
              onClick={() => trackCta('compare_demo', '/demo')}
              className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-7 py-3.5 text-base font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
            >
              {t('public.crm_landing.compare.cta')}
            </Link>
          </div>
        </div>
      </section>

      {/* 4. MOAT — short authority after compare */}
      <section
        id="moat"
        className="scroll-mt-20"
        style={{ background: `linear-gradient(180deg, ${NAVY} 0%, #10141C 100%)` }}
      >
        <div className="mx-auto max-w-3xl space-y-8 px-4 py-16 text-center sm:px-6 lg:py-20">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#00C2A8]">
            {t('public.crm_landing.moat.badge')}
          </p>
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl sm:leading-[1.1]">
            {t('public.crm_landing.moat.title')}
          </h2>
          <ul className="space-y-3 text-left">
            {moatItems.map((item) => (
              <li
                key={item}
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 text-base font-medium text-slate-200"
              >
                {item}
              </li>
            ))}
          </ul>
          <p className="text-lg font-semibold text-[#B8FFF3]">{t('public.crm_landing.moat.closing')}</p>
        </div>
      </section>

      {/* 5. STORY PROCESS — not a schema */}
      <section id="story" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-10 px-4 py-16 sm:px-6 lg:py-24">
          <div className="mx-auto max-w-2xl space-y-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2E6F74]">
              {t('public.crm_landing.story.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.story.title')}
            </h2>
            <p className="text-base text-slate-600">{t('public.crm_landing.story.lead')}</p>
          </div>
          <ol className="grid gap-3 md:grid-cols-5">
            {storySteps.map((step, idx) => (
              <li key={step.label} className="relative rounded-3xl border border-slate-200 bg-[#F7F8FA] p-5 text-center">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">0{idx + 1}</p>
                <p className="mt-3 text-3xl font-bold tracking-tight text-[#0B0E14]">{step.value}</p>
                <p className="mt-2 text-sm font-medium leading-snug text-slate-600">{step.label}</p>
              </li>
            ))}
          </ol>
          <p className="mx-auto max-w-2xl text-center text-sm font-medium text-slate-500">
            {t('public.crm_landing.story.footnote')}
          </p>
        </div>
      </section>

      {/* 6. HOW IT WORKS — cropped UI fragments only (Pipedrive-style Z rows) */}
      <section id="product" className="scroll-mt-20 bg-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-14 px-4 py-16 sm:px-6 lg:space-y-20 lg:py-24">
          <div className="mx-auto max-w-2xl space-y-3 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t('public.crm_landing.product.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.product.title')}
            </h2>
            <p className="text-base text-slate-600">{t('public.crm_landing.product.lead')}</p>
          </div>

          <div className="space-y-16 lg:space-y-24">
            {productBlocks.map((block, idx) => {
              const visualLeft = idx % 2 === 0
              const focus = idx === 0 ? 'left' : idx === 1 ? 'top' : 'center'
              const copy = (
                <div className="space-y-4">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">{block.why}</p>
                  <h3 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{block.title}</h3>
                  <p className="max-w-md text-base leading-relaxed text-slate-600">{block.body}</p>
                  <blockquote className="max-w-md border-l-2 border-[#00C2A8] pl-4">
                    <p className="text-sm italic leading-relaxed text-slate-500">“{block.quote}”</p>
                  </blockquote>
                </div>
              )
              const visual = (
                <div className={`flex ${visualLeft ? 'justify-start lg:justify-center' : 'justify-start lg:justify-end'}`}>
                  <ProductShot size="fragment" focus={focus} caption={block.caption} imageSrc={block.imageSrc} />
                </div>
              )
              return (
                <article
                  key={block.title}
                  className="grid items-center gap-8 lg:grid-cols-2 lg:gap-14"
                >
                  <div className={visualLeft ? 'order-2 lg:order-1' : 'order-2 lg:order-2'}>{visual}</div>
                  <div className={visualLeft ? 'order-1 lg:order-2' : 'order-1 lg:order-1'}>{copy}</div>
                </article>
              )
            })}
          </div>
        </div>
      </section>

      {/* 7. CASE — fragment shot beside story */}
      <section id="case" className="scroll-mt-20 bg-[#0B0E14] text-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-12 sm:px-6 lg:py-16">
          <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-12">
            <div className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">
                {t('public.crm_landing.case.badge')}
              </p>
              <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl sm:leading-[1.1]">
                {t('public.crm_landing.case.title')}
              </h2>
              <p className="text-base leading-relaxed text-slate-300">{t('public.crm_landing.case.lead')}</p>
              <ol className="mt-4 grid gap-3 sm:grid-cols-2">
                {caseSteps.map((step, idx) => (
                  <li key={step.label} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#00C2A8]">
                      0{idx + 1} · {step.label}
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-200">{step.body}</p>
                  </li>
                ))}
              </ol>
              <blockquote className="mt-2 border-l-2 border-[#00C2A8] pl-4">
                <p className="text-base font-medium leading-relaxed text-slate-100 sm:text-lg">
                  “{t('public.crm_landing.case.quote')}”
                </p>
                <footer className="mt-3 text-sm text-[#B8FFF3]">
                  <p className="font-semibold">{t('public.crm_landing.case.quote_name')}</p>
                  <p className="mt-1 text-slate-400">{t('public.crm_landing.case.quote_role')}</p>
                </footer>
              </blockquote>
            </div>
            <div className="flex justify-center lg:justify-end">
              <ProductShot
                size="fragment"
                focus="left"
                caption={t('public.crm_landing.case.screenshot_caption')}
                imageSrc={caseShot}
              />
            </div>
          </div>
        </div>
      </section>

      {/* 8. FOR WHOM */}
      <section className="bg-white">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-16 sm:px-6 lg:py-20">
          <div className="max-w-2xl space-y-3">
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.segments.title')}
            </h2>
            <p className="text-base text-slate-600">{t('public.crm_landing.segments.lead')}</p>
          </div>
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

      {/* 9. PRICING */}
      <section id="pricing" className="scroll-mt-20 bg-[#F7F8FA] sm:scroll-mt-24">
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

      {/* 10. FAQ */}
      <section id="faq" className="scroll-mt-20 bg-white sm:scroll-mt-24">
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
                  {open ? (
                    <p className="border-t border-slate-200 px-5 py-4 text-sm leading-relaxed text-slate-600">{item.a}</p>
                  ) : null}
                </article>
              )
            })}
          </div>
        </div>
      </section>

      {/* 11. FINAL CTA — positioning statement */}
      <section
        className="px-4 py-20 sm:px-6"
        style={{
          background: `radial-gradient(ellipse 70% 80% at 50% 0%, rgba(0,194,168,0.16), transparent 55%), ${NAVY}`,
        }}
      >
        <div className="mx-auto max-w-3xl space-y-6 text-center">
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl sm:leading-[1.15]">
            {t('public.crm_landing.final_cta.title')}
          </h2>
          <p className="text-base leading-relaxed text-slate-300 sm:text-lg">
            {t('public.crm_landing.final_cta.subtitle')}
          </p>
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
