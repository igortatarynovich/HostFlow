import type { ReactNode } from 'react'
import { Button } from '../ui/Button'

export type AnalyticsReportHeaderProps = {
  brand: string
  company?: string | null
  title: string
  periodLabel: string
  present: boolean
  onTogglePresent: () => void
  onCopyLink: () => void
  copyState?: 'idle' | 'copied' | 'failed'
  presentLabel: string
  workingLabel?: string
  copyLabel: string
  copiedLabel: string
  copyFailedLabel: string
  exitLabel: string
  extra?: ReactNode
}

export function AnalyticsReportHeader({
  brand,
  company,
  title,
  periodLabel,
  present,
  onTogglePresent,
  onCopyLink,
  copyState = 'idle',
  presentLabel,
  copyLabel,
  copiedLabel,
  copyFailedLabel,
  exitLabel,
  extra,
}: AnalyticsReportHeaderProps) {
  return (
    <header className="group flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-4">
      <div className="min-w-0 space-y-1">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {brand}
          {company ? <span className="text-slate-400"> · {company}</span> : null}
        </p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        <p className="text-sm text-slate-500">{periodLabel}</p>
      </div>
      <div
        className={
          present
            ? 'flex flex-wrap gap-2 print:hidden opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100'
            : 'flex flex-wrap gap-2 print:hidden'
        }
        data-hf-analytics-controls
      >
        {present ? null : extra}
        {present ? null : (
          <Button type="button" variant="secondary" size="sm" onClick={onCopyLink}>
            {copyState === 'copied' ? copiedLabel : copyState === 'failed' ? copyFailedLabel : copyLabel}
          </Button>
        )}
        <Button type="button" variant="secondary" size="sm" onClick={onTogglePresent}>
          {present ? exitLabel : presentLabel}
        </Button>
      </div>
    </header>
  )
}
