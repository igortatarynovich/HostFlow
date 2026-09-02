import type { ReactNode } from 'react'
import clsx from 'clsx'

/**
 * Unified filters/actions toolbar surface, modelled on the Candidates filters
 * toolbar. Sits between the page header and the table with a consistent inset
 * (`mx-4`), rounded surface and subtle gradient so every module's filter row
 * looks identical.
 */
export function Toolbar({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      data-hf-page-toolbar
      className={clsx(
        'mx-4 mb-1.5 shrink-0 rounded-xl border border-slate-200/90 bg-gradient-to-b from-white to-slate-50/90 px-3 py-1.5 shadow-sm',
        className,
      )}
    >
      {children}
    </div>
  )
}
