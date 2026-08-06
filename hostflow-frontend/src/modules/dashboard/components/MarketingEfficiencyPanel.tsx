import { useMemo } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TranslateFn } from '../../../i18n'
import { ChartHost } from './ChartHost'

export type MarketingCampaignMetric = {
  campaign_id: string
  name: string
  spend: number
  leads: number
  cost_per_lead: number | null
  impressions: number | null
  reach: number | null
  is_best_cpl: boolean
}

export type MarketingDaySeriesPoint = {
  day: string
  spend: number
  leads: number
  impressions: number
  reach: number
}

export type MarketingTotals = {
  spend: number
  leads: number
  cost_per_lead: number | null
  impressions: number | null
  reach: number | null
  currency: string | null
}

export interface MarketingEfficiencyPanelProps {
  t: TranslateFn
  formatNumber: (value?: number) => string
  formatMoney: (value?: number | null, currency?: string | null) => string
  rows: MarketingCampaignMetric[]
  totals: MarketingTotals
  series: MarketingDaySeriesPoint[]
  loading: boolean
}

const BAR_PALETTE = ['#0ea5e9', '#8b5cf6', '#14b8a6', '#f97316', '#6366f1', '#ec4899', '#84cc16']
const PIE_PALETTE = [
  '#0ea5e9',
  '#8b5cf6',
  '#14b8a6',
  '#f97316',
  '#e11d48',
  '#64748b',
  '#22c55e',
  '#06b6d4',
]

function truncateLabel(value: string, max = 18): string {
  const s = String(value || '')
  return s.length > max ? `${s.slice(0, max - 1)}…` : s
}

export function MarketingEfficiencyPanel({
  t,
  formatNumber,
  formatMoney,
  rows,
  totals,
  series,
  loading,
}: MarketingEfficiencyPanelProps) {
  const chartsReady = !loading

  const spendBars = useMemo(
    () =>
      [...rows]
        .sort((a, b) => b.spend - a.spend)
        .slice(0, 12)
        .map((r, i) => ({
          key: r.campaign_id,
          name: truncateLabel(r.name),
          fullName: r.name,
          value: r.spend,
          fill: BAR_PALETTE[i % BAR_PALETTE.length],
        })),
    [rows],
  )

  const leadsBars = useMemo(
    () =>
      [...rows]
        .sort((a, b) => b.leads - a.leads)
        .slice(0, 12)
        .map((r, i) => ({
          key: r.campaign_id,
          name: truncateLabel(r.name),
          fullName: r.name,
          value: r.leads,
          fill: BAR_PALETTE[i % BAR_PALETTE.length],
        })),
    [rows],
  )

  const cplBars = useMemo(
    () =>
      [...rows]
        .filter((r) => r.cost_per_lead != null && r.leads > 0)
        .sort((a, b) => (a.cost_per_lead ?? 0) - (b.cost_per_lead ?? 0))
        .slice(0, 12)
        .map((r, i) => ({
          key: r.campaign_id,
          name: truncateLabel(r.name),
          fullName: r.name,
          value: r.cost_per_lead ?? 0,
          fill: r.is_best_cpl ? '#16a34a' : BAR_PALETTE[i % BAR_PALETTE.length],
        })),
    [rows],
  )

  const leadsPie = useMemo(
    () =>
      [...rows]
        .filter((r) => r.leads > 0)
        .sort((a, b) => b.leads - a.leads)
        .slice(0, 8)
        .map((r, i) => ({
          key: r.campaign_id,
          name: truncateLabel(r.name, 26),
          value: r.leads,
          fill: PIE_PALETTE[i % PIE_PALETTE.length],
        })),
    [rows],
  )

  if (!loading && rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
        {t('app.dashboard.marketing.empty')}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('app.dashboard.marketing.stats.spend')}
          </div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {formatMoney(totals.spend, totals.currency)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('app.dashboard.marketing.stats.leads')}
          </div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {formatNumber(totals.leads)}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('app.dashboard.marketing.stats.cpl')}
          </div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {totals.cost_per_lead != null
              ? formatMoney(totals.cost_per_lead, totals.currency)
              : '—'}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('app.dashboard.marketing.stats.impressions')}
          </div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {totals.impressions != null ? formatNumber(totals.impressions) : '—'}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {t('app.dashboard.marketing.stats.reach')}
          </div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">
            {totals.reach != null ? formatNumber(totals.reach) : '—'}
          </div>
        </div>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.dashboard.marketing.charts.trend_title')}
        </h2>
        <p className="mt-0.5 text-xs text-slate-500">
          {t('app.dashboard.marketing.charts.trend_subtitle')}
        </p>
        {series.length === 0 ? (
          <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.marketing.empty')}</p>
        ) : (
          <ChartHost className="mt-2 h-64 w-full min-w-0" ready={chartsReady}>
            <LineChart data={series} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 10, fill: '#64748b' }}
                minTickGap={24}
              />
              <YAxis
                yAxisId="spend"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(v) => formatNumber(Number(v))}
              />
              <YAxis
                yAxisId="leads"
                orientation="right"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(v) => formatNumber(Number(v))}
              />
              <Tooltip
                formatter={((value: number, name: string) => {
                  if (name === 'spend') {
                    return [formatMoney(value, totals.currency), t('app.dashboard.marketing.stats.spend')]
                  }
                  return [formatNumber(value), t('app.dashboard.marketing.stats.leads')]
                }) as never}
                labelFormatter={(label) => String(label)}
              />
              <Legend
                formatter={(value) =>
                  value === 'spend'
                    ? t('app.dashboard.marketing.stats.spend')
                    : t('app.dashboard.marketing.stats.leads')
                }
              />
              <Line
                yAxisId="spend"
                type="monotone"
                dataKey="spend"
                stroke="#0ea5e9"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
              <Line
                yAxisId="leads"
                type="monotone"
                dataKey="leads"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ChartHost>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.marketing.charts.spend_title')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('app.dashboard.marketing.charts.spend_subtitle')}
          </p>
          {spendBars.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.marketing.empty')}</p>
          ) : (
            <ChartHost className="mt-2 h-64 w-full min-w-0" ready={chartsReady}>
              <BarChart
                layout="vertical"
                data={spendBars}
                margin={{ top: 4, right: 16, left: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={128}
                  tick={{ fontSize: 10, fill: '#475569' }}
                />
                <Tooltip
                  formatter={((value: number) => [
                    formatMoney(value, totals.currency),
                    t('app.dashboard.marketing.stats.spend'),
                  ]) as never}
                  labelFormatter={((_, payload) =>
                    String((payload as { payload?: { fullName?: string } }[])?.[0]?.payload?.fullName || ''),
                  ) as never}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {spendBars.map((d) => (
                    <Cell key={d.key} fill={d.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ChartHost>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.marketing.charts.leads_title')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('app.dashboard.marketing.charts.leads_subtitle')}
          </p>
          {leadsBars.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.marketing.empty')}</p>
          ) : (
            <ChartHost className="mt-2 h-64 w-full min-w-0" ready={chartsReady}>
              <BarChart
                layout="vertical"
                data={leadsBars}
                margin={{ top: 4, right: 16, left: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={128}
                  tick={{ fontSize: 10, fill: '#475569' }}
                />
                <Tooltip
                  formatter={((value: number) => [
                    formatNumber(value),
                    t('app.dashboard.marketing.stats.leads'),
                  ]) as never}
                  labelFormatter={((_, payload) =>
                    String((payload as { payload?: { fullName?: string } }[])?.[0]?.payload?.fullName || ''),
                  ) as never}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {leadsBars.map((d) => (
                    <Cell key={d.key} fill={d.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ChartHost>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.marketing.charts.cpl_title')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('app.dashboard.marketing.charts.cpl_subtitle')}
          </p>
          {cplBars.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.marketing.empty')}</p>
          ) : (
            <ChartHost className="mt-2 h-64 w-full min-w-0" ready={chartsReady}>
              <BarChart
                layout="vertical"
                data={cplBars}
                margin={{ top: 4, right: 16, left: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={128}
                  tick={{ fontSize: 10, fill: '#475569' }}
                />
                <Tooltip
                  formatter={((value: number) => [
                    formatMoney(value, totals.currency),
                    t('app.dashboard.marketing.stats.cpl'),
                  ]) as never}
                  labelFormatter={((_, payload) =>
                    String((payload as { payload?: { fullName?: string } }[])?.[0]?.payload?.fullName || ''),
                  ) as never}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {cplBars.map((d) => (
                    <Cell key={d.key} fill={d.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ChartHost>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.marketing.charts.mix_title')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('app.dashboard.marketing.charts.mix_subtitle')}
          </p>
          {leadsPie.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.marketing.empty')}</p>
          ) : (
            <div className="mt-2 flex flex-col items-center gap-3 sm:flex-row">
              <ChartHost className="h-52 w-full min-w-0 sm:w-1/2" ready={chartsReady}>
                <PieChart>
                  <Pie
                    data={leadsPie}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={88}
                    paddingAngle={2}
                  >
                    {leadsPie.map((d) => (
                      <Cell key={d.key} fill={d.fill} stroke="#fff" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={((value: number) => [
                      formatNumber(value),
                      t('app.dashboard.marketing.stats.leads'),
                    ]) as never}
                  />
                </PieChart>
              </ChartHost>
              <ul className="w-full space-y-2 sm:w-1/2">
                {leadsPie.map((entry) => (
                  <li key={entry.key} className="flex items-center justify-between gap-2 text-sm">
                    <span className="flex min-w-0 items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: entry.fill }}
                      />
                      <span className="truncate text-slate-700">{entry.name}</span>
                    </span>
                    <span className="shrink-0 tabular-nums font-semibold text-slate-900">
                      {formatNumber(entry.value)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </div>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.marketing.table.title')}
          </h3>
          <p className="text-xs text-slate-500">{t('app.dashboard.marketing.table.subtitle')}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">
                  {t('app.dashboard.marketing.table.campaign')}
                </th>
                <th className="px-4 py-2 font-medium">{t('app.dashboard.marketing.stats.leads')}</th>
                <th className="px-4 py-2 font-medium">{t('app.dashboard.marketing.stats.spend')}</th>
                <th className="px-4 py-2 font-medium">{t('app.dashboard.marketing.stats.cpl')}</th>
                <th className="px-4 py-2 font-medium">
                  {t('app.dashboard.marketing.stats.impressions')}
                </th>
                <th className="px-4 py-2 font-medium">{t('app.dashboard.marketing.stats.reach')}</th>
              </tr>
            </thead>
            <tbody>
              {[...rows]
                .sort((a, b) => b.spend - a.spend)
                .map((r) => (
                  <tr key={r.campaign_id} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-medium text-slate-800">
                      {r.name}
                      {r.is_best_cpl ? (
                        <span className="ml-2 rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-emerald-700">
                          {t('app.dashboard.marketing.table.best_cpl')}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-2 tabular-nums">{formatNumber(r.leads)}</td>
                    <td className="px-4 py-2 tabular-nums">
                      {formatMoney(r.spend, totals.currency)}
                    </td>
                    <td className="px-4 py-2 tabular-nums">
                      {r.cost_per_lead != null
                        ? formatMoney(r.cost_per_lead, totals.currency)
                        : '—'}
                    </td>
                    <td className="px-4 py-2 tabular-nums">
                      {r.impressions != null ? formatNumber(r.impressions) : '—'}
                    </td>
                    <td className="px-4 py-2 tabular-nums">
                      {r.reach != null ? formatNumber(r.reach) : '—'}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
