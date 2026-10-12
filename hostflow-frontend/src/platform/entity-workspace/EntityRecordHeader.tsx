import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'

/**
 * Entity record header. Callers supply identity, context and actions.
 * The header does not own candidate or HR actions.
 */
export function EntityRecordHeader({
  title,
  code,
  compact = false,
  back,
  actions,
  summary,
  pipeline,
  extra,
}: {
  title: string
  code?: string | null
  compact?: boolean
  back?: { to: string; label: string } | null
  actions?: ReactNode
  summary?: ReactNode
  pipeline?: ReactNode
  extra?: ReactNode
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className={clsx('bg-gradient-to-br from-brand-600 via-brand-500 to-brand-400 text-white', compact ? 'px-3 py-2' : 'px-3 py-2.5')}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            {back ? (
              <div className="text-[11px] text-white/80">
                <Link className="hover:underline text-white" to={back.to}>
                  {back.label}
                </Link>
              </div>
            ) : null}
            <div className="flex min-w-0 items-baseline gap-2">
              <h1 className="truncate text-base font-semibold leading-tight text-white">{title || '—'}</h1>
              {code ? <span className="shrink-0 text-xs font-medium text-white/80">{code}</span> : null}
            </div>
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
      </div>
      {summary ? (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-slate-100 px-3 py-1.5">
          {summary}
        </div>
      ) : null}
      {pipeline ? <div className="border-t border-slate-100 px-2 py-1.5">{pipeline}</div> : null}
      {extra ? <div className="border-t border-slate-100 px-3 py-2">{extra}</div> : null}
    </div>
  )
}
