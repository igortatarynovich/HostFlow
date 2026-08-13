import { Link } from 'react-router-dom'
import type { UiSemanticTone } from './palette'

export type InsightAction = {
  label: string
  href: string
}

export type InsightCardProps = {
  title: string
  body: string
  tone?: Extract<UiSemanticTone, 'success' | 'warning' | 'danger' | 'info' | 'neutral'>
  actions?: InsightAction[]
  present?: boolean
}

const TONE_WRAP: Record<NonNullable<InsightCardProps['tone']>, string> = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  warning: 'border-amber-200 bg-amber-50 text-amber-900',
  danger: 'border-rose-200 bg-rose-50 text-rose-900',
  info: 'border-blue-200 bg-blue-50 text-blue-900',
  neutral: 'border-slate-200 bg-slate-50 text-slate-800',
}

export function InsightCard({ title, body, tone = 'warning', actions = [], present = false }: InsightCardProps) {
  const visibleActions = present ? [] : actions
  return (
    <div className={`rounded-lg border px-3 py-2 text-sm ${TONE_WRAP[tone]}`}>
      <div className="font-medium">{title}</div>
      <p className="mt-0.5 text-xs opacity-90">{body}</p>
      {visibleActions.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {visibleActions.map((action) => (
            <Link
              key={action.href + action.label}
              to={action.href}
              className="text-xs font-medium text-brand-800 underline-offset-2 hover:underline"
            >
              {action.label}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  )
}
