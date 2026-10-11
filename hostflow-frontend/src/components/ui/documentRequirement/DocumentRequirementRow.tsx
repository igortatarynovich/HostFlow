import type { ReactNode } from 'react'
import { documentRequirementGridClass } from './documentRequirementGrid'

type Props = {
  title: string
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
  requirement,
  presence,
  fileStatus,
  action,
  expanded,
  onToggle,
  details,
}: Props) {
  const titleNode = onToggle ? (
    <button type="button" className="truncate text-left text-sm font-medium text-slate-900" onClick={onToggle}>
      {title}
    </button>
  ) : (
    <span className="truncate text-sm font-medium text-slate-900">{title}</span>
  )
  return (
    <div className="py-2">
      <div className={documentRequirementGridClass}>
        <div className="min-w-0">{titleNode}</div>
        <div className="min-w-0">{requirement}</div>
        <div className="min-w-0">{presence}</div>
        <div className="flex min-w-0 items-center gap-2">{fileStatus}</div>
        <div className="justify-self-start md:justify-self-end">{action}</div>
      </div>
      {expanded ? details : null}
    </div>
  )
}
