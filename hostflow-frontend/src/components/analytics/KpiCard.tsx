import clsx from 'clsx'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { KPI_TONE_CLASSES, type UiSemanticTone } from './palette'

export type KpiDelta = {
  label: string
  direction: 'up' | 'down' | 'flat'
  polarity: 'good' | 'bad' | 'neutral'
}

export type KpiCardProps = {
  label: string
  value: string
  tone?: UiSemanticTone
  delta?: KpiDelta
  comparison?: string
  href?: string
  className?: string
  size?: 'md' | 'hero'
}

const DELTA_CLASSES: Record<KpiDelta['polarity'], string> = {
  good: 'text-emerald-700',
  bad: 'text-rose-700',
  neutral: 'text-slate-500',
}

function DeltaMark({ direction }: { direction: KpiDelta['direction'] }) {
  if (direction === 'up') return <span aria-hidden>↑</span>
  if (direction === 'down') return <span aria-hidden>↓</span>
  return <span aria-hidden>→</span>
}

export function KpiCard({
  label,
  value,
  tone = 'neutral',
  delta,
  comparison,
  href,
  className,
  size = 'md',
}: KpiCardProps) {
  const styles = KPI_TONE_CLASSES[tone]
  const inner = (
    <>
      <div className={`absolute inset-y-0 left-0 w-1 ${styles.bar}`} />
      <div className="pl-1.5">
        <div className="text-xs text-slate-500">{label}</div>
        <div
          className={clsx(
            'font-semibold tabular-nums tracking-tight',
            size === 'hero' ? 'text-3xl' : 'text-xl',
            styles.value,
          )}
        >
          {value}
        </div>
        {delta ? (
          <div className={clsx('mt-0.5 text-xs', DELTA_CLASSES[delta.polarity])}>
            <DeltaMark direction={delta.direction} /> {delta.label}
          </div>
        ) : null}
        {comparison && !delta ? <div className="mt-0.5 text-xs text-slate-500">{comparison}</div> : null}
      </div>
    </>
  )

  const wrapClass = clsx(
    'relative overflow-hidden rounded-lg border px-3 py-2',
    styles.wrap,
    href && 'block hover:ring-1 hover:ring-brand-200',
    className,
  )

  if (href) {
    return (
      <Link to={href} className={wrapClass}>
        {inner}
      </Link>
    )
  }

  return <div className={wrapClass}>{inner}</div>
}

export function KpiCardGrid({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={clsx('grid gap-3 sm:grid-cols-2 lg:grid-cols-4', className)}>{children}</div>
}
