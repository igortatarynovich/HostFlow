import { Link, Navigate, useParams } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'
import {
  docsLocaleFromApp,
  getDocsArticle,
  type DocsArticle,
  type DocsLocale,
} from '../../content/docs/docsCatalog'

export default function DocsArticlePage() {
  const { slug = '' } = useParams<{ slug: string }>()
  const article = getDocsArticle(slug)

  if (!article) {
    return <Navigate to="/docs" replace />
  }

  return <DocsArticleView article={article} />
}

function DocsArticleView({ article }: { article: DocsArticle }) {
  const { t, locale } = useI18n()
  const loc = docsLocaleFromApp(locale) as DocsLocale
  const { trackCta } = useSeoTracking({ pageType: 'docs', pageKey: article.slug })

  useSeoMeta({
    title: article.seoTitle[loc],
    description: article.seoDescription[loc],
    canonicalPath: `/docs/${article.slug}`,
  })

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-8">
        <section className="card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {article.category[loc]}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">{article.title[loc]}</h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600 sm:text-base">{article.summary[loc]}</p>
          <p className="mt-2 text-xs text-slate-500">
            {t('public.docs.minutes', {
              defaultValue: '{n} min read',
              values: { n: article.minutes },
            })}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/docs" className="btn-secondary" onClick={() => trackCta('article_docs_hub', '/docs')}>
              {t('public.docs.all_docs', { defaultValue: 'All docs' })}
            </Link>
            <Link
              to={article.relatedFaq}
              className="btn-secondary"
              onClick={() => trackCta('article_faq', article.relatedFaq)}
            >
              {t('public.docs.related_faq', { defaultValue: 'Related FAQ' })}
            </Link>
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('article_signup', '/signup')}>
              {t('public.docs.cta_signup', { defaultValue: 'Create account' })}
            </Link>
          </div>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.docs.steps_title', { defaultValue: 'Steps' })}
          </h2>
          <ol className="mt-4 space-y-4">
            {article.steps.map((step, index) => (
              <li key={step.title.en} className="rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">
                  <span className="mr-2 text-brand-700">{index + 1}.</span>
                  {step.title[loc]}
                </p>
                <p className="mt-1 text-sm leading-relaxed text-slate-700">{step.body[loc]}</p>
              </li>
            ))}
          </ol>
        </section>

        {article.relatedSlugs.length > 0 ? (
          <section className="card cv-auto p-6">
            <h2 className="text-xl font-semibold text-slate-900">
              {t('public.docs.related_title', { defaultValue: 'Related guides' })}
            </h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {article.relatedSlugs.map((related) => (
                <Link
                  key={related}
                  to={`/docs/${related}`}
                  className="btn-secondary btn-sm"
                  onClick={() => trackCta(`related_${related}`, `/docs/${related}`)}
                >
                  {getDocsArticle(related)?.title[loc] ?? related}
                </Link>
              ))}
              <Link
                to="/academy"
                className="btn-secondary btn-sm"
                onClick={() => trackCta('related_academy', '/academy')}
              >
                {t('public.docs.cta_academy', { defaultValue: 'Academy' })}
              </Link>
            </div>
          </section>
        ) : null}

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
