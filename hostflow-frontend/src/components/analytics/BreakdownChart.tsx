import { Bar, BarChart, CartesianGrid, Cell, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartFrame } from './ChartFrame'
import { CHART_CHROME } from './palette'

export type BreakdownRow = {
  key: string
  name: string
  fullName?: string
  value: number
  fill: string
  href?: string
}

export type BreakdownChartProps = {
  data: BreakdownRow[]
  ready: boolean
  formatValue: (value: number) => string
  className?: string
  layout?: 'vertical' | 'horizontal'
  onPointClick?: (row: BreakdownRow) => void
}

export function BreakdownChart({
  data,
  ready,
  formatValue,
  className = 'h-52 w-full min-w-0',
  layout = 'vertical',
  onPointClick,
}: BreakdownChartProps) {
  const vertical = layout === 'vertical'
  return (
    <ChartFrame className={className} ready={ready}>
      <BarChart
        layout={vertical ? 'vertical' : 'horizontal'}
        data={data}
        margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_CHROME.grid} horizontal={!vertical} vertical={vertical} />
        {vertical ? (
          <>
            <XAxis type="number" tick={{ fontSize: 11, fill: CHART_CHROME.tick }} />
            <YAxis
              type="category"
              dataKey="name"
              width={110}
              tick={{ fontSize: 11, fill: CHART_CHROME.axis }}
            />
          </>
        ) : (
          <>
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: CHART_CHROME.tick }} />
            <YAxis type="number" tick={{ fontSize: 11, fill: CHART_CHROME.tick }} />
          </>
        )}
        <Tooltip
          formatter={((v: number) => formatValue(v)) as never}
          labelFormatter={(_, payload) =>
            String((payload?.[0]?.payload as BreakdownRow | undefined)?.fullName || '')
          }
        />
        <Bar
          dataKey="value"
          radius={vertical ? [0, 4, 4, 0] : [4, 4, 0, 0]}
          maxBarSize={18}
          cursor={onPointClick ? 'pointer' : undefined}
          onClick={(entry) => {
            const row = (entry as { payload?: BreakdownRow } | undefined)?.payload
            if (row && onPointClick) onPointClick(row)
          }}
        >
          {data.map((entry) => (
            <Cell key={entry.key} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ChartFrame>
  )
}
