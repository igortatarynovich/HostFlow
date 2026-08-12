import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { CompanySiteNav } from './components/CompanySiteNav'
import { ProductShot } from './components/ProductShot'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function MarketingServicesPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'company', pageKey: 'services' })

  const services = [0, 1, 2, 3, 4, 5].map((i) => ({
    title: t(`public.company.services.items.${i}.title`),
    body: t(`public.company.services.items.${i}.body`),
  }))

  useSeoMeta({
    title: t('public.company.services.seo.title', {
      defaultValue: 'HostFlow services — B2B recruitment CRM & Meta Lead Ads',
    }),
    description: t('public.company.services.seo.description', {
      defaultValue:
        'Services for companies: Meta Lead Ads intake, candidate pipeline, documents, WhatsApp workflow, team ownership — HostFlow is B2B SaaS, not a consumer app.',
    }),
    canonicalPath: '/services',
  })

  return (
    <PublicPageShell maxWidth="6xl" variant="marketing">
      <div className="space-y-8">
        <CompanySiteNav />

        <section className="card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('public.company.services.badge', { defaultValue: 'Services' })}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.company.services.title', {
              defaultValue: 'What HostFlow provides to businesses',
            })}
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.company.services.lead', {
              defaultValue:
                'HostFlow sells software subscriptions to companies. We help recruitment agencies and employers run hiring from first lead to hire — including optional Meta Lead Ads integration as a Tech Provider.',
            })}
          </p>
        </section>

        <div className="grid gap-6 lg:grid-cols-3">
          <ProductShot
            size="feature"
            src="/landing/shots/shot-meta.jpg"
            badge={t('public.company.shots.meta.badge', { defaultValue: 'Meta' })}
            caption={t('public.company.shots.meta.caption', {
              defaultValue: 'Meta Lead Ads sync into the client company CRM — Tech Provider model.',
            })}
          />
          <ProductShot
            size="feature"
            src="/landing/shots/hero-pipeline.jpg"
            badge={t('public.company.shots.pipeline.badge', { defaultValue: 'Pipeline' })}
            caption={t('public.company.shots.pipeline.caption', {
              defaultValue: 'Hiring pipeline with stages and owners inside the company tenant.',
            })}
          />
          <ProductShot
            size="feature"
            src="/landing/shots/shot-documents.jpg"
            badge={t('public.company.shots.documents.badge', { defaultValue: 'Documents' })}
            caption={t('public.company.shots.documents.caption', {
              defaultValue: 'Document checklist and verification for the recruiting company.',
            })}
          />
        </div>

        <section className="grid gap-4 md:grid-cols-2">
          {services.map((item) => (
            <article key={item.title} className="card cv-auto p-5">
              <h2 className="text-base font-semibold text-slate-900">{item.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">{item.body}</p>
            </article>
          ))}
        </section>

        <section className="card cv-auto border-brand-200 bg-brand-50/50 p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.company.services.customer_title', {
              defaultValue: 'Who the customer is',
            })}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">
            {t('public.company.services.customer_body', {
              defaultValue:
                'The paying customer and Meta app user is always a business (agency or employer). Individual candidates may fill lead forms or upload documents through links issued by that business — they are not HostFlow’s B2B customers and do not “install” HostFlow as a consumer Facebook app.',
            })}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link to="/pricing" className="btn-primary" onClick={() => trackCta('services_pricing', '/pricing')}>
              {t('public.company.services.cta_pricing', { defaultValue: 'View pricing' })}
            </Link>
            <Link to="/signup" className="btn-secondary" onClick={() => trackCta('services_signup', '/signup')}>
              {t('public.company.services.cta_signup', { defaultValue: 'Create company account' })}
            </Link>
            <Link to="/about" className="btn-secondary" onClick={() => trackCta('services_about', '/about')}>
              {t('public.company.nav.about', { defaultValue: 'About' })}
            </Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
