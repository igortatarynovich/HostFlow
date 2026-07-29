import type { ReactElement } from 'react'
import { ResponsiveContainer } from 'recharts'

/**
 * Mount ResponsiveContainer only when layout is ready.
 * Avoids recharts width/height(-1) spam during tab switches and range reloads.
 */
export function ChartHost({
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
        <div className="h-full w-full animate-pulse rounded-md bg-slate-100/80" aria-hidden />
      )}
    </div>
  )
}
