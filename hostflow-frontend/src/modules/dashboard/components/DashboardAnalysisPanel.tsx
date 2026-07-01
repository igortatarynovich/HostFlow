import { Link } from 'react-router-dom'
import type { TranslateFn } from '../../../i18n'
import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../../../app/crmAppPaths'
import type { FunnelStep, DocumentBlockerAnalytics } from '../hooks/useDashboardDerivedAnalytics'
import type { PivotDimension } from '../types'

type BreakdownMetric = 'count' | 'conversion' | 'time' | 'dropoff'

export interface BreakdownRow {
  label: string
  total: number
  hired: number
  lost: number
  conversion: number
  dropoff: number
  avgDaysInStage: number | null
  filterParams: Record<string, string>
}

export interface DashboardAnalysisPanelProps {
  t: TranslateFn
  formatNumber: (value?: number) => string
  makeCandidatesHref: (params: Record<string, string | null | undefined>) => string
  funnelSteps: FunnelStep[]
  breakdownGroup: PivotDimension
  setBreakdownGroup: (dimension: PivotDimension) => void
  breakdownGroupOptions: Array<{ value: PivotDimension; label: string }>
  breakdownMetric: BreakdownMetric
  setBreakdownMetric: (metric: BreakdownMetric) => void
  breakdownRows: BreakdownRow[]
  opsCounters:
    | {
        overdue_reminders?: number | null
        no_next_action_candidates?: number | null
        leads_sla_stuck_stage_reminders?: number | null
        leads_sla_no_next_action_reminders?: number | null
      }
    | null
    | undefined
  documentBlockerAnalytics: DocumentBlockerAnalytics
}

export function DashboardAnalysisPanel({
  t,
  formatNumber,
  makeCandidatesHref,
  funnelSteps,
  breakdownGroup,
  setBreakdownGroup,
  breakdownGroupOptions,
  breakdownMetric,
  setBreakdownMetric,
  breakdownRows,
  opsCounters,
  documentBlockerAnalytics,
}: DashboardAnalysisPanelProps) {
  const pipelineSteps = funnelSteps.filter((step) => step.outcome === 'pipeline')
  const outcomeSteps = funnelSteps.filter((step) => step.outcome !== 'pipeline')
  const topBottlenecks = pipelineSteps
    .filter((step) => step.lossCount > 0 && step.dropoff != null && !step.lowSample)
    .sort((a, b) => b.lossCount - a.lossCount)
    .slice(0, 3)

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-6">
      <div>
        <div className="text-sm font-semibold text-slate-900">{t('app.dashboard.analytics.analysis.title')}</div>
        <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.analytics.analysis.subtitle')}</p>
      </div>

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.dashboard.analytics.funnel.badge')}
        </div>
        <p className="mt-1 text-xs text-slate-500">{t('app.dashboard.analytics.funnel.hint')}</p>
        {pipelineSteps.length === 0 ? (
          <div className="mt-3 text-sm text-slate-500">{t('app.dashboard.analytics.funnel.empty')}</div>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-2 pr-4">{t('app.dashboard.analytics.funnel.col_stage')}</th>
                  <th className="py-2 pr-4 text-right">{t('app.dashboard.analytics.funnel.col_count')}</th>
                  <th className="py-2 pr-4 text-right">{t('app.dashboard.analytics.funnel.col_step_conv')}</th>
                  <th className="py-2 text-right">{t('app.dashboard.analytics.funnel.col_avg_days')}</th>
                </tr>
              </thead>
              <tbody>
                {pipelineSteps.map((step) => (
                  <tr key={step.key} className="border-t border-slate-100">
                    <td className="py-2 pr-4">
                      <Link
                        to={makeCandidatesHref({ stage: step.key })}
                        className="font-medium text-brand-700 hover:underline"
                      >
                        {step.label}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-right">{formatNumber(step.count)}</td>
                    <td className="py-2 pr-4 text-right text-slate-600">
                      {step.lowSample ? '—' : step.stepConv != null ? `${step.stepConv.toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-2 text-right text-slate-600">
                      {step.avgDays != null ? `${step.avgDays}d` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {outcomeSteps.length > 0 ? (
          <div className="mt-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Outcomes</div>
            <div className="mt-2 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-slate-500">
                    <th className="py-2 pr-4">{t('app.dashboard.analytics.funnel.col_stage')}</th>
                    <th className="py-2 text-right">{t('app.dashboard.analytics.funnel.col_count')}</th>
                  </tr>
                </thead>
                <tbody>
                  {outcomeSteps.map((step) => (
                    <tr key={step.key} className="border-t border-slate-100">
                      <td className="py-2 pr-4">
                        <Link to={makeCandidatesHref({ stage: step.key })} className="font-medium text-brand-700 hover:underline">
                          {step.label}
                        </Link>
                      </td>
                      <td className="py-2 text-right">{formatNumber(step.count)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </div>

      <div>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.dashboard.analytics.breakdown.badge')}
            </div>
            <p className="mt-1 text-xs text-slate-500">{t('app.dashboard.analytics.breakdown.hint')}</p>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <label className="flex flex-col gap-1">
              <span className="text-xs text-slate-500">{t('app.dashboard.analytics.breakdown.group')}</span>
              <select
                className="input text-sm"
                value={breakdownGroup}
                onChange={(e) => setBreakdownGroup(e.target.value as PivotDimension)}
              >
                {breakdownGroupOptions.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-slate-500">{t('app.dashboard.analytics.breakdown.metric')}</span>
              <select
                className="input text-sm"
                value={breakdownMetric}
                onChange={(e) => setBreakdownMetric(e.target.value as BreakdownMetric)}
              >
                <option value="count">{t('app.dashboard.analytics.breakdown.metric_count')}</option>
                <option value="conversion">{t('app.dashboard.analytics.breakdown.metric_conversion')}</option>
                <option value="time">{t('app.dashboard.analytics.breakdown.metric_time')}</option>
                <option value="dropoff">{t('app.dashboard.analytics.breakdown.metric_dropoff')}</option>
              </select>
            </label>
          </div>
        </div>
        {breakdownRows.length === 0 ? (
          <div className="mt-3 text-sm text-slate-500">{t('app.dashboard.analytics.breakdown.empty')}</div>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-slate-500">
                  <th className="py-2 pr-4">{t('app.dashboard.analytics.breakdown.col_segment')}</th>
                  <th className="py-2 text-right">{t('app.dashboard.analytics.breakdown.col_value')}</th>
                </tr>
              </thead>
              <tbody>
                {breakdownRows.map((row) => {
                  const href =
                    Object.keys(row.filterParams).length > 0
                      ? makeCandidatesHref(row.filterParams)
                      : CRM_APP_PATHS.candidates
                  let valueCell: string
                  if (breakdownMetric === 'count') valueCell = formatNumber(row.total)
                  else if (breakdownMetric === 'conversion') valueCell = `${row.conversion.toFixed(1)}%`
                  else if (breakdownMetric === 'dropoff') valueCell = `${row.dropoff.toFixed(1)}%`
                  else valueCell = row.avgDaysInStage != null ? `${Math.round(row.avgDaysInStage)}d` : '—'
                  return (
                    <tr key={row.label} className="border-t border-slate-100">
                      <td className="py-2 pr-4">
                        <Link to={href} className="font-medium text-brand-700 hover:underline">
                          {row.label}
                        </Link>
                      </td>
                      <td className="py-2 text-right text-slate-800">{valueCell}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.dashboard.analytics.problems.badge')}
        </div>
        <p className="mt-1 text-xs text-slate-500">{t('app.dashboard.analytics.problems.hint')}</p>
        {topBottlenecks.length > 0 ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {topBottlenecks.map((step) => (
              <Link
                key={`bottleneck-${step.key}`}
                to={makeCandidatesHref({ stage: step.key })}
                className="flex items-center justify-between rounded-lg border border-rose-100 bg-rose-50/60 px-3 py-2 text-sm hover:border-rose-200"
              >
                <span>{step.label}</span>
                <span className="font-semibold text-rose-800">
                  -{formatNumber(step.lossCount)}{step.dropoff != null ? ` (${step.dropoff.toFixed(1)}%)` : ''}
                </span>
              </Link>
            ))}
          </div>
        ) : null}
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <Link
            to={CRM_APP_DRILLDOWN_HREFS.tasksOverdueReminders}
            className="flex items-center justify-between rounded-lg border border-rose-100 bg-rose-50/60 px-3 py-2 text-sm hover:border-rose-200"
          >
            <span>{t('app.dashboard.analytics.problems.overdue_tasks')}</span>
            <span className="font-semibold text-rose-800">{formatNumber(opsCounters?.overdue_reminders ?? 0)}</span>
          </Link>
          <Link
            to={CRM_APP_DRILLDOWN_HREFS.candidatesQueueNoNextAction}
            className="flex items-center justify-between rounded-lg border border-amber-100 bg-amber-50/60 px-3 py-2 text-sm hover:border-amber-200"
          >
            <span>{t('app.dashboard.analytics.problems.no_next_candidate')}</span>
            <span className="font-semibold text-amber-900">
              {formatNumber(opsCounters?.no_next_action_candidates ?? 0)}
            </span>
          </Link>
          <Link
            to={CRM_APP_DRILLDOWN_HREFS.leadsProcessedStuck}
            className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm hover:border-brand-200"
          >
            <span>{t('app.dashboard.analytics.problems.stuck_leads')}</span>
            <span className="font-semibold">{formatNumber(opsCounters?.leads_sla_stuck_stage_reminders ?? 0)}</span>
          </Link>
          <Link
            to={CRM_APP_DRILLDOWN_HREFS.tasksLeadsSlaNudges}
            className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm hover:border-brand-200"
          >
            <span>{t('app.dashboard.analytics.problems.sla_leads')}</span>
            <span className="font-semibold">{formatNumber(opsCounters?.leads_sla_no_next_action_reminders ?? 0)}</span>
          </Link>
          <Link
            to={`${CRM_APP_PATHS.documents}?quick=missing`}
            className="flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50/60 px-3 py-2 text-sm hover:border-blue-200"
          >
            <span>{t('app.dashboard.analytics.problems.docs_missing')}</span>
            <span className="font-semibold text-blue-900">
              {formatNumber(documentBlockerAnalytics.missingOrRequested)}
            </span>
          </Link>
        </div>
      </div>
    </div>
  )
}
