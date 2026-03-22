import { useMemo } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

type PlanCard = {
  key: 'starter' | 'team' | 'pro'
  price: string
  seats: string
  features: string[]
  bestFor: string
  ctaHref: string
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
    : t('app.seo.landing.title', { defaultValue: 'CRM for Recruitment Teams' })
  const seoDescription = isPricingRoute
    ? t('app.seo.pricing.description', {
        defaultValue: 'Compare HostFlow plans and start your recruitment CRM trial in minutes.',
      })
    : t('app.seo.landing.description', {
        defaultValue: 'HostFlow helps recruitment teams run leads, candidates, documents, and operations in one CRM.',
      })
  const faq = useMemo(
    () => [
      {
        q: t('public.crm_landing.faq.q1', { defaultValue: 'Can we start without configuring everything?' }),
        a: t('public.crm_landing.faq.a1', {
          defaultValue: 'Yes. Core onboarding is account -> company -> first client/lead/action. Advanced settings can be done later.',
        }),
      },
      {
        q: t('public.crm_landing.faq.q2', { defaultValue: 'Can we invite team later?' }),
        a: t('public.crm_landing.faq.a2', { defaultValue: 'Yes. Start solo, then invite teammates from Team settings when ready.' }),
      },
      {
        q: t('public.crm_landing.faq.q3', { defaultValue: 'What if we choose wrong plan?' }),
        a: t('public.crm_landing.faq.a3', { defaultValue: 'Plans can be changed in Billing. The product flow keeps your workspace data intact.' }),
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
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
          description: 'Trial access available',
        },
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

  const plans: PlanCard[] = [
    {
      key: 'starter',
      price: t('public.crm_landing.pricing.starter.price', { defaultValue: '$39/mo' }),
      seats: t('public.crm_landing.pricing.starter.seats', { defaultValue: '1 user' }),
      features: [
        t('public.crm_landing.pricing.starter.features.0', { defaultValue: 'Candidate and client management' }),
        t('public.crm_landing.pricing.starter.features.1', { defaultValue: 'Lead source tracking' }),
        t('public.crm_landing.pricing.starter.features.2', { defaultValue: 'Basic dashboard' }),
      ],
      bestFor: t('public.crm_landing.pricing.starter.best_for', { defaultValue: 'Best for solo operators starting CRM operations' }),
      ctaHref: '/signup?plan=starter',
    },
    {
      key: 'team',
      price: t('public.crm_landing.pricing.team.price', { defaultValue: '$99/mo' }),
      seats: t('public.crm_landing.pricing.team.seats', { defaultValue: 'Up to 5 users' }),
      features: [
        t('public.crm_landing.pricing.team.features.0', { defaultValue: 'Team roles and permissions' }),
        t('public.crm_landing.pricing.team.features.1', { defaultValue: 'Shared workspace and assignments' }),
        t('public.crm_landing.pricing.team.features.2', { defaultValue: 'Communications workspace' }),
      ],
      bestFor: t('public.crm_landing.pricing.team.best_for', { defaultValue: 'Best for small teams managing shared pipelines' }),
      ctaHref: '/signup?plan=team',
    },
    {
      key: 'pro',
      price: t('public.crm_landing.pricing.pro.price', { defaultValue: '$199/mo' }),
      seats: t('public.crm_landing.pricing.pro.seats', { defaultValue: 'Advanced limits' }),
      features: [
        t('public.crm_landing.pricing.pro.features.0', { defaultValue: 'Advanced analytics and reporting' }),
        t('public.crm_landing.pricing.pro.features.1', { defaultValue: 'Priority support' }),
        t('public.crm_landing.pricing.pro.features.2', { defaultValue: 'Expanded integrations' }),
      ],
      bestFor: t('public.crm_landing.pricing.pro.best_for', { defaultValue: 'Best for scaled operations with advanced workflows' }),
      ctaHref: '/signup?plan=pro',
    },
  ]

  const comparisonRows = [
    {
      key: 'users',
      label: t('public.crm_landing.compare.users', { defaultValue: 'Users' }),
      starter: '1',
      team: 'Up to 5',
      pro: '15+',
    },
    {
      key: 'roles',
      label: t('public.crm_landing.compare.roles', { defaultValue: 'Roles & permissions' }),
      starter: 'Basic',
      team: 'Advanced',
      pro: 'Advanced',
    },
    {
      key: 'communications',
      label: t('public.crm_landing.compare.communications', { defaultValue: 'Communications workspace' }),
      starter: 'Limited',
      team: 'Included',
      pro: 'Included',
    },
    {
      key: 'analytics',
      label: t('public.crm_landing.compare.analytics', { defaultValue: 'Analytics' }),
      starter: 'Basic',
      team: 'Standard',
      pro: 'Advanced',
    },
  ]

  const objections = [
    t('public.crm_landing.objections.0', { defaultValue: 'Too many settings before work starts.' }),
    t('public.crm_landing.objections.1', { defaultValue: 'Hard to onboard team members.' }),
    t('public.crm_landing.objections.2', { defaultValue: 'Unclear path from lead to next action.' }),
  ]

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-14">
        <section className="overflow-hidden rounded-[32px] border border-brand-100 bg-white/95 p-7 shadow-card lg:p-10">
          <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                {t('public.crm_landing.hero.badge', { defaultValue: 'CRM for recruitment operations' })}
              </p>
              <h1 className="text-3xl font-semibold text-slate-900 lg:text-5xl">
                {t('public.crm_landing.hero.title', { defaultValue: 'Launch your hiring workflow in minutes' })}
              </h1>
              <p className="text-base text-slate-600">
                {t('public.crm_landing.hero.subtitle', {
                  defaultValue:
                    'Manage leads, candidates, team workload and communications in one workspace with a fast onboarding.',
                })}
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  to="/signup"
                  onClick={() => trackCta('hero_primary_signup', '/signup')}
                  className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-6 py-3 text-base font-semibold text-white shadow-lg shadow-brand-500/30 transition hover:bg-brand-700"
                >
                  {t('public.crm_landing.hero.primary_cta', { defaultValue: 'Start free trial' })}
                </Link>
                <Link
                  to="/login"
                  onClick={() => trackCta('hero_secondary_login', '/login')}
                  className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-6 py-3 text-base font-semibold text-slate-800 transition hover:bg-slate-50"
                >
                  {t('public.crm_landing.hero.secondary_cta', { defaultValue: 'Sign in' })}
                </Link>
              </div>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
              <p className="text-sm font-semibold text-slate-900">
                {t('public.crm_landing.hero.value_title', { defaultValue: 'What you get in the first 5 minutes' })}
              </p>
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                <li>• {t('public.crm_landing.hero.value_list.0', { defaultValue: 'Create workspace and company' })}</li>
                <li>• {t('public.crm_landing.hero.value_list.1', { defaultValue: 'Add first lead or client' })}</li>
                <li>• {t('public.crm_landing.hero.value_list.2', { defaultValue: 'Assign status, note and next task' })}</li>
              </ul>
            </div>
          </div>
        </section>

        <section id="pricing" className="cv-auto space-y-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                {t('public.crm_landing.pricing.badge', { defaultValue: 'Pricing' })}
              </p>
              <h2 className="text-2xl font-semibold text-slate-900">
                {t('public.crm_landing.pricing.title', { defaultValue: 'Choose a plan that fits your team' })}
              </h2>
            </div>
            <p className="text-sm text-slate-600">
              {t('public.crm_landing.pricing.note', { defaultValue: 'Payment gateway will be connected in the final launch step.' })}
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            {plans.map((plan) => (
              <article key={plan.key} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                  {t(`public.crm_landing.pricing.${plan.key}.name`, { defaultValue: plan.key })}
                </p>
                <p className="mt-3 text-3xl font-semibold text-slate-900">{plan.price}</p>
                <p className="mt-1 text-sm text-slate-600">{plan.seats}</p>
                <p className="mt-2 rounded-lg bg-slate-50 px-2 py-1 text-xs text-slate-700">{plan.bestFor}</p>
                <ul className="mt-4 space-y-2 text-sm text-slate-700">
                  {plan.features.map((feature) => (
                    <li key={feature}>• {feature}</li>
                  ))}
                </ul>
                <Link
                  to={plan.ctaHref}
                  onClick={() => trackCta(`pricing_select_${plan.key}`, plan.ctaHref)}
                  className="mt-5 inline-flex w-full items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
                >
                  {t('public.crm_landing.pricing.select_cta', { defaultValue: 'Select plan' })}
                </Link>
              </article>
            ))}
          </div>
        </section>

        <section className="cv-auto space-y-4">
          <h2 className="text-2xl font-semibold text-slate-900">
            {t('public.crm_landing.compare.title', { defaultValue: 'Plan comparison at a glance' })}
          </h2>
          <div className="space-y-3 md:hidden">
            {comparisonRows.map((row) => (
              <article key={row.key} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="text-sm font-semibold text-slate-900">{row.label}</h3>
                <dl className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-700">
                  <div className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                    <dt className="font-medium text-slate-600">{t('public.crm_landing.pricing.starter.name', { defaultValue: 'Starter' })}</dt>
                    <dd className="text-right">{row.starter}</dd>
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                    <dt className="font-medium text-slate-600">{t('public.crm_landing.pricing.team.name', { defaultValue: 'Team' })}</dt>
                    <dd className="text-right">{row.team}</dd>
                  </div>
                  <div className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                    <dt className="font-medium text-slate-600">{t('public.crm_landing.pricing.pro.name', { defaultValue: 'Pro' })}</dt>
                    <dd className="text-right">{row.pro}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
          <div className="hidden overflow-x-auto rounded-2xl border border-slate-200 bg-white md:block">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-700">
                <tr>
                  <th className="px-4 py-3 text-left">{t('public.crm_landing.compare.feature', { defaultValue: 'Feature' })}</th>
                  <th className="px-4 py-3 text-left">{t('public.crm_landing.pricing.starter.name', { defaultValue: 'Starter' })}</th>
                  <th className="px-4 py-3 text-left">{t('public.crm_landing.pricing.team.name', { defaultValue: 'Team' })}</th>
                  <th className="px-4 py-3 text-left">{t('public.crm_landing.pricing.pro.name', { defaultValue: 'Pro' })}</th>
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map((row) => (
                  <tr key={row.key} className="border-t border-slate-100 text-slate-700">
                    <td className="px-4 py-3 font-medium text-slate-900">{row.label}</td>
                    <td className="px-4 py-3">{row.starter}</td>
                    <td className="px-4 py-3">{row.team}</td>
                    <td className="px-4 py-3">{row.pro}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.crm_landing.objections.title', { defaultValue: 'Common blockers we remove' })}
          </h2>
          <ul className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-3">
            {objections.map((item) => (
              <li key={item} className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="cv-auto rounded-3xl border border-brand-200 bg-brand-50/60 p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.crm_landing.faq.title', { defaultValue: 'FAQ' })}
          </h2>
          <div className="mt-4 space-y-3">
            {faq.map((item) => (
              <article key={item.q} className="rounded-xl border border-brand-100 bg-white px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-900">{item.q}</h3>
                <p className="mt-1 text-sm text-slate-700">{item.a}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="cv-auto rounded-3xl border border-brand-200 bg-brand-50/60 p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.crm_landing.audience.title', { defaultValue: 'Who this CRM is for' })}
          </h2>
          <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
            <p>• {t('public.crm_landing.audience.items.0', { defaultValue: 'Recruitment agencies with distributed teams' })}</p>
            <p>• {t('public.crm_landing.audience.items.1', { defaultValue: 'Employers with high-volume candidate flows' })}</p>
            <p>• {t('public.crm_landing.audience.items.2', { defaultValue: 'Operations teams managing onboarding and docs' })}</p>
            <p>• {t('public.crm_landing.audience.items.3', { defaultValue: 'Managers who need clear pipeline and ownership' })}</p>
          </div>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.crm_landing.guides.title', { defaultValue: 'Explore product guides' })}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.crm_landing.guides.subtitle', { defaultValue: 'Start with the page closest to your current challenge and move to the next linked guide.' })}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
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
          </div>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 text-center">
          <h2 className="text-2xl font-semibold text-slate-900">
            {t('public.crm_landing.final_cta.title', { defaultValue: 'Ready to launch your CRM workflow?' })}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.crm_landing.final_cta.subtitle', { defaultValue: 'Create workspace now and reach first value in minutes.' })}
          </p>
          <div className="mt-4 flex justify-center">
            <Link
              to="/signup?plan=team"
              onClick={() => trackCta('final_cta_signup_team', '/signup?plan=team')}
              className="inline-flex items-center justify-center rounded-xl bg-brand-600 px-6 py-3 text-base font-semibold text-white shadow-lg shadow-brand-500/30 transition hover:bg-brand-700"
            >
              {t('public.crm_landing.final_cta.button', { defaultValue: 'Start free trial' })}
            </Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
