import type { ReactNode } from 'react'
import clsx from 'clsx'

/** Shared surface classes — same card shell as `DataTable`. */
export const DATA_TABLE_SURFACE_CLASS =
  'card relative m-0 flex min-h-0 flex-1 flex-col rounded-lg border border-slate-200 bg-white shadow-sm'

export const DATA_TABLE_SCROLL_CLASS =
  'min-h-0 flex-1 overflow-auto overscroll-contain rounded-b-lg'

export const DATA_TABLE_FOOTER_CLASS =
  'shrink-0 border-t border-slate-200/80 px-4 pb-4 pt-3 text-sm leading-6 text-slate-600'

/**
 * Card + scroll + optional header/footer shell for bespoke tables (Candidates,
 * Leads) that cannot use declarative `DataTable` columns yet.
 */
export function DataTableFrame({
  children,
  header,
  preScroll,
  footer,
  className,
}: {
  children: ReactNode
  /** Toolbar strip above the scroll area (bulk actions, hints). */
  header?: ReactNode
  /** Static strip between header and scroll (keyboard hints, banners). */
  preScroll?: ReactNode
  footer?: ReactNode
  className?: string
}) {
  return (
    <div className={clsx(DATA_TABLE_SURFACE_CLASS, className)}>
      {header}
      {preScroll}
      <div className={DATA_TABLE_SCROLL_CLASS}>{children}</div>
      {footer ? <div className={DATA_TABLE_FOOTER_CLASS}>{footer}</div> : null}
    </div>
  )
}
