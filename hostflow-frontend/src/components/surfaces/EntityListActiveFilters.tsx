import clsx from 'clsx'
import type { ReactNode } from 'react'

export type EntityListActiveFiltersProps = {
  children: ReactNode
  onResetAll?: () => void
  resetLabel?: string
  className?: string
}

export default function EntityListActiveFilters({
  children,
  onResetAll,
  resetLabel = 'Reset all',
  className,
}: EntityListActiveFiltersProps) {
  return (
    <div className={clsx('entity-list-active-filters flex flex-wrap items-center gap-2', className)}>
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{children}</div>
      {onResetAll ? (
        <button type="button" className="btn-secondary btn-xs shrink-0" onClick={onResetAll}>
          {resetLabel}
        </button>
      ) : null}
    </div>
  )
}
