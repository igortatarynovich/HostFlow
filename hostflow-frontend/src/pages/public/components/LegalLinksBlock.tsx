import { useI18n } from '../../../i18n'

const DOCS = [
  { key: 'rodo', href: '/legal/rodo.html' },
  { key: 'privacy', href: '/legal/privacy.html' },
  { key: 'terms', href: '/legal/terms.html' },
  { key: 'cookies', href: '/legal/cookies.html' },
]

type Props = {
  className?: string
}

export function LegalLinksBlock({ className = '' }: Props) {
  const { t } = useI18n()
  return (
    <p className={`flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-600 ${className}`}>
      {DOCS.map(({ key, href }, i) => (
        <span key={key} className="inline-flex items-center gap-x-2">
          {i > 0 && <span className="text-slate-300">·</span>}
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-600 hover:text-brand-700 hover:underline"
          >
            {t(`public.portal.landing.footer.links.${key}`, { defaultValue: key })}
          </a>
        </span>
      ))}
    </p>
  )
}
