import type { ReactNode } from 'react'
import clsx from 'clsx'

/** System filter strip for list / queue workspaces. Callers own filter fields and actions. */
export function FilterBar({
  filters,
  actions,
  className,
}: {
  filters: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div
      className={clsx(
        'flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3',
        className,
      )}
    >
      <div className="flex min-w-0 flex-1 flex-wrap items-end gap-3">{filters}</div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}
