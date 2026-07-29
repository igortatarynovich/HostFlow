import { useMemo } from 'react'
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
import type { TranslateFn } from '../../../i18n'
import type { ContactAttemptStatsResponse, DocumentStatsResponse } from '../../../api/analytics'
import type { CandidateSlicesResponse, NamedCount } from '../types'
import { ChartHost } from './ChartHost'

const TERMINAL_STAGES = new Set(['rejected', 'declined'])
const DOCS_WAIT_KEYS = new Set(['docs_wait', 'waiting_docs'])
const DOCS_GOT_KEYS = new Set(['docs_got'])

const OUTCOME_COLORS = {
  rejected: '#e11d48',
  declined: '#d97706',
  in_progress: '#0284c7',
} as const

const STAGE_COLORS: Record<string, string> = {
  rejected: '#e11d48',
  declined: '#d97706',
  new: '#64748b',
  contacted: '#0ea5e9',
  no_answer: '#f97316',
  processing_by_hr: '#8b5cf6',
  docs_wait: '#eab308',
  waiting_docs: '#eab308',
  docs_got: '#22c55e',
  ready_for_handoff: '#14b8a6',
  employment_pending: '#06b6d4',
  handoff_returned: '#f43f5e',
  employed: '#16a34a',
  hired: '#15803d',
  probation_ok: '#166534',
}

const STAGE_PALETTE = [
  '#0ea5e9',
  '#8b5cf6',
  '#14b8a6',
  '#f97316',
  '#6366f1',
  '#ec4899',
  '#84cc16',
  '#06b6d4',
]

const REJECT_BAR = '#e11d48'
const DECLINE_BAR = '#d97706'

const DOC_STATUS_COLORS: Record<string, string> = {
  approved: '#16a34a',
  received: '#0ea5e9',
  submitted: '#8b5cf6',
  requested: '#64748b',
  rejected: '#e11d48',
  verified: '#15803d',
  overdue: '#f97316',
  expired: '#b91c1c',
  missing: '#94a3b8',
}

function stageColor(key: string, index: number): string {
  const k = String(key || '').toLowerCase()
  return STAGE_COLORS[k] || STAGE_PALETTE[index % STAGE_PALETTE.length]
}

function stageCount(stages: NamedCount[], keys: Set<string>): number {
  return stages.reduce((sum, s) => (keys.has(String(s.key || '').toLowerCase()) ? sum + (s.count || 0) : sum), 0)
}

function pct(part: number, total: number): string {
  if (!total) return '0%'
  return `${((part / total) * 100).toFixed(1)}%`
}

function truncateLabel(value: string, max = 28): string {
  const s = String(value || '')
  return s.length > max ? `${s.slice(0, max - 1)}…` : s
}

const CONTACT_RESULT_COLORS: Record<string, string> = {
  answered: '#16a34a',
  no_answer: '#f97316',
  wrong_number: '#e11d48',
  unavailable: '#64748b',
  interested: '#0ea5e9',
  callback_requested: '#8b5cf6',
  not_interested: '#94a3b8',
}

export interface RecruitmentEfficiencyPanelProps {
  t: TranslateFn
  formatNumber: (value?: number) => string
  slices: CandidateSlicesResponse | null
  documentStats: DocumentStatsResponse | null
  contactStats?: ContactAttemptStatsResponse | null
  loading: boolean
}

function translateStageLabel(t: TranslateFn, key: string, fallback?: string): string {
  return t(`app.candidates.stage_labels.${key}`, { defaultValue: fallback || key })
}

function translateReasonLabel(t: TranslateFn, key: string, fallback?: string): string {
  if (key === 'no_reason' || key === 'Без причины') {
    return t('app.dashboard.labels.no_reason', { defaultValue: fallback || key })
  }
  return t(`app.dashboard.reason_codes.${key}`, { defaultValue: fallback || key })
}

function translateDocStatus(t: TranslateFn, status: string): string {
  return t(`app.dashboard.efficiency.docs.statuses.${status}`, { defaultValue: status })
}

/** Collapse duplicate stage keys (ORDER may list the same code in multiple lanes). */
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

export function RecruitmentEfficiencyPanel({
  t,
  formatNumber,
  slices,
  documentStats,
  contactStats = null,
  loading,
}: RecruitmentEfficiencyPanelProps) {
  const total = slices?.total ?? 0
  const stages = useMemo(
    () => mergeStagesByKey(slices?.stages ?? [], t),
    [slices?.stages, t],
  )
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

  const outcomePie = useMemo(
    () =>
      [
        {
          key: 'rejected',
          name: t('app.dashboard.efficiency.charts.outcome_rejected'),
          value: rejected,
          fill: OUTCOME_COLORS.rejected,
        },
        {
          key: 'declined',
          name: t('app.dashboard.efficiency.charts.outcome_declined'),
          value: declined,
          fill: OUTCOME_COLORS.declined,
        },
        {
          key: 'in_progress',
          name: t('app.dashboard.efficiency.charts.outcome_in_progress'),
          value: inProgress,
          fill: OUTCOME_COLORS.in_progress,
        },
      ].filter((d) => d.value > 0),
    [t, rejected, declined, inProgress],
  )

  const stageChartData = useMemo(
    () =>
      stages.map((row, i) => ({
        key: row.key,
        name: truncateLabel(row.label || row.key, 22),
        fullName: row.label || row.key,
        count: row.count || 0,
        fill: stageColor(row.key, i),
      })),
    [stages],
  )

  const rejectChartData = useMemo(
    () =>
      rejectedReasons.slice(0, 10).map((row) => ({
        name: truncateLabel(row.label || row.key, 26),
        fullName: row.label || row.key,
        count: row.count || 0,
      })),
    [rejectedReasons],
  )

  const declineChartData = useMemo(
    () =>
      declinedReasons.slice(0, 10).map((row) => ({
        name: truncateLabel(row.label || row.key, 26),
        fullName: row.label || row.key,
        count: row.count || 0,
      })),
    [declinedReasons],
  )

  const docChartData = useMemo(
    () =>
      docStatusRows.map(([status, count], i) => ({
        key: status,
        name: translateDocStatus(t, status),
        count,
        fill: DOC_STATUS_COLORS[status] || STAGE_PALETTE[i % STAGE_PALETTE.length],
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
          fill: '#64748b',
        },
        {
          key: 'attempted',
          name: t('app.dashboard.efficiency.contact.funnel_attempted'),
          value: attempted,
          fill: '#0ea5e9',
        },
        {
          key: 'reached',
          name: t('app.dashboard.efficiency.contact.funnel_reached'),
          value: reached,
          fill: '#16a34a',
        },
        {
          key: 'closed',
          name: t('app.dashboard.efficiency.contact.funnel_closed'),
          value: closed,
          fill: '#e11d48',
        },
      ].filter((row) => row.value > 0 || row.key === 'received'),
    [t, cohortTotal, attempted, reached, closed],
  )
  const contactResultRows = useMemo(() => {
    const entries = Object.entries(contactStats?.by_result ?? {}).sort((a, b) => b[1] - a[1])
    return entries.map(([key, count], i) => ({
      key,
      name: t(`app.dashboard.efficiency.contact.results.${key}`, { defaultValue: key }),
      count,
      fill: CONTACT_RESULT_COLORS[key] || STAGE_PALETTE[i % STAGE_PALETTE.length],
    }))
  }, [contactStats?.by_result, t])
  const stageContacted = stages.find((s) => String(s.key).toLowerCase() === 'contacted')?.count ?? 0
  const stageNoAnswer = stages.find((s) => String(s.key).toLowerCase() === 'no_answer')?.count ?? 0

  if (loading && !slices) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        {t('common.loading')}
      </div>
    )
  }

  if (!slices) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        {t('app.dashboard.efficiency.empty')}
      </div>
    )
  }

  const tooltipFmt = (value: number) => formatNumber(value)

  const chartsReady = !loading

  return (
    <div className={`space-y-4 ${loading ? 'opacity-70 transition-opacity' : ''}`}>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t('app.dashboard.efficiency.stats.total')} value={formatNumber(total)} tone="neutral" />
        <StatCard
          label={t('app.dashboard.efficiency.stats.in_progress')}
          value={formatNumber(inProgress)}
          tone="info"
        />
        <StatCard
          label={t('app.dashboard.efficiency.stats.closed')}
          value={formatNumber(closed)}
          tone="danger"
        />
        <StatCard
          label={t('app.dashboard.efficiency.stats.docs_pipeline')}
          value={formatNumber(docsWait + docsGot)}
          tone="warning"
        />
      </div>

      {total > 0 && closed / total >= 0.5 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {t('app.dashboard.efficiency.insight', {
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
        </div>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          {t('app.dashboard.efficiency.contact.title')}
        </h2>
        <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.efficiency.contact.subtitle')}</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <StatCard
            label={t('app.dashboard.efficiency.contact.received')}
            value={formatNumber(cohortTotal)}
            tone="neutral"
          />
          <StatCard
            label={t('app.dashboard.efficiency.contact.attempted')}
            value={formatNumber(attempted)}
            tone="info"
          />
          <StatCard
            label={t('app.dashboard.efficiency.contact.reached')}
            value={formatNumber(reached)}
            tone="success"
          />
          <StatCard
            label={t('app.dashboard.efficiency.contact.untouched')}
            value={formatNumber(untouched)}
            tone="warning"
          />
          <StatCard
            label={t('app.dashboard.efficiency.contact.attempts_total')}
            value={formatNumber(contactStats?.total_attempts)}
            tone="neutral"
          />
        </div>
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
          <p className="mt-4 text-sm text-slate-500">{t('app.dashboard.efficiency.contact.empty')}</p>
        ) : (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <ChartHost className="h-48 w-full min-w-0" ready={chartsReady}>
              <BarChart data={contactFunnel} layout="vertical" margin={{ left: 8, right: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11, fill: '#475569' }} />
                <Tooltip formatter={tooltipFmt as never} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {contactFunnel.map((entry) => (
                    <Cell key={entry.key} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ChartHost>
            <ChartHost className="h-48 w-full min-w-0" ready={chartsReady}>
              <PieChart>
                <Pie
                  data={contactResultRows}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                >
                  {contactResultRows.map((entry) => (
                    <Cell key={entry.key} fill={entry.fill} stroke="#fff" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip formatter={tooltipFmt as never} />
              </PieChart>
            </ChartHost>
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.efficiency.charts.outcomes_title')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.efficiency.charts.outcomes_hint')}</p>
          {outcomePie.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.efficiency.empty')}</p>
          ) : (
            <div className="mt-2 flex flex-col items-center gap-3 sm:flex-row">
              <ChartHost className="h-52 w-full min-w-0 sm:w-1/2" ready={chartsReady}>
                <PieChart>
                  <Pie
                    data={outcomePie}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={78}
                    paddingAngle={2}
                  >
                    {outcomePie.map((entry) => (
                      <Cell key={entry.key} fill={entry.fill} stroke="#fff" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip formatter={tooltipFmt as never} />
                </PieChart>
              </ChartHost>
              <ul className="w-full space-y-2 sm:w-1/2">
                {outcomePie.map((entry) => (
                  <li key={entry.key} className="flex items-center justify-between gap-2 text-sm">
                    <span className="flex min-w-0 items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: entry.fill }}
                      />
                      <span className="truncate text-slate-700">{entry.name}</span>
                    </span>
                    <span className="shrink-0 tabular-nums font-semibold text-slate-900">
                      {formatNumber(entry.value)}
                      <span className="ml-1 text-xs font-normal text-slate-500">
                        ({pct(entry.value, total)})
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.dashboard.efficiency.stages.title')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.efficiency.stages.subtitle')}</p>
          {stageChartData.length === 0 ? (
            <p className="mt-6 text-sm text-slate-500">{t('app.dashboard.efficiency.empty')}</p>
          ) : (
            <ChartHost className="mt-2 h-52 w-full min-w-0" ready={chartsReady}>
              <BarChart
                layout="vertical"
                data={stageChartData.slice(0, 8)}
                margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={110}
                  tick={{ fontSize: 11, fill: '#475569' }}
                />
                <Tooltip
                  formatter={tooltipFmt as never}
                  labelFormatter={(_, payload) =>
                    String((payload?.[0]?.payload as { fullName?: string } | undefined)?.fullName || '')
                  }
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {stageChartData.slice(0, 8).map((entry) => (
                    <Cell key={entry.key} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ChartHost>
          )}
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">{t('app.dashboard.efficiency.stages.title')}</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3 font-medium">{t('app.dashboard.efficiency.stages.col_stage')}</th>
                <th className="py-2 pr-3 text-right font-medium">{t('app.dashboard.efficiency.stages.col_count')}</th>
                <th className="py-2 text-right font-medium">{t('app.dashboard.efficiency.stages.col_share')}</th>
              </tr>
            </thead>
            <tbody>
              {stages.map((row, i) => {
                const key = String(row.key || '').toLowerCase()
                const isTerminal = TERMINAL_STAGES.has(key)
                const color = stageColor(row.key, i)
                return (
                  <tr key={row.key} className="border-b border-slate-50">
                    <td className="py-2 pr-3 text-slate-800">
                      <span className="inline-flex items-center gap-2">
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
                        {row.label || row.key}
                        {isTerminal ? (
                          <span className="text-[10px] uppercase tracking-wide text-slate-400">
                            {t('app.dashboard.efficiency.stages.terminal')}
                          </span>
                        ) : null}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-right font-medium tabular-nums text-slate-900">
                      {formatNumber(row.count)}
                    </td>
                    <td className="py-2 text-right tabular-nums text-slate-600">{pct(row.count || 0, total)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <ReasonsCard
          title={t('app.dashboard.efficiency.reasons.rejected_title', {
            values: { count: formatNumber(rejected) },
          })}
          hint={t('app.dashboard.efficiency.reasons.hint')}
          rows={rejectedReasons}
          chartData={rejectChartData}
          barColor={REJECT_BAR}
          formatNumber={formatNumber}
          empty={t('app.dashboard.efficiency.reasons.empty')}
          chartsReady={chartsReady}
        />
        <ReasonsCard
          title={t('app.dashboard.efficiency.reasons.declined_title', {
            values: { count: formatNumber(declined) },
          })}
          hint={t('app.dashboard.efficiency.reasons.hint')}
          rows={declinedReasons}
          chartData={declineChartData}
          barColor={DECLINE_BAR}
          formatNumber={formatNumber}
          empty={t('app.dashboard.efficiency.reasons.empty')}
          chartsReady={chartsReady}
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">{t('app.dashboard.efficiency.docs.title')}</h2>
        <p className="mt-0.5 text-xs text-slate-500">{t('app.dashboard.efficiency.docs.subtitle')}</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <StatCard
            label={t('app.dashboard.efficiency.docs.wait')}
            value={formatNumber(docsWait)}
            tone="warning"
          />
          <StatCard
            label={t('app.dashboard.efficiency.docs.got')}
            value={formatNumber(docsGot)}
            tone="success"
          />
          <StatCard
            label={t('app.dashboard.efficiency.docs.complete')}
            value={formatNumber(documentStats?.candidates_with_complete_docs ?? 0)}
            tone="info"
          />
        </div>

        {docChartData.length > 0 ? (
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <ChartHost className="h-48 w-full min-w-0" ready={chartsReady}>
              <PieChart>
                <Pie
                  data={docChartData}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                >
                  {docChartData.map((entry) => (
                    <Cell key={entry.key} fill={entry.fill} stroke="#fff" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip formatter={tooltipFmt as never} />
              </PieChart>
            </ChartHost>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-3 font-medium">{t('app.dashboard.efficiency.docs.col_status')}</th>
                    <th className="py-2 text-right font-medium">{t('app.dashboard.efficiency.docs.col_count')}</th>
                  </tr>
                </thead>
                <tbody>
                  {docChartData.map((row) => (
                    <tr key={row.key} className="border-b border-slate-50">
                      <td className="py-2 pr-3 text-slate-800">
                        <span className="inline-flex items-center gap-2">
                          <span
                            className="h-2.5 w-2.5 shrink-0 rounded-full"
                            style={{ backgroundColor: row.fill }}
                          />
                          {row.name}
                        </span>
                      </td>
                      <td className="py-2 text-right font-medium tabular-nums text-slate-900">
                        {formatNumber(row.count)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-xs text-slate-500">
                {t('app.dashboard.efficiency.docs.files_total', {
                  values: { count: formatNumber(documentStats?.total_docs ?? 0) },
                })}
              </p>
            </div>
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">{t('app.dashboard.efficiency.docs.empty_files')}</p>
        )}
      </section>
    </div>
  )
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: 'neutral' | 'info' | 'danger' | 'warning' | 'success'
}) {
  const styles =
    tone === 'danger'
      ? {
          wrap: 'border-rose-200 bg-rose-50/80',
          value: 'text-rose-800',
          bar: 'bg-rose-500',
        }
      : tone === 'warning'
        ? {
            wrap: 'border-amber-200 bg-amber-50/80',
            value: 'text-amber-900',
            bar: 'bg-amber-500',
          }
        : tone === 'info'
          ? {
              wrap: 'border-sky-200 bg-sky-50/80',
              value: 'text-sky-900',
              bar: 'bg-sky-500',
            }
          : tone === 'success'
            ? {
                wrap: 'border-emerald-200 bg-emerald-50/80',
                value: 'text-emerald-900',
                bar: 'bg-emerald-500',
              }
            : {
                wrap: 'border-slate-200 bg-slate-50/90',
                value: 'text-slate-900',
                bar: 'bg-slate-400',
              }

  return (
    <div className={`relative overflow-hidden rounded-lg border px-3 py-2.5 ${styles.wrap}`}>
      <div className={`absolute inset-y-0 left-0 w-1 ${styles.bar}`} />
      <div className="pl-1.5">
        <div className="text-[11px] text-slate-500">{label}</div>
        <div className={`text-xl font-semibold tabular-nums ${styles.value}`}>{value}</div>
      </div>
    </div>
  )
}

function ReasonsCard({
  title,
  hint,
  rows,
  chartData,
  barColor,
  formatNumber,
  empty,
  chartsReady,
}: {
  title: string
  hint: string
  rows: NamedCount[]
  chartData: Array<{ name: string; fullName: string; count: number }>
  barColor: string
  formatNumber: (value?: number) => string
  empty: string
  chartsReady: boolean
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      <p className="mt-0.5 text-xs text-slate-500">{hint}</p>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{empty}</p>
      ) : (
        <>
          <ChartHost className="mt-2 h-56 w-full min-w-0" ready={chartsReady}>
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis
                type="category"
                dataKey="name"
                width={120}
                tick={{ fontSize: 10, fill: '#475569' }}
              />
              <Tooltip
                formatter={((v: number) => formatNumber(v)) as never}
                labelFormatter={(_, payload) =>
                  String((payload?.[0]?.payload as { fullName?: string } | undefined)?.fullName || '')
                }
              />
              <Bar dataKey="count" fill={barColor} radius={[0, 4, 4, 0]} maxBarSize={16} />
            </BarChart>
          </ChartHost>
          <div className="mt-3 space-y-1.5 border-t border-slate-100 pt-3">
            {rows.slice(0, 8).map((row) => {
              const max = rows[0]?.count || 1
              const width = Math.max(4, Math.round(((row.count || 0) / max) * 100))
              return (
                <div key={row.key}>
                  <div className="mb-0.5 flex items-center justify-between gap-2 text-xs">
                    <span className="truncate text-slate-600">{row.label || row.key}</span>
                    <span className="shrink-0 tabular-nums font-medium text-slate-900">
                      {formatNumber(row.count)}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded bg-slate-100">
                    <div className="h-full rounded" style={{ width: `${width}%`, backgroundColor: barColor }} />
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </section>
  )
}
