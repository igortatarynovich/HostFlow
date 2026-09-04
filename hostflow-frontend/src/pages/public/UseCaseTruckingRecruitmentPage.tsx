import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

export default function UseCaseTruckingRecruitmentPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'use_case', pageKey: 'trucking_recruitment' })

  const whyItems = [0, 1, 2, 3].map((i) => t(`public.marketing.use_case_trucking_recruitment.why.items.${i}`))
  const driverData = [0, 1, 2, 3, 4, 5].map((i) => ({
    title: t(`public.marketing.use_case_trucking_recruitment.driver_data.items.${i}.title`),
    body: t(`public.marketing.use_case_trucking_recruitment.driver_data.items.${i}.body`),
  }))
  const workflow = [0, 1, 2, 3, 4].map((i) => ({
    title: t(`public.marketing.use_case_trucking_recruitment.workflow.steps.${i}.title`),
    body: t(`public.marketing.use_case_trucking_recruitment.workflow.steps.${i}.body`),
  }))
  const docStatuses = [0, 1, 2, 3].map((i) => t(`public.marketing.use_case_trucking_recruitment.documents.statuses.${i}`))
  const boundaryItems = [0, 1, 2, 3].map((i) => t(`public.marketing.use_case_trucking_recruitment.boundary.items.${i}`))
  const faq = [0, 1, 2, 3].map((i) => ({
    q: t(`public.marketing.use_case_trucking_recruitment.faq.items.${i}.q`),
    a: t(`public.marketing.use_case_trucking_recruitment.faq.items.${i}.a`),
  }))

  useSeoMeta({
    title: t('public.marketing.use_case_trucking_recruitment.seo.title', {
      defaultValue: 'Driver Recruitment for Transport Companies | HostFlow',
    }),
    description: t('public.marketing.use_case_trucking_recruitment.seo.description', {
      defaultValue:
        'Manage driver candidates, licence and document context, ownership and recruitment pipelines in one system built for transport operations.',
    }),
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
        <section className="card space-y-5 p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('public.marketing.use_case_trucking_recruitment.hero.badge')}
          </p>
          <div className="space-y-3">
            <h1 className="text-balance text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              {t('public.marketing.use_case_trucking_recruitment.hero.title')}
            </h1>
            <p className="text-lg font-medium text-slate-800 sm:text-xl">
              {t('public.marketing.use_case_trucking_recruitment.hero.subtitle')}
            </p>
            <p className="max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base">
              {t('public.marketing.use_case_trucking_recruitment.hero.lead')}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('primary_signup', '/signup')}>
              {t('public.marketing.use_case_trucking_recruitment.cta.start_trial')}
            </Link>
            <Link to="/demo" className="btn-secondary" onClick={() => trackCta('secondary_demo', '/demo')}>
              {t('public.marketing.use_case_trucking_recruitment.cta.explore_demo')}
            </Link>
            <Link to="/pricing" className="btn-secondary" onClick={() => trackCta('secondary_pricing', '/pricing')}>
              {t('public.marketing.common.cta.view_pricing')}
            </Link>
          </div>
        </section>

        <section className="card cv-auto space-y-4 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl">
            {t('public.marketing.use_case_trucking_recruitment.why.title')}
          </h2>
          <p className="text-base font-medium text-slate-800">
            {t('public.marketing.use_case_trucking_recruitment.why.lead')}
          </p>
          <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.why.body')}
          </p>
          <ul className="grid gap-3 sm:grid-cols-2">
            {whyItems.map((item) => (
              <li key={item} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm leading-relaxed text-slate-700">
                {item}
              </li>
            ))}
          </ul>
          <p className="text-sm font-semibold leading-relaxed text-slate-900 sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.why.closing')}
          </p>
        </section>

        <section className="card cv-auto space-y-5 p-6 sm:p-8">
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl">
              {t('public.marketing.use_case_trucking_recruitment.driver_data.title')}
            </h2>
            <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
              {t('public.marketing.use_case_trucking_recruitment.driver_data.lead')}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {driverData.map((item) => (
              <article key={item.title} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-4">
                <h3 className="text-sm font-semibold text-slate-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{item.body}</p>
              </article>
            ))}
          </div>
          <p className="text-sm leading-relaxed text-slate-600">
            {t('public.marketing.use_case_trucking_recruitment.driver_data.note')}
          </p>
        </section>

        <section className="card cv-auto space-y-5 p-6 sm:p-8">
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl">
              {t('public.marketing.use_case_trucking_recruitment.workflow.title')}
            </h2>
            <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
              {t('public.marketing.use_case_trucking_recruitment.workflow.lead')}
            </p>
          </div>
          <ol className="grid gap-3 md:grid-cols-5">
            {workflow.map((step, idx) => (
              <li key={step.title} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-4">
                <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">0{idx + 1}</p>
                <h3 className="mt-2 text-sm font-semibold text-slate-900">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="card cv-auto space-y-4 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl">
            {t('public.marketing.use_case_trucking_recruitment.documents.title')}
          </h2>
          <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.documents.lead')}
          </p>
          <ul className="flex flex-wrap gap-2">
            {docStatuses.map((status) => (
              <li
                key={status}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-700"
              >
                {status}
              </li>
            ))}
          </ul>
          <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.documents.body')}
          </p>
        </section>

        <section className="card cv-auto space-y-4 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl">
            {t('public.marketing.use_case_trucking_recruitment.team.title')}
          </h2>
          <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.team.body')}
          </p>
          <p className="text-sm font-medium leading-relaxed text-slate-800 sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.team.distribution')}
          </p>
        </section>

        <section className="card cv-auto space-y-4 border-slate-200 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl">
            {t('public.marketing.use_case_trucking_recruitment.boundary.title')}
          </h2>
          <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.boundary.lead')}
          </p>
          <ul className="space-y-2">
            {boundaryItems.map((item) => (
              <li key={item} className="flex gap-2 text-sm leading-relaxed text-slate-700">
                <span className="mt-0.5 font-semibold text-slate-400" aria-hidden>
                  —
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card cv-auto space-y-4 bg-slate-900 p-6 text-white sm:p-8">
          <h2 className="text-xl font-semibold sm:text-2xl">
            {t('public.marketing.use_case_trucking_recruitment.platform.title')}
          </h2>
          <p className="text-sm leading-relaxed text-slate-300 sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.platform.body')}
          </p>
          <p className="text-sm font-semibold text-[#B8FFF3] sm:text-base">
            {t('public.marketing.use_case_trucking_recruitment.platform.closing')}
          </p>
        </section>

        <section className="card cv-auto space-y-4 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.marketing.common.faq')}</h2>
          <div className="space-y-3">
            {faq.map((item) => (
              <article key={item.q} className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-900">{item.q}</h3>
                <p className="mt-1 text-sm leading-relaxed text-slate-700">{item.a}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="cv-auto space-y-5 rounded-xl border border-brand-200 bg-brand-50/60 p-6 sm:p-8">
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-slate-900 sm:text-2xl">
              {t('public.marketing.use_case_trucking_recruitment.final_cta.title')}
            </h2>
            <p className="text-sm leading-relaxed text-slate-700 sm:text-base">
              {t('public.marketing.use_case_trucking_recruitment.final_cta.body')}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('final_signup', '/signup')}>
              {t('public.marketing.use_case_trucking_recruitment.cta.start_trial')}
            </Link>
            <Link to="/demo" className="btn-secondary" onClick={() => trackCta('final_demo', '/demo')}>
              {t('public.marketing.use_case_trucking_recruitment.cta.explore_demo')}
            </Link>
          </div>
          <div className="border-t border-brand-200/80 pt-4">
            <p className="text-sm font-semibold text-slate-900">
              {t('public.marketing.use_case_trucking_recruitment.related.title')}
            </p>
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              <Link
                to="/"
                className="btn-secondary btn-sm"
                onClick={() => trackCta('related_home', '/')}
              >
                {t('public.marketing.use_case_trucking_recruitment.related.home')}
              </Link>
              <Link
                to="/features/document-control"
                className="btn-secondary btn-sm"
                onClick={() => trackCta('related_document_control', '/features/document-control')}
              >
                {t('public.marketing.common.related.document_control')}
              </Link>
              <Link
                to="/features/candidate-pipeline"
                className="btn-secondary btn-sm"
                onClick={() => trackCta('related_pipeline', '/features/candidate-pipeline')}
              >
                {t('public.marketing.common.related.candidate_pipeline')}
              </Link>
            </div>
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
