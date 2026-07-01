import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function FeatureDocumentControlPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'feature', pageKey: 'document_control' })
  const faq = [
    {
      q: t('public.marketing.feature_document_control.faq.q1.q', { defaultValue: 'Can we manage document deadlines automatically?' }),
      a: t('public.marketing.feature_document_control.faq.q1.a', { defaultValue: 'Yes. HostFlow tracks statuses, deadlines, and reminders across required document sets.' }),
    },
    {
      q: t('public.marketing.feature_document_control.faq.q2.q', { defaultValue: 'Will teams see missing files quickly?' }),
      a: t('public.marketing.feature_document_control.faq.q2.a', { defaultValue: 'Yes. Missing and overdue states are visible in candidate workflow and dashboard widgets.' }),
    },
    {
      q: t('public.marketing.feature_document_control.faq.q3.q', { defaultValue: 'Can this work with onboarding at scale?' }),
      a: t('public.marketing.feature_document_control.faq.q3.a', { defaultValue: 'The flow is built for high candidate volume and reduces manual follow-up operations.' }),
    },
  ]

  useSeoMeta({
    title: t('public.marketing.feature_document_control.seo.title', { defaultValue: 'Recruitment Document Control Software' }),
    description: t(
      'public.marketing.feature_document_control.seo.description',
      { defaultValue: 'Automate document collection, expiry checks, and reminders in one recruitment document control workflow.' },
    ),
    canonicalPath: '/features/document-control',
    structuredData: {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: faq.map((item) => ({
        '@type': 'Question',
        name: item.q,
        acceptedAnswer: { '@type': 'Answer', text: item.a },
      })),
    },
  })

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-8">
        <section className="card p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{t('public.marketing.feature_document_control.hero.badge', { defaultValue: 'Feature' })}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.marketing.feature_document_control.hero.title', { defaultValue: 'Document Control for Recruitment Operations' })}
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            {t('public.marketing.feature_document_control.hero.subtitle', { defaultValue: 'Keep candidate files complete and valid with clear statuses, reminders, and shared visibility for teams.' })}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('primary_signup', '/signup')}>
              {t('public.marketing.common.cta.start_trial', { defaultValue: 'Start free trial' })}
            </Link>
            <Link to="/pricing" className="btn-secondary" onClick={() => trackCta('secondary_pricing', '/pricing')}>
              {t('public.marketing.common.cta.view_pricing', { defaultValue: 'View pricing' })}
            </Link>
          </div>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.feature_document_control.problem.title', { defaultValue: 'Why teams need this' })}</h2>
          <p className="mt-2 text-sm text-slate-700">
            {t('public.marketing.feature_document_control.problem.body', { defaultValue: 'Manual tracking of passports, permits, and certificates creates risk and delays. HostFlow organizes required documents by workflow stage and alerts users before issues become blockers.' })}
          </p>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.feature_document_control.outcome.title', { defaultValue: 'Workflow outcome' })}</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>{t('public.marketing.feature_document_control.outcome.items.1', { defaultValue: 'Standardized checklist for required files.' })}</li>
            <li>{t('public.marketing.feature_document_control.outcome.items.2', { defaultValue: 'Automatic status updates for missing/received/approved/expired documents.' })}</li>
            <li>{t('public.marketing.feature_document_control.outcome.items.3', { defaultValue: 'Reminder operations linked to candidate and owner context.' })}</li>
            <li>{t('public.marketing.feature_document_control.outcome.items.4', { defaultValue: 'Faster onboarding with less manual coordination.' })}</li>
          </ul>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.common.faq', { defaultValue: 'FAQ' })}</h2>
          <div className="mt-3 space-y-3">
            {faq.map((item) => (
              <article key={item.q} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-900">{item.q}</h3>
                <p className="mt-1 text-sm text-slate-700">{item.a}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="cv-auto rounded-xl border border-brand-200 bg-brand-50/60 p-6">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.feature_document_control.related.title', { defaultValue: 'Related guides' })}</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm" onClick={() => trackCta('related_pipeline', '/features/candidate-pipeline')}>
              {t('public.marketing.common.related.candidate_pipeline', { defaultValue: 'Candidate pipeline' })}
            </Link>
            <Link to="/use-cases/high-volume-onboarding" className="btn-secondary btn-sm" onClick={() => trackCta('related_high_volume', '/use-cases/high-volume-onboarding')}>
              {t('public.marketing.common.related.high_volume_onboarding', { defaultValue: 'High-volume onboarding' })}
            </Link>
            <Link to="/use-cases/trucking-recruitment" className="btn-secondary btn-sm" onClick={() => trackCta('related_trucking', '/use-cases/trucking-recruitment')}>
              {t('public.marketing.common.related.trucking_recruitment_use_case', { defaultValue: 'Trucking recruitment use-case' })}
            </Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
