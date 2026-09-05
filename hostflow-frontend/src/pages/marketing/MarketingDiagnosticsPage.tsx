/**
 * Marketing Source Diagnostics — recent Acquisition submissions + case detail.
 * PR2: list filters (source / flight / failed-only).
 * PR7: mapping drift filter + list badges + alert strip.
 * PR8: Replay CTA → existing Leads process façade (not a Diagnostics writer).
 * PR9: windowed drift-summary banner + deep-link to drift_only list.
 * SoT: Lead + Acquisition Activity. Sibling of Sources, not a tab.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { processLead } from '../../api/client'
import {
  exportDiagnosticsCase,
  getDiagnosticsCase,
  getDiagnosticsDriftSummary,
  listDiagnosticsSubmissions,
  type DiagnosticsCase,
  type DiagnosticsDriftSummary,
  type DiagnosticsSubmission,
} from '../../api/marketingDiagnostics'
import {
  mappingAssessmentCopy,
  mappingContractTone,
  mappingWorkspaceCta,
} from '../../api/marketingSources'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'
import { MarketingWorkspaceNav } from './MarketingWorkspaceNav'

function JsonBlock({ title, value, testId }: { title: string; value: unknown; testId: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50" data-testid={testId}>
      <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700">
        {title}
      </div>
      <pre className="max-h-64 overflow-auto p-3 text-[11px] leading-relaxed text-slate-800">
        {JSON.stringify(value ?? {}, null, 2)}
      </pre>
    </div>
  )
}

function CaseDetail({
  leadId,
  onBack,
}: {
  leadId: string
  onBack: () => void
}) {
  const { t } = useI18n()
  const [row, setRow] = useState<DiagnosticsCase | null>(null)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [exportError, setExportError] = useState<FriendlyErrorInfo | null>(null)
  const [replayError, setReplayError] = useState<FriendlyErrorInfo | null>(null)
  const [replaying, setReplaying] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRow(await getDiagnosticsCase(leadId))
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.diagnostics.errors.load_case'),
          t,
        ),
      )
      setRow(null)
    } finally {
      setLoading(false)
    }
  }, [leadId, t])

  useEffect(() => {
    void load()
  }, [load])

  if (loading) {
    return <p className="text-sm text-slate-500">…</p>
  }
  if (error) {
    return <ErrorRecoveryBanner error={error} onRetry={() => void load()} />
  }
  if (!row) return null

  const onExport = async () => {
    setExportError(null)
    try {
      const blob = await exportDiagnosticsCase(leadId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `diagnostics-case-${leadId}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: unknown) {
      setExportError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.diagnostics.errors.export'),
          t,
        ),
      )
    }
  }

  const onReplay = async () => {
    setReplayError(null)
    setReplaying(true)
    try {
      // Leads process façade — Diagnostics stays read-compose only (PR8 boundary).
      await processLead(leadId)
      await load()
    } catch (err: unknown) {
      setReplayError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.diagnostics.errors.replay'),
          t,
        ),
      )
    } finally {
      setReplaying(false)
    }
  }

  return (
    <div className="space-y-4" data-testid="marketing-diagnostics-case">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button
            type="button"
            className="text-xs text-blue-700 hover:underline"
            onClick={onBack}
            data-testid="marketing-diagnostics-back"
          >
            {t('app.marketing.diagnostics.back_list')}
          </button>
          <h2 className="mt-2 text-lg font-semibold text-slate-900">
            {row.full_name || row.email || row.phone || row.lead_id}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {row.status_label}
            {row.source ? ` · ${row.source}` : ''}
            {row.created_at ? ` · ${formatDateTime(row.created_at)}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => void onExport()}
            data-testid="marketing-diagnostics-export"
          >
            {t('app.marketing.diagnostics.export_json')}
          </button>
          <button
            type="button"
            className="btn-primary btn-sm"
            disabled={replaying}
            onClick={() => void onReplay()}
            data-testid="marketing-diagnostics-replay"
            title={t('app.marketing.diagnostics.replay_hint')}
          >
            {replaying
              ? t('app.marketing.diagnostics.replaying')
              : t('app.marketing.diagnostics.replay')}
          </button>
          <Link
            className="btn-secondary btn-sm"
            to={`${CRM_APP_PATHS.leads}/${encodeURIComponent(row.lead_id)}`}
            data-testid="marketing-diagnostics-open-lead"
          >
            {t('app.marketing.diagnostics.open_lead')}
          </Link>
        </div>
      </div>

      {exportError ? (
        <ErrorRecoveryBanner error={exportError} onRetry={() => void onExport()} />
      ) : null}
      {replayError ? (
        <ErrorRecoveryBanner error={replayError} onRetry={() => void onReplay()} />
      ) : null}

      {row.lead_error ? (
        <div
          className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900"
          role="alert"
        >
          {row.lead_error}
        </div>
      ) : null}

      {row.duplicate?.active ? (
        <section
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3"
          data-testid="marketing-diagnostics-duplicate"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-amber-950">{t('app.marketing.diagnostics.duplicate.title')}</h3>
              <p className="mt-1 text-xs text-amber-900/80">
                {t('app.marketing.diagnostics.duplicate.body')}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                className="btn-secondary btn-sm"
                to={`${CRM_APP_PATHS.leads}/${encodeURIComponent(row.lead_id)}`}
                data-testid="marketing-diagnostics-duplicate-open-lead"
              >
                {t('app.marketing.diagnostics.duplicate.resolve')}
              </Link>
              {row.duplicate.suggested_candidate_id || row.duplicate.attach_candidate_id ? (
                <Link
                  className="btn-secondary btn-sm"
                  to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(
                    row.duplicate.suggested_candidate_id || row.duplicate.attach_candidate_id || '',
                  )}`}
                  data-testid="marketing-diagnostics-duplicate-open-candidate"
                >
                  {t('app.marketing.diagnostics.duplicate.open_candidate')}
                </Link>
              ) : null}
            </div>
          </div>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
            <div>
              <dt className="text-amber-900/70">{t('app.marketing.diagnostics.duplicate.lead_status')}</dt>
              <dd className="font-medium text-amber-950" data-testid="marketing-diagnostics-duplicate-status">
                {row.duplicate.lead_status || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-amber-900/70">{t('app.marketing.diagnostics.duplicate.disposition')}</dt>
              <dd className="font-medium text-amber-950">{row.duplicate.disposition || '—'}</dd>
            </div>
            <div>
              <dt className="text-amber-900/70">{t('app.marketing.diagnostics.duplicate.match_level')}</dt>
              <dd className="font-medium text-amber-950" data-testid="marketing-diagnostics-duplicate-level">
                {row.duplicate.match_level || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-amber-900/70">{t('app.marketing.diagnostics.duplicate.error_code')}</dt>
              <dd className="font-mono text-amber-950">{row.duplicate.error_code || '—'}</dd>
            </div>
            <div>
              <dt className="text-amber-900/70">{t('app.marketing.diagnostics.duplicate.needs_review')}</dt>
              <dd className="font-medium text-amber-950">
                {row.duplicate.needs_duplicate_review ? t('common.yes') : t('common.no')}
              </dd>
            </div>
            <div>
              <dt className="text-amber-900/70">{t('app.marketing.diagnostics.duplicate.suggested')}</dt>
              <dd className="truncate font-mono text-amber-950">
                {row.duplicate.suggested_candidate_id ||
                  row.duplicate.attach_candidate_id ||
                  '—'}
              </dd>
            </div>
          </dl>
          {row.duplicate.reasons.length ? (
            <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-amber-950" data-testid="marketing-diagnostics-duplicate-reasons">
              {row.duplicate.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : null}
          {row.duplicate.hr_blockers.length ? (
            <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-rose-900" data-testid="marketing-diagnostics-duplicate-hr">
              {row.duplicate.hr_blockers.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {row.mapping?.active || row.mapping?.profile_missing || row.mapping?.source_id ? (
        <section
          className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"
          data-testid="marketing-diagnostics-mapping"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">{t('app.marketing.diagnostics.mapping.title')}</h3>
              <p className="mt-1 text-xs text-slate-600">
                {t('app.marketing.diagnostics.mapping.body')}
              </p>
            </div>
            {row.mapping.mapping_path ? (
              <Link
                className="btn-secondary btn-sm"
                to={row.mapping.mapping_path}
                data-testid="marketing-diagnostics-open-mapping"
              >
                {mappingWorkspaceCta(row.mapping)}
              </Link>
            ) : null}
          </div>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
            <div>
              <dt className="text-slate-500">{t('app.marketing.diagnostics.mapping.source')}</dt>
              <dd className="font-medium text-slate-900" data-testid="marketing-diagnostics-mapping-name">
                {row.mapping.display_name || row.mapping.source_id || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">{t('app.marketing.diagnostics.mapping.health')}</dt>
              <dd
                className={`font-medium ${mappingContractTone(row.mapping.contract_health || row.mapping.mapping_health)}`}
                data-testid="marketing-diagnostics-mapping-health"
              >
                {row.mapping.profile_missing
                  ? t('app.marketing.diagnostics.mapping.profile_missing')
                  : mappingAssessmentCopy(row.mapping)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">{t('app.marketing.diagnostics.mapping.rules')}</dt>
              <dd className="font-medium text-slate-900">
                {row.mapping.mapping_rules_count}
                {row.mapping.rules_source ? ` · ${row.mapping.rules_source}` : ''}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">{t('app.marketing.diagnostics.mapping.profile_updated')}</dt>
              <dd className="font-mono text-slate-800">
                {row.mapping.profile_updated_at || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">{t('app.marketing.diagnostics.mapping.historical')}</dt>
              <dd className="font-medium text-slate-900" data-testid="marketing-diagnostics-mapping-historical">
                {row.mapping.historical_version_available
                  ? `${row.mapping.applied_rules_fingerprint || t('app.marketing.diagnostics.mapping.stamped')}${
                      row.mapping.applied_rules_count != null
                        ? ` · ${t('app.marketing.diagnostics.mapping.rules_count', { values: { count: row.mapping.applied_rules_count } })}`
                        : ''
                    }`
                  : t('app.marketing.diagnostics.mapping.not_stamped')}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">{t('app.marketing.diagnostics.mapping.drift')}</dt>
              <dd
                className={`font-medium ${row.mapping.drift ? 'text-rose-700' : 'text-slate-900'}`}
                data-testid="marketing-diagnostics-mapping-drift"
              >
                {row.mapping.historical_version_available
                  ? row.mapping.drift
                    ? t('app.marketing.diagnostics.mapping.drift_yes')
                    : t('common.no')
                  : '—'}
              </dd>
            </div>
          </dl>
        </section>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">{t('app.marketing.diagnostics.case.routing')}</div>
          <div className="font-medium text-slate-900">{row.routing_status || '—'}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">{t('app.marketing.diagnostics.case.route_intent')}</div>
          <div className="font-medium text-slate-900">{row.route_intent || '—'}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">{t('app.marketing.diagnostics.case.campaign')}</div>
          <div className="truncate font-mono text-xs text-slate-800">{row.campaign_id || '—'}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">{t('app.marketing.diagnostics.case.flight')}</div>
          <div className="truncate font-mono text-xs text-slate-800">{row.flight_id || '—'}</div>
        </div>
      </div>

      <section>
        <h3 className="text-sm font-semibold text-slate-900">{t('app.marketing.diagnostics.timeline_title')}</h3>
        {row.timeline.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500" data-testid="marketing-diagnostics-timeline-empty">
            {t('app.marketing.diagnostics.timeline_empty')}
          </p>
        ) : (
          <ol className="mt-2 space-y-2" data-testid="marketing-diagnostics-timeline">
            {row.timeline.map((ev) => (
              <li
                key={ev.id}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs"
              >
                <div className="font-semibold text-slate-900">{ev.event_type}</div>
                <div className="mt-0.5 text-slate-500">{formatDateTime(ev.occurred_at)}</div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <div className="grid gap-3 lg:grid-cols-2">
        <JsonBlock title={t('app.marketing.diagnostics.json.routing')} value={row.routing} testId="marketing-diagnostics-routing" />
        <JsonBlock title={t('app.marketing.diagnostics.json.decision')} value={row.decision} testId="marketing-diagnostics-decision" />
        <JsonBlock title={t('app.marketing.diagnostics.json.normalized')} value={row.normalized} testId="marketing-diagnostics-normalized" />
        <JsonBlock title={t('app.marketing.diagnostics.json.payload')} value={row.payload} testId="marketing-diagnostics-payload" />
      </div>
    </div>
  )
}

export default function MarketingDiagnosticsPage() {
  const { t } = useI18n()
  const { leadId } = useParams<{ leadId?: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [items, setItems] = useState<DiagnosticsSubmission[]>([])
  const [driftAlertCount, setDriftAlertCount] = useState(0)
  const [driftSummary, setDriftSummary] = useState<DiagnosticsDriftSummary | null>(null)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const sourceFilter = (searchParams.get('source') || '').trim()
  const flightFilter = (searchParams.get('flight_id') || '').trim()
  const failedOnly = searchParams.get('failed_only') === '1'
  const driftOnly = searchParams.get('drift_only') === '1'

  const loadSummary = useCallback(async () => {
    try {
      const summary = await getDiagnosticsDriftSummary()
      setDriftSummary(summary)
    } catch {
      setDriftSummary(null)
    }
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listDiagnosticsSubmissions({
        limit: 50,
        ...(sourceFilter ? { source: sourceFilter } : {}),
        ...(flightFilter ? { flight_id: flightFilter } : {}),
        ...(failedOnly ? { failed_only: true } : {}),
        ...(driftOnly ? { drift_only: true } : {}),
      })
      setItems(res.items || [])
      setDriftAlertCount(Number(res.drift_alert_count || 0))
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.diagnostics.errors.load_list'),
          t,
        ),
      )
      setItems([])
      setDriftAlertCount(0)
    } finally {
      setLoading(false)
    }
  }, [driftOnly, failedOnly, flightFilter, sourceFilter, t])

  useEffect(() => {
    if (!leadId) {
      void load()
      void loadSummary()
    }
  }, [leadId, load, loadSummary])

  const patchFilters = (patch: {
    source?: string
    flight_id?: string
    failed_only?: boolean
    drift_only?: boolean
  }) => {
    const next = new URLSearchParams(searchParams)
    if (patch.source !== undefined) {
      const v = patch.source.trim()
      if (v) next.set('source', v)
      else next.delete('source')
    }
    if (patch.flight_id !== undefined) {
      const v = patch.flight_id.trim()
      if (v) next.set('flight_id', v)
      else next.delete('flight_id')
    }
    if (patch.failed_only !== undefined) {
      if (patch.failed_only) next.set('failed_only', '1')
      else next.delete('failed_only')
    }
    if (patch.drift_only !== undefined) {
      if (patch.drift_only) next.set('drift_only', '1')
      else next.delete('drift_only')
    }
    setSearchParams(next, { replace: true })
  }

  return (
    <PageShell data-testid="marketing-diagnostics-page">
      <PageShellHeader>
        <PageHeader
          kind="browse"
        />
        <MarketingWorkspaceNav />
      </PageShellHeader>

      {!leadId && driftSummary && driftSummary.drift_count > 0 ? (
        <div
          className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          data-testid="marketing-diagnostics-drift-summary"
        >
          <span>
            {t('app.marketing.diagnostics.drift_summary', {
              values: {
                hours: driftSummary.window_hours,
                count: driftSummary.drift_count,
                scanned: driftSummary.scanned,
              },
            })}
            {driftSummary.scan_capped
              ? t('app.marketing.diagnostics.drift_summary_capped')
              : ''}
          </span>
          {!driftOnly ? (
            <button
              type="button"
              className="btn-secondary btn-sm"
              data-testid="marketing-diagnostics-drift-summary-link"
              onClick={() => patchFilters({ drift_only: true })}
            >
              {t('app.marketing.diagnostics.show_drift')}
            </button>
          ) : null}
        </div>
      ) : null}

      <div className="mt-4">
        {leadId ? (
          <CaseDetail
            leadId={leadId}
            onBack={() =>
              navigate({
                pathname: CRM_APP_PATHS.marketingDiagnostics,
                search: searchParams.toString() ? `?${searchParams.toString()}` : '',
              })
            }
          />
        ) : (
          <>
            <form
              key={`${sourceFilter}|${flightFilter}|${failedOnly ? '1' : '0'}|${driftOnly ? '1' : '0'}`}
              className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3"
              data-testid="marketing-diagnostics-filters"
              onSubmit={(e) => {
                e.preventDefault()
                const fd = new FormData(e.currentTarget)
                patchFilters({
                  source: String(fd.get('source') || ''),
                  flight_id: String(fd.get('flight_id') || ''),
                  failed_only: fd.get('failed_only') === 'on',
                  drift_only: fd.get('drift_only') === 'on',
                })
              }}
            >
              <label className="min-w-[8rem] flex-1 text-xs text-slate-600">
                {t('app.marketing.diagnostics.filter_source')}
                <input
                  name="source"
                  defaultValue={sourceFilter}
                  placeholder="meta"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  data-testid="marketing-diagnostics-filter-source"
                />
              </label>
              <label className="min-w-[12rem] flex-[2] text-xs text-slate-600">
                {t('app.marketing.diagnostics.filter_flight')}
                <input
                  name="flight_id"
                  defaultValue={flightFilter}
                  placeholder="uuid"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm text-slate-900"
                  data-testid="marketing-diagnostics-filter-flight"
                />
              </label>
              <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  name="failed_only"
                  defaultChecked={failedOnly}
                  data-testid="marketing-diagnostics-filter-failed"
                />
                {t('app.marketing.diagnostics.failed_only')}
              </label>
              <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  name="drift_only"
                  defaultChecked={driftOnly}
                  data-testid="marketing-diagnostics-filter-drift"
                />
                {t('app.marketing.diagnostics.drift_only')}
              </label>
              <button type="submit" className="btn-secondary btn-sm" data-testid="marketing-diagnostics-filter-apply">
                {t('app.marketing.diagnostics.apply')}
              </button>
            </form>

            {!driftOnly && driftAlertCount > 0 ? (
              <div
                className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
                data-testid="marketing-diagnostics-drift-alert"
              >
                <span>
                  {t('app.marketing.diagnostics.drift_alert', {
                    values: { count: driftAlertCount },
                  })}
                </span>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  data-testid="marketing-diagnostics-drift-alert-filter"
                  onClick={() => patchFilters({ drift_only: true })}
                >
                  {t('app.marketing.diagnostics.show_drift')}
                </button>
              </div>
            ) : null}

            {error ? <ErrorRecoveryBanner error={error} onRetry={() => void load()} /> : null}
            {loading ? (
              <p className="text-sm text-slate-500">…</p>
            ) : items.length === 0 ? (
              <p className="text-sm text-slate-500" data-testid="marketing-diagnostics-empty">
                {t('app.marketing.diagnostics.empty')}
              </p>
            ) : (
              <ul className="space-y-2" data-testid="marketing-diagnostics-list">
                {items.map((row) => (
                  <li key={row.lead_id}>
                    <button
                      type="button"
                      className="flex w-full flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left hover:border-slate-300"
                      onClick={() =>
                        navigate({
                          pathname: `${CRM_APP_PATHS.marketingDiagnostics}/${encodeURIComponent(row.lead_id)}`,
                          search: searchParams.toString() ? `?${searchParams.toString()}` : '',
                        })
                      }
                      data-testid={`marketing-diagnostics-row-${row.lead_id}`}
                    >
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="truncate font-medium text-slate-900">
                            {row.full_name || row.email || row.phone || row.lead_id}
                          </span>
                          {row.mapping_drift ? (
                            <span
                              className="inline-flex rounded bg-rose-100 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-rose-800"
                              data-testid="marketing-diagnostics-drift-badge"
                            >
                              {t('app.marketing.diagnostics.drift_badge')}
                            </span>
                          ) : null}
                        </div>
                        <div className="mt-0.5 text-xs text-slate-500">
                          {row.status_label}
                          {row.source ? ` · ${row.source}` : ''}
                        </div>
                      </div>
                      <div className="text-xs text-slate-500">
                        {row.created_at ? formatDateTime(row.created_at) : ''}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </PageShell>
  )
}
