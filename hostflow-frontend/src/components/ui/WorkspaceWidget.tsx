import clsx from 'clsx'
import type { ReactNode } from 'react'

/** Compact sidebar widget. Callers own the domain content. */
export function WorkspaceWidget({
  title,
  icon,
  action,
  children,
  className,
}: {
  title: string
  icon?: ReactNode
  action?: ReactNode
  children?: ReactNode
  className?: string
}) {
  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white', className)}>
      <header className="flex items-center justify-between gap-2 px-3 py-2">
        <div className="flex min-w-0 items-center gap-1.5">
          {icon ? <span className="inline-flex shrink-0 text-slate-500">{icon}</span> : null}
          <h2 className="truncate text-xs font-semibold text-slate-800">{title}</h2>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </header>
      {children ? <div className="border-t border-slate-100 px-3 py-2.5">{children}</div> : null}
    </section>
  )
}
