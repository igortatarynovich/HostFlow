import { Area, AreaChart, CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartFrame } from './ChartFrame'
import { CHART_CHROME, UI_SEMANTIC_FILL } from './palette'

export type TrendPoint = {
  key: string
  label: string
  value: number
}

export type TrendChartProps = {
  data: TrendPoint[]
  ready: boolean
  formatValue: (value: number) => string
  variant?: 'line' | 'area'
  className?: string
  stroke?: string
}

export function TrendChart({
  data,
  ready,
  formatValue,
  variant = 'line',
  className = 'h-52 w-full min-w-0',
  stroke = UI_SEMANTIC_FILL.info,
}: TrendChartProps) {
  const Chart = variant === 'area' ? AreaChart : LineChart
  return (
    <ChartFrame className={className} ready={ready}>
      <Chart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_CHROME.grid} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: CHART_CHROME.tick }} />
        <YAxis tick={{ fontSize: 11, fill: CHART_CHROME.tick }} />
        <Tooltip formatter={((v: number) => formatValue(v)) as never} />
        {variant === 'area' ? (
          <Area type="monotone" dataKey="value" stroke={stroke} fill={stroke} fillOpacity={0.15} />
        ) : (
          <Line type="monotone" dataKey="value" stroke={stroke} strokeWidth={2} dot={false} />
        )}
      </Chart>
    </ChartFrame>
  )
}
