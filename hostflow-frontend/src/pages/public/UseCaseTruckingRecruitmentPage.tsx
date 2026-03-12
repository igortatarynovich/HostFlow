import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function UseCaseTruckingRecruitmentPage() {
  const { trackCta } = useSeoTracking({ pageType: 'use_case', pageKey: 'trucking_recruitment' })
  const faq = [
    {
      q: 'Is this relevant for driver CE hiring?',
      a: 'Yes. The workflow is designed for trucking recruitment with document-heavy onboarding.',
    },
    {
      q: 'Can operations and recruiters collaborate in one workspace?',
      a: 'Yes. Shared pipeline, reminders, and document states keep all roles aligned.',
    },
    {
      q: 'Can we start with a small team first?',
      a: 'You can launch quickly and scale roles and permissions as volume grows.',
    },
  ]

  useSeoMeta({
    title: 'CRM for Trucking Recruitment Teams',
    description:
      'Manage driver recruitment, onboarding documents, and team coordination in one CRM workflow for trucking operations.',
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
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">Use-case</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">CRM for Trucking Recruitment</h1>
          <p className="mt-3 text-sm text-slate-600">
            Build a repeatable driver hiring process from lead to onboarding with document control and ownership clarity.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('primary_signup', '/signup')}>Start free trial</Link>
            <Link to="/pricing" className="btn-secondary" onClick={() => trackCta('secondary_pricing', '/pricing')}>View pricing</Link>
          </div>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Operational challenges</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>High candidate volume with multi-step qualification.</li>
            <li>Document readiness directly affects deployment timing.</li>
            <li>Recruiters and operations need shared status context.</li>
          </ul>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Recommended flow in HostFlow</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-700">
            <li>Capture and qualify incoming driver leads.</li>
            <li>Move candidates through standardized stage checkpoints.</li>
            <li>Track mandatory file statuses before dispatch.</li>
            <li>Use reminders to prevent missed follow-ups.</li>
          </ol>
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
            <Link to="/use-cases/high-volume-onboarding" className="btn-secondary btn-sm" onClick={() => trackCta('related_high_volume', '/use-cases/high-volume-onboarding')}>High-volume onboarding</Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
