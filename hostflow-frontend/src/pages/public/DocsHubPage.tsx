import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'
import { docsCategories, docsLocaleFromApp } from '../../content/docs/docsCatalog'

export default function DocsHubPage() {
  const { t, locale } = useI18n()
  const loc = docsLocaleFromApp(locale)
  const { trackCta } = useSeoTracking({ pageType: 'docs', pageKey: 'hub' })
  const categories = docsCategories(loc)

  useSeoMeta({
    title: t('public.docs.seo.title', {
      defaultValue: 'HostFlow Docs — get to first hire without support',
    }),
    description: t('public.docs.seo.description', {
      defaultValue:
        'How-to guides for signup, company setup, Meta, vacancies, leads, candidates, and documents.',
    }),
    canonicalPath: '/docs',
  })

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-8">
        <section className="card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('public.docs.badge', { defaultValue: 'Docs' })}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.docs.title', { defaultValue: 'How to use HostFlow' })}
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600 sm:text-base">
            {t('public.docs.subtitle', {
              defaultValue:
                'Short how-tos for the Success Path — from company setup to first candidate contact.',
            })}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('docs_signup', '/signup')}>
              {t('public.docs.cta_signup', { defaultValue: 'Create account' })}
            </Link>
            <Link to="/academy" className="btn-secondary" onClick={() => trackCta('docs_academy', '/academy')}>
              {t('public.docs.cta_academy', { defaultValue: 'Academy' })}
            </Link>
            <Link to="/faq" className="btn-secondary" onClick={() => trackCta('docs_faq', '/faq')}>
              {t('public.docs.cta_faq', { defaultValue: 'FAQ' })}
            </Link>
          </div>
        </section>

        {categories.map((category) => (
          <section key={category.id} className="card cv-auto p-6">
            <h2 className="text-xl font-semibold text-slate-900">{category.title}</h2>
            <ul className="mt-4 space-y-3">
              {category.articles.map((article) => (
                <li key={article.slug}>
                  <Link
                    to={`/docs/${article.slug}`}
                    className="block rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3 transition hover:border-brand-200 hover:bg-white"
                    onClick={() => trackCta(`docs_card_${article.slug}`, `/docs/${article.slug}`)}
                  >
                    <span className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="text-sm font-semibold text-slate-900">{article.title[loc]}</span>
                      <span className="text-xs text-slate-500">
                        {t('public.docs.minutes', {
                          defaultValue: '{n} min',
                          values: { n: article.minutes },
                        })}
                      </span>
                    </span>
                    <span className="mt-1 block text-sm text-slate-600">{article.summary[loc]}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}

        <section className="rounded-xl border border-brand-200 bg-brand-50/60 p-6 text-center">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('public.docs.still_title', { defaultValue: 'Prefer short lessons?' })}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.docs.still_body', {
              defaultValue: 'Academy lists the same Success Path as 2–8 minute lessons.',
            })}
          </p>
          <Link
            to="/academy"
            className="btn-primary mt-4 inline-flex"
            onClick={() => trackCta('docs_footer_academy', '/academy')}
          >
            {t('public.docs.cta_academy', { defaultValue: 'Open Academy' })}
          </Link>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
