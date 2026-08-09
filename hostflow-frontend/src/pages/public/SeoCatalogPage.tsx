import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'
import {
  getSeoPageById,
  seoLocaleFromApp,
  type SeoPageDefinition,
} from '../../content/seo/seoPageCatalog'

type SeoCatalogPageProps = {
  pageId: string
}

export default function SeoCatalogPage({ pageId }: SeoCatalogPageProps) {
  const { t, locale } = useI18n()
  const page = getSeoPageById(pageId)
  const loc = seoLocaleFromApp(locale)

  if (!page) {
    return (
      <PublicPageShell>
        <p className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
          {t('public.seo.missing_page', { defaultValue: 'This page is not in the SEO catalog.' })}
        </p>
      </PublicPageShell>
    )
  }

  return <SeoCatalogPageView page={page} locale={loc} />
}

function SeoCatalogPageView({
  page,
  locale,
}: {
  page: SeoPageDefinition
  locale: 'en' | 'ru' | 'pl'
}) {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: page.pageType, pageKey: page.id })

  const faq = page.faq.map((item) => ({
    q: item.q[locale],
    a: item.a[locale],
  }))

  useSeoMeta({
    title: page.seoTitle[locale],
    description: page.seoDescription[locale],
    canonicalPath: page.path,
    structuredData: {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: page.faq.map((item) => ({
        '@type': 'Question',
        name: item.q.en,
        acceptedAnswer: { '@type': 'Answer', text: item.a.en },
      })),
    },
  })

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-8">
        <section className="card p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{page.badge[locale]}</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">{page.h1[locale]}</h1>
          <p className="mt-3 max-w-3xl text-sm text-slate-600 sm:text-base">{page.subtitle[locale]}</p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('primary_signup', '/signup')}>
              {t('public.marketing.common.cta.start_trial', { defaultValue: 'Create account' })}
            </Link>
            <Link to="/pricing" className="btn-secondary" onClick={() => trackCta('secondary_pricing', '/pricing')}>
              {t('public.marketing.common.cta.view_pricing', { defaultValue: 'View pricing' })}
            </Link>
            <Link to="/faq" className="btn-secondary" onClick={() => trackCta('secondary_faq', '/faq')}>
              {t('public.marketing.common.related.faq', { defaultValue: 'FAQ' })}
            </Link>
          </div>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{page.problemTitle[locale]}</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
            {page.problemItems.map((item) => (
              <li key={item.en}>{item[locale]}</li>
            ))}
          </ul>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{page.solutionTitle[locale]}</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">{page.solutionBody[locale]}</p>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">{page.flowTitle[locale]}</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-700">
            {page.flowItems.map((item) => (
              <li key={item.en}>{item[locale]}</li>
            ))}
          </ol>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.marketing.common.faq', { defaultValue: 'FAQ' })}
          </h2>
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
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.seo.related_title', { defaultValue: 'Related pages' })}
          </h2>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            {page.related.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className="btn-secondary btn-sm"
                onClick={() => trackCta(`related_${link.path}`, link.path)}
              >
                {link.label[locale]}
              </Link>
            ))}
          </div>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
