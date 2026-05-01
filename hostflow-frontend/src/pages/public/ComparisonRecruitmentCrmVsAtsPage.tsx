import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function ComparisonRecruitmentCrmVsAtsPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'comparison', pageKey: 'recruitment_crm_vs_ats' })
  const faq = [
    {
      q: t('public.marketing.comparison_recruitment_crm_vs_ats.faq.q1.q', { defaultValue: 'Is ATS enough for operational recruiting teams?' }),
      a: t('public.marketing.comparison_recruitment_crm_vs_ats.faq.q1.a', { defaultValue: 'ATS is strong for application tracking, but daily recruitment operations often need deeper workflow ownership and follow-up tooling.' }),
    },
    {
      q: t('public.marketing.comparison_recruitment_crm_vs_ats.faq.q2.q', { defaultValue: 'Can CRM and ATS coexist?' }),
      a: t('public.marketing.comparison_recruitment_crm_vs_ats.faq.q2.a', { defaultValue: 'Yes. Many teams use CRM for operations and ATS for broader hiring records, depending on process maturity.' }),
    },
    {
      q: t('public.marketing.comparison_recruitment_crm_vs_ats.faq.q3.q', { defaultValue: 'What if we start without ATS integration?' }),
      a: t('public.marketing.comparison_recruitment_crm_vs_ats.faq.q3.a', { defaultValue: 'You can start with CRM-first workflow and add integrations later when process baseline is stable.' }),
    },
  ]

  useSeoMeta({
    title: t('public.marketing.comparison_recruitment_crm_vs_ats.seo.title', { defaultValue: 'Recruitment CRM vs ATS Comparison' }),
    description: t(
      'public.marketing.comparison_recruitment_crm_vs_ats.seo.description',
      { defaultValue: 'Understand when a recruitment CRM outperforms ATS-only setup for operational pipeline, documents, and team coordination.' },
    ),
    canonicalPath: '/comparison/recruitment-crm-vs-ats',
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
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{t('public.marketing.comparison_recruitment_crm_vs_ats.hero.badge', { defaultValue: 'Comparison' })}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">{t('public.marketing.comparison_recruitment_crm_vs_ats.hero.title', { defaultValue: 'Recruitment CRM vs ATS' })}</h1>
          <p className="mt-3 text-sm text-slate-600">
            {t('public.marketing.comparison_recruitment_crm_vs_ats.hero.subtitle', { defaultValue: 'Compare where ATS helps and where CRM-driven operations improve execution speed for active recruiting teams.' })}
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
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.comparison_recruitment_crm_vs_ats.decision.title', { defaultValue: 'Decision lens' })}</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
            <li>{t('public.marketing.comparison_recruitment_crm_vs_ats.decision.items.1', { defaultValue: 'Use ATS when application intake and hiring administration are central.' })}</li>
            <li>{t('public.marketing.comparison_recruitment_crm_vs_ats.decision.items.2', { defaultValue: 'Use CRM when operational throughput, ownership, and multi-step follow-up are critical.' })}</li>
            <li>{t('public.marketing.comparison_recruitment_crm_vs_ats.decision.items.3', { defaultValue: 'Blend both when your process needs operational control and broader HR stack compatibility.' })}</li>
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
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.comparison_recruitment_crm_vs_ats.related.title', { defaultValue: 'Related pages' })}</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <Link to="/comparison/hostflow-vs-spreadsheets" className="btn-secondary btn-sm" onClick={() => trackCta('related_vs_spreadsheets', '/comparison/hostflow-vs-spreadsheets')}>
              {t('public.marketing.common.related.hostflow_vs_spreadsheets', { defaultValue: 'HostFlow vs spreadsheets' })}
            </Link>
            <Link to="/features/candidate-pipeline" className="btn-secondary btn-sm" onClick={() => trackCta('related_pipeline', '/features/candidate-pipeline')}>
              {t('public.marketing.common.related.candidate_pipeline', { defaultValue: 'Candidate pipeline' })}
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
