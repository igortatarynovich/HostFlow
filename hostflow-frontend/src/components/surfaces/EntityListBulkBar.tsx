import clsx from 'clsx'
import type { ReactNode } from 'react'

export type EntityListBulkBarProps = {
  selectedCount: number
  onClearSelection: () => void
  clearLabel?: string
  selectedLabel?: (count: number) => string
  actions?: ReactNode
  className?: string
}

/**
 * Presentational bulk bar content. Visibility is controlled by EntityListShell + selection.
 */
export default function EntityListBulkBar({
  selectedCount,
  onClearSelection,
  clearLabel = 'Clear selection',
  selectedLabel = (count) => `Selected: ${count}`,
  actions,
  className,
}: EntityListBulkBarProps) {
  return (
    <div className={clsx('entity-list-bulk-bar-inner flex flex-wrap items-center gap-3', className)}>
      <span className="text-xs font-medium text-slate-700">{selectedLabel(selectedCount)}</span>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      <button type="button" className="btn-secondary btn-xs ml-auto" onClick={onClearSelection}>
        {clearLabel}
      </button>
    </div>
  )
}
