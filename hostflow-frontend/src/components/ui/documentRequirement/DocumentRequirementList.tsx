import type { ReactNode } from 'react'
import { documentRequirementGridClass } from './documentRequirementGrid'

export type DocumentRequirementColumns = {
  name: string
  requirement: string
  presence: string
  file: string
  action: string
}

export function DocumentRequirementList({
  children,
  columns,
}: {
  children: ReactNode
  columns?: DocumentRequirementColumns
}) {
  return (
    <div>
      {columns ? (
        <div className={`${documentRequirementGridClass} pb-2 text-xs text-slate-500`}>
          <div>{columns.name}</div>
          <div>{columns.requirement}</div>
          <div>{columns.presence}</div>
          <div>{columns.file}</div>
          <div className="md:text-right">{columns.action}</div>
        </div>
      ) : null}
      <div className="divide-y divide-slate-100">{children}</div>
    </div>
  )
}
