import clsx from 'clsx'
import type { ReactNode } from 'react'

/** Light workspace card. Dense padding stays opt-in so list cards keep their own scale. */
export function WorkspaceSurface({
  children,
  className,
  padded = false,
}: {
  children: ReactNode
  className?: string
  padded?: boolean
}) {
  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white', padded && 'p-3', className)}>
      {children}
    </section>
  )
}
