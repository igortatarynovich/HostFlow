import clsx from 'clsx'
import { useI18n } from '../../i18n'

type PublicLegalFooterProps = {
  variant?: 'card' | 'inline'
  className?: string
}

const DOC_LINKS = [
  { key: 'privacy', href: '/legal/privacy.html' },
  { key: 'terms', href: '/legal/terms.html' },
  { key: 'cookies', href: '/legal/cookies.html' },
  { key: 'rodo', href: '/legal/rodo.html' },
]

export function PublicLegalFooter({ variant = 'inline', className }: PublicLegalFooterProps) {
  const { t } = useI18n()
  const companyLines = t('public.portal.landing.footer.company')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !/request a new one/i.test(line) && !/can't find the link/i.test(line))

  const docsList = (
    <ul className="space-y-2 text-sm text-brand-700">
      {DOC_LINKS.map(({ key, href }) => (
        <li key={key}>
          <a href={href} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">
            {t(`public.portal.landing.footer.links.${key}`, { defaultValue: key })}
          </a>
        </li>
      ))}
    </ul>
  )

  const companyBlock = (
    <address className="space-y-1 text-sm not-italic text-slate-700">
      {companyLines.map((line) =>
        line.includes('@') ? (
          <div key={line}>
            <a href={`mailto:${line}`} className="text-brand-700 underline-offset-2 hover:underline">
              {line}
            </a>
          </div>
        ) : (
          <div key={line}>{line}</div>
        ),
      )}
    </address>
  )

  const content = (
    <div className="grid gap-8 md:grid-cols-2 md:gap-12">
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('public.portal.landing.footer.title')}
        </div>
        <div className="mt-3">{docsList}</div>
      </div>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('public.portal.landing.footer.address_title')}
        </div>
        <div className="mt-3">{companyBlock}</div>
      </div>
    </div>
  )

  if (variant === 'card') {
    return (
      <section className={clsx('rounded-3xl border border-slate-200 bg-white/95 p-6 shadow-card', className)}>
        {content}
        <p className="mt-6 text-xs text-slate-500">© 2025 HostFlow. All rights reserved.</p>
      </section>
    )
  }

  return (
    <footer className={clsx('border-t border-slate-200 pt-8 text-sm text-slate-600', className)}>
      {content}
      <p className="mt-6 text-xs text-slate-500">© 2025 HostFlow. All rights reserved.</p>
    </footer>
  )
}
