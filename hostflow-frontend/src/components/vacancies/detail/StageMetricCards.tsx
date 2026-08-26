import React from 'react'
import StageTag from '../../StageTag'
import type { StageMetric } from './pipelineMetrics'

export type { StageMetric }

const ACCENT: Record<string, string> = {
  new: 'border-blue-200 bg-blue-50',
  contacted: 'border-blue-200 bg-blue-50',
  docs_wait: 'border-amber-200 bg-amber-50',
  permit: 'border-fuchsia-200 bg-fuchsia-50',
  employed: 'border-emerald-200 bg-emerald-50',
  hired: 'border-emerald-200 bg-emerald-50',
  rejected: 'border-rose-200 bg-rose-50',
  declined: 'border-slate-200 bg-slate-50',
}

function accentFor(code: string): string {
  const c = code.toLowerCase()
  for (const [k, v] of Object.entries(ACCENT)) {
    if (c === k || c.includes(k)) return v
  }
  return 'border-slate-200 bg-white'
}

type Props = {
  stages: StageMetric[]
  loading?: boolean
  viewListLabel: string
  onSelect: (stageCode: string) => void
}

export function StageMetricCards({ stages, loading, viewListLabel, onSelect }: Props) {
  if (loading) {
    return <div className="text-xs text-slate-500">…</div>
  }
  if (!stages.length) return null

  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {stages.map((s) => (
        <button
          key={s.code}
          type="button"
          onClick={() => onSelect(s.code)}
          className={`min-w-[7.5rem] flex-shrink-0 rounded-xl border px-3 py-2 text-left transition hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-400 ${accentFor(s.code)}`}
        >
          <div className="text-xl font-semibold tabular-nums text-slate-900">{s.count}</div>
          <div className="mt-1 line-clamp-2 text-xs text-slate-700">
            <StageTag code={s.code} />
          </div>
          <div className="mt-2 text-[11px] font-medium text-slate-600 underline-offset-2 hover:underline">
            {viewListLabel}
          </div>
        </button>
      ))}
    </div>
  )
}
