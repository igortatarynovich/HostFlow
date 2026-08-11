/**
 * Marketing Source Mapping workspace (Acquisition UI Cutover C-5).
 * Persists IntakeSourceProfile.mapping_rules + dry-run routing preview.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CRM_APP_PATHS,
  marketingSourceTestLeadPath,
} from '../../app/crmAppPaths'
import {
  getMarketingSourceMapping,
  getMarketingSourceSample,
  listMarketingSources,
  postMarketingSourceRoutingPreview,
  putMarketingSourceMapping,
  type MarketingSourceMapping,
  type MarketingSourceMappingRule,
  type MarketingSourceRoutingPreview,
  type MarketingSourceSample,
  type MarketingSourceSummary,
} from '../../api/marketingSources'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

type DraftRule = {
  source: string
  target: string
  action: string
  sample_value_masked: string
}

function healthLabel(status: string, t: (k: string, o?: object) => string): string {
  switch (status) {
    case 'ready':
      return t('app.marketing.sources.health.ready', { defaultValue: 'Ready' })
    case 'needs_review':
      return t('app.marketing.sources.health.needs_review', { defaultValue: 'Needs review' })
    case 'broken':
      return t('app.marketing.sources.health.broken', { defaultValue: 'Broken' })
    default:
      return status
  }
}

function ruleToDraft(rule: MarketingSourceMappingRule, sampleMasked = ''): DraftRule {
  const action = String(rule.action || '').toLowerCase() === 'ignore' ? 'ignore' : 'map'
  return {
    source: String(rule.source || ''),
    target: String(rule.target || rule.qualified_field_code || ''),
    action,
    sample_value_masked: sampleMasked,
  }
}

function draftsFromMappingAndSample(
  mapping: MarketingSourceMapping,
  sample: MarketingSourceSample | null,
): DraftRule[] {
  const sampleBySource = new Map(
    (sample?.fields || []).map((f) => [f.source.toLowerCase(), f.sample_value_masked]),
  )
  const bySource = new Map<string, DraftRule>()
  for (const rule of mapping.mapping_rules || []) {
    const src = String(rule.source || '').trim()
    if (!src) continue
    bySource.set(
      src.toLowerCase(),
      ruleToDraft(rule, sampleBySource.get(src.toLowerCase()) || ''),
    )
  }
  for (const field of sample?.fields || []) {
    const key = field.source.toLowerCase()
    if (bySource.has(key)) continue
    bySource.set(key, {
      source: field.source,
      target: field.proposed_target || '',
      action: 'map',
      sample_value_masked: field.sample_value_masked,
    })
  }
  return Array.from(bySource.values()).sort((a, b) => a.source.localeCompare(b.source))
}

function draftsToRules(drafts: DraftRule[]): MarketingSourceMappingRule[] {
  return drafts
    .filter((d) => d.source.trim())
    .map((d) => {
      if (d.action === 'ignore') {
        return { source: d.source.trim(), action: 'ignore', format: 'string' }
      }
      return {
        source: d.source.trim(),
        target: d.target.trim() || undefined,
        format: 'string',
      }
    })
    .filter((r) => r.action === 'ignore' || Boolean(r.target))
}

export default function MarketingSourceMappingPage() {
  const { t } = useI18n()
  const { sourceId = '' } = useParams<{ sourceId: string }>()

  const [source, setSource] = useState<MarketingSourceSummary | null>(null)
  const [mapping, setMapping] = useState<MarketingSourceMapping | null>(null)
  const [sample, setSample] = useState<MarketingSourceSample | null>(null)
  const [drafts, setDrafts] = useState<DraftRule[]>([])
  const [routing, setRouting] = useState<MarketingSourceRoutingPreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!sourceId) return
    setLoading(true)
    setError(null)
    try {
      const [rows, mappingRow, sampleRow] = await Promise.all([
        listMarketingSources(),
        getMarketingSourceMapping(sourceId),
        getMarketingSourceSample(sourceId).catch(() => null),
      ])
      setSource(rows.find((row) => row.source_id === sourceId) ?? null)
      setMapping(mappingRow)
      setSample(sampleRow)
      setDrafts(draftsFromMappingAndSample(mappingRow, sampleRow))
      setRouting(null)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.mapping.errors.load', {
            defaultValue: 'Failed to load mapping for source',
          }),
          t,
        ),
      )
      setMapping(null)
    } finally {
      setLoading(false)
    }
  }, [sourceId, t])

  useEffect(() => {
    void load()
  }, [load])

  const title = useMemo(() => {
    const name = mapping?.display_name || source?.display_name
    return name
      ? t('app.marketing.mapping.title_named', {
          defaultValue: 'Mapping — {name}',
          values: { name },
        })
      : t('app.marketing.mapping.title', { defaultValue: 'Source mapping' })
  }, [mapping?.display_name, source?.display_name, t])

  async function runAction(fn: () => Promise<void>) {
    setBusy(true)
    setError(null)
    setActionMessage(null)
    try {
      await fn()
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.mapping.errors.action', {
            defaultValue: 'Failed to run action',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  function updateDraft(index: number, patch: Partial<DraftRule>) {
    setDrafts((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)))
  }

  return (
    <PageShell data-testid="marketing-source-mapping-page">
      <PageShellHeader>
        <PageHeader
          title={title}
          subtitle={t('app.marketing.mapping.subtitle', {
            defaultValue:
              'Confirm field placement and review dry-run routing — without creating a Candidate / Application.',
          })}
          actions={
            <div className="flex flex-wrap gap-2">
              <Link
                to={marketingSourceTestLeadPath(sourceId)}
                className="btn-secondary btn-sm"
                data-testid="marketing-mapping-to-test-lead"
              >
                {t('app.marketing.mapping.actions.test_lead', { defaultValue: 'Test lead' })}
              </Link>
              <Link
                to={CRM_APP_PATHS.marketingSources}
                className="btn-secondary btn-sm"
                data-testid="marketing-mapping-back-sources"
              >
                {t('app.marketing.mapping.actions.back', { defaultValue: '← Sources' })}
              </Link>
            </div>
          }
        />
      </PageShellHeader>

      {error ? (
        <div data-testid="marketing-mapping-error">
          <ErrorRecoveryBanner info={error} onRetry={() => void load()} />
        </div>
      ) : null}

      {actionMessage ? (
        <p
          className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
          data-testid="marketing-mapping-action-message"
        >
          {actionMessage}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500" data-testid="marketing-mapping-loading">
          {t('app.common.loading', { defaultValue: 'Loading…' })}
        </p>
      ) : mapping ? (
        <div className="space-y-6">
          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-mapping-context"
          >
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.mapping.fields.provider', { defaultValue: 'Provider' })}
                </dt>
                <dd data-testid="marketing-mapping-provider">{mapping.provider || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.mapping.fields.health', { defaultValue: 'Mapping Health' })}
                </dt>
                <dd data-testid="marketing-mapping-health">
                  {healthLabel(mapping.mapping_health, t)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.mapping.fields.destination', { defaultValue: 'Destination' })}
                </dt>
                <dd data-testid="marketing-mapping-destination">
                  {mapping.destination_label || mapping.destination || '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.mapping.fields.rules_source', { defaultValue: 'Rules source' })}
                </dt>
                <dd data-testid="marketing-mapping-rules-source">{mapping.rules_source}</dd>
              </div>
            </dl>
          </section>

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-mapping-rules"
          >
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.marketing.mapping.rules.title', { defaultValue: 'Field mapping' })}
              </h2>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={busy}
                data-testid="marketing-mapping-save"
                onClick={() =>
                  void runAction(async () => {
                    const saved = await putMarketingSourceMapping(sourceId, draftsToRules(drafts))
                    setMapping(saved)
                    setDrafts(draftsFromMappingAndSample(saved, sample))
                    setActionMessage(
                      t('app.marketing.mapping.saved', {
                        defaultValue: 'Mapping saved on IntakeSourceProfile.mapping_rules',
                      }),
                    )
                  })
                }
              >
                {t('app.marketing.mapping.actions.save', { defaultValue: 'Save mapping' })}
              </button>
            </div>

            {drafts.length === 0 ? (
              <p className="text-sm text-slate-500" data-testid="marketing-mapping-rules-empty">
                {t('app.marketing.mapping.rules.empty', {
                  defaultValue:
                    'No rules or sample fields. Get a sample on Test lead first.',
                })}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table
                  className="min-w-full divide-y divide-slate-200 text-sm"
                  data-testid="marketing-mapping-rules-table"
                >
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Provider field</th>
                      <th className="px-3 py-2">Sample</th>
                      <th className="px-3 py-2">HostFlow target</th>
                      <th className="px-3 py-2">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {drafts.map((row, index) => (
                      <tr key={row.source} data-testid={`marketing-mapping-row-${row.source}`}>
                        <td className="px-3 py-2 font-mono text-xs text-slate-800">{row.source}</td>
                        <td className="px-3 py-2 text-slate-600">
                          {row.sample_value_masked || '—'}
                        </td>
                        <td className="px-3 py-2">
                          <input
                            className="w-full rounded border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-50"
                            value={row.target}
                            disabled={row.action === 'ignore' || busy}
                            data-testid={`marketing-mapping-target-${row.source}`}
                            onChange={(e) => updateDraft(index, { target: e.target.value })}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <select
                            className="rounded border border-slate-300 px-2 py-1 text-sm"
                            value={row.action}
                            disabled={busy}
                            data-testid={`marketing-mapping-action-${row.source}`}
                            onChange={(e) => updateDraft(index, { action: e.target.value })}
                          >
                            <option value="map">Map</option>
                            <option value="ignore">Ignore</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-mapping-routing"
          >
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.marketing.mapping.routing.title', { defaultValue: 'Routing preview' })}
              </h2>
              <button
                type="button"
                className="btn-secondary btn-sm"
                disabled={busy}
                data-testid="marketing-mapping-routing-run"
                onClick={() =>
                  void runAction(async () => {
                    const preview = await postMarketingSourceRoutingPreview(sourceId)
                    setRouting(preview)
                  })
                }
              >
                {t('app.marketing.mapping.actions.preview_routing', {
                  defaultValue: 'Run routing preview',
                })}
              </button>
            </div>

            {routing ? (
              <div className="space-y-2 text-sm" data-testid="marketing-mapping-routing-result">
                <p data-testid="marketing-mapping-routing-destination">
                  <span className="text-slate-500">Destination: </span>
                  {routing.destination_label || routing.destination || '—'}
                </p>
                <p data-testid="marketing-mapping-routing-needs-review">
                  <span className="text-slate-500">Needs review: </span>
                  {routing.needs_review ? 'yes' : 'no'}
                </p>
                <p data-testid="marketing-mapping-routing-creates">
                  <span className="text-slate-500">Creates entities: </span>
                  {routing.creates_entities ? 'yes' : 'no'}
                </p>
                <p data-testid="marketing-mapping-routing-unmapped">
                  <span className="text-slate-500">Unmapped: </span>
                  {routing.unmapped_fields.length
                    ? routing.unmapped_fields.join(', ')
                    : '—'}
                </p>
                <p data-testid="marketing-mapping-routing-ignored">
                  <span className="text-slate-500">Ignored: </span>
                  {routing.ignored_fields.length ? routing.ignored_fields.join(', ') : '—'}
                </p>
                <p className="text-slate-600" data-testid="marketing-mapping-routing-note">
                  {routing.note}
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-500" data-testid="marketing-mapping-routing-empty">
                {t('app.marketing.mapping.routing.empty', {
                  defaultValue:
                    'Preview shows destination, ignored, and unmapped fields without production writes.',
                })}
              </p>
            )}
          </section>
        </div>
      ) : null}
    </PageShell>
  )
}
