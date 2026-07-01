import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function UseCaseTruckingRecruitmentPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'use_case', pageKey: 'trucking_recruitment' })
  const faq = [
    {
      q: t('public.marketing.use_case_trucking_recruitment.faq.q1.q', { defaultValue: 'Is this relevant for driver CE hiring?' }),
      a: t('public.marketing.use_case_trucking_recruitment.faq.q1.a', { defaultValue: 'Yes. The workflow is designed for trucking recruitment with document-heavy onboarding.' }),
    },
    {
      q: t('public.marketing.use_case_trucking_recruitment.faq.q2.q', { defaultValue: 'Can operations and recruiters collaborate in one workspace?' }),
      a: t('public.marketing.use_case_trucking_recruitment.faq.q2.a', { defaultValue: 'Yes. Shared pipeline, reminders, and document states keep all roles aligned.' }),
    },
    {
      q: t('public.marketing.use_case_trucking_recruitment.faq.q3.q', { defaultValue: 'Can we start with a small team first?' }),
      a: t('public.marketing.use_case_trucking_recruitment.faq.q3.a', { defaultValue: 'You can launch quickly and scale roles and permissions as volume grows.' }),
    },
  ]

  useSeoMeta({
    title: t('public.marketing.use_case_trucking_recruitment.seo.title', { defaultValue: 'CRM for Trucking Recruitment Teams' }),
    description: t(
      'public.marketing.use_case_trucking_recruitment.seo.description',
      { defaultValue: 'Manage driver recruitment, onboarding documents, and team coordination in one CRM workflow for trucking operations.' },
    ),
    canonicalPath: '/use-cases/trucking-recruitment',
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
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{t('public.marketing.use_case_trucking_recruitment.hero.badge', { defaultValue: 'Use-case' })}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.marketing.use_case_trucking_recruitment.hero.title', { defaultValue: 'CRM for Trucking Recruitment' })}
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            {t('public.marketing.use_case_trucking_recruitment.hero.subtitle', { defaultValue: 'Build a repeatable driver hiring process from lead to onboarding with document control and ownership clarity.' })}
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
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.use_case_trucking_recruitment.challenges.title', { defaultValue: 'Operational challenges' })}</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>{t('public.marketing.use_case_trucking_recruitment.challenges.items.1', { defaultValue: 'High candidate volume with multi-step qualification.' })}</li>
            <li>{t('public.marketing.use_case_trucking_recruitment.challenges.items.2', { defaultValue: 'Document readiness directly affects deployment timing.' })}</li>
            <li>{t('public.marketing.use_case_trucking_recruitment.challenges.items.3', { defaultValue: 'Recruiters and operations need shared status context.' })}</li>
          </ul>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.use_case_trucking_recruitment.flow.title', { defaultValue: 'Recommended flow in HostFlow' })}</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-700">
            <li>{t('public.marketing.use_case_trucking_recruitment.flow.items.1', { defaultValue: 'Capture and qualify incoming driver leads.' })}</li>
            <li>{t('public.marketing.use_case_trucking_recruitment.flow.items.2', { defaultValue: 'Move candidates through standardized stage checkpoints.' })}</li>
            <li>{t('public.marketing.use_case_trucking_recruitment.flow.items.3', { defaultValue: 'Track mandatory file statuses before dispatch.' })}</li>
            <li>{t('public.marketing.use_case_trucking_recruitment.flow.items.4', { defaultValue: 'Use reminders to prevent missed follow-ups.' })}</li>
          </ol>
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
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.use_case_trucking_recruitment.related.title', { defaultValue: 'Related guides' })}</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm" onClick={() => trackCta('related_pipeline', '/features/candidate-pipeline')}>
              {t('public.marketing.common.related.candidate_pipeline', { defaultValue: 'Candidate pipeline' })}
            </Link>
            <Link to="/features/document-control" className="btn-secondary btn-sm" onClick={() => trackCta('related_document_control', '/features/document-control')}>
              {t('public.marketing.common.related.document_control', { defaultValue: 'Document control' })}
            </Link>
            <Link to="/use-cases/high-volume-onboarding" className="btn-secondary btn-sm" onClick={() => trackCta('related_high_volume', '/use-cases/high-volume-onboarding')}>
              {t('public.marketing.common.related.high_volume_onboarding', { defaultValue: 'High-volume onboarding' })}
            </Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
