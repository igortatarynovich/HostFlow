import { Link } from 'react-router-dom'
import type { LocaleCode, TranslateFn } from '../../../i18n'
import { CRM_APP_DRILLDOWN_HREFS, CRM_APP_PATHS } from '../../../app/crmAppPaths'
import type { ExecutiveKpis } from '../hooks/useDashboardDerivedAnalytics'
import type { StageLabelConfig } from '../types'

export interface DashboardExecutiveOverviewProps {
  t: TranslateFn
  locale: LocaleCode
  formatNumber: (value?: number) => string
  periodTotal: number
  executiveKpis: ExecutiveKpis
  stageLabels: StageLabelConfig
  makeCandidatesHref: (params: Record<string, string | null | undefined>) => string
}

export function DashboardExecutiveOverview({
  t,
  locale,
  formatNumber,
  periodTotal,
  executiveKpis,
  stageLabels,
  makeCandidatesHref,
}: DashboardExecutiveOverviewProps) {
  const currencyFormatter = new Intl.NumberFormat(
    locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US',
    {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    },
  )
  const noReplyTone = (executiveKpis.noReplyProxyPct ?? 0) > 20 ? 'text-rose-700' : 'text-slate-900'
  const noNextTone = executiveKpis.pctNoNextQueue > 25 ? 'text-rose-700' : 'text-slate-900'
  const slaTone = executiveKpis.slaProxyPct < 70 ? 'text-rose-700' : 'text-slate-900'
  const hiredHref = makeCandidatesHref({ stage: (stageLabels.hired ?? [])[0] ?? 'employed' })

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {t('app.dashboard.analytics.executive.badge')}
      </div>
      <p className="mt-1 max-w-3xl text-xs text-slate-500">
        {t('app.dashboard.analytics.executive.hint')}
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <Link
          to={CRM_APP_PATHS.candidates}
          className="rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2.5 hover:border-brand-200"
        >
          <div className="text-[11px] text-slate-500">
            {t('app.dashboard.analytics.executive.leads')}
          </div>
          <div className="text-xl font-semibold text-slate-900">{formatNumber(periodTotal)}</div>
        </Link>
        <Link
          to={hiredHref}
          className="rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2.5 hover:border-brand-200"
        >
          <div className="text-[11px] text-slate-500">
            {t('app.dashboard.analytics.executive.hired')}
          </div>
          <div className="text-xl font-semibold text-emerald-800">
            {formatNumber(executiveKpis.hired)}{' '}
            <span className="text-sm font-medium text-slate-600">
              ({executiveKpis.conversionPct.toFixed(1)}%)
            </span>
          </div>
        </Link>
        <Link
          to={CRM_APP_DRILLDOWN_HREFS.candidatesStageEmploymentPending}
          className="rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2.5 hover:border-brand-200"
        >
          <div className="text-[11px] text-slate-500">
            {t('app.dashboard.analytics.executive.employment_pending')}
          </div>
          <div className="text-xl font-semibold text-sky-800">{formatNumber(executiveKpis.employmentPending)}</div>
        </Link>
        <div className="rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2.5">
          <div className="text-[11px] text-slate-500">
            {t('app.dashboard.analytics.executive.avg_days_employ')}
          </div>
          <div className="text-xl font-semibold text-slate-900">
            {executiveKpis.avgDaysToEmploy != null
              ? `${Math.round(executiveKpis.avgDaysToEmploy)}`
              : '—'}
          </div>
        </div>
        <div className="rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2.5">
          <div className="text-[11px] text-slate-500">
            {t('app.dashboard.analytics.executive.no_reply_proxy')}
          </div>
          <div className={`text-xl font-semibold ${noReplyTone}`}>
            {executiveKpis.noReplyProxyPct != null ? `${executiveKpis.noReplyProxyPct}%` : '—'}
          </div>
        </div>
        <Link
          to={CRM_APP_DRILLDOWN_HREFS.candidatesQueueNoNextAction}
          className="rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2.5 hover:border-brand-200"
        >
          <div className="text-[11px] text-slate-500">
            {t('app.dashboard.analytics.executive.no_next_queue')}
          </div>
          <div className={`text-xl font-semibold ${noNextTone}`}>{executiveKpis.pctNoNextQueue}%</div>
        </Link>
        <Link
          to={CRM_APP_DRILLDOWN_HREFS.tasksOverdueReminders}
          className="rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2.5 hover:border-brand-200"
        >
          <div className="text-[11px] text-slate-500">
            {t('app.dashboard.analytics.executive.sla_proxy')}
          </div>
          <div className={`text-xl font-semibold ${slaTone}`}>{executiveKpis.slaProxyPct}%</div>
        </Link>
        {executiveKpis.leadCost != null ? (
          <div className="rounded-lg border border-slate-100 bg-slate-50/90 px-3 py-2.5">
            <div className="text-[11px] text-slate-500">
              {t('app.dashboard.analytics.executive.lead_cost')}
            </div>
            <div className="text-xl font-semibold text-slate-900">
              {currencyFormatter.format(executiveKpis.leadCost)}
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-200 bg-white px-3 py-2.5">
            <div className="text-[11px] text-slate-500">
              {t('app.dashboard.analytics.executive.lead_cost')}
            </div>
            <div className="text-sm text-slate-400">
              {t('app.dashboard.analytics.executive.lead_cost_na')}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
