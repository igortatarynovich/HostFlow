/**
 * MA-3 Mapping workspace — one editor over IntakeSourceProfile.mapping_rules.
 * Schema-first. Sample is an optional example. C-5 route reused.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CRM_APP_PATHS,
  marketingSourceTestLeadPath,
} from '../../app/crmAppPaths'
import {
  getMarketingSourceMapping,
  listMarketingSources,
  postMarketingSourceRoutingPreview,
  putMarketingSourceMapping,
  type MappingDestination,
  type MappingWorkspaceRow,
  type MarketingSourceMapping,
  type MarketingSourceMappingRule,
  type MarketingSourceRoutingPreview,
  type MarketingSourceSummary,
} from '../../api/marketingSources'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

const OPTION_IGNORE_VALUE = '__ignore__'

type DraftRow = {
  source: string
  label: string
  options: string[]
  sample_example: string
  binding: 'mapped' | 'ignored' | 'unmapped'
  destination_code: string
  destination_label: string
  choice: boolean
  option_map: Record<string, string>
  in_schema: boolean
  field_type: string
  drift: string | null
  drift_human: string | null
}

function rowsFromWorkspace(mapping: MarketingSourceMapping): DraftRow[] {
  const schema = mapping.schema_fields || []
  if (schema.length) {
    return schema.map((row: MappingWorkspaceRow) => ({
      source: row.source,
      label: row.label || row.source,
      options: row.options || [],
      sample_example: row.sample_example || '',
      binding:
        row.binding === 'ignored' || row.binding === 'mapped' ? row.binding : 'unmapped',
      destination_code: row.destination_code || '',
      destination_label: row.destination_label || '',
      choice: Boolean(row.choice),
      option_map: { ...(row.option_map || {}) },
      in_schema: Boolean(row.in_schema),
      field_type: row.field_type || '',
      drift: row.drift || null,
      drift_human: row.drift_human || null,
    }))
  }
  return (mapping.mapping_rules || []).map((rule) => ({
    source: String(rule.source || ''),
    label: String(rule.source || ''),
    options: [],
    sample_example: '',
    binding: String(rule.action || '').toLowerCase() === 'ignore' ? 'ignored' : 'mapped',
    destination_code: String(rule.qualified_field_code || rule.target || ''),
    destination_label: '',
    choice: false,
    option_map: { ...(rule.option_map || {}) },
    in_schema: false,
    field_type: '',
    drift: null,
    drift_human: null,
  }))
}

function draftsToRules(drafts: DraftRow[]): MarketingSourceMappingRule[] {
  return drafts
    .filter((d) => d.source.trim())
    .map((d) => {
      if (d.binding === 'ignored') {
        return { source: d.source.trim(), action: 'ignore', format: 'string' }
      }
      if (d.binding !== 'mapped' || !d.destination_code.trim()) {
        return null
      }
      const code = d.destination_code.trim()
      const looksQualified = code.includes('.')
      const rule: MarketingSourceMappingRule = {
        source: d.source.trim(),
        format: 'string',
        ...(looksQualified ? { qualified_field_code: code } : { target: code }),
      }
      if (Object.keys(d.option_map).length) {
        rule.option_map = d.option_map
      }
      return rule
    })
    .filter((r): r is MarketingSourceMappingRule => r != null)
}

function destinationFor(
  code: string,
  destinations: MappingDestination[],
): MappingDestination | undefined {
  const key = code.trim().toLowerCase()
  if (!key) return undefined
  return destinations.find((d) => {
    if (d.code.toLowerCase() === key) return true
    return (d.aliases || []).some((a) => a.toLowerCase() === key)
  })
}

export default function MarketingSourceMappingPage() {
  const { t } = useI18n()
  const { sourceId = '' } = useParams<{ sourceId: string }>()

  const [source, setSource] = useState<MarketingSourceSummary | null>(null)
  const [mapping, setMapping] = useState<MarketingSourceMapping | null>(null)
  const [drafts, setDrafts] = useState<DraftRow[]>([])
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
      const [rows, mappingRow] = await Promise.all([
        listMarketingSources(),
        getMarketingSourceMapping(sourceId),
      ])
      setSource(rows.find((row) => row.source_id === sourceId) ?? null)
      setMapping(mappingRow)
      setDrafts(rowsFromWorkspace(mappingRow))
      setRouting(null)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(err, t('app.marketing.mapping.errors.load'), t),
      )
      setMapping(null)
    } finally {
      setLoading(false)
    }
  }, [sourceId, t])

  useEffect(() => {
    void load()
  }, [load])

  const destinations = mapping?.destinations || []

  const title = useMemo(() => {
    const name = mapping?.display_name || source?.display_name
    return name
      ? t('app.marketing.mapping.title_named', { values: { name } })
      : t('app.marketing.mapping.title')
  }, [mapping?.display_name, source?.display_name, t])

  async function runAction(fn: () => Promise<void>) {
    setBusy(true)
    setError(null)
    setActionMessage(null)
    try {
      await fn()
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(err, t('app.marketing.mapping.errors.action'), t),
      )
    } finally {
      setBusy(false)
    }
  }

  function updateDraft(index: number, patch: Partial<DraftRow>) {
    setDrafts((prev) =>
      prev.map((row, i) => {
        if (i !== index) return row
        const next = { ...row, ...patch }
        if (patch.destination_code != null) {
          const dest = destinationFor(patch.destination_code, destinations)
          next.choice = Boolean(dest?.choice)
          if (!next.choice) next.option_map = {}
        }
        return next
      }),
    )
  }

  return (
    <PageShell data-testid="marketing-source-mapping-page">
      <PageShellHeader>
        <PageHeader
          title={title}
          subtitle={t('app.marketing.mapping.subtitle')}
          actions={
            <div className="flex flex-wrap gap-2">
              <Link
                to={marketingSourceTestLeadPath(sourceId)}
                className="btn-secondary btn-sm"
                data-testid="marketing-mapping-to-test-lead"
              >
                {t('app.marketing.mapping.actions.test_lead')}
              </Link>
              <Link
                to={CRM_APP_PATHS.marketingSources}
                className="btn-secondary btn-sm"
              >
                {t('app.marketing.mapping.actions.back')}
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
          {t('common.loading')}
        </p>
      ) : mapping ? (
        <div className="space-y-6">
          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-mapping-summary"
          >
            <p className="text-base font-semibold text-slate-900" data-testid="marketing-mapping-summary-human">
              {mapping.summary?.human || t('app.marketing.mapping.summary.fallback')}
            </p>
            <p className="mt-1 text-sm text-slate-600">
              {mapping.has_sample
                ? t('app.marketing.mapping.sample.present')
                : t('app.marketing.mapping.sample.none')}
            </p>
          </section>

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-mapping-context"
          >
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
              <div>
                <dt className="text-slate-500">{t('app.marketing.mapping.fields.provider')}</dt>
                <dd data-testid="marketing-mapping-provider">{mapping.provider || '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">{t('app.marketing.mapping.fields.health')}</dt>
                <dd data-testid="marketing-mapping-health">
                  {mapping.summary?.human || mapping.mapping_health}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">{t('app.marketing.mapping.fields.destination')}</dt>
                <dd data-testid="marketing-mapping-destination">
                  {mapping.destination_label || mapping.destination || '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">{t('app.marketing.mapping.fields.rules_source')}</dt>
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
                {t('app.marketing.mapping.rules.title')}
              </h2>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={busy}
                data-testid="marketing-mapping-save"
                onClick={() =>
                  void runAction(async () => {
                    const snapshot = mapping.has_schema
                      ? {
                          fields: drafts.map((d) => ({
                            source: d.source,
                            label: d.label,
                            options: d.options,
                            field_type: d.field_type,
                          })),
                        }
                      : null
                    const saved = await putMarketingSourceMapping(
                      sourceId,
                      draftsToRules(drafts),
                      snapshot,
                    )
                    setMapping(saved)
                    setDrafts(rowsFromWorkspace(saved))
                    setActionMessage(
                      saved.projection?.[0]?.sentence || t('app.marketing.mapping.saved'),
                    )
                  })
                }
              >
                {t('app.marketing.mapping.actions.save')}
              </button>
            </div>

            {drafts.length === 0 ? (
              <p className="text-sm text-slate-500" data-testid="marketing-mapping-rules-empty">
                {t('app.marketing.mapping.rules.empty')}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table
                  className="min-w-full divide-y divide-slate-200 text-sm"
                  data-testid="marketing-mapping-rules-table"
                >
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-3 py-2">{t('app.marketing.mapping.table.provider_field')}</th>
                      <th className="px-3 py-2">{t('app.marketing.mapping.table.sample')}</th>
                      <th className="px-3 py-2">{t('app.marketing.mapping.table.target')}</th>
                      <th className="px-3 py-2">{t('app.marketing.mapping.table.action')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {drafts.map((row, index) => {
                      const dest = destinationFor(row.destination_code, destinations)
                      const statusLabel =
                        row.binding === 'mapped'
                          ? t('app.marketing.mapping.binding.mapped')
                          : row.binding === 'ignored'
                            ? t('app.marketing.mapping.binding.ignored')
                            : t('app.marketing.mapping.binding.unmapped')
                      const driftLabel = row.drift
                        ? t(`app.marketing.mapping.drift.${row.drift}`, {
                            defaultValue: row.drift_human || row.drift,
                          })
                        : ''
                      return (
                        <tr key={row.source} data-testid={`marketing-mapping-row-${row.source}`}>
                          <td className="px-3 py-2 align-top">
                            <div className="font-medium text-slate-900">{row.label}</div>
                            <div className="mt-0.5 text-xs text-slate-500">{statusLabel}</div>
                            {!row.in_schema ? (
                              <p className="mt-1 text-xs text-amber-800" data-testid={`marketing-mapping-historical-${row.source}`}>
                                {t('app.marketing.mapping.historical', {
                                  defaultValue: 'Removed from the form — review this binding',
                                })}
                              </p>
                            ) : null}
                            {driftLabel ? (
                              <p
                                className="mt-1 text-xs text-amber-800"
                                data-testid={`marketing-mapping-drift-${row.source}`}
                              >
                                {driftLabel}
                              </p>
                            ) : null}
                          </td>
                          <td className="px-3 py-2 align-top text-slate-600">
                            {row.sample_example
                              ? t('app.marketing.mapping.sample.latest', {
                                  values: { value: row.sample_example },
                                })
                              : t('app.marketing.mapping.sample.none_short')}
                          </td>
                          <td className="px-3 py-2 align-top">
                            <select
                              className="w-full rounded border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-50"
                              value={row.destination_code}
                              disabled={row.binding === 'ignored' || busy}
                              data-testid={`marketing-mapping-target-${row.source}`}
                              onChange={(e) =>
                                updateDraft(index, {
                                  destination_code: e.target.value,
                                  binding: e.target.value ? 'mapped' : 'unmapped',
                                })
                              }
                            >
                              <option value="">
                                {t('app.marketing.mapping.destination.none')}
                              </option>
                              {destinations.map((item) => (
                                <option key={item.code} value={item.code}>
                                  {item.label}
                                </option>
                              ))}
                              {row.destination_code && !dest ? (
                                <option value={row.destination_code}>
                                  {row.destination_label ||
                                    t('app.marketing.mapping.destination.invalid', {
                                      defaultValue: 'HostFlow field is no longer valid',
                                    })}
                                </option>
                              ) : null}
                            </select>
                            {row.choice && row.binding === 'mapped' ? (
                              <div className="mt-2 space-y-1" data-testid={`marketing-mapping-options-${row.source}`}>
                                {(row.options.length ? row.options : Object.keys(row.option_map)).map((opt) => {
                                  const destOptions = dest?.options || []
                                  return (
                                  <label key={opt} className="flex items-center gap-2 text-xs text-slate-700">
                                    <span className="min-w-[8rem]">{opt}</span>
                                    {destOptions.length ? (
                                      <select
                                        className="flex-1 rounded border border-slate-300 px-2 py-0.5"
                                        value={row.option_map[opt] || ''}
                                        disabled={busy}
                                        onChange={(e) =>
                                          updateDraft(index, {
                                            option_map: { ...row.option_map, [opt]: e.target.value },
                                          })
                                        }
                                      >
                                        <option value="">
                                          {t('app.marketing.mapping.option_map.unset')}
                                        </option>
                                        <option value={OPTION_IGNORE_VALUE}>
                                          {t('app.marketing.mapping.option_map.ignore')}
                                        </option>
                                        {destOptions.map((item) => (
                                          <option key={item.value} value={item.value}>
                                            {item.label}
                                          </option>
                                        ))}
                                      </select>
                                    ) : (
                                      <input
                                        className="flex-1 rounded border border-slate-300 px-2 py-0.5"
                                        value={row.option_map[opt] || ''}
                                        disabled={busy}
                                        placeholder={t('app.marketing.mapping.option_map.hostflow')}
                                        onChange={(e) =>
                                          updateDraft(index, {
                                            option_map: { ...row.option_map, [opt]: e.target.value },
                                          })
                                        }
                                      />
                                    )}
                                  </label>
                                  )
                                })}
                              </div>
                            ) : null}
                          </td>
                          <td className="px-3 py-2 align-top">
                            <select
                              className="rounded border border-slate-300 px-2 py-1 text-sm"
                              value={row.binding === 'ignored' ? 'ignore' : 'map'}
                              disabled={busy}
                              data-testid={`marketing-mapping-action-${row.source}`}
                              onChange={(e) =>
                                updateDraft(index, {
                                  binding: e.target.value === 'ignore' ? 'ignored' : row.destination_code ? 'mapped' : 'unmapped',
                                })
                              }
                            >
                              <option value="map">{t('app.marketing.mapping.action.map')}</option>
                              <option value="ignore">{t('app.marketing.mapping.action.ignore')}</option>
                            </select>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {mapping.projection && mapping.projection.length > 0 ? (
            <section
              className="rounded-lg border border-slate-200 bg-white p-4"
              data-testid="marketing-mapping-projection"
            >
              <h2 className="mb-2 text-base font-semibold text-slate-900">
                {t('app.marketing.mapping.projection.title')}
              </h2>
              <ul className="space-y-1 text-sm text-slate-800">
                {mapping.projection.map((item) => (
                  <li key={`${item.source}-${item.destination_label}`}>{item.sentence}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-mapping-applied"
          >
            <h2 className="mb-2 text-base font-semibold text-slate-900">
              {t('app.marketing.mapping.applied.title')}
            </h2>
            {mapping.applied_evidence?.present ? (
              <div className="space-y-2 text-sm" data-testid="marketing-mapping-applied-result">
                <p
                  className={mapping.applied_evidence.drift ? 'text-amber-800' : 'text-slate-600'}
                  data-testid="marketing-mapping-applied-drift"
                >
                  {mapping.applied_evidence.drift
                    ? t('app.marketing.mapping.applied.drift')
                    : t('app.marketing.mapping.applied.current')}
                </p>
                {mapping.applied_evidence.sentences.length > 0 ? (
                  <ul className="space-y-1 text-slate-800" data-testid="marketing-mapping-applied-sentences">
                    {mapping.applied_evidence.sentences.map((item) => (
                      <li key={`${item.source}-${item.destination_label}`}>{item.sentence}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-slate-500" data-testid="marketing-mapping-applied-empty">
                {t('app.marketing.mapping.applied.none')}
              </p>
            )}
          </section>

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-mapping-routing"
          >
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                {t('app.marketing.mapping.routing.title')}
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
                {t('app.marketing.mapping.actions.preview_routing')}
              </button>
            </div>

            {routing ? (
              <div className="space-y-2 text-sm" data-testid="marketing-mapping-routing-result">
                <p data-testid="marketing-mapping-routing-destination">
                  <span className="text-slate-500">{t('app.marketing.mapping.routing.destination')}: </span>
                  {routing.destination_label || routing.destination || '—'}
                </p>
                <p data-testid="marketing-mapping-routing-needs-review">
                  <span className="text-slate-500">{t('app.marketing.mapping.routing.needs_review')}: </span>
                  {routing.needs_review ? t('common.yes') : t('common.no')}
                </p>
                <p data-testid="marketing-mapping-routing-creates">
                  <span className="text-slate-500">{t('app.marketing.mapping.routing.creates')}: </span>
                  {routing.creates_entities ? t('common.yes') : t('common.no')}
                </p>
                <p data-testid="marketing-mapping-routing-unmapped">
                  <span className="text-slate-500">{t('app.marketing.mapping.routing.unmapped')}: </span>
                  {routing.unmapped_fields.length ? routing.unmapped_fields.join(', ') : '—'}
                </p>
                <p data-testid="marketing-mapping-routing-ignored">
                  <span className="text-slate-500">{t('app.marketing.mapping.routing.ignored')}: </span>
                  {routing.ignored_fields.length ? routing.ignored_fields.join(', ') : '—'}
                </p>
                <p className="text-slate-600" data-testid="marketing-mapping-routing-note">
                  {routing.note}
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-500" data-testid="marketing-mapping-routing-empty">
                {t('app.marketing.mapping.routing.empty')}
              </p>
            )}
          </section>
        </div>
      ) : null}
    </PageShell>
  )
}
