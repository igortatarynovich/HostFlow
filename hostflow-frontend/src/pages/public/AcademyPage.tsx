import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'
import { ACADEMY_LESSONS, academyLocaleFromApp } from '../../content/docs/academyCatalog'

export default function AcademyPage() {
  const { t, locale } = useI18n()
  const loc = academyLocaleFromApp(locale)
  const { trackCta } = useSeoTracking({ pageType: 'academy', pageKey: 'hub' })

  useSeoMeta({
    title: t('public.academy.seo.title', {
      defaultValue: 'HostFlow Academy — short lessons to first hire',
    }),
    description: t('public.academy.seo.description', {
      defaultValue:
        '2–8 minute lessons for company setup, Meta, vacancies, leads, candidates, and documents. Full steps live in Docs.',
    }),
    canonicalPath: '/academy',
  })

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-8">
        <section className="card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('public.academy.badge', { defaultValue: 'Academy' })}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.academy.title', { defaultValue: 'Learn HostFlow in short lessons' })}
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600 sm:text-base">
            {t('public.academy.subtitle', {
              defaultValue:
                'Each lesson maps to a Success Path how-to. Video embeds land here when ready — steps are already in Docs.',
            })}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/docs" className="btn-primary" onClick={() => trackCta('academy_docs', '/docs')}>
              {t('public.academy.cta_docs', { defaultValue: 'Open Docs' })}
            </Link>
            <Link to="/signup" className="btn-secondary" onClick={() => trackCta('academy_signup', '/signup')}>
              {t('public.academy.cta_signup', { defaultValue: 'Start free setup' })}
            </Link>
            <Link to="/faq" className="btn-secondary" onClick={() => trackCta('academy_faq', '/faq')}>
              {t('public.academy.cta_faq', { defaultValue: 'FAQ' })}
            </Link>
          </div>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.academy.lessons_title', { defaultValue: 'Lessons' })}
          </h2>
          <ul className="mt-4 space-y-3">
            {ACADEMY_LESSONS.map((lesson, index) => {
              const href = `/docs/${lesson.docsSlug}`
              return (
                <li
                  key={lesson.id}
                  className="rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        <span className="mr-2 text-brand-700">{index + 1}.</span>
                        {lesson.title[loc]}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">{lesson.summary[loc]}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {t('public.academy.minutes', {
                          defaultValue: '~{n} min',
                          values: { n: lesson.minutes },
                        })}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link
                        to={href}
                        className="btn-secondary btn-sm"
                        onClick={() => trackCta(`lesson_${lesson.id}`, href)}
                      >
                        {t('public.academy.open_guide', { defaultValue: 'Open guide' })}
                      </Link>
                      {lesson.videoUrl ? (
                        <a
                          href={lesson.videoUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="btn-secondary btn-sm"
                          onClick={() => trackCta(`lesson_video_${lesson.id}`, lesson.videoUrl!)}
                        >
                          {t('public.academy.watch_video', { defaultValue: 'Watch video' })}
                        </a>
                      ) : (
                        <span className="inline-flex items-center rounded-lg border border-dashed border-slate-200 px-3 py-1.5 text-xs text-slate-500">
                          {t('public.academy.video_soon', { defaultValue: 'Video soon' })}
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="rounded-xl border border-brand-200 bg-brand-50/60 p-6 text-center">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('public.academy.still_title', { defaultValue: 'Ready to practice in product?' })}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.academy.still_body', {
              defaultValue: 'Create a workspace and follow the single next step on screen.',
            })}
          </p>
          <Link
            to="/signup"
            className="btn-primary mt-4 inline-flex"
            onClick={() => trackCta('academy_footer_signup', '/signup')}
          >
            {t('public.academy.cta_signup', { defaultValue: 'Start free setup' })}
          </Link>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
