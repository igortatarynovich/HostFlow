import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { CompanySiteNav } from './components/CompanySiteNav'
import { ProductShot } from './components/ProductShot'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function AboutPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'company', pageKey: 'about' })

  const audience = [0, 1, 2, 3].map((i) => t(`public.company.about.audience.items.${i}`))
  const notFor = [0, 1, 2].map((i) => t(`public.company.about.not_for.items.${i}`))

  useSeoMeta({
    title: t('public.company.about.seo.title', {
      defaultValue: 'About HostFlow — B2B recruitment operations platform',
    }),
    description: t('public.company.about.seo.description', {
      defaultValue:
        'HostFlow is a B2B SaaS for recruitment agencies and transport companies — not a consumer Facebook app. Learn who we are and how Meta Lead Ads connect to company workspaces.',
    }),
    canonicalPath: '/about',
    structuredData: {
      '@context': 'https://schema.org',
      '@type': 'AboutPage',
      name: 'About HostFlow',
      description: t('public.company.about.seo.description'),
      mainEntity: {
        '@type': 'Organization',
        name: 'HostFlow',
        url: 'https://hostflow.cc',
        email: 'info@hostflow.cc',
        address: {
          '@type': 'PostalAddress',
          streetAddress: 'ul. Leśna 1A/2',
          addressLocality: 'Przecław',
          postalCode: '64-514',
          addressCountry: 'PL',
        },
      },
    },
  })

  return (
    <PublicPageShell maxWidth="6xl">
      <div className="space-y-8">
        <CompanySiteNav />

        <section className="card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('public.company.about.badge', { defaultValue: 'About HostFlow' })}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.company.about.title', {
              defaultValue: 'B2B recruitment operations for companies',
            })}
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.company.about.lead', {
              defaultValue:
                'HostFlow is a business software platform for recruitment agencies and employers. Companies sign up, run hiring pipelines, and optionally connect their Meta (Facebook/Instagram) Lead Ads so leads land in their private workspace.',
            })}
          </p>
          <div className="mt-4 rounded-xl border border-brand-200 bg-brand-50/70 px-4 py-3 text-sm text-slate-800">
            <strong className="font-semibold text-brand-900">
              {t('public.company.about.b2b_label', { defaultValue: 'Important for Meta review:' })}{' '}
            </strong>
            {t('public.company.about.b2b_note', {
              defaultValue:
                'HostFlow is not a public consumer app for individual Facebook users. End customers are companies. Candidates appear as data subjects processed on behalf of those companies.',
            })}
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-2">
          <ProductShot
            size="feature"
            src="/landing/shots/shot-workspace.jpg"
            badge={t('public.company.shots.workspace.badge', { defaultValue: 'Workspace' })}
            caption={t('public.company.shots.workspace.caption', {
              defaultValue: 'Company workspace dashboard — leads, pipeline, and ownership in one tenant.',
            })}
          />
          <ProductShot
            size="feature"
            src="/landing/shots/shot-meta.jpg"
            badge={t('public.company.shots.meta.badge', { defaultValue: 'Meta' })}
            caption={t('public.company.shots.meta.caption', {
              defaultValue: 'Meta Lead Ads sync into the client company CRM — Tech Provider model.',
            })}
          />
        </div>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.company.about.who_title', { defaultValue: 'Who we are' })}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">
            {t('public.company.about.who_body', {
              defaultValue:
                'Host Flow — Viktoriia Tatarynovich (NIP 7872153072, REGON 542991376), ul. Leśna 1A/2, 64-514 Przecław, Poland. We build and operate HostFlow as a multi-tenant B2B SaaS for recruitment and workforce onboarding.',
            })}
          </p>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('public.company.about.legal_name_label', { defaultValue: 'Legal name' })}
              </dt>
              <dd className="mt-1 text-slate-800">Host Flow — Viktoriia Tatarynovich</dd>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('public.company.about.product_label', { defaultValue: 'Product' })}
              </dt>
              <dd className="mt-1 text-slate-800">HostFlow (hostflow.cc)</dd>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('public.company.about.model_label', { defaultValue: 'Business model' })}
              </dt>
              <dd className="mt-1 text-slate-800">
                {t('public.company.about.model_value', {
                  defaultValue: 'B2B SaaS / Tech Provider for Meta Lead Ads',
                })}
              </dd>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('public.company.about.contact_label', { defaultValue: 'Contact' })}
              </dt>
              <dd className="mt-1">
                <a href="mailto:info@hostflow.cc" className="text-brand-700 underline-offset-2 hover:underline">
                  info@hostflow.cc
                </a>
              </dd>
            </div>
          </dl>
        </section>

        <div className="grid gap-6 md:grid-cols-2">
          <section className="card cv-auto p-6">
            <h2 className="text-xl font-semibold text-slate-900">
              {t('public.company.about.audience.title', { defaultValue: 'Built for' })}
            </h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
              {audience.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
          <section className="card cv-auto p-6">
            <h2 className="text-xl font-semibold text-slate-900">
              {t('public.company.about.not_for.title', { defaultValue: 'Not built for' })}
            </h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
              {notFor.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        </div>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.company.about.meta_title', { defaultValue: 'How Meta fits in' })}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">
            {t('public.company.about.meta_body', {
              defaultValue:
                'A company administrator connects their own Facebook Page and Lead Ads forms to HostFlow. HostFlow retrieves lead submissions for that business (permissions such as leads_retrieval and pages_show_list) and stores them in the company’s private tenant. HostFlow does not publish content to personal timelines and does not offer a consumer social experience.',
            })}
          </p>
          <div className="mt-4 flex flex-wrap gap-2 text-sm">
            <Link to="/services" className="btn-secondary btn-sm" onClick={() => trackCta('about_services', '/services')}>
              {t('public.company.nav.services', { defaultValue: 'Services' })}
            </Link>
            <Link to="/contact" className="btn-secondary btn-sm" onClick={() => trackCta('about_contact', '/contact')}>
              {t('public.company.nav.contact', { defaultValue: 'Contact' })}
            </Link>
            <a href="/data-deletion.html" className="btn-secondary btn-sm" target="_blank" rel="noopener noreferrer">
              {t('public.company.nav.data_deletion', { defaultValue: 'Data deletion' })}
            </a>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
