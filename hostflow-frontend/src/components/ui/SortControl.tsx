import type { ReactNode } from 'react'
import clsx from 'clsx'

export type SortControlDirection = 'asc' | 'desc'

export type SortControlProps = {
  /** Column label. Keep this a string or plain text node — do not nest another button. */
  label: ReactNode
  active?: boolean
  direction?: SortControlDirection
  onClick: () => void
  title?: string
  activeTitle?: string
  className?: string
}

/**
 * TABLE_V1 header sort control (Candidates pixels).
 * Used by `DataTable` when a column is `sortable`; modules may also compose it in a custom header.
 */
export function SortControl({
  label,
  active = false,
  direction = 'asc',
  onClick,
  title,
  activeTitle,
  className,
}: SortControlProps) {
  return (
    <button
      type="button"
      className={clsx(
        'group/sort relative inline-flex h-5 min-w-0 shrink items-center gap-1 whitespace-nowrap text-left font-semibold leading-none text-slate-700 transition-colors hover:text-brand-600',
        className,
      )}
      onClick={onClick}
      title={active ? activeTitle ?? title : title}
    >
      <span className="truncate">{label}</span>
      {active ? (
        <span
          aria-hidden
          className="inline-flex h-4 w-4 items-center justify-center text-[11px] font-semibold text-brand-600/90"
          title={activeTitle}
        >
          {direction === 'asc' ? '▲' : '▼'}
        </span>
      ) : (
        <span
          aria-hidden
          className="inline-flex h-4 w-4 items-center justify-center text-[10px] text-slate-300 opacity-0 transition-opacity group-hover/sort:opacity-100 group-focus-visible/sort:opacity-100"
        >
          ↕
        </span>
      )}
    </button>
  )
}
