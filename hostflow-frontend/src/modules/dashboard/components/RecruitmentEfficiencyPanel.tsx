import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { TranslateFn } from '../../../i18n'
import type { ContactAttemptStatsResponse, DocumentStatsResponse } from '../../../api/analytics'
import {
  AnalyticsEmptyState,
  AnalyticsSection,
  AnalyticsTable,
  BreakdownChart,
  FunnelChart,
  InsightCard,
  KpiCard,
  KpiCardGrid,
  TargetProgress,
  fillForStatusKey,
  AnalyticsStoryHero,
} from '../../../components/analytics'
import type { CandidateSlicesResponse, NamedCount } from '../types'

const TERMINAL_STAGES = new Set(['rejected', 'declined'])
const DOCS_WAIT_KEYS = new Set(['docs_wait', 'waiting_docs'])
const DOCS_GOT_KEYS = new Set(['docs_got'])

export type CandidatesHrefBuilder = (opts: { stages?: string }) => string

export interface RecruitmentEfficiencyPanelProps {
  t: TranslateFn
  formatNumber: (value?: number) => string
  slices: CandidateSlicesResponse | null
  documentStats: DocumentStatsResponse | null
  contactStats?: ContactAttemptStatsResponse | null
  loading: boolean
  buildCandidatesHref?: CandidatesHrefBuilder
  present?: boolean
}

function translateStageLabel(t: TranslateFn, key: string, fallback?: string): string {
  return t(`app.candidates.stage_labels.${key}`, { defaultValue: fallback || key })
}

function translateReasonLabel(t: TranslateFn, key: string, fallback?: string): string {
  if (key === 'no_reason' || key === 'Без причины') {
    return t('app.dashboard.labels.no_reason', { defaultValue: 'No reason' })
  }
  return t(`app.dashboard.reason_codes.${key}`, { defaultValue: fallback || key })
}

function translateDocStatus(t: TranslateFn, status: string): string {
  return t(`app.dashboard.efficiency.docs.statuses.${status}`, { defaultValue: status })
}

function mergeStagesByKey(rows: NamedCount[], t: TranslateFn): NamedCount[] {
  const merged = new Map<string, NamedCount>()
  for (const row of rows) {
    const key = String(row.key || '').trim()
    if (!key) continue
    if (merged.has(key)) continue
    merged.set(key, {
      key,
      label: translateStageLabel(t, key, row.label || key),
      count: row.count || 0,
    })
  }
  return [...merged.values()].sort((a, b) => (b.count || 0) - (a.count || 0))
}

function localizeReasonRows(rows: NamedCount[], t: TranslateFn): NamedCount[] {
  return rows.map((row) => ({
    ...row,
    label: translateReasonLabel(t, String(row.key || ''), row.label),
  }))
}

function stageCount(stages: NamedCount[], keys: Set<string>): number {
  return stages.reduce(
    (sum, s) => (keys.has(String(s.key || '').toLowerCase()) ? sum + (s.count || 0) : sum),
    0,
  )
}

function pct(part: number, total: number): string {
  if (!total) return '0%'
  return `${((part / total) * 100).toFixed(1)}%`
}

function truncateLabel(value: string, max = 28): string {
  const s = String(value || '')
  return s.length > max ? `${s.slice(0, max - 1)}…` : s
}

function ColorSwatch({ fill }: { fill: string }) {
  return <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: fill }} />
}

export function RecruitmentEfficiencyPanel({
  t,
  formatNumber,
  slices,
  documentStats,
  contactStats = null,
  loading,
  buildCandidatesHref,
  present = false,
}: RecruitmentEfficiencyPanelProps) {
  const navigate = useNavigate()
  const hrefFor = (stages?: string) => (buildCandidatesHref ? buildCandidatesHref({ stages }) : undefined)
  const openRow = (row: { href?: string }) => {
    if (row.href) navigate(row.href)
  }
  const total = slices?.total ?? 0
  const stages = useMemo(() => mergeStagesByKey(slices?.stages ?? [], t), [slices?.stages, t])
  const rejected = stages.find((s) => String(s.key).toLowerCase() === 'rejected')?.count ?? 0
  const declined = stages.find((s) => String(s.key).toLowerCase() === 'declined')?.count ?? 0
  const closed = rejected + declined
  const inProgress = Math.max(0, total - closed)
  const docsWait = stageCount(stages, DOCS_WAIT_KEYS)
  const docsGot = stageCount(stages, DOCS_GOT_KEYS)
  const rejectedReasons = useMemo(
    () => localizeReasonRows(slices?.reasons?.rejected ?? [], t),
    [slices?.reasons?.rejected, t],
  )
  const declinedReasons = useMemo(
    () => localizeReasonRows(slices?.reasons?.declined ?? [], t),
    [slices?.reasons?.declined, t],
  )
  const docStatusRows = Object.entries(documentStats?.by_status ?? {}).sort((a, b) => b[1] - a[1])

  const outcomeRows = useMemo(
    () =>
      [
        {
          key: 'rejected',
          name: t('app.dashboard.efficiency.charts.outcome_rejected'),
          fullName: t('app.dashboard.efficiency.charts.outcome_rejected'),
          value: rejected,
          fill: fillForStatusKey('rejected'),
          href: buildCandidatesHref?.({ stages: 'rejected' }),
        },
        {
          key: 'declined',
          name: t('app.dashboard.efficiency.charts.outcome_declined'),
          fullName: t('app.dashboard.efficiency.charts.outcome_declined'),
          value: declined,
          fill: fillForStatusKey('declined'),
          href: buildCandidatesHref?.({ stages: 'declined' }),
        },
        {
          key: 'in_progress',
          name: t('app.dashboard.efficiency.charts.outcome_in_progress'),
          fullName: t('app.dashboard.efficiency.charts.outcome_in_progress'),
          value: inProgress,
          fill: fillForStatusKey('in_progress'),
        },
      ].filter((d) => d.value > 0),
    [t, rejected, declined, inProgress, buildCandidatesHref],
  )

  const stageChartData = useMemo(
    () =>
      stages.map((row, i) => ({
        key: row.key,
        name: truncateLabel(row.label || row.key, 22),
        fullName: row.label || row.key,
        value: row.count || 0,
        fill: fillForStatusKey(row.key, i),
        href: buildCandidatesHref?.({ stages: row.key }),
      })),
    [stages, buildCandidatesHref],
  )

  const rejectChartData = useMemo(
    () =>
      rejectedReasons.slice(0, 10).map((row) => ({
        key: row.key,
        name: truncateLabel(row.label || row.key, 26),
        fullName: row.label || row.key,
        value: row.count || 0,
        fill: fillForStatusKey('rejected'),
      })),
    [rejectedReasons],
  )

  const declineChartData = useMemo(
    () =>
      declinedReasons.slice(0, 10).map((row) => ({
        key: row.key,
        name: truncateLabel(row.label || row.key, 26),
        fullName: row.label || row.key,
        value: row.count || 0,
        fill: fillForStatusKey('declined'),
      })),
    [declinedReasons],
  )

  const docChartData = useMemo(
    () =>
      docStatusRows.map(([status, count], i) => ({
        key: status,
        name: translateDocStatus(t, status),
        fullName: translateDocStatus(t, status),
        value: count,
        fill: fillForStatusKey(status, i),
      })),
    [docStatusRows, t],
  )

  const cohortTotal = contactStats?.cohort_total ?? total
  const attempted = contactStats?.candidates_with_attempts ?? 0
  const reached = contactStats?.candidates_reached ?? 0
  const untouched = Math.max(0, cohortTotal - attempted)
  const contactFunnel = useMemo(
    () =>
      [
        {
          key: 'received',
          name: t('app.dashboard.efficiency.contact.funnel_received'),
          value: cohortTotal,
          fill: fillForStatusKey('received'),
        },
        {
          key: 'attempted',
          name: t('app.dashboard.efficiency.contact.funnel_attempted'),
          value: attempted,
          fill: fillForStatusKey('attempted'),
        },
        {
          key: 'reached',
          name: t('app.dashboard.efficiency.contact.funnel_reached'),
          value: reached,
          fill: fillForStatusKey('reached'),
        },
        {
          key: 'closed',
          name: t('app.dashboard.efficiency.contact.funnel_closed'),
          value: closed,
          fill: fillForStatusKey('rejected'),
        },
      ].filter((row) => row.value > 0 || row.key === 'received'),
    [t, cohortTotal, attempted, reached, closed],
  )
  const contactResultRows = useMemo(() => {
    const entries = Object.entries(contactStats?.by_result ?? {}).sort((a, b) => b[1] - a[1])
    return entries.map(([key, count], i) => ({
      key,
      name: t(`app.dashboard.efficiency.contact.results.${key}`, { defaultValue: key }),
      fullName: t(`app.dashboard.efficiency.contact.results.${key}`, { defaultValue: key }),
      value: count,
      fill: fillForStatusKey(key, i),
    }))
  }, [contactStats?.by_result, t])
  const stageContacted = stages.find((s) => String(s.key).toLowerCase() === 'contacted')?.count ?? 0
  const stageNoAnswer = stages.find((s) => String(s.key).toLowerCase() === 'no_answer')?.count ?? 0
  const docsComplete = documentStats?.candidates_with_complete_docs ?? 0

  if (loading && !slices) {
    return <AnalyticsEmptyState kind="no_data" title={t('common.loading')} />
  }

  if (!slices) {
    return <AnalyticsEmptyState kind="no_data" title={t('app.dashboard.efficiency.empty')} />
  }

  const chartsReady = !loading
  const closedHref = hrefFor('rejected,declined')

  return (
    <div className={`space-y-6 ${loading ? 'opacity-70 transition-opacity duration-300' : ''}`}>
      <AnalyticsStoryHero
        label={t('app.dashboard.efficiency.stats.total')}
        value={formatNumber(total)}
        unit={t('app.dashboard.share.unit_candidates', { defaultValue: 'candidates' })}
        caption={t('app.dashboard.efficiency.subtitle')}
        tone="neutral"
        supporting={
          <KpiCardGrid className="lg:grid-cols-3">
            <KpiCard
              label={t('app.dashboard.efficiency.stats.in_progress')}
              value={formatNumber(inProgress)}
              tone="info"
            />
            <KpiCard
              label={t('app.dashboard.efficiency.stats.closed')}
              value={formatNumber(closed)}
              tone="danger"
              href={present ? undefined : closedHref}
            />
            <KpiCard
              label={t('app.dashboard.efficiency.stats.docs_pipeline')}
              value={formatNumber(docsWait + docsGot)}
              tone="warning"
              href={present ? undefined : hrefFor('docs_wait')}
            />
          </KpiCardGrid>
        }
      />

      {total > 0 && closed / total >= 0.5 ? (
        <InsightCard
          tone="warning"
          present={present}
          title={t('app.dashboard.efficiency.insight_title', { defaultValue: 'Close rate is high' })}
          body={t('app.dashboard.efficiency.insight', {
            values: {
              closedPct: pct(closed, total),
              early: formatNumber(
                stages
                  .filter((s) => ['new', 'contacted', 'no_answer'].includes(String(s.key).toLowerCase()))
                  .reduce((n, s) => n + (s.count || 0), 0),
              ),
              docs: formatNumber(docsWait + docsGot),
            },
          })}
          actions={[
            ...(hrefFor('rejected')
              ? [
                  {
                    label: t('app.dashboard.efficiency.actions.view_rejected'),
                    href: hrefFor('rejected') as string,
                  },
                ]
              : []),
            ...(hrefFor('declined')
              ? [
                  {
                    label: t('app.dashboard.efficiency.actions.view_declined'),
                    href: hrefFor('declined') as string,
                  },
                ]
              : []),
            ...(hrefFor('docs_wait')
              ? [
                  {
                    label: t('app.dashboard.efficiency.actions.view_docs_wait'),
                    href: hrefFor('docs_wait') as string,
                  },
                ]
              : []),
          ]}
        />
      ) : null}

      <AnalyticsSection
        title={t('app.dashboard.efficiency.contact.title')}
        subtitle={t('app.dashboard.efficiency.contact.subtitle')}
        density="story"
      >
        <KpiCardGrid className="lg:grid-cols-5">
          <KpiCard
            label={t('app.dashboard.efficiency.contact.received')}
            value={formatNumber(cohortTotal)}
            tone="neutral"
          />
          <KpiCard
            label={t('app.dashboard.efficiency.contact.attempted')}
            value={formatNumber(attempted)}
            tone="info"
          />
          <KpiCard
            label={t('app.dashboard.efficiency.contact.reached')}
            value={formatNumber(reached)}
            tone="success"
          />
          <KpiCard
            label={t('app.dashboard.efficiency.contact.untouched')}
            value={formatNumber(untouched)}
            tone="warning"
          />
          <KpiCard
            label={t('app.dashboard.efficiency.contact.attempts_total')}
            value={formatNumber(contactStats?.total_attempts)}
            tone="neutral"
          />
        </KpiCardGrid>
        <p className="mt-2 text-xs text-slate-500">
          {t('app.dashboard.efficiency.contact.funnel_hint', {
            values: {
              avg: formatNumber(contactStats?.avg_per_candidate ?? 0),
              limit: formatNumber(contactStats?.limit_reached_count ?? 0),
            },
          })}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          {t('app.dashboard.efficiency.contact.stage_now', {
            values: {
              contacted: formatNumber(stageContacted),
              noAnswer: formatNumber(stageNoAnswer),
            },
          })}
        </p>
        {!contactStats || (contactStats.total_attempts === 0 && attempted === 0) ? (
          <div className="mt-4">
            <AnalyticsEmptyState
              kind="tracking_not_started"
              title={t('app.dashboard.efficiency.contact.empty')}
            />
          </div>
        ) : (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <FunnelChart steps={contactFunnel} ready={chartsReady} formatValue={formatNumber} />
            {contactResultRows.length === 0 ? (
              <AnalyticsEmptyState kind="no_data" title={t('app.dashboard.efficiency.empty')} />
            ) : (
              <BreakdownChart data={contactResultRows} ready={chartsReady} formatValue={formatNumber} />
            )}
          </div>
        )}
      </AnalyticsSection>

      <div className="grid gap-4 lg:grid-cols-2">
        <AnalyticsSection
          title={t('app.dashboard.efficiency.charts.outcomes_title')}
          subtitle={t('app.dashboard.efficiency.charts.outcomes_hint')}
        >
          {outcomeRows.length === 0 ? (
            <AnalyticsEmptyState kind="no_data" title={t('app.dashboard.efficiency.empty')} />
          ) : (
            <BreakdownChart
              data={outcomeRows}
              ready={chartsReady}
              formatValue={formatNumber}
              onPointClick={present ? undefined : openRow}
            />
          )}
        </AnalyticsSection>

        <AnalyticsSection
          title={t('app.dashboard.efficiency.stages.title')}
          subtitle={t('app.dashboard.efficiency.stages.subtitle')}
        >
          {stageChartData.length === 0 ? (
            <AnalyticsEmptyState kind="no_data" title={t('app.dashboard.efficiency.empty')} />
          ) : (
            <BreakdownChart
              data={stageChartData.slice(0, 8)}
              ready={chartsReady}
              formatValue={formatNumber}
              onPointClick={present ? undefined : openRow}
            />
          )}
        </AnalyticsSection>
      </div>

      <AnalyticsSection title={t('app.dashboard.efficiency.stages.title')}>
        <AnalyticsTable
          columns={[
            {
              id: 'stage',
              header: t('app.dashboard.efficiency.stages.col_stage'),
              cell: (row: (typeof stages)[number] & { fill: string; i: number }) => (
                <span className="inline-flex items-center gap-2">
                  <ColorSwatch fill={row.fill} />
                  {row.label || row.key}
                  {TERMINAL_STAGES.has(String(row.key || '').toLowerCase()) ? (
                    <span className="text-[10px] uppercase tracking-wide text-slate-400">
                      {t('app.dashboard.efficiency.stages.terminal')}
                    </span>
                  ) : null}
                </span>
              ),
            },
            {
              id: 'count',
              header: t('app.dashboard.efficiency.stages.col_count'),
              align: 'right',
              cell: (row) => <span className="font-medium text-slate-900">{formatNumber(row.count)}</span>,
            },
            {
              id: 'share',
              header: t('app.dashboard.efficiency.stages.col_share'),
              align: 'right',
              cell: (row) => pct(row.count || 0, total),
            },
          ]}
          rows={stages.map((row, i) => ({ ...row, fill: fillForStatusKey(row.key, i), i }))}
          rowKey={(row) => row.key}
          empty={<AnalyticsEmptyState kind="no_data" title={t('app.dashboard.efficiency.empty')} />}
        />
      </AnalyticsSection>

      <div className="grid gap-4 lg:grid-cols-2">
        <AnalyticsSection
          title={t('app.dashboard.efficiency.reasons.rejected_title', {
            values: { count: formatNumber(rejected) },
          })}
          subtitle={t('app.dashboard.efficiency.reasons.hint')}
        >
          {rejectedReasons.length === 0 ? (
            <AnalyticsEmptyState kind="no_data" title={t('app.dashboard.efficiency.reasons.empty')} />
          ) : (
            <BreakdownChart data={rejectChartData} ready={chartsReady} formatValue={formatNumber} className="h-56 w-full min-w-0" />
          )}
        </AnalyticsSection>
        <AnalyticsSection
          title={t('app.dashboard.efficiency.reasons.declined_title', {
            values: { count: formatNumber(declined) },
          })}
          subtitle={t('app.dashboard.efficiency.reasons.hint')}
        >
          {declinedReasons.length === 0 ? (
            <AnalyticsEmptyState kind="no_data" title={t('app.dashboard.efficiency.reasons.empty')} />
          ) : (
            <BreakdownChart data={declineChartData} ready={chartsReady} formatValue={formatNumber} className="h-56 w-full min-w-0" />
          )}
        </AnalyticsSection>
      </div>

      <AnalyticsSection
        title={t('app.dashboard.efficiency.docs.title')}
        subtitle={t('app.dashboard.efficiency.docs.subtitle')}
      >
        <KpiCardGrid className="sm:grid-cols-3 lg:grid-cols-3">
          <KpiCard
            label={t('app.dashboard.efficiency.docs.wait')}
            value={formatNumber(docsWait)}
            tone="warning"
            href={present ? undefined : hrefFor('docs_wait')}
          />
          <KpiCard
            label={t('app.dashboard.efficiency.docs.got')}
            value={formatNumber(docsGot)}
            tone="success"
            href={present ? undefined : hrefFor('docs_got')}
          />
          <KpiCard
            label={t('app.dashboard.efficiency.docs.complete')}
            value={formatNumber(docsComplete)}
            tone="info"
          />
        </KpiCardGrid>
        {total > 0 ? (
          <div className="mt-3">
            <TargetProgress
              label={t('app.dashboard.efficiency.docs.complete')}
              value={docsComplete}
              target={total}
              format={formatNumber}
              tone="success"
            />
          </div>
        ) : null}

        {docChartData.length > 0 ? (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <BreakdownChart data={docChartData} ready={chartsReady} formatValue={formatNumber} />
            <AnalyticsTable
              columns={[
                {
                  id: 'status',
                  header: t('app.dashboard.efficiency.docs.col_status'),
                  cell: (row: (typeof docChartData)[number]) => (
                    <span className="inline-flex items-center gap-2">
                      <ColorSwatch fill={row.fill} />
                      {row.name}
                    </span>
                  ),
                },
                {
                  id: 'count',
                  header: t('app.dashboard.efficiency.docs.col_count'),
                  align: 'right',
                  cell: (row) => <span className="font-medium text-slate-900">{formatNumber(row.value)}</span>,
                },
              ]}
              rows={docChartData}
              rowKey={(row) => row.key}
              totals={t('app.dashboard.efficiency.docs.files_total', {
                values: { count: formatNumber(documentStats?.total_docs ?? 0) },
              })}
            />
          </div>
        ) : (
          <div className="mt-3">
            <AnalyticsEmptyState kind="no_data" title={t('app.dashboard.efficiency.docs.empty_files')} />
          </div>
        )}
      </AnalyticsSection>
    </div>
  )
}
