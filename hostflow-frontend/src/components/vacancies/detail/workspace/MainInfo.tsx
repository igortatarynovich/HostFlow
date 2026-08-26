import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'

type Props = {
  title: string
  rows: { label: string; value: React.ReactNode }[]
}

export function MainInfo({ title, rows }: Props) {
  return (
    <SectionCard title={title}>
      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {rows.map((r) => (
          <div key={r.label}>
            <dt className="text-xs text-slate-500">{r.label}</dt>
            <dd className="mt-0.5 text-sm font-medium text-slate-900">{r.value || '—'}</dd>
          </div>
        ))}
      </dl>
    </SectionCard>
  )
}
