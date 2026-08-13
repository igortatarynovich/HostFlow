import type { ReactNode } from 'react'
import clsx from 'clsx'

import {
  DATA_TABLE_FOOTER_CLASS,
  DATA_TABLE_SCROLL_CLASS,
  DATA_TABLE_SURFACE_CLASS,
} from '../ui/DataTable'

export { DATA_TABLE_FOOTER_CLASS, DATA_TABLE_SCROLL_CLASS, DATA_TABLE_SURFACE_CLASS }

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
