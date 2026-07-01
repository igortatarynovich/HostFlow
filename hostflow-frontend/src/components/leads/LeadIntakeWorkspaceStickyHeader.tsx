import clsx from 'clsx'

export type LeadIntakeWorkspaceStickyHeaderProps = {
  /** intake = neutral bar; audit = subtle green tint after conversion */
  variant?: 'intake' | 'audit'
  displayName: string
  source: string
  vacancySummary: string
  statusLabel: string
  createdLabel: string
}

/**
 * Compact sticky strip (~72–88px): who, source, vacancy state, intake pill, created — no hero / ID wall.
 */
export default function LeadIntakeWorkspaceStickyHeader({
  variant = 'intake',
  displayName,
  source,
  vacancySummary,
  statusLabel,
  createdLabel,
}: LeadIntakeWorkspaceStickyHeaderProps) {
  return (
    <header
      className={clsx(
        'sticky top-0 z-20 -mx-px mb-1 flex min-h-[72px] max-h-[88px] shrink-0 items-center border-b px-3 py-2.5 backdrop-blur-md sm:px-4',
        variant === 'audit'
          ? 'border-emerald-200/70 bg-emerald-50/90 supports-[backdrop-filter]:bg-emerald-50/85'
          : 'border-slate-200/90 bg-white/95 supports-[backdrop-filter]:bg-white/88',
      )}
    >
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1.5 sm:flex-nowrap">
        <span className="max-w-[min(52vw,340px)] truncate text-base font-semibold tracking-tight text-slate-900">
          {displayName}
        </span>
        <span className="max-w-[120px] shrink-0 truncate text-sm text-slate-600 sm:max-w-none" title={source}>
          {source}
        </span>
        <span className="hidden max-w-[180px] truncate text-sm text-slate-500 md:inline xl:max-w-[240px]" title={vacancySummary}>
          {vacancySummary}
        </span>
        <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-700">
          {statusLabel}
        </span>
        <span className="ml-auto shrink-0 whitespace-nowrap text-[11px] text-slate-500 tabular-nums">{createdLabel}</span>
      </div>
    </header>
  )
}
