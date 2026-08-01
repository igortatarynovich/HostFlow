/**
 * Marketing Source Diagnostics — recent Acquisition submissions + case detail.
 * PR2: list filters (source / flight / failed-only).
 * PR7: mapping drift filter + list badges + alert strip.
 * SoT: Lead + Acquisition Activity. Sibling of Sources, not a tab.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  exportDiagnosticsCase,
  getDiagnosticsCase,
  listDiagnosticsSubmissions,
  type DiagnosticsCase,
  type DiagnosticsSubmission,
} from '../../api/marketingDiagnostics'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

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
          t('app.marketing.diagnostics.errors.load_case', {
            defaultValue: 'Не удалось загрузить кейс',
          }),
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
          t('app.marketing.diagnostics.errors.export', {
            defaultValue: 'Не удалось скачать export',
          }),
          t,
        ),
      )
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
            ← К списку
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
            Export JSON
          </button>
          <Link
            className="btn-secondary btn-sm"
            to={`${CRM_APP_PATHS.leads}/${encodeURIComponent(row.lead_id)}`}
            data-testid="marketing-diagnostics-open-lead"
          >
            Открыть Lead в CRM
          </Link>
        </div>
      </div>

      {exportError ? (
        <ErrorRecoveryBanner error={exportError} onRetry={() => void onExport()} />
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
              <h3 className="text-sm font-semibold text-amber-950">Duplicate decision</h3>
              <p className="mt-1 text-xs text-amber-900/80">
                Read-only compose from decision_result_v1 + duplicate_match_v1. Resolve in CRM Lead.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                className="btn-secondary btn-sm"
                to={`${CRM_APP_PATHS.leads}/${encodeURIComponent(row.lead_id)}`}
                data-testid="marketing-diagnostics-duplicate-open-lead"
              >
                Resolve in Lead
              </Link>
              {row.duplicate.suggested_candidate_id || row.duplicate.attach_candidate_id ? (
                <Link
                  className="btn-secondary btn-sm"
                  to={`${CRM_APP_PATHS.candidates}/${encodeURIComponent(
                    row.duplicate.suggested_candidate_id || row.duplicate.attach_candidate_id || '',
                  )}`}
                  data-testid="marketing-diagnostics-duplicate-open-candidate"
                >
                  Open candidate
                </Link>
              ) : null}
            </div>
          </div>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
            <div>
              <dt className="text-amber-900/70">Lead status</dt>
              <dd className="font-medium text-amber-950" data-testid="marketing-diagnostics-duplicate-status">
                {row.duplicate.lead_status || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-amber-900/70">Disposition</dt>
              <dd className="font-medium text-amber-950">{row.duplicate.disposition || '—'}</dd>
            </div>
            <div>
              <dt className="text-amber-900/70">Match level</dt>
              <dd className="font-medium text-amber-950" data-testid="marketing-diagnostics-duplicate-level">
                {row.duplicate.match_level || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-amber-900/70">Error code</dt>
              <dd className="font-mono text-amber-950">{row.duplicate.error_code || '—'}</dd>
            </div>
            <div>
              <dt className="text-amber-900/70">Needs review</dt>
              <dd className="font-medium text-amber-950">
                {row.duplicate.needs_duplicate_review ? 'yes' : 'no'}
              </dd>
            </div>
            <div>
              <dt className="text-amber-900/70">Suggested candidate</dt>
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
              <h3 className="text-sm font-semibold text-slate-900">Mapping / Mapping Health</h3>
              <p className="mt-1 text-xs text-slate-600">
                Current Source mapping (not a historical ingest stamp). Open Mapping workspace to review rules.
              </p>
            </div>
            {row.mapping.mapping_path ? (
              <Link
                className="btn-secondary btn-sm"
                to={row.mapping.mapping_path}
                data-testid="marketing-diagnostics-open-mapping"
              >
                Open Mapping
              </Link>
            ) : null}
          </div>
          <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
            <div>
              <dt className="text-slate-500">Source</dt>
              <dd className="font-medium text-slate-900" data-testid="marketing-diagnostics-mapping-name">
                {row.mapping.display_name || row.mapping.source_id || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Mapping Health</dt>
              <dd className="font-medium text-slate-900" data-testid="marketing-diagnostics-mapping-health">
                {row.mapping.profile_missing
                  ? 'profile missing'
                  : row.mapping.mapping_health || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Rules</dt>
              <dd className="font-medium text-slate-900">
                {row.mapping.mapping_rules_count}
                {row.mapping.rules_source ? ` · ${row.mapping.rules_source}` : ''}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Profile updated</dt>
              <dd className="font-mono text-slate-800">
                {row.mapping.profile_updated_at || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Historical version</dt>
              <dd className="font-medium text-slate-900" data-testid="marketing-diagnostics-mapping-historical">
                {row.mapping.historical_version_available
                  ? `${row.mapping.applied_rules_fingerprint || 'stamped'}${
                      row.mapping.applied_rules_count != null
                        ? ` · ${row.mapping.applied_rules_count} rules`
                        : ''
                    }`
                  : 'not stamped'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Drift</dt>
              <dd
                className={`font-medium ${row.mapping.drift ? 'text-rose-700' : 'text-slate-900'}`}
                data-testid="marketing-diagnostics-mapping-drift"
              >
                {row.mapping.historical_version_available
                  ? row.mapping.drift
                    ? 'yes — current rules differ from ingest'
                    : 'no'
                  : '—'}
              </dd>
            </div>
          </dl>
        </section>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">Routing</div>
          <div className="font-medium text-slate-900">{row.routing_status || '—'}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">Route intent</div>
          <div className="font-medium text-slate-900">{row.route_intent || '—'}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">Campaign</div>
          <div className="truncate font-mono text-xs text-slate-800">{row.campaign_id || '—'}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-3 py-2">
          <div className="text-xs text-slate-500">Flight</div>
          <div className="truncate font-mono text-xs text-slate-800">{row.flight_id || '—'}</div>
        </div>
      </div>

      <section>
        <h3 className="text-sm font-semibold text-slate-900">Timeline (Acquisition Activity)</h3>
        {row.timeline.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500" data-testid="marketing-diagnostics-timeline-empty">
            Нет событий по submission_id (или submission не уникален).
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
        <JsonBlock title="Routing stamp" value={row.routing} testId="marketing-diagnostics-routing" />
        <JsonBlock title="Decision" value={row.decision} testId="marketing-diagnostics-decision" />
        <JsonBlock title="Normalized" value={row.normalized} testId="marketing-diagnostics-normalized" />
        <JsonBlock title="Raw payload" value={row.payload} testId="marketing-diagnostics-payload" />
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
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const sourceFilter = (searchParams.get('source') || '').trim()
  const flightFilter = (searchParams.get('flight_id') || '').trim()
  const failedOnly = searchParams.get('failed_only') === '1'
  const driftOnly = searchParams.get('drift_only') === '1'

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
          t('app.marketing.diagnostics.errors.load_list', {
            defaultValue: 'Не удалось загрузить submissions',
          }),
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
    if (!leadId) void load()
  }, [leadId, load])

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
          title={t('app.nav.items.marketing_diagnostics', { defaultValue: 'Diagnostics' })}
          subtitle={t('app.marketing.diagnostics.subtitle', {
            defaultValue:
              'Операции по поступившим заявкам: маршрут, timeline, payload. Sources — настройка.',
          })}
        />
      </PageShellHeader>

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
                Source
                <input
                  name="source"
                  defaultValue={sourceFilter}
                  placeholder="meta"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  data-testid="marketing-diagnostics-filter-source"
                />
              </label>
              <label className="min-w-[12rem] flex-[2] text-xs text-slate-600">
                Flight ID
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
                Только failed / unresolved
              </label>
              <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  name="drift_only"
                  defaultChecked={driftOnly}
                  data-testid="marketing-diagnostics-filter-drift"
                />
                Только mapping drift
              </label>
              <button type="submit" className="btn-secondary btn-sm" data-testid="marketing-diagnostics-filter-apply">
                Применить
              </button>
            </form>

            {!driftOnly && driftAlertCount > 0 ? (
              <div
                className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
                data-testid="marketing-diagnostics-drift-alert"
              >
                <span>
                  {t('app.marketing.diagnostics.drift_alert', {
                    defaultValue:
                      'На этой странице {{count}} заявк(и) с Mapping drift — правила Source изменились после ingest.',
                    count: driftAlertCount,
                  })}
                </span>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  data-testid="marketing-diagnostics-drift-alert-filter"
                  onClick={() => patchFilters({ drift_only: true })}
                >
                  Показать drift
                </button>
              </div>
            ) : null}

            {error ? <ErrorRecoveryBanner error={error} onRetry={() => void load()} /> : null}
            {loading ? (
              <p className="text-sm text-slate-500">…</p>
            ) : items.length === 0 ? (
              <p className="text-sm text-slate-500" data-testid="marketing-diagnostics-empty">
                Нет заявок по текущему фильтру.
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
                              drift
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
