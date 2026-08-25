import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'
import {
  FAQ_SECTIONS,
  faqLocaleFromApp,
  flattenFaqItems,
} from '../../content/faq/faqCatalog'

export default function FaqPage() {
  const { t, locale } = useI18n()
  const location = useLocation()
  const faqLocale = faqLocaleFromApp(locale)
  const { trackCta } = useSeoTracking({ pageType: 'faq', pageKey: 'hub' })
  const [query, setQuery] = useState('')

  const hashSection = (location.hash || '').replace(/^#/, '')

  const filteredSections = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return FAQ_SECTIONS
    return FAQ_SECTIONS.map((section) => ({
      ...section,
      items: section.items.filter((item) => {
        const hay = `${item.q[faqLocale]} ${item.a[faqLocale]}`.toLowerCase()
        return hay.includes(q)
      }),
    })).filter((section) => section.items.length > 0)
  }, [faqLocale, query])

  const structuredFaq = useMemo(() => flattenFaqItems(FAQ_SECTIONS).slice(0, 40), [])

  useSeoMeta({
    title: t('public.faq.seo.title', {
      defaultValue: 'HostFlow FAQ — setup, Meta, recruitment, billing',
    }),
    description: t('public.faq.seo.description', {
      defaultValue:
        'Answers for getting started, Meta ads, WhatsApp, vacancies, documents, billing, security, and API — so you can hire without waiting on support.',
    }),
    canonicalPath: '/faq',
    structuredData: {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: structuredFaq.map((item) => ({
        '@type': 'Question',
        name: item.q.en,
        acceptedAnswer: { '@type': 'Answer', text: item.a.en },
      })),
    },
  })

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-8">
        <section className="card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('public.faq.badge', { defaultValue: 'Help' })}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.faq.title', { defaultValue: 'Frequently asked questions' })}
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600 sm:text-base">
            {t('public.faq.subtitle', {
              defaultValue:
                'From signup to first hire — clear answers so you can move without waiting on support.',
            })}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              to="/signup"
              className="btn-primary"
              onClick={() => trackCta('faq_signup', '/signup')}
            >
              {t('public.faq.cta_signup', { defaultValue: 'Start free setup' })}
            </Link>
            <Link
              to="/pricing"
              className="btn-secondary"
              onClick={() => trackCta('faq_pricing', '/pricing')}
            >
              {t('public.faq.cta_pricing', { defaultValue: 'View pricing' })}
            </Link>
            <Link
              to="/docs"
              className="btn-secondary"
              onClick={() => trackCta('faq_docs', '/docs')}
            >
              {t('public.faq.cta_docs', { defaultValue: 'Docs' })}
            </Link>
            <Link
              to="/academy"
              className="btn-secondary"
              onClick={() => trackCta('faq_academy', '/academy')}
            >
              {t('public.faq.cta_academy', { defaultValue: 'Academy' })}
            </Link>
            <Link
              to="/demo"
              className="btn-secondary"
              onClick={() => trackCta('faq_demo', '/demo')}
            >
              {t('public.faq.cta_demo', { defaultValue: 'Interactive demo' })}
            </Link>
          </div>
          <label className="mt-6 block">
            <span className="sr-only">{t('public.faq.search_label', { defaultValue: 'Search FAQ' })}</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('public.faq.search_placeholder', {
                defaultValue: 'Search questions…',
              })}
              className="input w-full max-w-xl rounded-xl border-slate-200 bg-white py-2.5 text-sm shadow-sm"
            />
          </label>
        </section>

        <nav
          className="flex flex-wrap gap-2"
          aria-label={t('public.faq.sections_aria', { defaultValue: 'FAQ sections' })}
        >
          {FAQ_SECTIONS.map((section) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                hashSection === section.id
                  ? 'border-brand-400 bg-brand-50 text-brand-800'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
              }`}
            >
              {section.title[faqLocale]}
            </a>
          ))}
        </nav>

        {filteredSections.length === 0 ? (
          <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
            {t('public.faq.no_results', { defaultValue: 'No questions match your search.' })}
          </p>
        ) : null}

        {filteredSections.map((section) => (
          <section
            key={section.id}
            id={section.id}
            className="scroll-mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <h2 className="text-xl font-semibold text-slate-900">{section.title[faqLocale]}</h2>
            <div className="mt-4 space-y-2">
              {section.items.map((item) => (
                <details
                  key={item.id}
                  id={`${section.id}-${item.id}`}
                  className="group rounded-xl border border-slate-100 bg-slate-50/80 open:bg-white open:shadow-sm"
                >
                  <summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold text-slate-900 marker:content-none [&::-webkit-details-marker]:hidden">
                    {item.q[faqLocale]}
                  </summary>
                  <p className="border-t border-slate-100 px-4 py-3 text-sm leading-relaxed text-slate-700">
                    {item.a[faqLocale]}
                  </p>
                </details>
              ))}
            </div>
          </section>
        ))}

        <section className="rounded-xl border border-brand-200 bg-brand-50/60 p-6 text-center">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('public.faq.still_title', { defaultValue: 'Ready to try it?' })}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.faq.still_body', {
              defaultValue: 'Create a workspace and follow the single next step on screen.',
            })}
          </p>
          <Link
            to="/signup"
            className="btn-primary mt-4 inline-flex"
            onClick={() => trackCta('faq_footer_signup', '/signup')}
          >
            {t('public.faq.cta_signup', { defaultValue: 'Start free setup' })}
          </Link>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
