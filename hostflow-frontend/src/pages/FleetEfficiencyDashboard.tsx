import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getFleetOverview, getFleetStatus, type FleetOverviewResponse } from '../api/fleet'
import { CRM_APP_PATHS } from '../app/crmAppPaths'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useI18n } from '../i18n'
import { formatAnalyticsLoadError } from '../modules/dashboard/analyticsLoad'

/**
 * Fleet-owned overview KPIs on the Analytics host (thin; full ops live under /app/fleet).
 */
export default function FleetEfficiencyDashboard() {
  const { t, locale } = useI18n()
  const loadSeq = useRef(0)
  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)
  const [overview, setOverview] = useState<FleetOverviewResponse | null>(null)
  const [moduleOk, setModuleOk] = useState<boolean | null>(null)

  const numberFormatter = useMemo(
    () =>
      new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US'),
    [locale],
  )
  const formatNumber = useCallback(
    (value?: number) => numberFormatter.format(value ?? 0),
    [numberFormatter],
  )

  const load = useCallback(async () => {
    const seq = ++loadSeq.current
    setLoading(true)
    setErrText(null)
    try {
      const status = await getFleetStatus().catch(() => ({ ok: false, module: 'fleet' }))
      const data = await getFleetOverview()
      if (seq !== loadSeq.current) return
      setModuleOk(Boolean(status.ok))
      setOverview(data)
    } catch (e: unknown) {
      if (seq !== loadSeq.current) return
      setErrText(formatAnalyticsLoadError(e, t))
    } finally {
      if (seq === loadSeq.current) setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.dashboard.fleet.title')}
          subtitle={t('app.dashboard.fleet.subtitle')}
          kind="browse"
          secondaryActions={
            <div className="flex items-center gap-2">
              <Link to={CRM_APP_PATHS.fleet} className="btn-secondary btn-sm">
                {t('app.dashboard.fleet.open_module')}
              </Link>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => void load()}
                disabled={loading}
              >
                {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
              </button>
            </div>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        {errText ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {errText}
          </div>
        ) : null}

        {moduleOk === false ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {t('app.dashboard.fleet.module_hint')}
          </div>
        ) : null}

        <div className={`space-y-4 ${loading ? 'opacity-70 transition-opacity' : ''}`}>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi label={t('app.dashboard.fleet.kpis.vehicles')} value={formatNumber(overview?.vehicles_total)} />
            <Kpi label={t('app.dashboard.fleet.kpis.trailers')} value={formatNumber(overview?.trailers_total)} />
            <Kpi label={t('app.dashboard.fleet.kpis.drivers')} value={formatNumber(overview?.drivers_total)} />
            <Kpi label={t('app.dashboard.fleet.kpis.lines')} value={formatNumber(overview?.operating_lines_total)} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Kpi
              label={t('app.dashboard.fleet.kpis.assignments')}
              value={formatNumber(overview?.assignments_total)}
            />
            <Kpi
              label={t('app.dashboard.fleet.kpis.assignments_today')}
              value={formatNumber(overview?.assignments_overlapping_today_utc_total)}
            />
            <Kpi
              label={t('app.dashboard.fleet.kpis.assignments_month')}
              value={formatNumber(overview?.assignments_overlapping_month_utc_total)}
            />
          </div>
        </div>
      </div>
    </PageShell>
  )
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{value}</div>
    </div>
  )
}
