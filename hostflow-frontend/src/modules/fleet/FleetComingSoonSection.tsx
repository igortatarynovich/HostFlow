import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'

type FleetComingSoonLink = {
  href: string
  labelKey: string
}

type Props = {
  titleKey: string
  bodyKey: string
  link?: FleetComingSoonLink
}

export default function FleetComingSoonSection({ titleKey, bodyKey, link }: Props) {
  const { t } = useI18n()

  return (
    <div className="mx-auto max-w-2xl space-y-4 rounded-lg border border-amber-200 bg-amber-50/60 p-6">
      <h1 className="text-xl font-semibold text-slate-900">{t(titleKey)}</h1>
      <p className="text-sm leading-relaxed text-slate-700">{t(bodyKey)}</p>
      {link ? (
        <p>
          <Link className="font-medium text-blue-700 underline-offset-4 hover:underline" to={link.href}>
            {t(link.labelKey)}
          </Link>
        </p>
      ) : null}
    </div>
  )
}
