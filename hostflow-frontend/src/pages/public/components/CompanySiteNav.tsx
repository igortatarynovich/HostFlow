import { Link, useLocation } from 'react-router-dom'
import { useI18n } from '../../../i18n'

const LINKS = [
  { to: '/about', key: 'about' },
  { to: '/services', key: 'services' },
  { to: '/contact', key: 'contact' },
  { to: '/legal/privacy.html', key: 'privacy', external: true },
  { to: '/legal/terms.html', key: 'terms', external: true },
  { to: '/data-deletion.html', key: 'data_deletion', external: true },
] as const

export function CompanySiteNav() {
  const { t } = useI18n()
  const location = useLocation()

  return (
    <nav
      className="flex flex-wrap gap-2"
      aria-label={t('public.company.nav.aria', { defaultValue: 'Company pages' })}
    >
      {LINKS.map((link) => {
        const label = t(`public.company.nav.${link.key}`, {
          defaultValue: link.key.replace('_', ' '),
        })
        const className = (active: boolean) =>
          `rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
            active
              ? 'border-brand-400 bg-brand-50 text-brand-800'
              : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
          }`

        if ('external' in link && link.external) {
          return (
            <a
              key={link.key}
              href={link.to}
              target="_blank"
              rel="noopener noreferrer"
              className={className(false)}
            >
              {label}
            </a>
          )
        }

        const active = location.pathname === link.to
        return (
          <Link key={link.key} to={link.to} className={className(active)}>
            {label}
          </Link>
        )
      })}
    </nav>
  )
}
