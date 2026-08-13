import type { ReactNode } from 'react'

export type AnalyticsDimension = {
  id: string
  label: string
  value: string
  options: { id: string; label: string }[]
  allLabel: string
  onChange: (value: string) => void
}

export type AnalyticsQuickRangeOption<T extends string = string> = {
  value: T
  label: string
}

export type AnalyticsFilterBarProps<T extends string = string> = {
  periodLabel: string
  quickRanges: AnalyticsQuickRangeOption<T>[]
  activeRange: T | 'custom'
  onQuickRange: (value: T) => void
  fromLabel: string
  toLabel: string
  dateFrom: string
  dateTo: string
  onDateFrom: (value: string) => void
  onDateTo: (value: string) => void
  dimensions?: AnalyticsDimension[]
  extra?: ReactNode
  sampleText?: string
  loading?: boolean
  loadingLabel?: string
}

export function AnalyticsFilterBar<T extends string>({
  periodLabel,
  quickRanges,
  activeRange,
  onQuickRange,
  fromLabel,
  toLabel,
  dateFrom,
  dateTo,
  onDateFrom,
  onDateTo,
  dimensions = [],
  extra,
  sampleText,
  loading,
  loadingLabel,
}: AnalyticsFilterBarProps<T>) {
  return (
    <div className="card space-y-3 p-4">
      <div className="flex flex-wrap items-end gap-3">
        {dimensions.map((dim) => (
          <label key={dim.id} className="flex flex-col gap-1 text-xs">
            <span className="text-slate-500">{dim.label}</span>
            <select
              className="input input-sm min-w-[180px]"
              value={dim.value}
              onChange={(e) => dim.onChange(e.target.value)}
            >
              <option value="">{dim.allLabel}</option>
              {dim.options.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        ))}

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-slate-500">{periodLabel}</span>
          <div className="flex flex-wrap gap-1">
            {quickRanges.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`rounded px-2 py-1 text-xs ${
                  activeRange === option.value
                    ? 'bg-brand-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
                onClick={() => onQuickRange(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-slate-500">{fromLabel}</span>
          <input
            type="date"
            className="input input-sm w-36"
            autoComplete="off"
            value={dateFrom}
            onChange={(e) => onDateFrom(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-slate-500">{toLabel}</span>
          <input
            type="date"
            className="input input-sm w-36"
            autoComplete="off"
            value={dateTo}
            onChange={(e) => onDateTo(e.target.value)}
          />
        </label>

        {extra}
      </div>

      {sampleText || loading ? (
        <div className="flex items-center justify-between border-t border-slate-100 pt-2 text-xs text-slate-500">
          <span>{sampleText}</span>
          {loading ? <span>{loadingLabel}</span> : null}
        </div>
      ) : null}
    </div>
  )
}
