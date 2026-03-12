import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { PublicPageShell } from './components/PublicPageShell'
import { useRobotsMeta } from '../../hooks/useRobotsMeta'

export default function PublicNotFoundPage() {
  const { t } = useI18n()
  useRobotsMeta({ index: false, follow: false })

  return (
    <PublicPageShell maxWidth="2xl">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('public.not_found.badge', { defaultValue: '404' })}
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">
          {t('public.not_found.title', { defaultValue: 'Page not found' })}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {t('public.not_found.subtitle', {
            defaultValue: 'The address is invalid or the page has moved.',
          })}
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link to="/" className="btn-primary">
            {t('public.not_found.go_home', { defaultValue: 'Go to home' })}
          </Link>
          <Link to="/login" className="btn-secondary">
            {t('public.not_found.go_login', { defaultValue: 'Go to login' })}
          </Link>
        </div>
      </section>
    </PublicPageShell>
  )
}
