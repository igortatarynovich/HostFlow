import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'

type Props = {
  title: string
  hint: string
  fulfilled: number
  needed: number
}

export function OrderProgress({ title, hint, fulfilled, needed }: Props) {
  const pct = needed > 0 ? Math.min(100, Math.round((fulfilled / needed) * 100)) : 0
  return (
    <SectionCard title={title}>
      <p className="mb-2 text-xs text-slate-500">{hint}</p>
      <div className="flex items-center justify-between text-sm font-medium text-slate-800">
        <span>
          {fulfilled} / {needed}
        </span>
        <span className="tabular-nums text-slate-500">{pct}%</span>
      </div>
      <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-teal-600 transition-all" style={{ width: `${pct}%` }} />
      </div>
    </SectionCard>
  )
}
