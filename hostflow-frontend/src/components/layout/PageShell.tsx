import type { HTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

/**
 * Unified page shell. It fills the available column height. `min-w-0` lets
 * flex/grid children shrink on narrow viewports instead of overflowing the
 * screen. Vertical overflow is scrollable so detail pages that forget an inner
 * scroller still remain reachable; list pages keep an inner `flex-1 min-h-0`
 * table and do not grow past this box.
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
        'relative flex min-h-0 min-w-0 w-full flex-1 flex-col overflow-x-auto overflow-y-auto overscroll-contain',
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
    <div
      data-hf-page-shell-header
      className={clsx('shrink-0 px-4 pt-2 pb-1', className)}
    >
      {children}
    </div>
  )
}

/**
 * Scroll region under `PageShellHeader`. Keeps breadcrumbs visible while the
 * page body scrolls on short / mobile viewports.
 */
export function PageShellBody({
  children,
  className,
  ...rest
}: {
  children: ReactNode
  className?: string
} & HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      data-hf-page-shell-body
      className={clsx(
        'min-h-0 min-w-0 flex-1 overflow-x-auto overflow-y-auto overscroll-contain pb-4',
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}
