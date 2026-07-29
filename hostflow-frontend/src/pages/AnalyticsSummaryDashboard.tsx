import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  getAnalyticsProfileSummary,
  getHandoffStats,
  getOpsCounters,
  getServicesAnalyticsOverview,
  type AnalyticsProfileSummary,
  type HandoffStatsResponse,
  type OpsCounters,
  type ServicesAnalyticsOverview,
} from '../api/analytics'
import { PageHeader } from '../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../components/layout'
import { useI18n } from '../i18n'
import { usePermissions } from '../hooks/usePermissions'
import { formatAnalyticsLoadError } from '../modules/dashboard/analyticsLoad'
import { calcRange } from '../modules/dashboard/utils'

/**
 * System summary tab — cross-module pulse (not a copy of any module drill-down).
 */
export default function AnalyticsSummaryDashboard() {
  const { t, locale } = useI18n()
  const { can } = usePermissions()
  const loadSeq = useRef(0)
  const [loading, setLoading] = useState(true)
  const [errText, setErrText] = useState<string | null>(null)
  const [ops, setOps] = useState<OpsCounters | null>(null)
  const [profile, setProfile] = useState<AnalyticsProfileSummary | null>(null)
  const [handoff, setHandoff] = useState<HandoffStatsResponse | null>(null)
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

  const load = useCallback(async () => {
    const seq = ++loadSeq.current
    setLoading(true)
    setErrText(null)
    const range = calcRange('30d')
    try {
      const [opsResp, profileResp, handoffResp, servicesResp] = await Promise.all([
        getOpsCounters(),
        getAnalyticsProfileSummary(),
        getHandoffStats({ from: range.from, to: range.to }),
        can('services.view')
          ? getServicesAnalyticsOverview({ days: 30 })
          : Promise.resolve(null),
      ])
      if (seq !== loadSeq.current) return
      setOps(opsResp)
      setProfile(profileResp)
      setHandoff(handoffResp)
      setServices(servicesResp)
    } catch (e: unknown) {
      if (seq !== loadSeq.current) return
      setErrText(formatAnalyticsLoadError(e, t))
    } finally {
      if (seq === loadSeq.current) setLoading(false)
    }
  }, [can, t])

  useEffect(() => {
    void load()
  }, [load])

  const businessType = profile?.business_type
  const kpis = profile?.kpis ?? {}

  return (
    <PageShell>
      <PageShellHeader>
        <PageHeader
          title={t('app.dashboard.summary.title')}
          subtitle={t('app.dashboard.summary.subtitle')}
          kind="browse"
          secondaryActions={
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => void load()}
              disabled={loading}
            >
              {loading ? t('app.dashboard.refresh.loading') : t('app.dashboard.refresh.action')}
            </button>
          }
        />
      </PageShellHeader>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
        {errText ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            {errText}
          </div>
        ) : null}

        <div className={`space-y-4 ${loading ? 'opacity-70 transition-opacity' : ''}`}>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.summary.pulse_title')}
              </h2>
              {businessType ? (
                <span className="text-xs text-slate-500">
                  {t(`app.dashboard.summary.business_type.${businessType}`, {
                    defaultValue: businessType,
                  })}
                  <span className="ml-2 text-slate-400">
                    {t('app.dashboard.summary.window_30d')}
                  </span>
                </span>
              ) : null}
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi
                label={t('app.dashboard.summary.kpis.pipeline')}
                value={formatNumber(ops?.overview_pipeline_total)}
              />
              <Kpi
                label={t('app.dashboard.summary.kpis.stuck')}
                value={formatNumber(ops?.overview_stuck)}
              />
              <Kpi
                label={t('app.dashboard.summary.kpis.active_today')}
                value={formatNumber(ops?.overview_active_today)}
              />
              <Kpi
                label={t('app.dashboard.summary.kpis.open_vacancies')}
                value={formatNumber(ops?.open_vacancies)}
              />
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.summary.modules.recruitment')}
              </h2>
              <ul className="mt-3 space-y-2 text-sm">
                <Row
                  label={t('app.dashboard.summary.kpis.candidates')}
                  value={formatNumber(kpis.candidates_total as number | undefined)}
                />
                <Row
                  label={t('app.dashboard.summary.kpis.vacancies_active')}
                  value={formatNumber(kpis.vacancies_active as number | undefined)}
                />
                <Row
                  label={t('app.dashboard.summary.kpis.on_open_vacancies')}
                  value={formatNumber(ops?.open_vacancies_candidates)}
                />
              </ul>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.summary.modules.sales')}
              </h2>
              <ul className="mt-3 space-y-2 text-sm">
                <Row
                  label={t('app.dashboard.summary.kpis.leads')}
                  value={formatNumber(
                    (kpis.leads_total as number | undefined) ?? ops?.leads_total,
                  )}
                />
                <Row
                  label={t('app.dashboard.summary.kpis.leads_overdue')}
                  value={formatNumber(ops?.leads_overdue)}
                />
                <Row
                  label={t('app.dashboard.summary.kpis.open_orders')}
                  value={formatNumber(ops?.open_service_orders)}
                />
              </ul>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.dashboard.summary.modules.hr_finance')}
              </h2>
              <ul className="mt-3 space-y-2 text-sm">
                <Row
                  label={t('app.dashboard.summary.kpis.handoff_requested')}
                  value={formatNumber(handoff?.total_requested)}
                />
                <Row
                  label={t('app.dashboard.summary.kpis.handoff_accepted')}
                  value={formatNumber(handoff?.total_accepted)}
                />
                <Row
                  label={t('app.dashboard.summary.kpis.orders_30d')}
                  value={formatNumber(services?.totals.orders_total)}
                />
              </ul>
            </section>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-700">{t('app.dashboard.summary.body')}</p>
            <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-600">
              <li>{t('app.dashboard.summary.bullets.modules')}</li>
              <li>{t('app.dashboard.summary.bullets.filters')}</li>
              <li>{t('app.dashboard.summary.bullets.owned')}</li>
            </ul>
          </div>
        </div>
      </div>
    </PageShell>
  )
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2.5">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="mt-0.5 text-xl font-semibold tabular-nums text-slate-900">{value}</div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex items-center justify-between gap-3">
      <span className="text-slate-600">{label}</span>
      <span className="tabular-nums font-semibold text-slate-900">{value}</span>
    </li>
  )
}
