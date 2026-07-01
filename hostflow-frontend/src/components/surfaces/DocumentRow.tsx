import clsx from 'clsx'
import DocumentStatus from './DocumentStatus'

type Props = {
  label: string
  subtitle?: string
  statusLabel?: string
  displayStatus?: string
  severity?: 'ok' | 'warn' | 'bad' | 'info' | string
  compact?: boolean
  className?: string
}

export default function DocumentRow({
  label,
  subtitle,
  statusLabel,
  displayStatus,
  severity,
  compact = false,
  className,
}: Props) {
  return (
    <div className={clsx('rounded-lg border bg-white p-3 shadow-sm', compact && 'p-2', className)}>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-slate-900">{label}</p>
          {subtitle ? <p className="truncate text-xs text-slate-500">{subtitle}</p> : null}
        </div>
        {statusLabel ? (
          <DocumentStatus label={statusLabel} displayStatus={displayStatus} severity={severity} />
        ) : null}
      </div>
    </div>
  )
}

