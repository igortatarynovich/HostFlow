/**
 * Marketing Source Test Lead + field discovery (Acquisition UI Cutover C-4).
 * Uses sample / capture-next / preview API façade — no mapping persist (C-5).
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  CRM_APP_PATHS,
  marketingSourceMappingPath,
} from '../../app/crmAppPaths'
import {
  getMarketingSourceSample,
  listMarketingSources,
  postMarketingSourceCaptureNext,
  postMarketingSourceSampleFromPayload,
  postMarketingSourceSamplePreview,
  type MarketingSourceSample,
  type MarketingSourceSamplePreview,
  type MarketingSourceSummary,
} from '../../api/marketingSources'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { PageHeader } from '../../components/nav/PageHeader'
import { PageShell, PageShellHeader } from '../../components/layout'
import { useI18n } from '../../i18n'
import { getFriendlyErrorInfo, type FriendlyErrorInfo } from '../../utils/friendlyError'

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

function fieldStatusLabel(status: string, t: (k: string, o?: object) => string): string {
  switch (status) {
    case 'mapped':
      return t('app.marketing.test_lead.field.mapped', { defaultValue: 'Mapped' })
    case 'unmapped':
      return t('app.marketing.test_lead.field.unmapped', { defaultValue: 'Unmapped' })
    case 'new':
      return t('app.marketing.test_lead.field.new', { defaultValue: 'New' })
    default:
      return status
  }
}

export default function MarketingSourceTestLeadPage() {
  const { t } = useI18n()
  const { sourceId = '' } = useParams<{ sourceId: string }>()

  const [source, setSource] = useState<MarketingSourceSummary | null>(null)
  const [sample, setSample] = useState<MarketingSourceSample | null>(null)
  const [preview, setPreview] = useState<MarketingSourceSamplePreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [showAdvancedPaste, setShowAdvancedPaste] = useState(false)
  const [pasteText, setPasteText] = useState('')
  const [showRaw, setShowRaw] = useState(false)
  const [showNormalized, setShowNormalized] = useState(false)

  const load = useCallback(async () => {
    if (!sourceId) return
    setLoading(true)
    setError(null)
    try {
      const [rows, sampleRow] = await Promise.all([
        listMarketingSources(),
        getMarketingSourceSample(sourceId),
      ])
      setSource(rows.find((row) => row.source_id === sourceId) ?? null)
      setSample(sampleRow)
      setPreview(null)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('app.marketing.test_lead.errors.load'),
          t,
        ),
      )
      setSample(null)
    } finally {
      setLoading(false)
    }
  }, [sourceId, t])

  useEffect(() => {
    void load()
  }, [load])

  const mappingHref = useMemo(() => {
    if (source?.mapping_path) return source.mapping_path
    return sourceId
      ? marketingSourceMappingPath(sourceId)
      : CRM_APP_PATHS.marketingSources
  }, [source?.mapping_path, sourceId])

  const title = source?.display_name
    ? t('app.marketing.test_lead.title_named', {
        values: { name: source.display_name },
      })
    : t('app.marketing.test_lead.title', { defaultValue: 'Test lead & field discovery' })

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
          t('app.marketing.test_lead.errors.action'),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <PageShell data-testid="marketing-source-test-lead-page">
      <PageShellHeader>
        <PageHeader
          title={title}
          subtitle={t('app.marketing.test_lead.subtitle')}
          actions={
            <Link
              to={CRM_APP_PATHS.marketingSources}
              className="btn-secondary btn-sm"
              data-testid="marketing-test-lead-back-sources"
            >
              {t('app.marketing.test_lead.actions.back', { defaultValue: '← Sources' })}
            </Link>
          }
        />
      </PageShellHeader>

      {error ? (
        <div data-testid="marketing-test-lead-error">
          <ErrorRecoveryBanner info={error} onRetry={() => void load()} />
        </div>
      ) : null}

      {actionMessage ? (
        <p
          className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
          data-testid="marketing-test-lead-action-message"
        >
          {actionMessage}
        </p>
      ) : null}

      {loading ? (
        <p className="text-sm text-slate-500" data-testid="marketing-test-lead-loading">
          {t('common.loading')}
        </p>
      ) : (
        <div className="space-y-6">
          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-test-lead-context"
          >
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.marketing.test_lead.context.title', { defaultValue: 'Source' })}
            </h2>
            <dl className="mt-3 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.test_lead.context.provider', { defaultValue: 'Provider' })}
                </dt>
                <dd data-testid="marketing-test-lead-provider">
                  {source?.provider || t('app.marketing.sources.none', { defaultValue: '—' })}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.test_lead.context.health', { defaultValue: 'Mapping Health' })}
                </dt>
                <dd data-testid="marketing-test-lead-health">
                  {source ? healthLabel(String(source.mapping_health), t) : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.test_lead.context.sample_source', {
                    defaultValue: 'Sample source',
                  })}
                </dt>
                <dd data-testid="marketing-test-lead-sample-source">
                  {sample?.sample_source || 'none'}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">
                  {t('app.marketing.test_lead.context.rules', {
                    defaultValue: 'Mapping rules',
                  })}
                </dt>
                <dd data-testid="marketing-test-lead-rules-count">
                  {sample?.mapping_rules_count ?? source?.mapping_rules_count ?? 0}
                </dd>
              </div>
            </dl>
            {sample?.capture_next_until ? (
              <p
                className="mt-3 text-sm text-amber-800"
                data-testid="marketing-test-lead-capture-armed"
              >
                {t('app.marketing.test_lead.capture.armed', {
                  values: { until: sample.capture_next_until },
                })}
              </p>
            ) : null}
          </section>

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-test-lead-obtain"
          >
            <h2 className="text-sm font-semibold text-slate-900">
              {t('app.marketing.test_lead.obtain.title', { defaultValue: 'Obtain sample' })}
            </h2>
            <div className="mt-3 space-y-4 text-sm text-slate-700">
              <div data-testid="marketing-test-lead-mode-a">
                <p className="font-medium text-slate-900">
                  {t('app.marketing.test_lead.mode_a.title', {
                    defaultValue: 'A — Official Meta test lead (primary)',
                  })}
                </p>
                <p className="mt-1 text-slate-600">
                  {t('app.marketing.test_lead.mode_a.body')}
                </p>
                <button
                  type="button"
                  className="btn-secondary btn-sm mt-2"
                  disabled={busy || !sourceId}
                  data-testid="marketing-test-lead-refresh"
                  onClick={() => void runAction(async () => {
                    const next = await getMarketingSourceSample(sourceId)
                    setSample(next)
                    setPreview(null)
                    setActionMessage(
                      t('app.marketing.test_lead.mode_a.refreshed', {
                        defaultValue: 'Sample refreshed',
                      }),
                    )
                  })}
                >
                  {t('app.marketing.test_lead.actions.refresh', { defaultValue: 'Refresh sample' })}
                </button>
              </div>

              <div data-testid="marketing-test-lead-mode-b">
                <p className="font-medium text-slate-900">
                  {t('app.marketing.test_lead.mode_b.title', {
                    defaultValue: 'B — Capture next real lead',
                  })}
                </p>
                <p className="mt-1 text-slate-600">
                  {t('app.marketing.test_lead.mode_b.body')}
                </p>
                <button
                  type="button"
                  className="btn-primary btn-sm mt-2"
                  disabled={busy || !sourceId}
                  data-testid="marketing-test-lead-capture-next"
                  onClick={() => void runAction(async () => {
                    const armed = await postMarketingSourceCaptureNext(sourceId)
                    const next = await getMarketingSourceSample(sourceId)
                    setSample(next)
                    setActionMessage(armed.message)
                  })}
                >
                  {t('app.marketing.test_lead.actions.capture_next', {
                    defaultValue: 'Arm capture next',
                  })}
                </button>
              </div>

              <div data-testid="marketing-test-lead-mode-c">
                <button
                  type="button"
                  className="text-sm font-medium text-brand-700 hover:underline"
                  data-testid="marketing-test-lead-advanced-toggle"
                  onClick={() => setShowAdvancedPaste((v) => !v)}
                >
                  {showAdvancedPaste
                    ? t('app.marketing.test_lead.mode_c.hide', {
                        defaultValue: 'Hide advanced paste',
                      })
                    : t('app.marketing.test_lead.mode_c.show', {
                        defaultValue: 'Advanced — paste saved payload',
                      })}
                </button>
                {showAdvancedPaste ? (
                  <div className="mt-2 space-y-2">
                    <textarea
                      className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-xs"
                      rows={8}
                      value={pasteText}
                      onChange={(e) => setPasteText(e.target.value)}
                      placeholder='{"entry":[{"changes":[{"value":{"field_data":[...]}}]}]}'
                      data-testid="marketing-test-lead-paste-input"
                    />
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={busy || !sourceId || !pasteText.trim()}
                      data-testid="marketing-test-lead-paste-submit"
                      onClick={() => {
                        let parsed: Record<string, unknown>
                        try {
                          parsed = JSON.parse(pasteText) as Record<string, unknown>
                        } catch {
                          setError({
                            title: t('app.marketing.test_lead.mode_c.invalid_json', {
                              defaultValue: 'Invalid JSON',
                            }),
                            hint: t('app.marketing.test_lead.mode_c.invalid_json_hint', {
                              defaultValue: 'Paste a JSON object payload.',
                            }),
                          })
                          return
                        }
                        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
                          setError({
                            title: t('app.marketing.test_lead.mode_c.invalid_object', {
                              defaultValue: 'Payload must be a JSON object',
                            }),
                            hint: t('app.marketing.test_lead.mode_c.invalid_object_hint', {
                              defaultValue: 'Arrays and primitives are not accepted.',
                            }),
                          })
                          return
                        }
                        void runAction(async () => {
                          const next = await postMarketingSourceSampleFromPayload(sourceId, parsed)
                          setSample(next)
                          setPreview(null)
                          setActionMessage(
                            t('app.marketing.test_lead.mode_c.saved', {
                              defaultValue: 'Pasted payload stored as sample',
                            }),
                          )
                        })
                      }}
                    >
                      {t('app.marketing.test_lead.actions.use_paste', {
                        defaultValue: 'Use pasted payload',
                      })}
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          </section>

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-test-lead-fields"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-slate-900">
                {t('app.marketing.test_lead.fields.title', {
                  defaultValue: 'Field discovery',
                })}
              </h2>
              <button
                type="button"
                className="btn-primary btn-sm"
                disabled={busy || !sourceId || !sample?.has_sample}
                data-testid="marketing-test-lead-preview"
                onClick={() => void runAction(async () => {
                  const result = await postMarketingSourceSamplePreview(sourceId)
                  setPreview(result)
                  setActionMessage(
                    t('app.marketing.test_lead.preview.done', {
                      defaultValue: 'Dry-run normalize complete (no entities created)',
                    }),
                  )
                })}
              >
                {t('app.marketing.test_lead.actions.preview', {
                  defaultValue: 'Dry-run normalize',
                })}
              </button>
            </div>

            {!sample?.has_sample ? (
              <p
                className="mt-3 text-sm text-slate-500"
                data-testid="marketing-test-lead-fields-empty"
              >
                {t('app.marketing.test_lead.fields.empty')}
              </p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table
                  className="min-w-full text-left text-sm"
                  data-testid="marketing-test-lead-fields-table"
                >
                  <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-2 py-2">
                        {t('app.marketing.test_lead.fields.col_field', {
                          defaultValue: 'Provider field',
                        })}
                      </th>
                      <th className="px-2 py-2">
                        {t('app.marketing.test_lead.fields.col_sample', {
                          defaultValue: 'Sample (masked)',
                        })}
                      </th>
                      <th className="px-2 py-2">
                        {t('app.marketing.test_lead.fields.col_target', {
                          defaultValue: 'Proposed target',
                        })}
                      </th>
                      <th className="px-2 py-2">
                        {t('app.marketing.test_lead.fields.col_status', {
                          defaultValue: 'Status',
                        })}
                      </th>
                      <th className="px-2 py-2">
                        {t('app.marketing.test_lead.fields.col_action', {
                          defaultValue: 'Action',
                        })}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {(preview?.fields ?? sample.fields).map((field) => (
                      <tr
                        key={field.source}
                        className="border-b border-slate-100"
                        data-testid={`marketing-test-lead-field-${field.source}`}
                      >
                        <td className="px-2 py-2 font-mono text-xs">{field.source}</td>
                        <td className="px-2 py-2 font-mono text-xs">
                          {field.sample_value_masked || '—'}
                        </td>
                        <td className="px-2 py-2 font-mono text-xs">
                          {field.proposed_target || '—'}
                        </td>
                        <td className="px-2 py-2">{fieldStatusLabel(field.status, t)}</td>
                        <td className="px-2 py-2">
                          <Link
                            to={mappingHref}
                            className="text-sm font-medium text-brand-700 hover:underline"
                            data-testid={`marketing-test-lead-field-map-${field.source}`}
                          >
                            {t('app.marketing.test_lead.fields.select_mapping', {
                              defaultValue: 'Select in Mapping',
                            })}
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {preview ? (
              <p
                className="mt-3 text-xs text-slate-500"
                data-testid="marketing-test-lead-preview-flag"
              >
                creates_entities={String(preview.creates_entities)}
              </p>
            ) : null}
          </section>

          <section
            className="rounded-lg border border-slate-200 bg-white p-4"
            data-testid="marketing-test-lead-raw"
          >
            <button
              type="button"
              className="text-sm font-semibold text-slate-900 hover:underline"
              data-testid="marketing-test-lead-raw-toggle"
              onClick={() => setShowRaw((v) => !v)}
            >
              {showRaw
                ? t('app.marketing.test_lead.raw.hide', { defaultValue: 'Hide raw payload' })
                : t('app.marketing.test_lead.raw.show', {
                    defaultValue: 'Show raw payload (masked)',
                  })}
            </button>
            {showRaw ? (
              <pre
                className="mt-3 max-h-80 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100"
                data-testid="marketing-test-lead-raw-body"
              >
                {JSON.stringify(sample?.raw_payload_masked ?? {}, null, 2)}
              </pre>
            ) : null}

            {preview ? (
              <div className="mt-4">
                <button
                  type="button"
                  className="text-sm font-semibold text-slate-900 hover:underline"
                  data-testid="marketing-test-lead-normalized-toggle"
                  onClick={() => setShowNormalized((v) => !v)}
                >
                  {showNormalized
                    ? t('app.marketing.test_lead.normalized.hide', {
                        defaultValue: 'Hide normalized preview',
                      })
                    : t('app.marketing.test_lead.normalized.show', {
                        defaultValue: 'Show normalized preview',
                      })}
                </button>
                {showNormalized ? (
                  <pre
                    className="mt-3 max-h-80 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100"
                    data-testid="marketing-test-lead-normalized-body"
                  >
                    {JSON.stringify(preview.normalized_payload ?? {}, null, 2)}
                  </pre>
                ) : null}
              </div>
            ) : null}
          </section>

          <div className="flex flex-wrap gap-3">
            <Link
              to={mappingHref}
              className="btn-primary btn-sm"
              data-testid="marketing-test-lead-continue-mapping"
            >
              {t('app.marketing.test_lead.actions.continue_mapping', {
                defaultValue: 'Continue to Mapping',
              })}
            </Link>
            <Link
              to={CRM_APP_PATHS.marketingSources}
              className="btn-secondary btn-sm"
              data-testid="marketing-test-lead-back-footer"
            >
              {t('app.marketing.test_lead.actions.back', { defaultValue: '← Sources' })}
            </Link>
          </div>
        </div>
      )}
    </PageShell>
  )
}
