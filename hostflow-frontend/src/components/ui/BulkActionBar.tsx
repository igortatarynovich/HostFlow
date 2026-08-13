import type { ReactNode } from 'react'

import { Button } from './Button'

export type BulkActionBarProps = {
  selectedCount: number
  onClearSelection: () => void
  clearLabel?: string
  selectedLabel?: (count: number) => string
  actions?: ReactNode
  className?: string
}

/**
 * ListWorkspace bulk bar. Visible only when the shell has a non-empty selection.
 */
export function BulkActionBar({
  selectedCount,
  onClearSelection,
  clearLabel = 'Clear selection',
  selectedLabel = (count) => `Selected: ${count}`,
  actions,
  className,
}: BulkActionBarProps) {
  return (
    <div className={`entity-list-bulk-bar-inner flex flex-wrap items-center gap-3 ${className ?? ''}`}>
      <span className="text-xs font-medium text-slate-700">{selectedLabel(selectedCount)}</span>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      <Button type="button" variant="secondary" size="xs" className="ml-auto" onClick={onClearSelection}>
        {clearLabel}
      </Button>
    </div>
  )
}
