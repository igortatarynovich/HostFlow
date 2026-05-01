import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function FeatureCandidatePipelinePage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'feature', pageKey: 'candidate_pipeline' })
  const faq = [
    {
      q: t('public.marketing.feature_candidate_pipeline.faq.q1.q', { defaultValue: 'Can we configure pipeline stages for different teams?' }),
      a: t('public.marketing.feature_candidate_pipeline.faq.q1.a', { defaultValue: 'Yes. Teams can adapt stages and keep a shared operating model without losing reporting consistency.' }),
    },
    {
      q: t('public.marketing.feature_candidate_pipeline.faq.q2.q', { defaultValue: 'Will managers see bottlenecks fast?' }),
      a: t('public.marketing.feature_candidate_pipeline.faq.q2.a', { defaultValue: 'The workflow highlights blocked candidates, overdue actions, and ownership gaps in one place.' }),
    },
    {
      q: t('public.marketing.feature_candidate_pipeline.faq.q3.q', { defaultValue: 'Do we need extra onboarding before launch?' }),
      a: t('public.marketing.feature_candidate_pipeline.faq.q3.a', { defaultValue: 'No. You can start with default stages and refine them while work is already running.' }),
    },
  ]

  useSeoMeta({
    title: t('public.marketing.feature_candidate_pipeline.seo.title', { defaultValue: 'Candidate Pipeline CRM for Recruitment' }),
    description: t(
      'public.marketing.feature_candidate_pipeline.seo.description',
      { defaultValue: 'Run candidate stages, ownership, and next actions in one recruitment pipeline CRM built for fast operations.' },
    ),
    canonicalPath: '/features/candidate-pipeline',
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
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{t('public.marketing.feature_candidate_pipeline.hero.badge', { defaultValue: 'Feature' })}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.marketing.feature_candidate_pipeline.hero.title', { defaultValue: 'Candidate Pipeline CRM for Recruitment Teams' })}
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            {t('public.marketing.feature_candidate_pipeline.hero.subtitle', { defaultValue: 'Keep every candidate moving with clear stages, owners, and next actions so your pipeline does not stall.' })}
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
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.feature_candidate_pipeline.problem.title', { defaultValue: 'What this solves' })}</h2>
          <p className="mt-2 text-sm text-slate-700">
            {t('public.marketing.feature_candidate_pipeline.problem.body', { defaultValue: 'Teams lose time when candidate status lives across chats and spreadsheets. HostFlow centralizes stages, ownership, and reminders, so recruiters and managers work from the same source of truth.' })}
          </p>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.feature_candidate_pipeline.flow.title', { defaultValue: 'How the workflow runs' })}</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-700">
            <li>{t('public.marketing.feature_candidate_pipeline.flow.items.1', { defaultValue: 'Create or import candidates into the pipeline.' })}</li>
            <li>{t('public.marketing.feature_candidate_pipeline.flow.items.2', { defaultValue: 'Assign responsible users and due actions per stage.' })}</li>
            <li>{t('public.marketing.feature_candidate_pipeline.flow.items.3', { defaultValue: 'Track bottlenecks and SLA risks in dashboard and reminders.' })}</li>
            <li>{t('public.marketing.feature_candidate_pipeline.flow.items.4', { defaultValue: 'Move candidates forward with auditable stage history.' })}</li>
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
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.feature_candidate_pipeline.related.title', { defaultValue: 'Related guides' })}</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Link to="/features/document-control" className="btn-secondary btn-sm" onClick={() => trackCta('related_document_control', '/features/document-control')}>
              {t('public.marketing.common.related.document_control', { defaultValue: 'Document control' })}
            </Link>
            <Link to="/use-cases/trucking-recruitment" className="btn-secondary btn-sm" onClick={() => trackCta('related_trucking', '/use-cases/trucking-recruitment')}>
              {t('public.marketing.common.related.trucking_recruitment_use_case', { defaultValue: 'Trucking recruitment use-case' })}
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
