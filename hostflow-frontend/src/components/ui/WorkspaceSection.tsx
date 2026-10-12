import { useState, type ReactNode } from 'react'
import clsx from 'clsx'

export function WorkspaceSection({
  title,
  description,
  icon,
  action,
  collapsible = false,
  defaultOpen = true,
  open,
  onOpenChange,
  children,
  className,
}: {
  title: string
  description?: string | null
  icon?: ReactNode
  action?: ReactNode
  collapsible?: boolean
  defaultOpen?: boolean
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children?: ReactNode
  className?: string
}) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen)
  const expanded = open ?? internalOpen
  const toggle = () => {
    const next = !expanded
    onOpenChange?.(next)
    if (open === undefined) setInternalOpen(next)
  }

  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white', className)}>
      <div className="flex items-start gap-2 px-3 py-2.5">
        {icon ? <span className="mt-0.5 inline-flex shrink-0 text-slate-500">{icon}</span> : null}
        <div className="min-w-0 flex-1">
          {collapsible ? (
            <button type="button" className="min-w-0 text-left" aria-expanded={expanded} onClick={toggle}>
              <div className="text-sm font-semibold text-slate-900">{title}</div>
              {description ? <div className="truncate text-xs text-slate-500">{description}</div> : null}
            </button>
          ) : (
            <>
              <div className="text-sm font-semibold text-slate-900">{title}</div>
              {description ? <div className="text-xs text-slate-500">{description}</div> : null}
            </>
          )}
        </div>
        {action}
        {collapsible ? (
          <button
            type="button"
            className="shrink-0 px-1 text-sm leading-none text-slate-400"
            aria-label={expanded ? 'Collapse' : 'Expand'}
            onClick={toggle}
          >
            {expanded ? '−' : '+'}
          </button>
        ) : null}
      </div>
      {(!collapsible || expanded) && children ? (
        <div className="border-t border-slate-100 px-3 py-2.5">{children}</div>
      ) : null}
    </section>
  )
}
