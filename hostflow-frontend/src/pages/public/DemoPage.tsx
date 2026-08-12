import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

const TRY_ITEMS = ['vacancy', 'leads', 'candidates', 'documents'] as const
const STEPS = ['signup', 'company', 'seed', 'explore'] as const

export default function DemoPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'landing', pageKey: 'demo' })

  useSeoMeta({
    title: t('public.demo.seo.title'),
    description: t('public.demo.seo.description'),
    canonicalPath: '/demo',
  })

  return (
    <PublicPageShell maxWidth="5xl" variant="marketing">
      <div className="space-y-8">
        <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2E6F74]">
            {t('public.demo.badge')}
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            {t('public.demo.title')}
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
            {t('public.demo.subtitle')}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/signup"
              onClick={() => trackCta('demo_signup', '/signup')}
              className="inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-5 py-2.5 text-sm font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
            >
              {t('public.demo.cta_signup')}
            </Link>
            <Link
              to="/login"
              onClick={() => trackCta('demo_login', '/login')}
              className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
            >
              {t('public.demo.cta_login')}
            </Link>
            <Link
              to="/docs/getting-started"
              onClick={() => trackCta('demo_docs', '/docs/getting-started')}
              className="inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:text-slate-900"
            >
              {t('public.demo.cta_docs')}
            </Link>
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.demo.try_title')}</h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {TRY_ITEMS.map((id) => (
              <li key={id} className="rounded-2xl border border-slate-100 bg-[#F7F8FA] px-4 py-4">
                <p className="text-sm font-semibold text-slate-900">{t(`public.demo.try.${id}.title`)}</p>
                <p className="mt-1 text-sm leading-relaxed text-slate-600">{t(`public.demo.try.${id}.body`)}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">{t('public.demo.how_title')}</h2>
          <ol className="mt-4 space-y-3">
            {STEPS.map((id, index) => (
              <li key={id} className="rounded-2xl border border-slate-100 bg-[#F7F8FA] px-4 py-4">
                <p className="text-sm font-semibold text-slate-900">
                  <span className="mr-2 text-[#00C2A8]">{index + 1}.</span>
                  {t(`public.demo.steps.${id}.title`)}
                </p>
                <p className="mt-1 text-sm leading-relaxed text-slate-600">{t(`public.demo.steps.${id}.body`)}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-[#0B0E14] p-6 text-white sm:p-8">
          <h2 className="text-lg font-semibold">{t('public.demo.safety_title')}</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-300">{t('public.demo.safety_body')}</p>
        </section>

        <section className="rounded-3xl border border-[#00C2A8]/25 bg-white p-6 text-center shadow-sm sm:p-8">
          <h2 className="text-lg font-semibold text-slate-900">{t('public.demo.still_title')}</h2>
          <p className="mt-2 text-sm text-slate-600">{t('public.demo.still_body')}</p>
          <Link
            to="/signup"
            onClick={() => trackCta('demo_footer_signup', '/signup')}
            className="mt-5 inline-flex items-center justify-center rounded-xl bg-[#00C2A8] px-6 py-2.5 text-sm font-semibold text-[#04201C] transition hover:bg-[#1ad4bb]"
          >
            {t('public.demo.cta_signup')}
          </Link>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
