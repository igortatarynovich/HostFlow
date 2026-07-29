import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  getServicesAnalyticsOverview,
  type ServicesAnalyticsOverview,
} from '../api/analytics'
import api from '../api/client'
import {
  fetchLeadConversionFunnel,
  type LeadConversionFunnelResponse,
} from '../api/leadConversionFunnel'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useI18n } from '../i18n'
import { formatAnalyticsLoadError } from '../modules/dashboard/analyticsLoad'
import { ChartHost } from '../modules/dashboard/components/ChartHost'
import { QUICK_RANGE_OPTIONS } from '../modules/dashboard/constants'
import type { QuickRange } from '../modules/dashboard/types'
import { calcRange } from '../modules/dashboard/utils'
import { usePermissions } from '../hooks/usePermissions'

const FUNNEL_COLORS: Record<string, string> = {
  lead: '#64748b',
  qualified: '#0ea5e9',
  active: '#8b5cf6',
  final: '#16a34a',
  lost: '#e11d48',
}

const STATUS_COLORS = ['#0ea5e9', '#8b5cf6', '#14b8a6', '#f97316', '#e11d48', '#64748b']

type ListResp<T> = { items: T[]; total?: number } | T[]

function daysBetween(from: string, to: string): number {
  if (!from || !to) return 30
  const a = new Date(`${from}T00:00:00Z`).getTime()
  const b = new Date(`${to}T23:59:59Z`).getTime()
  if (!Number.isFinite(a) || !Number.isFinite(b) || b < a) return 30
  return Math.max(1, Math.ceil((b - a) / 86400000))
}

function toExclusiveIsoEnd(dateTo: string): string | undefined {
  if (!dateTo) return undefined
  const d = new Date(`${dateTo}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + 1)
  return d.toISOString()
}

function toIsoStart(dateFrom: string): string | undefined {
  if (!dateFrom) return undefined
  return new Date(`${dateFrom}T00:00:00Z`).toISOString()
}

/**
 * Sales-owned efficiency: inquiry conversion funnel + commercial services slice.
 * Not a copy of recruitment candidate stages.
 */
export default function SalesEfficiencyDashboard() {
  const { t, locale } = useI18n()
  const { can } = usePermissions()
  const canServices = can('services.view')
  const loadSeq = useRef(0)

  const initialRange = calcRange('90d')
  const [dateFrom, setDateFrom] = useState(initialRange.from)
  const [dateTo, setDateTo] = useState(initialRange.to)
  const [activeRange, setActiveRange] = useState<QuickRange | 'custom'>('90d')
  const [sourceFilter, setSourceFilter] = useState('')
  const [sourceDraft, setSourceDraft] = useState('')
  const [vacancyFilter, setVacancyFilter] = useState('')
  const [vacancyOptions, setVacancyOptions] = useState<{ id: string; label: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)
  const [funnel, setFunnel] = useState<LeadConversionFunnelResponse | null>(null)
  const [services, setServices] = useState<ServicesAnalyticsOverview | null>(null)

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
      const after = toIsoStart(dateFrom)
      const before = toExclusiveIsoEnd(dateTo)
      const [funnelResp, servicesResp] = await Promise.all([
        fetchLeadConversionFunnel({
          ...(after && before
            ? { cohortCreatedAfter: after, cohortCreatedBeforeExclusive: before }
            : {}),
          ...(sourceFilter.trim() ? { source: sourceFilter.trim() } : {}),
          ...(vacancyFilter ? { vacancyId: vacancyFilter } : {}),
        }),
        canServices
          ? getServicesAnalyticsOverview({ days: daysBetween(dateFrom, dateTo) })
          : Promise.resolve(null),
      ])
      if (seq !== loadSeq.current) return
      setFunnel(funnelResp)
      setServices(servicesResp)
    } catch (e: unknown) {
      if (seq !== loadSeq.current) return
      setErrText(formatAnalyticsLoadError(e, t))
    } finally {
      if (seq === loadSeq.current) setLoading(false)
    }
  }, [canServices, dateFrom, dateTo, sourceFilter, vacancyFilter, t])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    ;(async () => {
      try {
        const { data } = await api.get<
          ListResp<{
            id?: string
            title?: string
            vacancy_title?: string
            company_name?: string
            company?: { name?: string }
          }>
        >('/vacancies/', { params: { limit: 200, offset: 0 } })
        const list = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
        const untitled = t('app.dashboard.labels.untitled', { defaultValue: '—' })
        setVacancyOptions(
          list
            .map((item) => {
              const id = item?.id
              if (!id) return null
              const title = item?.title || item?.vacancy_title || untitled
              const companyName = item?.company_name || item?.company?.name || ''
              return { id, label: companyName ? `${title} • ${companyName}` : title }
            })
            .filter(Boolean) as { id: string; label: string }[],
        )
      } catch {
        setVacancyOptions([])
      }
    })()
  }, [t])

  const applyQuickRange = (range: QuickRange) => {
    const next = calcRange(range)
    setActiveRange(range)
    setDateFrom(next.from)
    setDateTo(next.to)
  }

  const stageRows = funnel?.stages ?? []
  const lost = funnel?.lost_processed_count ?? 0
  const winPath = funnel?.total_win_path_processed ?? 0
  const newCount = funnel?.status_new_count ?? 0
  const leadTotal = Math.max(winPath + lost, newCount, stageRows[0]?.count ?? 0)

  const funnelChart = [
    ...stageRows.map((row) => ({
      key: row.stage,
      name: t(`app.dashboard.sales.funnel_stages.${row.stage}`, { defaultValue: row.stage }),
      value: row.count,
      fill: FUNNEL_COLORS[row.stage] || '#64748b',
    })),
    ...(lost > 0
      ? [
          {
            key: 'lost',
            name: t('app.dashboard.sales.funnel_stages.lost', { defaultValue: 'Lost' }),
            value: lost,
            fill: FUNNEL_COLORS.lost,
          },
        ]
      : []),
  ]

  const lostReasons = (funnel?.lost_reason_breakdown ?? [])
    .slice(0, 8)
    .map((row) => ({
      name: t(`app.dashboard.sales.lost_reasons.${row.reason_code}`, {
        defaultValue: row.reason_code,
      }),
      count: row.lead_count,
    }))

  const statusPie = (services?.status_breakdown ?? [])
    .filter((row) => row.count > 0)
    .map((row, i) => ({
      key: row.status,
      name: t(`app.dashboard.sales.order_status.${row.status}`, { defaultValue: row.status }),
      value: row.count,
      fill: STATUS_COLORS[i % STATUS_COLORS.length],
    }))

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.dashboard.sales.title')}
          subtitle={t('app.dashboard.sales.subtitle')}
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

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
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
            <label className="flex flex-col gap-0.5 text-xs">
              <span className="text-slate-500">{t('app.dashboard.sales.filters.source')}</span>
              <input
                type="text"
                className="input input-sm w-40"
                value={sourceDraft}
                placeholder={t('app.dashboard.sales.filters.source_placeholder')}
                onChange={(e) => setSourceDraft(e.target.value)}
                onBlur={() => setSourceFilter(sourceDraft.trim())}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    setSourceFilter(sourceDraft.trim())
                  }
                }}
              />
            </label>
            <label className="flex flex-col gap-0.5 text-xs">
              <span className="text-slate-500">{t('app.dashboard.sales.filters.vacancy')}</span>
              <select
                className="input input-sm min-w-[12rem]"
                value={vacancyFilter}
                onChange={(e) => setVacancyFilter(e.target.value)}
              >
                <option value="">{t('app.dashboard.sales.filters.vacancy_all')}</option>
                {vacancyOptions.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="border-t border-slate-100 pt-2 text-xs text-slate-500">
            {t('app.dashboard.filters.sample', { values: { count: formatNumber(leadTotal) } })}
            {dateFrom && dateTo ? (
              <span className="ml-2">
                • {dateFrom} — {dateTo}
              </span>
            ) : null}
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
            <Kpi
              label={t('app.dashboard.sales.stats.inquiries')}
              value={formatNumber(leadTotal)}
              accent="#64748b"
            />
            <Kpi
              label={t('app.dashboard.sales.stats.win_path')}
              value={formatNumber(winPath)}
              accent="#16a34a"
            />
            <Kpi
              label={t('app.dashboard.sales.stats.lost')}
              value={formatNumber(lost)}
              accent="#e11d48"
            />
            <Kpi
              label={t('app.dashboard.sales.stats.new_untouched')}
              value={formatNumber(newCount)}
              accent="#f97316"
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-800">
                {t('app.dashboard.sales.funnel_title')}
              </div>
              <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.sales.funnel_subtitle')}</p>
              <div className="mt-3 h-56 min-w-0">
                {funnelChart.length === 0 ? (
                  <Empty />
                ) : (
                  <ChartHost className="h-full w-full min-w-0" ready={chartsReady}>
                    <BarChart data={funnelChart} layout="vertical" margin={{ left: 8, right: 12 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" width={88} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(value: number) => formatNumber(value)} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {funnelChart.map((entry) => (
                          <Cell key={entry.key} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ChartHost>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold text-slate-800">
                {t('app.dashboard.sales.lost_title')}
              </div>
              <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.sales.lost_subtitle')}</p>
              {lostReasons.length === 0 ? (
                <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.sales.lost_empty')}</p>
              ) : (
                <ChartHost className="mt-3 h-56 w-full min-w-0" ready={chartsReady}>
                  <BarChart data={lostReasons} layout="vertical" margin={{ left: 8, right: 12 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value: number) => formatNumber(value)} />
                    <Bar dataKey="count" fill="#e11d48" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ChartHost>
              )}
            </div>
          </div>

          {canServices ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="text-sm font-semibold text-slate-800">
                  {t('app.dashboard.sales.orders_title')}
                </div>
                <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.sales.orders_subtitle')}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <MiniStat
                    label={t('app.dashboard.sales.orders_total')}
                    value={formatNumber(services?.totals.orders_total)}
                  />
                  <MiniStat
                    label={t('app.dashboard.sales.orders_delivered')}
                    value={formatNumber(services?.totals.delivered_orders)}
                  />
                  <MiniStat
                    label={t('app.dashboard.sales.orders_cancelled')}
                    value={formatNumber(services?.totals.cancelled_orders)}
                  />
                  <MiniStat
                    label={t('app.dashboard.sales.orders_revenue')}
                    value={formatNumber(services?.totals.revenue)}
                  />
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="text-sm font-semibold text-slate-800">
                  {t('app.dashboard.sales.orders_status_title')}
                </div>
                <div className="mt-3 h-48 min-w-0">
                  {statusPie.length === 0 ? (
                    <Empty />
                  ) : (
                    <ChartHost className="h-full w-full min-w-0" ready={chartsReady}>
                      <PieChart>
                        <Pie
                          data={statusPie}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={45}
                          outerRadius={75}
                          paddingAngle={2}
                        >
                          {statusPie.map((entry) => (
                            <Cell key={entry.key} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value: number) => formatNumber(value)} />
                      </PieChart>
                    </ChartHost>
                  )}
                </div>
              </div>
            </div>
          ) : null}
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

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="text-lg font-semibold text-slate-900">{value}</div>
    </div>
  )
}

function Empty() {
  return <div className="flex h-full items-center justify-center text-sm text-slate-400">—</div>
}
