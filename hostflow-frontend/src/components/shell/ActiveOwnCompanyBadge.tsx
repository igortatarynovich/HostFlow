import clsx from 'clsx'
import { IconBuildingCommunity } from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { useActiveOwnCompanyLabel } from '../../hooks/useActiveOwnCompanyLabel'

type Props = {
  className?: string
  /** e.g. dark text on gradient hero */
  variant?: 'default' | 'onBrand'
}

/**
 * Shows the active own-company (tenant legal entity) when multiple exist or when resolved from API.
 */
export function ActiveOwnCompanyBadge({ className, variant = 'default' }: Props) {
  const { t } = useI18n()
  const { label, loading } = useActiveOwnCompanyLabel()

  if (loading && !label) return null
  if (!label) return null

  const isBrand = variant === 'onBrand'

  return (
    <span
      className={clsx(
        'inline-flex max-w-[min(18rem,100%)] items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium tabular-nums',
        isBrand
          ? 'border-white/40 bg-white/15 text-white'
          : 'border-slate-200 bg-slate-50 text-slate-700',
        className,
      )}
      title={t('app.shell.active_own_company.badge_title', { name: label })}
    >
      <IconBuildingCommunity size={12} className={clsx('shrink-0', isBrand ? 'text-white/90' : 'text-slate-500')} aria-hidden />
      <span className="truncate">{label}</span>
    </span>
  )
}
