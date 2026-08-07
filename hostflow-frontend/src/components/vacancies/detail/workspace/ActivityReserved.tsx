import React from 'react'
import { SectionCard } from '../../ui/SectionCard'

type Props = {
  title: string
  message: string
}

export function ActivityReserved({ title, message }: Props) {
  return (
    <SectionCard title={title}>
      <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-600">
        {message}
      </p>
    </SectionCard>
  )
}
