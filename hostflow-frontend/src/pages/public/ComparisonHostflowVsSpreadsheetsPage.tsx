import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function ComparisonHostflowVsSpreadsheetsPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'comparison', pageKey: 'hostflow_vs_spreadsheets' })
  const faq = [
    {
      q: t('public.marketing.comparison_hostflow_vs_spreadsheets.faq.q1.q', { defaultValue: 'Can spreadsheets still work for early stage teams?' }),
      a: t('public.marketing.comparison_hostflow_vs_spreadsheets.faq.q1.a', { defaultValue: 'They can for very low volume, but coordination overhead grows quickly when pipeline and documents scale.' }),
    },
    {
      q: t('public.marketing.comparison_hostflow_vs_spreadsheets.faq.q2.q', { defaultValue: 'What is the biggest operational gain from CRM migration?' }),
      a: t('public.marketing.comparison_hostflow_vs_spreadsheets.faq.q2.a', { defaultValue: 'Single-source workflow ownership and reminders, which removes hidden blockers from manual tracking.' }),
    },
    {
      q: t('public.marketing.comparison_hostflow_vs_spreadsheets.faq.q3.q', { defaultValue: 'Do we need a long implementation project?' }),
      a: t('public.marketing.comparison_hostflow_vs_spreadsheets.faq.q3.a', { defaultValue: 'No. Teams can start with baseline onboarding and move active work immediately.' }),
    },
  ]

  useSeoMeta({
    title: t('public.marketing.comparison_hostflow_vs_spreadsheets.seo.title', { defaultValue: 'HostFlow vs Spreadsheets for Recruitment' }),
    description: t(
      'public.marketing.comparison_hostflow_vs_spreadsheets.seo.description',
      { defaultValue: 'Compare HostFlow CRM with spreadsheet-based recruitment operations across speed, visibility, and onboarding control.' },
    ),
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
    <PublicPageShell maxWidth="5xl" variant="marketing">
      <div className="space-y-8">
        <section className="card p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{t('public.marketing.comparison_hostflow_vs_spreadsheets.hero.badge', { defaultValue: 'Comparison' })}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.marketing.comparison_hostflow_vs_spreadsheets.hero.title', { defaultValue: 'HostFlow vs Spreadsheets for Recruitment Ops' })}
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            {t('public.marketing.comparison_hostflow_vs_spreadsheets.hero.subtitle', { defaultValue: 'A practical comparison for teams deciding whether to keep manual spreadsheets or switch to an operational CRM.' })}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('primary_signup', '/signup')}>
              {t('public.marketing.common.cta.start_trial', { defaultValue: 'Create account' })}
            </Link>
            <Link to="/pricing" className="btn-secondary" onClick={() => trackCta('secondary_pricing', '/pricing')}>
              {t('public.marketing.common.cta.view_pricing', { defaultValue: 'View pricing' })}
            </Link>
          </div>
        </section>

        <section className="card cv-auto overflow-x-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.title', { defaultValue: 'Side-by-side overview' })}
          </h2>
          <table className="mt-3 min-w-full text-sm">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                <th className="px-3 py-2 text-left">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.columns.area', { defaultValue: 'Area' })}</th>
                <th className="px-3 py-2 text-left">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.columns.spreadsheets', { defaultValue: 'Spreadsheets' })}</th>
                <th className="px-3 py-2 text-left">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.columns.hostflow', { defaultValue: 'HostFlow' })}</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.pipeline.area', { defaultValue: 'Pipeline visibility' })}</td>
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.pipeline.spreadsheets', { defaultValue: 'Manual updates, fragmented ownership' })}</td>
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.pipeline.hostflow', { defaultValue: 'Shared stage flow with clear owners' })}</td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.documents.area', { defaultValue: 'Document control' })}</td>
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.documents.spreadsheets', { defaultValue: 'Separate trackers and reminders' })}</td>
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.documents.hostflow', { defaultValue: 'Unified statuses and due-date reminders' })}</td>
              </tr>
              <tr className="border-t border-slate-100">
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.scaling.area', { defaultValue: 'Scaling team operations' })}</td>
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.scaling.spreadsheets', { defaultValue: 'Coordination overhead grows quickly' })}</td>
                <td className="px-3 py-2">{t('public.marketing.comparison_hostflow_vs_spreadsheets.overview.rows.scaling.hostflow', { defaultValue: 'Role-aware workflow and audit trail' })}</td>
              </tr>
            </tbody>
          </table>
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
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.comparison_hostflow_vs_spreadsheets.related.title', { defaultValue: 'Related pages' })}</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Link to="/comparison/recruitment-crm-vs-ats" className="btn-secondary btn-sm" onClick={() => trackCta('related_crm_vs_ats', '/comparison/recruitment-crm-vs-ats')}>
              {t('public.marketing.common.related.crm_vs_ats', { defaultValue: 'Recruitment CRM vs ATS' })}
            </Link>
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm" onClick={() => trackCta('related_pipeline', '/features/candidate-pipeline')}>
              {t('public.marketing.common.related.candidate_pipeline', { defaultValue: 'Candidate pipeline' })}
            </Link>
            <Link to="/features/document-control" className="btn-secondary btn-sm" onClick={() => trackCta('related_documents', '/features/document-control')}>
              {t('public.marketing.common.related.document_control', { defaultValue: 'Document control' })}
            </Link>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
