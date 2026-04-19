import { Link } from 'react-router-dom'
import clsx from 'clsx'
import type { ReactNode } from 'react'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'

export type SettingsSubpageHeaderProps = {
  backHref?: string
  backLabel: string
  kicker?: string
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  className?: string
}

/**
 * Shared chrome for settings drill-down pages: back link, optional role kicker, title, subtitle, optional actions.
 */
export function SettingsSubpageHeader({
  backHref = CRM_APP_PATHS.settings,
  backLabel,
  kicker,
  title,
  subtitle,
  actions,
  className,
}: SettingsSubpageHeaderProps) {
  return (
    <div className={clsx('flex flex-wrap items-start justify-between gap-3', className)}>
      <div className="min-w-0 flex-1">
        <Link to={backHref} className="text-sm font-medium text-brand-600 hover:underline">
          {backLabel}
        </Link>
        {kicker ? <p className="mt-1 text-sm text-slate-500">{kicker}</p> : null}
        <h1 className={clsx('text-2xl font-semibold text-slate-900', kicker ? 'mt-1' : 'mt-2')}>{title}</h1>
        {subtitle ? <div className="mt-1 text-sm text-slate-500">{subtitle}</div> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}
