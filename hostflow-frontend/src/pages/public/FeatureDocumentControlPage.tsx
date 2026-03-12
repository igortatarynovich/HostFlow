import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useSeoMeta } from '../../hooks/useSeoMeta'

export default function FeatureDocumentControlPage() {
  const faq = [
    {
      q: 'Can we manage document deadlines automatically?',
      a: 'Yes. HostFlow tracks statuses, deadlines, and reminders across required document sets.',
    },
    {
      q: 'Will teams see missing files quickly?',
      a: 'Yes. Missing and overdue states are visible in candidate workflow and dashboard widgets.',
    },
    {
      q: 'Can this work with onboarding at scale?',
      a: 'The flow is built for high candidate volume and reduces manual follow-up operations.',
    },
  ]

  useSeoMeta({
    title: 'Recruitment Document Control Software',
    description:
      'Automate document collection, expiry checks, and reminders in one recruitment document control workflow.',
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
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">Feature</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Document Control for Recruitment Operations</h1>
          <p className="mt-3 text-sm text-slate-600">
            Keep candidate files complete and valid with clear statuses, reminders, and shared visibility for teams.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary">Start free trial</Link>
            <Link to="/pricing" className="btn-secondary">View pricing</Link>
          </div>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Why teams need this</h2>
          <p className="mt-2 text-sm text-slate-700">
            Manual tracking of passports, permits, and certificates creates risk and delays. HostFlow organizes required
            documents by workflow stage and alerts users before issues become blockers.
          </p>
        </section>

        <section className="cv-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Workflow outcome</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>Standardized checklist for required files.</li>
            <li>Automatic status updates for missing/received/approved/expired documents.</li>
            <li>Reminder operations linked to candidate and owner context.</li>
            <li>Faster onboarding with less manual coordination.</li>
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
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm">Candidate pipeline</Link>
            <Link to="/use-cases/high-volume-onboarding" className="btn-secondary btn-sm">High-volume onboarding</Link>
            <Link to="/use-cases/trucking-recruitment" className="btn-secondary btn-sm">Trucking recruitment use-case</Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
