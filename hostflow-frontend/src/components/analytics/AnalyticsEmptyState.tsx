import type { ReactNode } from 'react'

export type AnalyticsEmptyKind = 'no_data' | 'insufficient_data' | 'tracking_not_started'

export type AnalyticsEmptyStateProps = {
  kind: AnalyticsEmptyKind
  title: string
  description?: string
  action?: ReactNode
}

export function AnalyticsEmptyState({ kind, title, description, action }: AnalyticsEmptyStateProps) {
  return (
    <div
      className="rounded-lg border border-slate-200 bg-white px-4 py-6 text-sm text-slate-600"
      data-analytics-empty={kind}
    >
      <div className="font-medium text-slate-800">{title}</div>
      {description ? <p className="mt-1 text-xs text-slate-500">{description}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  )
}
