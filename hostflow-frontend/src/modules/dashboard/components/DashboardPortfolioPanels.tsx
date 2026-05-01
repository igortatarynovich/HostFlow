import { Link } from 'react-router-dom'
import type { TranslateFn } from '../../../i18n'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { stageHighlights } from '../stageNormalize'
import type {
  CandidateSlicesResponse,
  DashboardWidgetId,
  StageLabelConfig,
} from '../types'
import type {
  CountryHeatmapRow,
  DocStageStats,
  ManagerLoadRow,
  SourceStageRow,
  StageVelocityRow,
} from '../hooks/useDashboardDerivedAnalytics'
import type { DashboardCompanyLabels } from './DashboardOpsOverviewPanels'

export interface DashboardPortfolioPanelsProps {
  t: TranslateFn
  formatNumber: (value?: number) => string
  makeCandidatesHref: (params: Record<string, string | null | undefined>) => string
  drilldownTitle: string
  drillInlineClass: string
  isWidgetVisible: (id: DashboardWidgetId) => boolean
  slices: CandidateSlicesResponse | null | undefined
  stageLabels: StageLabelConfig
  dashboardCompanyLabels: DashboardCompanyLabels
  sourceStageRows: SourceStageRow[]
  docStageStats: DocStageStats
  stageVelocityRows: StageVelocityRow[]
  managerLoadRows: ManagerLoadRow[]
  countryHeatmapRows: CountryHeatmapRow[]
}

export function DashboardPortfolioPanels(props: DashboardPortfolioPanelsProps) {
  const {
    t,
    formatNumber,
    makeCandidatesHref,
    drilldownTitle,
    drillInlineClass,
    isWidgetVisible,
    slices,
    stageLabels,
    dashboardCompanyLabels,
    sourceStageRows,
    docStageStats,
    stageVelocityRows,
    managerLoadRows,
    countryHeatmapRows,
  } = props

  const showCompaniesVacancies = isWidgetVisible('companies') || isWidgetVisible('vacancies')
  const showSourcesRisk =
    (isWidgetVisible('sources') || isWidgetVisible('docsRisk') || isWidgetVisible('velocity')) &&
    (sourceStageRows.length > 0 || docStageStats.total > 0 || stageVelocityRows.length > 0)
  const showManagerCountries = isWidgetVisible('managerLoad') || isWidgetVisible('countries')

  return (
    <>
      {showCompaniesVacancies && (
        <div className="grid gap-4 lg:grid-cols-2">
          {isWidgetVisible('companies') && (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold">
                  {t('app.dashboard.companies.title', { values: { label: dashboardCompanyLabels.plural } })}
                </div>
                <div className="text-xs text-slate-500">
                  {t('app.dashboard.companies.subtitle', { values: { label: dashboardCompanyLabels.plural.toLowerCase() } })}
                </div>
              </div>
              {slices?.companies?.length ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>{dashboardCompanyLabels.singular}</th>
                      <th className="text-right">{t('app.dashboard.companies.table.total')}</th>
                      <th className="text-right">{t('app.dashboard.companies.table.in_pipeline')}</th>
                      <th className="text-right">{t('app.dashboard.companies.table.hired')}</th>
                      <th className="text-right">{t('app.dashboard.companies.table.rejected')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {slices.companies.map((item) => {
                      const highlight = stageHighlights(item.by_stage, stageLabels)
                      return (
                        <tr key={`company-${item.key}`}>
                          <td className="truncate">
                            <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {item.label}
                            </Link>
                          </td>
                          <td className="text-right font-medium">
                            <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(item.count)}
                            </Link>
                          </td>
                          <td className="text-right">
                            <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(highlight.pipeline)}
                            </Link>
                          </td>
                          <td className="text-right text-emerald-600">
                            <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(highlight.hired)}
                            </Link>
                          </td>
                          <td className="text-right text-red-600">
                            <Link to={makeCandidatesHref({ q: item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(highlight.rejected + highlight.declined)}
                            </Link>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              ) : (
                <div className="text-sm text-slate-500">
                  {t('app.dashboard.companies.empty', { values: { label: dashboardCompanyLabels.singular.toLowerCase() } })}
                </div>
              )}
            </div>
          )}
          {isWidgetVisible('vacancies') && (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold">{t('app.dashboard.vacancies.title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.vacancies.subtitle')}</div>
              </div>
              {slices?.vacancies?.length ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t('app.dashboard.vacancies.table.vacancy')}</th>
                      <th className="text-right">{t('app.dashboard.vacancies.table.total')}</th>
                      <th className="text-right">{t('app.dashboard.vacancies.table.in_pipeline')}</th>
                      <th className="text-right">{t('app.dashboard.vacancies.table.hired')}</th>
                      <th className="text-right">{t('app.dashboard.vacancies.table.rejected')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {slices.vacancies.map((item) => {
                      const highlight = stageHighlights(item.by_stage, stageLabels)
                      return (
                        <tr key={`vacancy-${item.key}`}>
                          <td className="truncate">
                            <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {item.label}
                            </Link>
                          </td>
                          <td className="text-right font-medium">
                            <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(item.count)}
                            </Link>
                          </td>
                          <td className="text-right">
                            <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(highlight.pipeline)}
                            </Link>
                          </td>
                          <td className="text-right text-emerald-600">
                            <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(highlight.hired)}
                            </Link>
                          </td>
                          <td className="text-right text-red-600">
                            <Link to={makeCandidatesHref({ vacancy: item.key || item.label })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(highlight.rejected + highlight.declined)}
                            </Link>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.vacancies.empty')}</div>
              )}
            </div>
          )}
        </div>
      )}

      {showSourcesRisk && (
        <div className="grid gap-4 lg:grid-cols-3">
          {isWidgetVisible('sources') && (
            <div className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-semibold">{t('app.dashboard.sources.detail_title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.sources.detail_subtitle')}</div>
              </div>
              {sourceStageRows.length ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t('app.dashboard.sources.table.source')}</th>
                      <th className="text-right">{t('app.dashboard.sources.table.pipeline')}</th>
                      <th className="text-right">{t('app.dashboard.sources.table.hired')}</th>
                      <th className="text-right">{t('app.dashboard.sources.table.rejected')}</th>
                      <th className="text-right">{t('app.dashboard.sources.table.total')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sourceStageRows.map((row) => (
                      <tr key={`source-${row.label}`}>
                        <td className="truncate">
                          <Link to={makeCandidatesHref({ preferred_channel: row.label })} title={drilldownTitle} className={drillInlineClass}>
                            {row.label}
                          </Link>
                        </td>
                        <td className="text-right">
                          <Link to={makeCandidatesHref({ preferred_channel: row.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(row.highlight.pipeline)}
                          </Link>
                        </td>
                        <td className="text-right text-emerald-600">
                          <Link to={makeCandidatesHref({ preferred_channel: row.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(row.highlight.hired)}
                          </Link>
                        </td>
                        <td className="text-right text-rose-600">
                          <Link to={makeCandidatesHref({ preferred_channel: row.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(row.highlight.rejected + row.highlight.declined)}
                          </Link>
                        </td>
                        <td className="text-right font-semibold">
                          <Link to={makeCandidatesHref({ preferred_channel: row.label })} title={drilldownTitle} className={drillInlineClass}>
                            {formatNumber(row.total)}
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.sources.empty')}</div>
              )}
            </div>
          )}
          {isWidgetVisible('docsRisk') && (
            <div className="card p-4 space-y-3">
              <div>
                <div className="text-sm font-semibold">{t('app.dashboard.docs_risk.title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.docs_risk.subtitle')}</div>
              </div>
              {docStageStats.total ? (
                <div className="space-y-3">
                  {(['waiting', 'attention', 'ready'] as const).map((bucket) => {
                    const value = docStageStats[bucket]
                    const percent = docStageStats.total ? Math.round((value / docStageStats.total) * 100) : 0
                    const barColor =
                      bucket === 'ready'
                        ? 'bg-emerald-400'
                        : bucket === 'attention'
                          ? 'bg-amber-400'
                          : 'bg-brand-400'
                    return (
                      <div key={bucket} className="space-y-1">
                        <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
                          <Link
                            to={
                              bucket === 'ready'
                                ? `${CRM_APP_PATHS.documents}?quick=ready`
                                : bucket === 'attention'
                                  ? `${CRM_APP_PATHS.documents}?status=rejected`
                                  : `${CRM_APP_PATHS.documents}?quick=requested`
                            }
                            className="hover:underline"
                          >
                            {t(`app.dashboard.docs_risk.${bucket}`)}
                          </Link>
                          <span>{percent}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100">
                          <div
                            className={`h-full rounded-full ${barColor}`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                        <div className="text-xs text-slate-500">
                          {t('app.dashboard.docs_risk.count', { values: { count: formatNumber(value) } })}
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.docs_risk.empty')}</div>
              )}
            </div>
          )}
          {isWidgetVisible('velocity') && (
            <div className="card p-4 space-y-3">
              <div>
                <div className="text-sm font-semibold">{t('app.dashboard.velocity.title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.velocity.subtitle')}</div>
              </div>
              {stageVelocityRows.length ? (
                <div className="space-y-2">
                  {stageVelocityRows.map((row) => (
                    <div key={row.stageCode} className="relative overflow-hidden rounded-xl border border-slate-200">
                      <div
                        className="absolute inset-y-0 left-0 bg-brand-500/20"
                        style={{ width: `${Math.max(row.intensity * 100, 8)}%` }}
                      />
                      <Link
                        to={makeCandidatesHref({ stage: row.stageCode })}
                        className="relative flex items-center justify-between px-3 py-2 text-sm"
                        title={drilldownTitle}
                      >
                        <div>
                          <div className="font-medium">{row.label}</div>
                          <div className="text-xs text-slate-500">
                            {t('app.dashboard.velocity.avg', { values: { value: Math.round(row.avgDays) } })}
                            {' · '}
                            {t('app.dashboard.velocity.p90', { values: { value: Math.round(row.p90) } })}
                          </div>
                        </div>
                        <div className="text-xs text-slate-500">
                          {t('app.dashboard.velocity.count', { values: { value: formatNumber(row.total) } })}
                        </div>
                      </Link>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.velocity.empty')}</div>
              )}
            </div>
          )}
        </div>
      )}

      {showManagerCountries && (
        <div className="grid gap-4 lg:grid-cols-2">
          {isWidgetVisible('managerLoad') && (
            <div className="card p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="text-sm font-semibold">{t('app.dashboard.manager_load.title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.manager_load.subtitle')}</div>
              </div>
              {managerLoadRows.length ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t('app.dashboard.manager_load.manager')}</th>
                      <th className="text-right">{t('app.dashboard.manager_load.pipeline')}</th>
                      <th className="text-right">{t('app.dashboard.manager_load.total')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {managerLoadRows.map((row) => (
                      <tr key={row.label}>
                        <td>
                          {row.managerIdForFilter ? (
                            <Link to={makeCandidatesHref({ manager_id: row.managerIdForFilter })} title={drilldownTitle} className={drillInlineClass}>
                              {row.label}
                            </Link>
                          ) : (
                            <span>{row.label}</span>
                          )}
                        </td>
                        <td className="text-right font-semibold">
                          {row.managerIdForFilter ? (
                            <Link to={makeCandidatesHref({ manager_id: row.managerIdForFilter })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(row.pipeline)}
                            </Link>
                          ) : (
                            <span>{formatNumber(row.pipeline)}</span>
                          )}
                        </td>
                        <td className="text-right text-slate-600">
                          {row.managerIdForFilter ? (
                            <Link to={makeCandidatesHref({ manager_id: row.managerIdForFilter })} title={drilldownTitle} className={drillInlineClass}>
                              {formatNumber(row.total)}
                            </Link>
                          ) : (
                            <span>{formatNumber(row.total)}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.manager_load.empty')}</div>
              )}
            </div>
          )}
          {isWidgetVisible('countries') && (
            <div className="card p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="text-sm font-semibold">{t('app.dashboard.country_heatmap.title')}</div>
                <div className="text-xs text-slate-500">{t('app.dashboard.country_heatmap.subtitle')}</div>
              </div>
              {countryHeatmapRows.length ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {countryHeatmapRows.map((row) => (
                    <div
                      key={`country-heat-${row.label}`}
                      className="rounded-2xl p-3 text-sm font-medium text-white shadow-inner"
                      style={{
                        background: `linear-gradient(135deg, rgba(59,130,246,${
                          0.35 + row.intensity * 0.45
                        }), rgba(99,102,241,${0.45 + row.intensity * 0.35}))`,
                      }}
                    >
                      <div>{row.label}</div>
                      <div className="text-xs text-white/80">{formatNumber(row.count)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.country_heatmap.empty')}</div>
              )}
            </div>
          )}
        </div>
      )}
    </>
  )
}
