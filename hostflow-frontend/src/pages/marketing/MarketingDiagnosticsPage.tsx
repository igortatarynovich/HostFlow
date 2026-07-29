/**
 * Marketing Source Diagnostics (PR1) — recent Acquisition submissions + case detail.
 * SoT: Lead + Acquisition Activity. Sibling of Sources, not a tab.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
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
        <Link
          className="btn-secondary btn-sm"
          to={`${CRM_APP_PATHS.leads}/${encodeURIComponent(row.lead_id)}`}
          data-testid="marketing-diagnostics-open-lead"
        >
          Открыть Lead в CRM
        </Link>
      </div>

      {row.lead_error ? (
        <div
          className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900"
          role="alert"
        >
          {row.lead_error}
        </div>
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
  const [items, setItems] = useState<DiagnosticsSubmission[]>([])
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listDiagnosticsSubmissions({ limit: 50 })
      setItems(res.items || [])
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
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    if (!leadId) void load()
  }, [leadId, load])

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
            onBack={() => navigate(CRM_APP_PATHS.marketingDiagnostics)}
          />
        ) : (
          <>
            {error ? <ErrorRecoveryBanner error={error} onRetry={() => void load()} /> : null}
            {loading ? (
              <p className="text-sm text-slate-500">…</p>
            ) : items.length === 0 ? (
              <p className="text-sm text-slate-500" data-testid="marketing-diagnostics-empty">
                Пока нет Acquisition-заявок со штампом маршрута.
              </p>
            ) : (
              <ul className="space-y-2" data-testid="marketing-diagnostics-list">
                {items.map((row) => (
                  <li key={row.lead_id}>
                    <button
                      type="button"
                      className="flex w-full flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left hover:border-slate-300"
                      onClick={() =>
                        navigate(
                          `${CRM_APP_PATHS.marketingDiagnostics}/${encodeURIComponent(row.lead_id)}`,
                        )
                      }
                      data-testid={`marketing-diagnostics-row-${row.lead_id}`}
                    >
                      <div className="min-w-0">
                        <div className="truncate font-medium text-slate-900">
                          {row.full_name || row.email || row.phone || row.lead_id}
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
