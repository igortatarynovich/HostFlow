import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function ComparisonHostflowVsSpreadsheetsPage() {
  const { trackCta } = useSeoTracking({ pageType: 'comparison', pageKey: 'hostflow_vs_spreadsheets' })
  const faq = [
    {
      q: 'Can spreadsheets still work for early stage teams?',
      a: 'They can for very low volume, but coordination overhead grows quickly when pipeline and documents scale.',
    },
    {
      q: 'What is the biggest operational gain from CRM migration?',
      a: 'Single-source workflow ownership and reminders, which removes hidden blockers from manual tracking.',
    },
    {
      q: 'Do we need a long implementation project?',
      a: 'No. Teams can start with baseline onboarding and move active work immediately.',
    },
  ]

  useSeoMeta({
    title: 'HostFlow vs Spreadsheets for Recruitment',
    description:
      'Compare HostFlow CRM with spreadsheet-based recruitment operations across speed, visibility, and onboarding control.',
    canonicalPath: '/comparison/hostflow-vs-spreadsheets',
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
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">Comparison</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">HostFlow vs Spreadsheets for Recruitment Ops</h1>
          <p className="mt-3 text-sm text-slate-600">
            A practical comparison for teams deciding whether to keep manual spreadsheets or switch to an operational CRM.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('primary_signup', '/signup')}>Start free trial</Link>
            <Link to="/pricing" className="btn-secondary" onClick={() => trackCta('secondary_pricing', '/pricing')}>View pricing</Link>
          </div>
        </section>

        <section className="cv-auto overflow-x-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Side-by-side overview</h2>
          <table className="mt-3 min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                <th className="px-3 py-2 text-left">Area</th>
                <th className="px-3 py-2 text-left">Spreadsheets</th>
                <th className="px-3 py-2 text-left">HostFlow</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2">Pipeline visibility</td>
                <td className="px-3 py-2">Manual updates, fragmented ownership</td>
                <td className="px-3 py-2">Shared stage flow with clear owners</td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2">Document control</td>
                <td className="px-3 py-2">Separate trackers and reminders</td>
                <td className="px-3 py-2">Unified statuses and due-date reminders</td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2">Scaling team operations</td>
                <td className="px-3 py-2">Coordination overhead grows quickly</td>
                <td className="px-3 py-2">Role-aware workflow and audit trail</td>
              </tr>
            </tbody>
          </table>
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
          <h2 className="text-xl font-semibold text-slate-900">Related pages</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Link to="/comparison/recruitment-crm-vs-ats" className="btn-secondary btn-sm" onClick={() => trackCta('related_crm_vs_ats', '/comparison/recruitment-crm-vs-ats')}>Recruitment CRM vs ATS</Link>
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm" onClick={() => trackCta('related_pipeline', '/features/candidate-pipeline')}>Candidate pipeline</Link>
            <Link to="/features/document-control" className="btn-secondary btn-sm" onClick={() => trackCta('related_documents', '/features/document-control')}>Document control</Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
