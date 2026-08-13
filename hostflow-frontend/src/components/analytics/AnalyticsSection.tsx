import type { ReactNode } from 'react'

export function AnalyticsSection({
  title,
  subtitle,
  actions,
  children,
  density = 'operational',
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
  density?: 'story' | 'operational'
}) {
  return (
    <section
      className={
        density === 'story'
          ? 'rounded-xl border border-slate-200 bg-white p-6 shadow-sm'
          : 'rounded-xl border border-slate-200 bg-white p-4 shadow-sm'
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {subtitle ? <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p> : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  )
}
