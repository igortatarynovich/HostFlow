import type { ReactElement } from 'react'
import { ResponsiveContainer } from 'recharts'

/** Implementation frame for kit charts. Product pages must not import this. */
export function ChartFrame({
  className,
  ready,
  children,
}: {
  className: string
  ready: boolean
  children: ReactElement
}) {
  return (
    <div className={className}>
      {ready ? (
        <ResponsiveContainer width="100%" height="100%" minWidth={0} debounce={50}>
          {children}
        </ResponsiveContainer>
      ) : (
        <div className="h-full w-full animate-pulse rounded bg-slate-100/80" aria-hidden />
      )}
    </div>
  )
}
