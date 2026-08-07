import React from 'react'
import { SectionCard } from '../../../ui/SectionCard'
import StageTag from '../../../StageTag'
import { CRM_APP_PATHS } from '../../../../app/crmAppPaths'

type Props = {
  loading: boolean
  items: any[]
  stageFilter: string | null
  onClearFilter: () => void
  labels: {
    title: string
    loading: string
    empty: string
    filterActive: string
    clearFilter: string
    candidate: string
    email: string
    stage: string
  }
}

export function CandidatesTab({
  loading,
  items,
  stageFilter,
  onClearFilter,
  labels,
}: Props) {
  const filtered = stageFilter
    ? items.filter((c) => String(c.stage ?? c.status ?? '') === stageFilter)
    : items

  return (
    <SectionCard title={labels.title}>
      {stageFilter ? (
        <div className="mb-3 flex flex-wrap items-center gap-2 text-sm text-slate-700">
          <span>
            {labels.filterActive}: <StageTag code={stageFilter} />
          </span>
          <button type="button" className="btn-secondary btn-xs" onClick={onClearFilter}>
            {labels.clearFilter}
          </button>
        </div>
      ) : null}
      {loading ? (
        <div className="text-slate-500">{labels.loading}</div>
      ) : filtered.length === 0 ? (
        <div className="text-slate-500">{labels.empty}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
              <tr>
                <th>{labels.candidate}</th>
                <th>{labels.email}</th>
                <th>{labels.stage}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c: any) => (
                <tr key={c.id}>
                  <td className="py-2 pr-3">
                    <a
                      className="hover:underline"
                      href={`${CRM_APP_PATHS.candidates}/${c.id}`}
                    >
                      {c.name ||
                        [c.first_name, c.last_name].filter(Boolean).join(' ') ||
                        '—'}
                    </a>
                  </td>
                  <td className="py-2 pr-3 text-slate-600">{c.email || '—'}</td>
                  <td className="py-2 pr-3">
                    <StageTag code={String(c.stage ?? c.status ?? 'new')} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  )
}
