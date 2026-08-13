import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartFrame } from './ChartFrame'
import { CHART_CHROME } from './palette'

export type FunnelStep = {
  key: string
  name: string
  value: number
  fill: string
}

export type FunnelChartProps = {
  steps: FunnelStep[]
  ready: boolean
  formatValue: (value: number) => string
  className?: string
}

function conversionLabel(current: number, previous: number): string | null {
  if (!previous) return null
  return `${((current / previous) * 100).toFixed(1)}%`
}

export function FunnelChart({
  steps,
  ready,
  formatValue,
  className = 'h-48 w-full min-w-0',
}: FunnelChartProps) {
  return (
    <div className="space-y-2">
      <ChartFrame className={className} ready={ready}>
        <BarChart data={steps} layout="vertical" margin={{ left: 8, right: 12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_CHROME.grid} horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11, fill: CHART_CHROME.tick }} />
          <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11, fill: CHART_CHROME.axis }} />
          <Tooltip formatter={((v: number) => formatValue(v)) as never} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
            {steps.map((entry) => (
              <Cell key={entry.key} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ChartFrame>
      {steps.length > 1 ? (
        <ol className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
          {steps.map((step, i) => {
            if (i === 0) return null
            const conv = conversionLabel(step.value, steps[i - 1].value)
            return (
              <li key={step.key}>
                {steps[i - 1].name} → {step.name}
                {conv ? <span className="ml-1 font-medium tabular-nums text-slate-700">{conv}</span> : null}
              </li>
            )
          })}
        </ol>
      ) : null}
    </div>
  )
}
