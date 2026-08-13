import { CHART_CHROME, resolveSeriesFill, type UiSemanticTone } from './palette'

export type TargetProgressProps = {
  label: string
  value: number
  target: number
  format?: (value: number) => string
  tone?: UiSemanticTone
}

export function TargetProgress({
  label,
  value,
  target,
  format = (n) => String(n),
  tone = 'info',
}: TargetProgressProps) {
  const safeTarget = target > 0 ? target : 0
  const ratio = safeTarget ? Math.min(1, Math.max(0, value / safeTarget)) : 0
  const fill = resolveSeriesFill({ space: 'semantic', tone })

  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-2 text-xs">
        <span className="truncate text-slate-600">{label}</span>
        <span className="shrink-0 tabular-nums text-slate-800">
          {format(value)} / {format(target)}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded bg-slate-100" style={{ backgroundColor: CHART_CHROME.track }}>
        <div className="h-full rounded" style={{ width: `${Math.round(ratio * 100)}%`, backgroundColor: fill }} />
      </div>
    </div>
  )
}
