/**
 * Marketing Sources foundation (Acquisition UI Cutover C-3).
 * Read-only inventory: connection, canonical mapping assessment, last lead/error, CTA deep-links.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  getDiagnosticsDriftSummary,
  type DiagnosticsDriftSummary,
} from '../../api/marketingDiagnostics'
import {
  listMarketingSources,
  mappingAssessmentCopy,
  mappingContractTone,
  type MarketingSourceSummary,
} from '../../api/marketingSources'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { formatDateTime } from '../../utils/dateFormat'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

function connectionLabel(status: string, t: (k: string, o?: object) => string): string {
  switch (status) {
    case 'connected':
      return t('app.marketing.sources.connection.connected')
    case 'attention':
      return t('app.marketing.sources.connection.attention')
    case 'disconnected':
      return t('app.marketing.sources.connection.disconnected')
    default:
      return status
  }
}

function connectionTone(status: string): string {
  if (status === 'connected') return 'bg-emerald-50 text-emerald-800'
  if (status === 'attention') return 'bg-amber-50 text-amber-900'
  return 'bg-rose-50 text-rose-800'
}

export default function MarketingSourcesPage() {
  const { t, locale } = useI18n()
  const [items, setItems] = useState<MarketingSourceSummary[]>([])
  const [driftSummary, setDriftSummary] = useState<DiagnosticsDriftSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await listMarketingSources()
      setItems(rows)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.sources.errors.load'),
          t,
        ),
      )
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [t])

  const loadDriftSummary = useCallback(async () => {
    try {
      setDriftSummary(await getDiagnosticsDriftSummary())
    } catch {
      setDriftSummary(null)
    }
  }, [])

  useEffect(() => {
    void load()
    void loadDriftSummary()
  }, [load, loadDriftSummary])

  return (
    <PageShell data-testid="marketing-sources-page">
      <PageShellHeader>
        <PageHeader
          kind="browse"
          secondaryActions={
            <Link
              to={CRM_APP_PATHS.settingsIntegrationsMeta}
              className="btn-secondary btn-sm"
              data-testid="marketing-sources-open-integrations"
            >
              {t('app.marketing.sources.actions.integrations')}
            </Link>
          }
        />
      </PageShellHeader>

      {driftSummary && driftSummary.drift_count > 0 ? (
        <div
          className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          data-testid="marketing-sources-drift-summary"
        >
          <span>
            {t('app.marketing.sources.drift_summary', {
              values: {
                count: driftSummary.drift_count,
                hours: driftSummary.window_hours,
              },
            })}
          </span>
          <Link
            to={`${CRM_APP_PATHS.marketingDiagnostics}?drift_only=1`}
            className="btn-secondary btn-sm"
            data-testid="marketing-sources-drift-summary-link"
          >
            {t('app.marketing.sources.actions.open_drift')}
          </Link>
        </div>
      ) : null}

      {error ? (
        <div data-testid="marketing-sources-error">
          <ErrorRecoveryBanner info={error} onRetry={() => void load()} />
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500" data-testid="marketing-sources-loading">
          {t('common.loading')}
        </p>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <div
          className="rounded-lg border border-dashed border-slate-200 bg-white px-6 py-10 text-center"
          data-testid="marketing-sources-empty"
        >
          <p className="text-base font-medium text-slate-900">
            {t('app.marketing.sources.empty_title')}
          </p>
          <p className="mt-2 text-sm text-slate-600">
            {t('app.marketing.sources.empty_body')}
          </p>
          <Link
            to={CRM_APP_PATHS.settingsIntegrationsMeta}
            className="btn-primary btn-sm mt-4 inline-flex"
            data-testid="marketing-sources-empty-cta"
          >
            {t('app.marketing.sources.actions.connect')}
          </Link>
        </div>
      ) : null}

      {!loading && items.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full text-left text-sm" data-testid="marketing-sources-table">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.source')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.provider')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.page')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.provider_form')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.destination')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.connection')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.mapping_health')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.last_lead')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.waiting')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.routing_issue')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.last_error')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.campaigns_flights')}
                </th>
                <th className="px-4 py-3 font-medium">
                  {t('app.marketing.sources.columns.actions')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((row) => (
                <tr key={row.source_id} data-testid={`marketing-source-row-${row.source_id}`}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{row.display_name}</div>
                    {row.code ? (
                      <div className="mt-0.5 font-mono text-xs text-slate-500">{row.code}</div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-slate-700">{row.provider}</td>
                  <td
                    className="px-4 py-3 text-slate-700"
                    data-testid={`marketing-source-page-${row.source_id}`}
                  >
                    {row.page_name || row.page_id || t('app.marketing.sources.none')}
                  </td>
                  <td
                    className="px-4 py-3 text-slate-700"
                    data-testid={`marketing-source-provider-form-${row.source_id}`}
                  >
                    {row.provider_form || t('app.marketing.sources.none')}
                  </td>
                  <td
                    className="px-4 py-3 text-slate-700"
                    data-testid={`marketing-source-destination-${row.source_id}`}
                  >
                    {row.destination_label ||
                      row.destination ||
                      t('app.marketing.sources.none')}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${connectionTone(row.connection_status)}`}
                      data-testid={`marketing-source-connection-${row.source_id}`}
                    >
                      {connectionLabel(row.connection_status, t)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${mappingContractTone(row.contract_health || row.mapping_health)}`}
                      data-testid={`marketing-source-health-${row.source_id}`}
                    >
                      {mappingAssessmentCopy(row)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {row.last_submission_at
                      ? formatDateTime(row.last_submission_at, locale)
                      : t('app.marketing.sources.none')}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {(row.waiting_submissions ?? 0) > 0 ? (
                      <span
                        className="inline-flex rounded bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-900"
                        data-testid={`marketing-source-waiting-${row.source_id}`}
                      >
                        {row.waiting_submissions}
                      </span>
                    ) : (
                      t('app.marketing.sources.none')
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {row.routing_issue_code ? (
                      <div data-testid={`marketing-source-routing-issue-${row.source_id}`}>
                        <div className="text-sm text-rose-800">
                          {t('app.marketing.sources.routing_issue.missing_campaign_flight')}
                        </div>
                        {row.last_problematic_ad_id ? (
                          <div className="mt-0.5 font-mono text-xs text-slate-500">
                            Ad ID: {row.last_problematic_ad_id}
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      t('app.marketing.sources.none')
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {row.last_error_at ? (
                      <div>
                        <div>{formatDateTime(row.last_error_at, locale)}</div>
                        {row.last_error_code ? (
                          <div className="font-mono text-xs text-rose-700">{row.last_error_code}</div>
                        ) : null}
                      </div>
                    ) : (
                      t('app.marketing.sources.none')
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-700">
                    {row.campaign_count} / {row.flight_count}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {row.setup_campaign_flight_path ? (
                        <Link
                          to={row.setup_campaign_flight_path}
                          className="text-sm font-medium text-brand-700 hover:underline"
                          data-testid={`marketing-source-setup-campaign-flight-${row.source_id}`}
                        >
                          {t('app.marketing.sources.actions.setup_campaign_flight')}
                        </Link>
                      ) : null}
                      <Link
                        to={row.mapping_path}
                        className="text-sm font-medium text-brand-700 hover:underline"
                        data-testid={`marketing-source-mapping-${row.source_id}`}
                      >
                        {t('app.marketing.sources.actions.mapping')}
                      </Link>
                      <Link
                        to={row.test_lead_path}
                        className="text-sm font-medium text-brand-700 hover:underline"
                        data-testid={`marketing-source-test-lead-${row.source_id}`}
                      >
                        {t('app.marketing.sources.actions.test_lead')}
                      </Link>
                      <Link
                        to={row.settings_path}
                        className="text-sm font-medium text-slate-600 hover:underline"
                        data-testid={`marketing-source-settings-${row.source_id}`}
                      >
                        {t('app.marketing.sources.actions.connection')}
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </PageShell>
  )
}
