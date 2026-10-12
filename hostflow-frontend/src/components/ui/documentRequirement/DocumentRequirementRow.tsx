import type { ReactNode } from 'react'
import { documentRequirementGridClass } from './documentRequirementGrid'

type Props = {
  title: string
  subtitle?: string | null
  requirement?: ReactNode
  presence: ReactNode
  fileStatus?: ReactNode
  action?: ReactNode
  expanded?: boolean
  onToggle?: () => void
  details?: ReactNode
}

export function DocumentRequirementRow({
  title,
  subtitle,
  requirement,
  presence,
  fileStatus,
  action,
  expanded,
  onToggle,
  details,
}: Props) {
  const titleClass = 'block max-w-full truncate text-left text-sm font-medium text-slate-900'
  const titleNode = onToggle ? (
    <button type="button" className={titleClass} onClick={onToggle}>
      {title}
    </button>
  ) : (
    <span className={titleClass}>{title}</span>
  )
  return (
    <div className="py-1.5">
      <div className={documentRequirementGridClass}>
        <div className="min-w-0">
          {titleNode}
          {subtitle ? <div className="truncate text-xs text-slate-500">{subtitle}</div> : null}
        </div>
        <div className="min-w-0">{requirement}</div>
        <div className="min-w-0">{presence}</div>
        <div className="flex min-w-0 items-center gap-2 overflow-hidden">{fileStatus}</div>
        <div className="flex min-w-0 justify-start md:justify-end">{action}</div>
      </div>
      {expanded ? details : null}
    </div>
  )
}
