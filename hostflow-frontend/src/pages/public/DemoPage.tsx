import { Link } from 'react-router-dom'
import { PublicPageShell } from './components/PublicPageShell'
import { PublicLegalFooter } from '../../components/public/PublicLegalFooter'
import { useI18n } from '../../i18n'
import { useSeoMeta } from '../../hooks/useSeoMeta'
import { useSeoTracking } from '../../hooks/useSeoTracking'

const TRY_ITEMS = [
  {
    id: 'vacancy',
    titleKey: 'public.demo.try.vacancy.title',
    titleDefault: 'Create a vacancy',
    bodyKey: 'public.demo.try.vacancy.body',
    bodyDefault: 'See how a hiring container owns pipeline and intake.',
  },
  {
    id: 'leads',
    titleKey: 'public.demo.try.leads.title',
    titleDefault: 'Browse sample leads',
    bodyKey: 'public.demo.try.leads.body',
    bodyDefault: 'Open Leads with owned applications and next actions.',
  },
  {
    id: 'candidates',
    titleKey: 'public.demo.try.candidates.title',
    titleDefault: 'Inspect candidates',
    bodyKey: 'public.demo.try.candidates.body',
    bodyDefault: 'Move stages and see how ownership stays visible.',
  },
  {
    id: 'documents',
    titleKey: 'public.demo.try.documents.title',
    titleDefault: 'Check documents',
    bodyKey: 'public.demo.try.documents.body',
    bodyDefault: 'Required slots and status without messenger folders.',
  },
] as const

const STEPS = [
  {
    id: 'signup',
    titleKey: 'public.demo.steps.signup.title',
    titleDefault: 'Create your workspace',
    bodyKey: 'public.demo.steps.signup.body',
    bodyDefault: 'Sign up — you get your own tenant, not a shared guest login.',
  },
  {
    id: 'company',
    titleKey: 'public.demo.steps.company.title',
    titleDefault: 'Add company once',
    bodyKey: 'public.demo.steps.company.body',
    bodyDefault: 'Short company form, then the normal product with one next step.',
  },
  {
    id: 'seed',
    titleKey: 'public.demo.steps.seed.title',
    titleDefault: 'Load sample data',
    bodyKey: 'public.demo.steps.seed.body',
    bodyDefault: 'From Getting started, load the sample pack — leads, candidates, tasks. Clear anytime.',
  },
  {
    id: 'explore',
    titleKey: 'public.demo.steps.explore.title',
    titleDefault: 'Click through HostFlow',
    bodyKey: 'public.demo.steps.explore.body',
    bodyDefault: 'Explore vacancies, leads, candidates, and documents with synthetic data.',
  },
] as const

export default function DemoPage() {
  const { t } = useI18n()
  const { trackCta } = useSeoTracking({ pageType: 'landing', pageKey: 'demo' })

  useSeoMeta({
    title: t('public.demo.seo.title', {
      defaultValue: 'Interactive HostFlow demo — try with sample data',
    }),
    description: t('public.demo.seo.description', {
      defaultValue:
        'Create your workspace, load a sample recruiting pack, and click through vacancies, leads, candidates, and documents. Clear sample data in one action.',
    }),
    canonicalPath: '/demo',
  })

  return (
    <PublicPageShell maxWidth="5xl">
      <div className="space-y-8">
        <section className="card p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            {t('public.demo.badge', { defaultValue: 'Interactive demo' })}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">
            {t('public.demo.title', { defaultValue: 'Click through HostFlow with sample data' })}
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-600 sm:text-base">
            {t('public.demo.subtitle', {
              defaultValue:
                'Not a video. Not screenshots. Your own workspace plus a sample pack you can wipe in one click.',
            })}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/signup" className="btn-primary" onClick={() => trackCta('demo_signup', '/signup')}>
              {t('public.demo.cta_signup', { defaultValue: 'Start free setup' })}
            </Link>
            <Link to="/login" className="btn-secondary" onClick={() => trackCta('demo_login', '/login')}>
              {t('public.demo.cta_login', { defaultValue: 'Sign in to load samples' })}
            </Link>
            <Link to="/docs/getting-started" className="btn-secondary" onClick={() => trackCta('demo_docs', '/docs/getting-started')}>
              {t('public.demo.cta_docs', { defaultValue: 'Getting started guide' })}
            </Link>
          </div>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.demo.try_title', { defaultValue: 'What you can try' })}
          </h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {TRY_ITEMS.map((item) => (
              <li key={item.id} className="rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">
                  {t(item.titleKey, { defaultValue: item.titleDefault })}
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  {t(item.bodyKey, { defaultValue: item.bodyDefault })}
                </p>
              </li>
            ))}
          </ul>
        </section>

        <section className="card cv-auto p-6">
          <h2 className="text-xl font-semibold text-slate-900">
            {t('public.demo.how_title', { defaultValue: 'How the interactive demo works' })}
          </h2>
          <ol className="mt-4 space-y-3">
            {STEPS.map((step, index) => (
              <li key={step.id} className="rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3">
                <p className="text-sm font-semibold text-slate-900">
                  <span className="mr-2 text-brand-700">{index + 1}.</span>
                  {t(step.titleKey, { defaultValue: step.titleDefault })}
                </p>
                <p className="mt-1 text-sm text-slate-700">
                  {t(step.bodyKey, { defaultValue: step.bodyDefault })}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section className="card cv-auto border-amber-200 bg-amber-50/50 p-6">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('public.demo.safety_title', { defaultValue: 'Why not a shared guest login?' })}
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">
            {t('public.demo.safety_body', {
              defaultValue:
                'A shared demo tenant that everyone edits needs isolation and a hard reset policy. Wave-1 keeps data inside your tenant only — safer for you and for HostFlow.',
            })}
          </p>
        </section>

        <section className="rounded-xl border border-brand-200 bg-brand-50/60 p-6 text-center">
          <h2 className="text-lg font-semibold text-slate-900">
            {t('public.demo.still_title', { defaultValue: 'Ready to explore?' })}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {t('public.demo.still_body', {
              defaultValue: 'Create a workspace, then use Load sample data on Getting started.',
            })}
          </p>
          <Link
            to="/signup"
            className="btn-primary mt-4 inline-flex"
            onClick={() => trackCta('demo_footer_signup', '/signup')}
          >
            {t('public.demo.cta_signup', { defaultValue: 'Start free setup' })}
          </Link>
        </section>

        <PublicLegalFooter />
      </div>
    </PublicPageShell>
  )
}
