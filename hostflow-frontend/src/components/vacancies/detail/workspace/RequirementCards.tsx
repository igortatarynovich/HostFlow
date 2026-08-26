import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'

export type RequirementCardModel = {
  title: string
  items: string[]
  empty?: string
}

type Props = {
  title: string
  mandatoryTitle: string
  preferredTitle: string
  preferredEmptyNote: string
  mandatory: RequirementCardModel[]
  preferred: RequirementCardModel[]
  onEdit?: () => void
  editLabel?: string
}

function Cards({ models }: { models: RequirementCardModel[] }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {models.map((m) => (
        <div key={m.title} className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="text-sm font-semibold text-slate-800">{m.title}</div>
          {m.items.length === 0 ? (
            <p className="mt-2 text-xs text-slate-500">{m.empty || '—'}</p>
          ) : (
            <ul className="mt-2 space-y-1">
              {m.items.map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="text-emerald-600" aria-hidden>
                    ✔
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  )
}

export function RequirementCards({
  title,
  mandatoryTitle,
  preferredTitle,
  preferredEmptyNote,
  mandatory,
  preferred,
  onEdit,
  editLabel,
}: Props) {
  const preferredHasItems = preferred.some((p) => p.items.length > 0)

  return (
    <SectionCard title={title}>
      {onEdit && editLabel ? (
        <div className="mb-3 flex justify-end">
          <button type="button" className="btn-secondary btn-xs" onClick={onEdit}>
            {editLabel}
          </button>
        </div>
      ) : null}
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {mandatoryTitle}
      </div>
      <Cards models={mandatory} />
      <div className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {preferredTitle}
      </div>
      {preferredHasItems ? (
        <Cards models={preferred} />
      ) : (
        <p className="text-xs text-slate-500">{preferredEmptyNote}</p>
      )}
    </SectionCard>
  )
}
