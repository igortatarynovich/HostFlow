import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getHandoffStats, type HandoffStatsResponse } from '../api/analytics'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useI18n } from '../i18n'
import { formatAnalyticsLoadError } from '../modules/dashboard/analyticsLoad'
import { ChartHost } from '../modules/dashboard/components/ChartHost'
import { QUICK_RANGE_OPTIONS } from '../modules/dashboard/constants'
import type { QuickRange } from '../modules/dashboard/types'
import { calcRange } from '../modules/dashboard/utils'

/**
 * HR-owned efficiency: handoff in → accepted / returned / rejected.
 * Not recruitment stages or sales inquiry funnel.
 */
export default function HrEfficiencyDashboard() {
  const { t, locale } = useI18n()
  const loadSeq = useRef(0)
  const initialRange = calcRange('30d')
  const [dateFrom, setDateFrom] = useState(initialRange.from)
  const [dateTo, setDateTo] = useState(initialRange.to)
  const [activeRange, setActiveRange] = useState<QuickRange | 'custom'>('30d')
  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)
  const [stats, setStats] = useState<HandoffStatsResponse | null>(null)

  const numberFormatter = useMemo(
    () =>
      new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US'),
    [locale],
  )
  const formatNumber = useCallback(
    (value?: number) => numberFormatter.format(value ?? 0),
    [numberFormatter],
  )

  const quickRangeOptions = useMemo(
    () =>
      QUICK_RANGE_OPTIONS.map((value) => ({
        value,
        label: t(`app.dashboard.ranges.${value}`),
      })),
    [t],
  )

  const rangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo)
  const chartsReady = !loading

  const load = useCallback(async () => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      setErrText(t('app.dashboard.errors.range_invalid'))
      return
    }
    const seq = ++loadSeq.current
    setLoading(true)
    setErrText(null)
    try {
      const data = await getHandoffStats({
        from: dateFrom || undefined,
        to: dateTo || undefined,
      })
      if (seq !== loadSeq.current) return
      setStats(data)
    } catch (e: unknown) {
      if (seq !== loadSeq.current) return
      setErrText(formatAnalyticsLoadError(e, t))
    } finally {
      if (seq === loadSeq.current) setLoading(false)
    }
  }, [dateFrom, dateTo, t])

  useEffect(() => {
    void load()
  }, [load])

  const applyQuickRange = (range: QuickRange) => {
    const next = calcRange(range)
    setActiveRange(range)
    setDateFrom(next.from)
    setDateTo(next.to)
  }

  const requested = stats?.total_requested ?? 0
  const accepted = stats?.total_accepted ?? 0
  const rejected = stats?.total_rejected ?? 0
  const returned = stats?.total_returned ?? 0

  const flow = [
    {
      key: 'requested',
      name: t('app.dashboard.hr.flow.requested'),
      value: requested,
      fill: '#64748b',
    },
    {
      key: 'accepted',
      name: t('app.dashboard.hr.flow.accepted'),
      value: accepted,
      fill: '#16a34a',
    },
    {
      key: 'returned',
      name: t('app.dashboard.hr.flow.returned'),
      value: returned,
      fill: '#f97316',
    },
    {
      key: 'rejected',
      name: t('app.dashboard.hr.flow.rejected'),
      value: rejected,
      fill: '#e11d48',
    },
  ].filter((row) => row.value > 0 || row.key === 'requested')

  const byClient = (stats?.by_client ?? [])
    .map((row) => ({
      name: row.client_id || '—',
      requested: row.requested,
      accepted: row.accepted,
      returned: row.returned,
      rejected: row.rejected,
    }))
    .sort((a, b) => b.requested - a.requested)
    .slice(0, 8)

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.dashboard.hr.title')}
          subtitle={t('app.dashboard.hr.subtitle')}
          kind="browse"
          secondaryActions={
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => void load()}
              disabled={loading || rangeInvalid}
            >
              {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pb-4">
        <div className="card space-y-3 p-4">
          <div className="flex flex-wrap items-end gap-3 gap-y-2">
            <label className="flex flex-col gap-0.5 text-xs">
              <span className="text-slate-500">{t('app.dashboard.filters.period')}</span>
              <div className="flex flex-wrap gap-1">
                {quickRangeOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`rounded px-2 py-1 text-xs ${
                      activeRange === option.value
                        ? 'bg-brand-600 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                    onClick={() => applyQuickRange(option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </label>
            <label className="flex flex-col gap-0.5 text-xs">
              <span className="text-slate-500">{t('app.dashboard.filters.from')}</span>
              <input
                type="date"
                className="input input-sm w-36"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value)
                  setActiveRange('custom')
                }}
              />
            </label>
            <label className="flex flex-col gap-0.5 text-xs">
              <span className="text-slate-500">{t('app.dashboard.filters.to')}</span>
              <input
                type="date"
                className="input input-sm w-36"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value)
                  setActiveRange('custom')
                }}
              />
            </label>
          </div>
          <div className="border-t border-slate-100 pt-2 text-xs text-slate-500">
            {t('app.dashboard.filters.sample', { values: { count: formatNumber(requested) } })}
            {loading ? <span className="ml-2">{t('common.loading')}</span> : null}
          </div>
        </div>

        {errText ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {errText}
          </div>
        ) : null}

        <div className={`space-y-4 ${loading ? 'opacity-70 transition-opacity' : ''}`}>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi label={t('app.dashboard.hr.flow.requested')} value={formatNumber(requested)} accent="#64748b" />
            <Kpi label={t('app.dashboard.hr.flow.accepted')} value={formatNumber(accepted)} accent="#16a34a" />
            <Kpi label={t('app.dashboard.hr.flow.returned')} value={formatNumber(returned)} accent="#f97316" />
            <Kpi label={t('app.dashboard.hr.flow.rejected')} value={formatNumber(rejected)} accent="#e11d48" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.hr.flow_title')}</div>
              <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.hr.flow_subtitle')}</p>
              <ChartHost className="mt-3 h-56 w-full min-w-0" ready={chartsReady}>
                <BarChart data={flow} layout="vertical" margin={{ left: 8, right: 12 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value: number) => formatNumber(value)} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {flow.map((entry) => (
                      <Cell key={entry.key} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ChartHost>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.hr.by_client_title')}</div>
              <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.hr.by_client_subtitle')}</p>
              {byClient.length === 0 ? (
                <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.efficiency.empty')}</p>
              ) : (
                <ul className="mt-3 max-h-56 space-y-2 overflow-y-auto">
                  {byClient.map((row) => (
                    <li
                      key={row.name}
                      className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2 text-sm"
                    >
                      <span className="truncate text-slate-700">{row.name}</span>
                      <span className="shrink-0 text-slate-900">
                        {formatNumber(row.accepted)}/{formatNumber(row.requested)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </PageShell>
  )
}

function Kpi({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="mb-2 h-1 rounded-full" style={{ backgroundColor: accent }} />
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  )
}
