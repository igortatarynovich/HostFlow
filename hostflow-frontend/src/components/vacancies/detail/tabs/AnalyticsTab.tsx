import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'
import { FunnelPanel } from '../workspace/FunnelPanel'
import type { PipelineMetrics } from '../pipelineMetrics'

type Props = {
  metrics: PipelineMetrics
  onStageClick: (code: string) => void
  labels: {
    title: string
    funnel: string
    funnelEmpty: string
    reserved: string
    applications: string
    conversion: string
    sources: string
    cost: string
    timeToHire: string
    hireRate: string
  }
}

const SLOTS = [
  'applications',
  'conversion',
  'sources',
  'cost',
  'timeToHire',
  'hireRate',
] as const

export function AnalyticsTab({ metrics, onStageClick, labels }: Props) {
  const slotLabel: Record<(typeof SLOTS)[number], string> = {
    applications: labels.applications,
    conversion: labels.conversion,
    sources: labels.sources,
    cost: labels.cost,
    timeToHire: labels.timeToHire,
    hireRate: labels.hireRate,
  }

  return (
    <div className="space-y-4">
      <SectionCard title={labels.title}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {SLOTS.map((key) => (
            <div
              key={key}
              className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-4"
            >
              <div className="text-xs uppercase tracking-wide text-slate-400">{slotLabel[key]}</div>
              <div className="mt-2 text-lg font-semibold text-slate-300">—</div>
              <div className="mt-1 text-[11px] text-slate-400">{labels.reserved}</div>
            </div>
          ))}
        </div>
      </SectionCard>
      <FunnelPanel
        title={labels.funnel}
        stages={metrics.stages}
        total={metrics.total}
        onStageClick={onStageClick}
        emptyLabel={labels.funnelEmpty}
      />
    </div>
  )
}
