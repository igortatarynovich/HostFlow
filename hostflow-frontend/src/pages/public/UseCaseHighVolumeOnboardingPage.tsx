import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function UseCaseHighVolumeOnboardingPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'use_case', pageKey: 'high_volume_onboarding' })
  const faq = [
    {
      q: t('public.marketing.use_case_high_volume_onboarding.faq.q1.q', { defaultValue: 'Can we onboard many candidates without losing control?' }),
      a: t('public.marketing.use_case_high_volume_onboarding.faq.q1.a', { defaultValue: 'Yes. Shared visibility and task ownership keep throughput stable under load.' }),
    },
    {
      q: t('public.marketing.use_case_high_volume_onboarding.faq.q2.q', { defaultValue: 'Do reminders help reduce follow-up delays?' }),
      a: t('public.marketing.use_case_high_volume_onboarding.faq.q2.a', { defaultValue: 'Reminders and status cues reduce missed actions and speed up completion.' }),
    },
    {
      q: t('public.marketing.use_case_high_volume_onboarding.faq.q3.q', { defaultValue: 'Can managers monitor progress in real time?' }),
      a: t('public.marketing.use_case_high_volume_onboarding.faq.q3.a', { defaultValue: 'Dashboard and workflow states show where teams are blocked and what to fix next.' }),
    },
  ]

  useSeoMeta({
    title: t('public.marketing.use_case_high_volume_onboarding.seo.title', { defaultValue: 'High-Volume Candidate Onboarding Workflow' }),
    description: t(
      'public.marketing.use_case_high_volume_onboarding.seo.description',
      { defaultValue: 'Run high-volume candidate onboarding with clear stages, reminders, and document readiness in one CRM flow.' },
    ),
    canonicalPath: '/use-cases/high-volume-onboarding',
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
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{t('public.marketing.use_case_high_volume_onboarding.hero.badge', { defaultValue: 'Use-case' })}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.marketing.use_case_high_volume_onboarding.hero.title', { defaultValue: 'High-Volume Candidate Onboarding' })}
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            {t('public.marketing.use_case_high_volume_onboarding.hero.subtitle', { defaultValue: 'Maintain speed and quality when many candidates move through onboarding at the same time.' })}
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

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.use_case_high_volume_onboarding.problem.title', { defaultValue: 'Where teams get stuck' })}</h2>
          <p className="mt-2 text-sm text-slate-700">
            {t('public.marketing.use_case_high_volume_onboarding.problem.body', { defaultValue: 'Volume breaks onboarding when actions are not assigned and document follow-up is manual. HostFlow gives a shared operational layer for recruiters, coordinators, and managers.' })}
          </p>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.use_case_high_volume_onboarding.execution.title', { defaultValue: 'Execution pattern' })}</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>{t('public.marketing.use_case_high_volume_onboarding.execution.items.1', { defaultValue: 'Standard stage path with ownership at every step.' })}</li>
            <li>{t('public.marketing.use_case_high_volume_onboarding.execution.items.2', { defaultValue: 'Document checklist attached to each candidate journey.' })}</li>
            <li>{t('public.marketing.use_case_high_volume_onboarding.execution.items.3', { defaultValue: 'Reminders and alerts for pending or overdue tasks.' })}</li>
            <li>{t('public.marketing.use_case_high_volume_onboarding.execution.items.4', { defaultValue: 'Manager visibility on throughput and blockers.' })}</li>
          </ul>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
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

        <section className="cv-auto rounded-3xl border border-brand-200 bg-brand-50/60 p-6">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.use_case_high_volume_onboarding.related.title', { defaultValue: 'Related guides' })}</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm" onClick={() => trackCta('related_pipeline', '/features/candidate-pipeline')}>
              {t('public.marketing.common.related.candidate_pipeline', { defaultValue: 'Candidate pipeline' })}
            </Link>
            <Link to="/features/document-control" className="btn-secondary btn-sm" onClick={() => trackCta('related_document_control', '/features/document-control')}>
              {t('public.marketing.common.related.document_control', { defaultValue: 'Document control' })}
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
