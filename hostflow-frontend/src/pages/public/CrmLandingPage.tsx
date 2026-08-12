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
      ? 'max-w-[896px]'
      : size === 'wide'
        ? 'max-w-[1080px]'
        : size === 'compact'
          ? 'max-w-[420px]'
          : size === 'fragment'
            ? 'max-w-[520px]'
            : 'max-w-[560px]'

  const frameH =
    size === 'fragment'
      ? 'h-[240px] sm:h-[280px]'
      : size === 'compact'
        ? 'h-auto'
        : size === 'wide'
          ? 'h-auto'
          : 'h-auto'

  const objectPos =
    focus === 'top' ? 'object-top' : focus === 'left' ? 'object-left' : focus === 'right' ? 'object-right' : 'object-center'

  return (
    <figure
      className={`w-full overflow-hidden rounded-2xl border border-white/10 bg-[#0F131A] ring-1 ring-white/5 ${maxW} ${
        isHero
          ? 'mx-auto shadow-[0_48px_120px_-36px_rgba(0,0,0,0.9)]'
          : 'shadow-[0_24px_60px_-36px_rgba(0,0,0,0.55)]'
      }`}
    >
      <div className={`relative overflow-hidden bg-slate-200 ${frameH}`}>
        <img
          src={src}
          alt={caption}
          width={imgW}
          height={imgH}
          className={
            isFragment
              ? `absolute inset-0 h-[145%] w-[145%] max-w-none ${objectPos} object-cover`
              : 'block h-auto w-full'
          }
          style={isFragment ? { left: focus === 'right' ? 'auto' : focus === 'left' ? '-8%' : '-18%', top: '-8%' } : undefined}
          loading={isHero ? 'eager' : 'lazy'}
          decoding="async"
        />
        {caption ? (
          <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/50 to-transparent px-3 pb-2.5 pt-8 text-xs text-slate-200 sm:px-4 sm:text-sm">
            {caption}
          </figcaption>
        ) : null}
      </div>
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
  const problemItems = useMemo(() => [0, 1, 2, 3, 4].map((i) => t(`public.crm_landing.problem.items.${i}`)), [t])
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
      [0, 1, 2, 3, 4].map((i) => ({
        why: t(`public.crm_landing.product.blocks.${i}.why`),
        title: t(`public.crm_landing.product.blocks.${i}.title`),
        body: t(`public.crm_landing.product.blocks.${i}.body`),
        caption: t(`public.crm_landing.product.blocks.${i}.caption`),
        imageSrc: t(`public.crm_landing.product.blocks.${i}.screenshot_src`, { defaultValue: '' }),
      })),
    [t],
  )
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

      {/* 1. HERO — copy left, shot shifted right */}
      <section
        id="top"
        className="relative overflow-x-clip pt-14 sm:pt-16"
        style={{
          background: `radial-gradient(ellipse 80% 60% at 70% 20%, rgba(0,194,168,0.12), transparent 55%), linear-gradient(180deg, ${NAVY} 0%, ${NAVY_SOFT} 100%)`,
        }}
      >
        <div className="mx-auto grid max-w-[1600px] items-center gap-10 px-4 pb-12 pt-10 sm:px-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:gap-10 lg:pb-16 lg:pt-14 xl:grid-cols-[minmax(0,26rem)_minmax(0,1fr)] xl:gap-12">
          <div className="space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#00C2A8]">
              {t('public.crm_landing.hero.badge')}
            </p>
            <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-[3.15rem]">
              {t('public.crm_landing.hero.title_line1')}
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
                href="/#trust"
                onClick={(e) => {
                  e.preventDefault()
                  scrollToId('trust')
                  trackCta('hero_trust', '#trust')
                }}
                className="inline-flex items-center justify-center gap-2 px-2 py-3 text-sm font-semibold text-slate-300 transition hover:text-white"
              >
                <span
                  className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/20 text-[10px]"
                  aria-hidden
                >
                  ▶
                </span>
                {t('public.crm_landing.hero.secondary_cta')}
              </a>
            </div>
            <ul className="flex flex-wrap gap-x-4 gap-y-2 pt-2 text-sm text-slate-300">
              {heroProof.map((chip) => (
                <li key={chip} className="inline-flex items-center gap-1.5">
                  <span className="text-[#00C2A8]" aria-hidden>
                    ✓
                  </span>
                  {chip}
                </li>
              ))}
            </ul>
          </div>

          <div className="relative min-w-0 lg:-mr-2 xl:-mr-6">
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

      {/* 3. PROBLEM — after trust */}
      <section id="problem" className="scroll-mt-20 bg-[#F7F8FA] sm:scroll-mt-24">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1.15fr_0.85fr] lg:gap-12 lg:py-24">
          <div className="space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t('public.crm_landing.problem.badge')}
            </p>
            <h2 className="max-w-xl text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.problem.title')}
            </h2>
            <p className="max-w-xl text-base leading-relaxed text-slate-600">{t('public.crm_landing.problem.lead')}</p>
            <ul className="grid gap-3 sm:grid-cols-2">
              {problemItems.map((item) => (
                <li key={item} className="rounded-2xl border border-slate-200 bg-white px-4 py-4 text-sm font-medium text-slate-800">
                  {item}
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

      {/* 4. MOAT — why not any other ATS */}
      <section
        id="moat"
        className="scroll-mt-20"
        style={{ background: `linear-gradient(180deg, ${NAVY} 0%, #10141C 100%)` }}
      >
        <div className="mx-auto max-w-3xl space-y-8 px-4 py-20 text-center sm:px-6 lg:py-28">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#00C2A8]">
            {t('public.crm_landing.moat.badge')}
          </p>
          <h2 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-5xl sm:leading-[1.1]">
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

      {/* 6. HOW IT WORKS — varied compositions; UI lives inside each step */}
      <section id="product" className="scroll-mt-20 bg-[#F7F8FA] sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-10 px-4 py-12 sm:px-6 lg:space-y-14 lg:py-16">
          <div className="mx-auto max-w-2xl space-y-2 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
              {t('public.crm_landing.product.badge')}
            </p>
            <h2 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.crm_landing.product.title')}
            </h2>
            <p className="text-base text-slate-600">{t('public.crm_landing.product.lead')}</p>
          </div>

          <div className="space-y-12 lg:space-y-14">
            {productBlocks[0] ? (
              <article className="grid items-center gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-8">
                <div className="space-y-2">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">{productBlocks[0].why}</p>
                  <h3 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{productBlocks[0].title}</h3>
                  <p className="max-w-md text-sm leading-relaxed text-slate-600 sm:text-base">{productBlocks[0].body}</p>
                </div>
                <div className="flex justify-start lg:justify-end">
                  <ProductShot
                    size="compact"
                    caption={productBlocks[0].caption}
                    imageSrc={productBlocks[0].imageSrc}
                  />
                </div>
              </article>
            ) : null}

            {productBlocks[1] ? (
              <article className="grid items-center gap-5 rounded-3xl border border-slate-200/80 bg-white p-5 sm:p-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-8 lg:p-8">
                <div className="space-y-2">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">{productBlocks[1].why}</p>
                  <h3 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{productBlocks[1].title}</h3>
                  <p className="max-w-md text-sm leading-relaxed text-slate-600 sm:text-base">{productBlocks[1].body}</p>
                </div>
                <div className="min-w-0">
                  <ProductShot
                    size="support"
                    caption={productBlocks[1].caption}
                    imageSrc={productBlocks[1].imageSrc}
                  />
                </div>
              </article>
            ) : null}

            {productBlocks[2] ? (
              <article className="space-y-4">
                <div className="mx-auto max-w-2xl space-y-2 text-center sm:text-left">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">{productBlocks[2].why}</p>
                  <h3 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{productBlocks[2].title}</h3>
                  <p className="text-sm leading-relaxed text-slate-600 sm:text-base">{productBlocks[2].body}</p>
                </div>
                <div className="flex justify-center">
                  <ProductShot
                    size="wide"
                    caption={productBlocks[2].caption}
                    imageSrc={productBlocks[2].imageSrc}
                  />
                </div>
              </article>
            ) : null}

            {productBlocks[3] ? (
              <article className="grid items-center gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-8">
                <div className="order-2 flex justify-start lg:order-1">
                  <ProductShot
                    size="fragment"
                    focus="left"
                    caption={productBlocks[3].caption}
                    imageSrc={productBlocks[3].imageSrc}
                  />
                </div>
                <div className="order-1 space-y-2 lg:order-2">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">{productBlocks[3].why}</p>
                  <h3 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{productBlocks[3].title}</h3>
                  <p className="max-w-md text-sm leading-relaxed text-slate-600 sm:text-base">{productBlocks[3].body}</p>
                </div>
              </article>
            ) : null}

            {productBlocks[4] ? (
              <article className="grid items-end gap-5 overflow-hidden rounded-3xl border border-slate-200/80 bg-[#0B0E14] p-5 text-white sm:p-6 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-8 lg:p-8">
                <div className="space-y-2 pb-1">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#00C2A8]">{productBlocks[4].why}</p>
                  <h3 className="text-xl font-semibold tracking-tight sm:text-2xl">{productBlocks[4].title}</h3>
                  <p className="max-w-md text-sm leading-relaxed text-slate-300 sm:text-base">{productBlocks[4].body}</p>
                </div>
                <div className="min-w-0 lg:-mb-2 lg:-mr-2">
                  <ProductShot
                    size="wide"
                    caption={productBlocks[4].caption}
                    imageSrc={productBlocks[4].imageSrc}
                  />
                </div>
              </article>
            ) : null}
          </div>
        </div>
      </section>

      {/* 7. CASE — UI embedded with story, not a separate chapter */}
      <section id="case" className="scroll-mt-20 bg-[#0B0E14] text-white sm:scroll-mt-24">
        <div className="mx-auto max-w-6xl space-y-8 px-4 py-12 sm:px-6 lg:py-16">
          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:gap-8">
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
            </div>
            <div className="min-w-0 space-y-4">
              <ProductShot
                size="support"
                caption={t('public.crm_landing.case.screenshot_caption')}
                imageSrc={caseShot}
              />
              <blockquote className="rounded-2xl border border-[#00C2A8]/30 bg-[#00C2A8]/10 p-5">
                <p className="text-base font-medium leading-relaxed text-white sm:text-lg">
                  “{t('public.crm_landing.case.quote')}”
                </p>
                <footer className="mt-4 text-sm text-[#B8FFF3]">
                  <p className="font-semibold">{t('public.crm_landing.case.quote_name')}</p>
                  <p className="mt-1 text-slate-300">{t('public.crm_landing.case.quote_role')}</p>
                </footer>
              </blockquote>
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
