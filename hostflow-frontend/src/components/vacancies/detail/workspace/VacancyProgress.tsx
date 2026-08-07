import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'
import type { PipelineMetrics } from '../pipelineMetrics'

type Props = {
  title: string
  metrics: PipelineMetrics
  labels: {
    headcount: string
    hired: string
    remaining: string
    completion: string
  }
}

function Donut({ pct }: { pct: number }) {
  const r = 36
  const c = 2 * Math.PI * r
  const clamped = Math.max(0, Math.min(100, pct))
  const offset = c - (clamped / 100) * c
  return (
    <svg width="96" height="96" viewBox="0 0 96 96" className="flex-shrink-0" aria-hidden>
      <circle cx="48" cy="48" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
      <circle
        cx="48"
        cy="48"
        r={r}
        fill="none"
        stroke="#0d9488"
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={offset}
        transform="rotate(-90 48 48)"
      />
      <text
        x="48"
        y="52"
        textAnchor="middle"
        className="fill-slate-800"
        style={{ fontSize: '16px', fontWeight: 600 }}
      >
        {Number.isFinite(clamped) ? `${Math.round(clamped)}%` : '—'}
      </text>
    </svg>
  )
}

export function VacancyProgress({ title, metrics, labels }: Props) {
  const cells = [
    { label: labels.headcount, value: metrics.plan ?? '—' },
    { label: labels.hired, value: metrics.hired },
    { label: labels.remaining, value: metrics.remaining ?? '—' },
    {
      label: labels.completion,
      value: metrics.completionPct != null ? `${metrics.completionPct}%` : '—',
    },
  ]

  return (
    <SectionCard title={title}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <Donut pct={metrics.completionPct ?? 0} />
        <div className="grid flex-1 grid-cols-2 gap-3 sm:grid-cols-4">
          {cells.map((cell) => (
            <div
              key={cell.label}
              className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2"
            >
              <div className="text-[11px] uppercase tracking-wide text-slate-500">{cell.label}</div>
              <div className="mt-1 text-xl font-semibold tabular-nums text-slate-900">
                {cell.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </SectionCard>
  )
}
