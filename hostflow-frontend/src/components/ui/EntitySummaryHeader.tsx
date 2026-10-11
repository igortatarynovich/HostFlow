import type { ReactNode } from 'react'
import { IconCopy } from '@tabler/icons-react'

/** Identity row for a person or company record. Callers supply facts and actions. */
export function EntitySummaryHeader({
  initials,
  title,
  code,
  onCopyCode,
  copyLabel,
  meta,
  actions,
  context,
  pipeline,
}: {
  initials: string
  title: string
  code?: string | null
  onCopyCode?: () => void
  copyLabel?: string
  meta?: ReactNode
  actions?: ReactNode
  context?: ReactNode
  pipeline?: ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold tracking-wide text-slate-700">
            {initials}
          </div>
          <div className="min-w-0">
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              <h1 className="truncate text-lg font-semibold leading-tight text-slate-900">{title}</h1>
              {code ? (
                <span className="inline-flex items-center gap-0.5 text-xs font-medium text-slate-500">
                  {code}
                  {onCopyCode ? (
                    <button
                      type="button"
                      className="btn-icon btn-icon-sm h-6 w-6 text-slate-400"
                      onClick={onCopyCode}
                      aria-label={copyLabel || 'Copy'}
                    >
                      <IconCopy size={13} />
                    </button>
                  ) : null}
                </span>
              ) : null}
            </div>
            {meta ? <div className="mt-1.5 flex flex-wrap items-center gap-1.5">{meta}</div> : null}
          </div>
        </div>
        {actions ? <div className="flex flex-wrap items-center justify-end gap-1.5">{actions}</div> : null}
      </div>
      {context ? <div className="border-t border-slate-100 px-4 py-2.5">{context}</div> : null}
      {pipeline ? <div className="border-t border-slate-100 px-3 py-2">{pipeline}</div> : null}
    </section>
  )
}
