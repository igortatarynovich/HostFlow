import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'

type Props = {
  title: string
  name: string
  subtitle?: string
  messageLabel?: string
  messageHref?: string
}

export function OwnerCard({ title, name, subtitle, messageLabel, messageHref }: Props) {
  return (
    <SectionCard title={title}>
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-sm font-semibold text-emerald-800">
          {(name || '?').slice(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-slate-900">{name || '—'}</div>
          {subtitle ? <div className="truncate text-xs text-slate-500">{subtitle}</div> : null}
        </div>
      </div>
      {messageHref && messageLabel ? (
        <a href={messageHref} className="btn-secondary btn-sm mt-3 inline-flex">
          {messageLabel}
        </a>
      ) : null}
    </SectionCard>
  )
}
