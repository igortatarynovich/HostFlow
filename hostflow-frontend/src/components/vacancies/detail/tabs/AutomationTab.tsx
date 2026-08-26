import React, { useMemo } from 'react'
import { SectionCard } from '../../../ui/SectionCard'
import {
  buildAutomationRules,
  type CriteriaFormSlice,
} from '../criteriaForm'

type Props = {
  values: CriteriaFormSlice
  title: string
  empty: string
  ifLabel: string
  thenLabel: string
}

export function AutomationTab({ values, title, empty, ifLabel, thenLabel }: Props) {
  const rules = useMemo(() => buildAutomationRules(values), [values])

  return (
    <SectionCard title={title}>
      {rules.length === 0 ? (
        <p className="text-sm text-slate-500">{empty}</p>
      ) : (
        <ol className="space-y-3">
          {rules.map((r) => (
            <li
              key={r.id}
              className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
            >
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {ifLabel}
              </div>
              <div className="mt-1 text-sm font-medium text-slate-900">{r.when}</div>
              <div className="my-2 text-center text-slate-400">↓</div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {thenLabel}
              </div>
              <div className="mt-1 inline-flex rounded-md bg-teal-50 px-2 py-1 text-sm font-semibold text-teal-800">
                {r.then}
              </div>
            </li>
          ))}
        </ol>
      )}
    </SectionCard>
  )
}
