import type { HTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

/**
 * Unified full-bleed list-page shell, modelled on the Candidates list screen
 * (the canonical reference layout). It fills the available column height,
 * owns its own vertical scroll via the child `DataTable`, and hosts a vertical
 * stack of: header → toolbar → table.
 *
 * Pages using this shell must be routed through the AppShell "full-bleed list"
 * branch (no `crm-page-inset`), the same treatment the Candidates table gets.
 */
export function PageShell({
  children,
  className,
  ...rest
}: {
  children: ReactNode
  className?: string
} & HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      data-hf-page-shell
      className={clsx(
        'relative flex min-h-0 w-full flex-1 flex-col overflow-hidden',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

/**
 * Inset wrapper for chrome that sits above the full-bleed table (header,
 * toolbar, banners). Mirrors the Candidates `mx-4` inset so every module keeps
 * the exact same horizontal rhythm while the table itself bleeds to the edges.
 */
export function PageShellHeader({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={clsx('shrink-0 px-4 pt-4 pb-2', className)}>{children}</div>
  )
}
