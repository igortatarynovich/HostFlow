import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  getServicesAnalyticsOverview,
  type ServicesAnalyticsOverview,
} from '../api/analytics'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useI18n } from '../i18n'
import { formatAnalyticsLoadError } from '../modules/dashboard/analyticsLoad'
import { QUICK_RANGE_OPTIONS } from '../modules/dashboard/constants'
import type { QuickRange } from '../modules/dashboard/types'
import { calcRange } from '../modules/dashboard/utils'

function daysBetween(from: string, to: string): number {
  if (!from || !to) return 30
  const a = new Date(`${from}T00:00:00Z`).getTime()
  const b = new Date(`${to}T23:59:59Z`).getTime()
  if (!Number.isFinite(a) || !Number.isFinite(b) || b < a) return 30
  return Math.max(1, Math.ceil((b - a) / 86400000))
}

/**
 * Finance-owned slice: invoices / receivables from services analytics totals.
 * Not sales inquiry funnel and not recruitment stages.
 */
export default function FinanceEfficiencyDashboard() {
  const { t, locale } = useI18n()
  const loadSeq = useRef(0)
  const initialRange = calcRange('30d')
  const [dateFrom, setDateFrom] = useState(initialRange.from)
  const [dateTo, setDateTo] = useState(initialRange.to)
  const [activeRange, setActiveRange] = useState<QuickRange | 'custom'>('30d')
  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)
  const [services, setServices] = useState<ServicesAnalyticsOverview | null>(null)

  const numberFormatter = useMemo(
    () =>
      new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US', {
        maximumFractionDigits: 0,
      }),
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

  const load = useCallback(async () => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      setErrText(t('app.dashboard.errors.range_invalid'))
      return
    }
    const seq = ++loadSeq.current
    setLoading(true)
    setErrText(null)
    try {
      const data = await getServicesAnalyticsOverview({ days: daysBetween(dateFrom, dateTo) })
      if (seq !== loadSeq.current) return
      setServices(data)
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

  const totals = services?.totals

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
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
            {dateFrom && dateTo ? `${dateFrom} — ${dateTo}` : null}
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
              label={t('app.dashboard.finance.stats.invoiced')}
              value={formatNumber(totals?.invoices_invoiced)}
              accent="#0ea5e9"
            />
            <Kpi
              label={t('app.dashboard.finance.stats.paid')}
              value={formatNumber(totals?.invoices_paid)}
              accent="#16a34a"
            />
            <Kpi
              label={t('app.dashboard.finance.stats.outstanding')}
              value={formatNumber(totals?.invoices_outstanding)}
              accent="#f97316"
            />
            <Kpi
              label={t('app.dashboard.finance.stats.overdue')}
              value={formatNumber(totals?.invoices_overdue_count)}
              accent="#e11d48"
            />
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.finance.margin_title')}</div>
            <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.finance.margin_subtitle')}</p>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Mini label={t('app.dashboard.finance.stats.revenue')} value={formatNumber(totals?.revenue)} />
              <Mini label={t('app.dashboard.finance.stats.cost')} value={formatNumber(totals?.actual_cost)} />
              <Mini label={t('app.dashboard.finance.stats.profit')} value={formatNumber(totals?.gross_profit)} />
              <Mini
                label={t('app.dashboard.finance.stats.margin')}
                value={`${formatNumber(Math.round((totals?.gross_margin || 0) * 100))}%`}
              />
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

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="text-lg font-semibold text-slate-900">{value}</div>
    </div>
  )
}
