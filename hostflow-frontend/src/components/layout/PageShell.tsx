import type { HTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

/**
 * Unified page shell. It fills the available column height and owns vertical
 * scroll. List tables (Candidates, Отклики) are routed as edge-to-edge in
 * AppShell (no `crm-page-inset`); detail/form pages keep the shell but sit
 * inside `crm-page-inset` so content does not stick to the screen edges.
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
    <div
      data-hf-page-shell-header
      className={clsx('shrink-0 px-4 pt-4 pb-2', className)}
    >
      {children}
    </div>
  )
}
