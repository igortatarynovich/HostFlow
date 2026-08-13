import type { ReactNode } from 'react'
import clsx from 'clsx'
import { KPI_TONE_CLASSES, type UiSemanticTone } from './palette'

export type AnalyticsStoryHeroProps = {
  label: string
  value: string
  unit?: string
  caption?: string
  tone?: UiSemanticTone
  supporting?: ReactNode
}

export function AnalyticsStoryHero({
  label,
  value,
  unit,
  caption,
  tone = 'neutral',
  supporting,
}: AnalyticsStoryHeroProps) {
  const styles = KPI_TONE_CLASSES[tone]
  return (
    <section className={clsx('rounded-xl border px-6 py-6 shadow-sm', styles.wrap)}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <div className="mt-2 flex flex-wrap items-baseline gap-2">
        <span className={clsx('text-3xl font-semibold tabular-nums tracking-tight', styles.value)}>{value}</span>
        {unit ? <span className="text-sm text-slate-500">{unit}</span> : null}
      </div>
      {caption ? <p className="mt-2 max-w-2xl text-sm text-slate-600">{caption}</p> : null}
      {supporting ? <div className="mt-6">{supporting}</div> : null}
    </section>
  )
}
