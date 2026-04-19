import { Link } from 'react-router-dom'
import type { LocaleCode, TranslateFn } from '../../../i18n'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths'
import { STAGE_STACK_COLORS } from '../stageNormalize'
import type {
  HandoffStatsResponse,
  ContactAttemptStatsResponse,
  DocumentStatsResponse,
  AnalyticsProfileSummary,
} from '../../../api/analytics'
import type { DashboardWidgetId } from '../types'
import type {
  BusinessProfileCard,
  DocumentBlockerAnalytics,
  GroupedReason,
  GroupedStage,
  StageStackSegment,
} from '../hooks/useDashboardDerivedAnalytics'

export interface DashboardCompanyLabels {
  singular: string
  plural: string
}

export interface DashboardOpsOverviewPanelsProps {
  t: TranslateFn
  locale: LocaleCode
  formatNumber: (value?: number) => string
  makeCandidatesHref: (params: Record<string, string | null | undefined>) => string
  documentQuickFilterHref: (status: string) => string
  drilldownTitle: string
  isWidgetVisible: (id: DashboardWidgetId) => boolean
  handoffStats: HandoffStatsResponse | null
  contactStats: ContactAttemptStatsResponse | null
  documentStats: DocumentStatsResponse | null
  documentBlockerAnalytics: DocumentBlockerAnalytics
  profileSummary: AnalyticsProfileSummary | null
  stageStackSegments: StageStackSegment[]
  errText: string | null
  rangeInvalid: boolean
  globalCounts: { candidates: number; companies: number; vacancies: number }
  periodTotal: number
  dateField: 'created' | 'updated'
  dashboardCompanyLabels: DashboardCompanyLabels
  businessProfileCards: BusinessProfileCard[]
  businessTypeLabel: string
  businessCardHref: (key: string) => string
  groupedStages: GroupedStage[]
  groupedRejectedReasons: GroupedReason[]
  groupedDeclinedReasons: GroupedReason[]
  drillInlineClass: string
}

export function DashboardOpsOverviewPanels(props: DashboardOpsOverviewPanelsProps) {
  const {
    t,
    locale,
    formatNumber,
    makeCandidatesHref,
    documentQuickFilterHref,
    drilldownTitle,
    isWidgetVisible,
    handoffStats,
    contactStats,
    documentStats,
    documentBlockerAnalytics,
    profileSummary,
    stageStackSegments,
    errText,
    rangeInvalid,
    globalCounts,
    periodTotal,
    dateField,
    dashboardCompanyLabels,
    businessProfileCards,
    businessTypeLabel,
    businessCardHref,
    groupedStages,
    groupedRejectedReasons,
    groupedDeclinedReasons,
    drillInlineClass,
  } = props

  const showTripleWidgets =
    (isWidgetVisible('handoff') && !!handoffStats) ||
    (isWidgetVisible('contact') && !!contactStats) ||
    (isWidgetVisible('documents') && !!documentStats)

  return (
    <>
      {showTripleWidgets && (
        <div className="grid gap-4 md:grid-cols-3">
          {isWidgetVisible('handoff') && handoffStats && (
            <div className="card p-4">
              <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.handoff.title')}</div>
              <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.handoff.subtitle')}</div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <Link
                  to={makeCandidatesHref({ handoff_status: 'pending' })}
                  className="rounded-lg bg-slate-50 p-2 hover:bg-slate-100"
                  title={drilldownTitle}
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.handoff.requested')}</span>
                  <div className="font-semibold">{formatNumber(handoffStats.total_requested)}</div>
                </Link>
                <Link
                  to={makeCandidatesHref({ handoff_status: 'accepted' })}
                  className="rounded-lg bg-emerald-50 p-2 hover:bg-emerald-100"
                  title={drilldownTitle}
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.handoff.accepted')}</span>
                  <div className="font-semibold text-emerald-700">{formatNumber(handoffStats.total_accepted)}</div>
                </Link>
                <Link
                  to={makeCandidatesHref({ handoff_status: 'rejected' })}
                  className="rounded-lg bg-rose-50 p-2 hover:bg-rose-100"
                  title={drilldownTitle}
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.handoff.rejected')}</span>
                  <div className="font-semibold text-rose-700">{formatNumber(handoffStats.total_rejected)}</div>
                </Link>
                <Link
                  to={makeCandidatesHref({ handoff_status: 'returned' })}
                  className="rounded-lg bg-amber-50 p-2 hover:bg-amber-100"
                  title={drilldownTitle}
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.handoff.returned')}</span>
                  <div className="font-semibold text-amber-700">{formatNumber(handoffStats.total_returned)}</div>
                </Link>
              </div>
            </div>
          )}
          {isWidgetVisible('contact') && contactStats && (
            <div className="card p-4">
              <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.contact_attempts.title')}</div>
              <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.contact_attempts.subtitle')}</div>
              <div className="mt-3 space-y-2 text-sm">
                <Link
                  to={makeCandidatesHref({ contact_attempts: 'some' })}
                  className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                  title={drilldownTitle}
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.total')}</span>
                  <span className="font-semibold">{formatNumber(contactStats.total_attempts)}</span>
                </Link>
                <Link
                  to={makeCandidatesHref({ contact_attempts: 'some' })}
                  className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                  title={drilldownTitle}
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.avg')}</span>
                  <span className="font-semibold">{contactStats.avg_per_candidate.toFixed(1)}</span>
                </Link>
                <Link
                  to={makeCandidatesHref({ contact_attempts: 'limit_reached' })}
                  className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                  title={drilldownTitle}
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.contact_attempts.limit_reached')}</span>
                  <span className="font-semibold">{formatNumber(contactStats.limit_reached_count)}</span>
                </Link>
              </div>
            </div>
          )}
          {isWidgetVisible('documents') && documentStats && (
            <div className="card p-4">
              <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.widgets.documents.title')}</div>
              <div className="text-xs text-slate-500 mt-0.5">{t('app.dashboard.widgets.documents.subtitle')}</div>
              <div className="mt-3 space-y-2 text-sm">
                <Link
                  to={CRM_APP_PATHS.documents}
                  title={drilldownTitle}
                  className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.documents.total')} <span className="text-[10px]">↗</span></span>
                  <span className="font-semibold">{formatNumber(documentStats.total_docs)}</span>
                </Link>
                <Link
                  to={`${CRM_APP_PATHS.documents}?quick=ready`}
                  title={drilldownTitle}
                  className="flex justify-between rounded px-1 py-0.5 hover:bg-slate-50"
                >
                  <span className="text-slate-500">{t('app.dashboard.widgets.documents.complete')} <span className="text-[10px]">↗</span></span>
                  <span className="font-semibold">{formatNumber(documentStats.candidates_with_complete_docs)}</span>
                </Link>
                {Object.keys(documentStats.by_status || {}).length > 0 && (
                  <div className="mt-2 pt-2 border-t border-slate-100">
                    <span className="text-xs text-slate-500">{t('app.dashboard.widgets.documents.by_status')}</span>
                    <ul className="mt-1 space-y-0.5 text-xs">
                      {Object.entries(documentStats.by_status || {}).slice(0, 5).map(([status, count]) => (
                        <li key={status} className="flex justify-between">
                          <Link className="hover:underline" to={documentQuickFilterHref(status)}>{status}</Link>
                          <span>{formatNumber(count)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="mt-2 pt-2 border-t border-slate-100">
                  <div className="text-xs text-slate-500">
                    {t('app.dashboard.widgets.documents.blockers_title')}
                  </div>
                  <div className="mt-1 grid grid-cols-1 gap-1.5 text-xs">
                    <Link
                      to={`${CRM_APP_PATHS.documents}?quick=missing`}
                      className="flex items-center justify-between rounded bg-blue-50 px-2 py-1 text-blue-800 hover:bg-blue-100"
                    >
                      <span>{t('app.dashboard.widgets.documents.blockers_missing')}</span>
                      <span className="font-semibold">{formatNumber(documentBlockerAnalytics.missingOrRequested)}</span>
                    </Link>
                    <Link
                      to={`${CRM_APP_PATHS.documents}?quick=in_progress`}
                      className="flex items-center justify-between rounded bg-amber-50 px-2 py-1 text-amber-800 hover:bg-amber-100"
                    >
                      <span>{t('app.dashboard.widgets.documents.blockers_review')}</span>
                      <span className="font-semibold">{formatNumber(documentBlockerAnalytics.awaitingReview)}</span>
                    </Link>
                    <Link
                      to={`${CRM_APP_PATHS.documents}?status=rejected`}
                      className="flex items-center justify-between rounded bg-rose-50 px-2 py-1 text-rose-800 hover:bg-rose-100"
                    >
                      <span>{t('app.dashboard.widgets.documents.blockers_problematic')}</span>
                      <span className="font-semibold">{formatNumber(documentBlockerAnalytics.problematic)}</span>
                    </Link>
                  </div>
                  {documentBlockerAnalytics.total > 0 ? (
                    <div className="mt-2 text-[11px] text-slate-600">
                      {t('app.dashboard.widgets.documents.blockers_total_hint', { values: { count: formatNumber(documentBlockerAnalytics.total) } })}
                    </div>
                  ) : null}
                  {profileSummary?.business_type === 'services' && documentBlockerAnalytics.estimatedBlockedRevenue > 0 ? (
                    <div className="mt-2 rounded border border-rose-200 bg-rose-50 px-2 py-1.5 text-[11px] text-rose-800">
                      {t('app.dashboard.widgets.documents.blockers_cost_hint', {
                        values: {
                          amount: new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : locale === 'pl' ? 'pl-PL' : 'en-US', {
                            style: 'currency',
                            currency: 'EUR',
                            maximumFractionDigits: 0,
                          }).format(documentBlockerAnalytics.estimatedBlockedRevenue),
                        },
                      })}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {isWidgetVisible('stageStack') && stageStackSegments.length > 0 && (
        <div className="card p-4 space-y-3">
          <div>
            <div className="text-sm font-semibold text-slate-800">{t('app.dashboard.stages.stack_title')}</div>
            <div className="text-xs text-slate-500">{t('app.dashboard.stages.stack_subtitle')}</div>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100 flex">
            {stageStackSegments.map((segment) => (
              <div
                key={`stack-${segment.label}`}
                className={['h-full', STAGE_STACK_COLORS[segment.outcome]].join(' ')}
                style={{ width: `${segment.percent}%` }}
                title={`${segment.label}: ${formatNumber(segment.value)} (${segment.percent}%)`}
              />
            ))}
          </div>
          <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2 lg:grid-cols-3">
            {stageStackSegments.slice(0, 6).map((segment) => (
              <Link
                key={`legend-${segment.label}`}
                to={makeCandidatesHref({ stage: segment.stageKeyForFilter })}
                className="flex items-center gap-2 rounded px-1 py-0.5 hover:bg-slate-50"
              >
                <span className={`h-2 w-2 rounded-full ${STAGE_STACK_COLORS[segment.outcome]}`} />
                <span className="truncate">
                  {segment.label} · {segment.percent}%
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {errText && (
        <div className="text-sm text-red-600 whitespace-pre-wrap break-words">
          {errText}
        </div>
      )}

      {rangeInvalid && (
        <div className="text-sm text-red-600">{t('app.dashboard.errors.range_invalid')}</div>
      )}

      {isWidgetVisible('globalStats') && (
        <div className="grid w-full gap-4 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
          <Link to={CRM_APP_PATHS.candidates} className="card block p-4 hover:border-brand-200">
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.candidates_total')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.candidates)}</div>
          </Link>
          <Link to={CRM_APP_PATHS.clientsDirectory} className="card block p-4 hover:border-brand-200">
            <div className="text-slate-500 text-sm mb-1">{dashboardCompanyLabels.plural}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.companies)}</div>
          </Link>
          <Link to={CRM_APP_PATHS.vacancies} className="card block p-4 hover:border-brand-200">
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.vacancies')}</div>
            <div className="text-2xl font-semibold">{formatNumber(globalCounts.vacancies)}</div>
          </Link>
          <Link
            to={CRM_APP_PATHS.candidates}
            className="card block p-4 border border-brand-100 hover:border-brand-200"
          >
            <div className="text-slate-500 text-sm mb-1">{t('app.dashboard.stats.period')}</div>
            <div className="text-2xl font-semibold">{formatNumber(periodTotal)}</div>
            <div className="text-xs text-slate-500 mt-1">
              {dateField === 'created'
                ? t('app.dashboard.stats.period_suffix_created')
                : t('app.dashboard.stats.period_suffix_updated')}
            </div>
          </Link>
        </div>
      )}

      {businessProfileCards.length > 0 && (
        <div className="card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">
              {t('app.dashboard.business.title')}
            </div>
            <div className="text-xs text-slate-500">
              {t('app.dashboard.business.type_label')}: {businessTypeLabel}
            </div>
          </div>
          <div className="grid w-full gap-3 grid-cols-[repeat(auto-fill,minmax(180px,1fr))]">
            {businessProfileCards.map((card) => (
              <Link key={card.key} to={businessCardHref(card.key)} className="block rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 hover:border-brand-200">
                <div className="text-xs text-slate-500">{card.label}</div>
                <div className="mt-1 text-xl font-semibold text-slate-900">{formatNumber(card.value)}</div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {(isWidgetVisible('stages') || isWidgetVisible('reasons')) && (
        <div className="grid gap-4 lg:grid-cols-3">
          {isWidgetVisible('stages') && (
            <div className="card p-4 lg:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-sm font-semibold">{t('app.dashboard.stages.title')}</div>
                  <div className="text-xs text-slate-500">{t('app.dashboard.stages.subtitle')}</div>
                </div>
              </div>
              {groupedStages.length ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>{t('app.dashboard.stages.table.status')}</th>
                      <th className="text-right">{t('app.dashboard.stages.table.count')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupedStages.map((stage, index) => (
                      <tr key={`grouped-stage-${index}-${stage.keys.join('-')}`}>
                        <td>
                          <Link to={makeCandidatesHref({ stage: stage.keys[0] })} title={drilldownTitle} className={drillInlineClass}>
                            {stage.label}
                          </Link>
                        </td>
                        <td className="text-right font-medium">{formatNumber(stage.count)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-sm text-slate-500">{t('app.dashboard.stages.empty')}</div>
              )}
            </div>
          )}
          {isWidgetVisible('reasons') && (
            <div className="card p-4 space-y-4">
              <div>
                <div className="text-sm font-semibold mb-2">{t('app.dashboard.reasons.rejected_title')}</div>
                {groupedRejectedReasons.length ? (
                  <ul className="space-y-1 text-sm">
                    {groupedRejectedReasons.slice(0, 8).map((item, index) => (
                      <li key={`rejected-grouped-${index}-${Array.from(item.codes).join('-') || item.label}`} className="flex justify-between gap-2">
                        <Link
                          to={makeCandidatesHref({ stage: 'rejected', status_reason: Array.from(item.codes)[0] || item.label })}
                          className="truncate hover:underline"
                        >
                          {item.label}
                        </Link>
                        <span className="font-medium">{formatNumber(item.count)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-sm text-slate-500">{t('app.dashboard.reasons.rejected_empty')}</div>
                )}
              </div>
              <div>
                <div className="text-sm font-semibold mb-2">{t('app.dashboard.reasons.declined_title')}</div>
                {groupedDeclinedReasons.length ? (
                  <ul className="space-y-1 text-sm">
                    {groupedDeclinedReasons.slice(0, 8).map((item, index) => (
                      <li key={`declined-grouped-${index}-${Array.from(item.codes).join('-') || item.label}`} className="flex justify-between gap-2">
                        <Link
                          to={makeCandidatesHref({ stage: 'declined', status_reason: Array.from(item.codes)[0] || item.label })}
                          className="truncate hover:underline"
                        >
                          {item.label}
                        </Link>
                        <span className="font-medium">{formatNumber(item.count)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-sm text-slate-500">{t('app.dashboard.reasons.declined_empty')}</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  )
}
