import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { CompanySiteNav } from './components/CompanySiteNav'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function ContactPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'company', pageKey: 'contact' })

  useSeoMeta({
    title: t('public.company.contact.seo.title', {
      defaultValue: 'Contact HostFlow — B2B support & Meta review',
    }),
    description: t('public.company.contact.seo.description', {
      defaultValue:
        'Contact HostFlow for business inquiries, Meta integration support, privacy and data deletion requests. B2B SaaS for companies.',
    }),
    canonicalPath: '/contact',
  })

  const channels = [
    {
      title: t('public.company.contact.channels.general.title', { defaultValue: 'General & sales' }),
      body: t('public.company.contact.channels.general.body', {
        defaultValue: 'Plans, demos, and company onboarding questions.',
      }),
      href: 'mailto:info@hostflow.cc',
      label: 'info@hostflow.cc',
    },
    {
      title: t('public.company.contact.channels.privacy.title', { defaultValue: 'Privacy & data deletion' }),
      body: t('public.company.contact.channels.privacy.body', {
        defaultValue: 'GDPR requests and Meta lead data deletion.',
      }),
      href: 'mailto:info@hostflow.cc?subject=Data%20Deletion%20Request%20%E2%80%94%20HostFlow%20Leads',
      label: 'info@hostflow.cc',
    },
    {
      title: t('public.company.contact.channels.meta.title', { defaultValue: 'Meta / integrations' }),
      body: t('public.company.contact.channels.meta.body', {
        defaultValue: 'App Review, Access Verification, and Lead Ads connection help for business clients.',
      }),
      href: 'mailto:info@hostflow.cc?subject=Meta%20integration%20%E2%80%94%20HostFlow',
      label: 'info@hostflow.cc',
    },
  ]

  return (
    <PublicPageShell maxWidth="5xl" variant="marketing">
      <div className="space-y-8">
        <CompanySiteNav />

        <section className="card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('public.company.contact.badge', { defaultValue: 'Contact' })}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.company.contact.title', {
              defaultValue: 'Contact the HostFlow team',
            })}
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.company.contact.lead', {
              defaultValue:
                'We support business customers who use HostFlow for recruitment operations. For Meta App Review / Access Verification, use the company details below — HostFlow is a B2B service for companies, not a consumer app.',
            })}
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {channels.map((channel) => (
            <article key={channel.title} className="card cv-auto p-5">
              <h2 className="text-base font-semibold text-slate-900">{channel.title}</h2>
              <p className="mt-2 text-sm text-slate-600">{channel.body}</p>
              <a
                href={channel.href}
                className="mt-4 inline-flex text-sm font-semibold text-brand-700 underline-offset-2 hover:underline"
                onClick={() => trackCta('contact_email', channel.href)}
              >
                {channel.label}
              </a>
            </article>
          ))}
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.company.contact.company_title', { defaultValue: 'Company details' })}
          </h2>
          <address className="mt-3 space-y-1 text-sm not-italic text-slate-700">
            <div className="font-semibold text-slate-900">Host Flow — Viktoriia Tatarynovich</div>
            <div>NIP: 7872153072 · REGON: 542991376</div>
            <div>ul. Leśna 1A/2, 64-514 Przecław, Poland</div>
            <div>
              <a href="mailto:info@hostflow.cc" className="text-brand-700 underline-offset-2 hover:underline">
                info@hostflow.cc
              </a>
            </div>
            <div>
              <a
                href="https://hostflow.cc"
                className="text-brand-700 underline-offset-2 hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                https://hostflow.cc
              </a>
            </div>
          </address>
          <div className="mt-5 flex flex-wrap gap-2 text-sm">
            <a href="/legal/privacy.html" className="btn-secondary btn-sm" target="_blank" rel="noopener noreferrer">
              {t('public.company.nav.privacy', { defaultValue: 'Privacy Policy' })}
            </a>
            <a href="/legal/terms.html" className="btn-secondary btn-sm" target="_blank" rel="noopener noreferrer">
              {t('public.company.nav.terms', { defaultValue: 'Terms of Service' })}
            </a>
            <a href="/data-deletion.html" className="btn-secondary btn-sm" target="_blank" rel="noopener noreferrer">
              {t('public.company.nav.data_deletion', { defaultValue: 'Data deletion' })}
            </a>
            <Link to="/about" className="btn-secondary btn-sm" onClick={() => trackCta('contact_about', '/about')}>
              {t('public.company.nav.about', { defaultValue: 'About' })}
            </Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
