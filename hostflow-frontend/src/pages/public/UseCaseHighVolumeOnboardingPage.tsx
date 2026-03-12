import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function UseCaseHighVolumeOnboardingPage() {
  const { trackCta } = useSeoTracking({ pageType: 'use_case', pageKey: 'high_volume_onboarding' })
  const faq = [
    {
      q: 'Can we onboard many candidates without losing control?',
      a: 'Yes. Shared visibility and task ownership keep throughput stable under load.',
    },
    {
      q: 'Do reminders help reduce follow-up delays?',
      a: 'Reminders and status cues reduce missed actions and speed up completion.',
    },
    {
      q: 'Can managers monitor progress in real time?',
      a: 'Dashboard and workflow states show where teams are blocked and what to fix next.',
    },
  ]

  useSeoMeta({
    title: 'High-Volume Candidate Onboarding Workflow',
    description:
      'Run high-volume candidate onboarding with clear stages, reminders, and document readiness in one CRM flow.',
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
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">Use-case</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">High-Volume Candidate Onboarding</h1>
          <p className="mt-3 text-sm text-slate-600">
            Maintain speed and quality when many candidates move through onboarding at the same time.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('primary_signup', '/signup')}>Start free trial</Link>
            <Link to="/pricing" className="btn-secondary" onClick={() => trackCta('secondary_pricing', '/pricing')}>View pricing</Link>
          </div>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Where teams get stuck</h2>
          <p className="mt-2 text-sm text-slate-700">
            Volume breaks onboarding when actions are not assigned and document follow-up is manual. HostFlow gives a
            shared operational layer for recruiters, coordinators, and managers.
          </p>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Execution pattern</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>Standard stage path with ownership at every step.</li>
            <li>Document checklist attached to each candidate journey.</li>
            <li>Reminders and alerts for pending or overdue tasks.</li>
            <li>Manager visibility on throughput and blockers.</li>
          </ul>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">FAQ</h2>
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
          <h2 className="text-xl font-semibold text-slate-900">Related guides</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm" onClick={() => trackCta('related_pipeline', '/features/candidate-pipeline')}>Candidate pipeline</Link>
            <Link to="/features/document-control" className="btn-secondary btn-sm" onClick={() => trackCta('related_document_control', '/features/document-control')}>Document control</Link>
            <Link to="/use-cases/trucking-recruitment" className="btn-secondary btn-sm" onClick={() => trackCta('related_trucking', '/use-cases/trucking-recruitment')}>Trucking recruitment use-case</Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
