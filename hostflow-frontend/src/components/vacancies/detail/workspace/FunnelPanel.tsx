import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'
import StageTag from '../../../StageTag'
import type { StageCount } from '../pipelineMetrics'

type Props = {
  title: string
  stages: StageCount[]
  total: number
  onStageClick: (code: string) => void
  emptyLabel: string
}

export function FunnelPanel({ title, stages, total, onStageClick, emptyLabel }: Props) {
  if (!stages.length) {
    return (
      <SectionCard title={title}>
        <p className="text-sm text-slate-500">{emptyLabel}</p>
      </SectionCard>
    )
  }

  const max = Math.max(...stages.map((s) => s.count), 1)

  return (
    <SectionCard title={title}>
      <ul className="space-y-2">
        {stages.map((s) => {
          const pct = total > 0 ? Math.round((s.count / total) * 1000) / 10 : 0
          const width = Math.max(8, Math.round((s.count / max) * 100))
          return (
            <li key={s.code}>
              <button
                type="button"
                onClick={() => onStageClick(s.code)}
                className="group flex w-full items-center gap-3 rounded-lg border border-transparent px-1 py-1.5 text-left hover:border-slate-200 hover:bg-slate-50"
              >
                <div className="w-28 flex-shrink-0 text-xs text-slate-700">
                  <StageTag code={s.code} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-slate-700/80 group-hover:bg-teal-600"
                      style={{ width: `${width}%` }}
                    />
                  </div>
                </div>
                <div className="w-16 flex-shrink-0 text-right text-sm font-semibold tabular-nums text-slate-900">
                  {s.count}
                </div>
                <div className="w-14 flex-shrink-0 text-right text-xs tabular-nums text-slate-500">
                  {pct}%
                </div>
              </button>
            </li>
          )
        })}
      </ul>
    </SectionCard>
  )
}
