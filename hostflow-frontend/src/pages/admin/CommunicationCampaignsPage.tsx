/**
 * C2.3 PR-6 — thin Campaign Orchestrator UI over `/communications/campaigns`.
 *
 * Operator tools only: draft / publish / freeze run / execute (request_only).
 * No inbox, no N× Write loop, no provider knobs, no rich audience builder.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  archiveCommunicationCampaign,
  createCommunicationCampaign,
  createCommunicationCampaignRun,
  dryRunCommunicationCampaignAudience,
  executeCommunicationCampaignRun,
  listCommunicationCampaignRuns,
  listCommunicationCampaigns,
  listCommunicationCampaignVersions,
  publishCommunicationCampaign,
  updateCommunicationCampaignDraft,
  type CommunicationCampaignBundle,
  type CommunicationCampaignRun,
  type CommunicationCampaignVersion,
} from '../../api/communications/campaigns'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'

type DraftForm = {
  intent_key: string
  preferred_template_key: string
  channel: string
  audienceType: string
  audienceJson: string
}

const DEFAULT_AUDIENCE = {
  recipients: [
    {
      entity_type: 'candidate',
      entity_id: 'example-1',
      address: 'example@hostflow.local',
    },
  ],
}

function draftFromBundle(bundle: CommunicationCampaignBundle | null): DraftForm {
  const d = bundle?.draft
  const aud = d?.audience_definition
  return {
    intent_key: d?.intent_key ?? 'follow_up',
    preferred_template_key: d?.preferred_template_key ?? '',
    channel: d?.channel ?? 'email',
    audienceType: aud?.definition_type ?? 'static_list',
    audienceJson: JSON.stringify(aud?.definition || DEFAULT_AUDIENCE, null, 2),
  }
}

export default function CommunicationCampaignsPage() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [includeArchived, setIncludeArchived] = useState(false)
  const [items, setItems] = useState<CommunicationCampaignBundle[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [draftForm, setDraftForm] = useState<DraftForm>(draftFromBundle(null))
  const [versions, setVersions] = useState<CommunicationCampaignVersion[]>([])
  const [runs, setRuns] = useState<CommunicationCampaignRun[]>([])
  const [dryRunSummary, setDryRunSummary] = useState<string | null>(null)
  const [lastRunResult, setLastRunResult] = useState<string | null>(null)

  const [createKey, setCreateKey] = useState('')
  const [createName, setCreateName] = useState('')
  const [createIntent, setCreateIntent] = useState('follow_up')

  const selected = useMemo(
    () => items.find((x) => x.id === selectedId) || null,
    [items, selectedId],
  )

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await listCommunicationCampaigns({ includeArchived })
      setItems(rows)
      setSelectedId((prev) => {
        if (prev && rows.some((r) => r.id === prev)) return prev
        return rows[0]?.id ?? null
      })
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_campaigns.errors.load', {
            defaultValue: 'Failed to load campaigns',
          }),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }, [includeArchived, t])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    setDraftForm(draftFromBundle(selected))
    setDryRunSummary(null)
    setLastRunResult(null)
    if (!selected) {
      setVersions([])
      setRuns([])
      return
    }
    let mounted = true
    ;(async () => {
      try {
        const [vers, runRows] = await Promise.all([
          listCommunicationCampaignVersions(selected.id),
          listCommunicationCampaignRuns(selected.id, 10),
        ])
        if (!mounted) return
        setVersions(vers)
        setRuns(runRows)
      } catch (err: unknown) {
        if (mounted) {
          setError(
            getFriendlyErrorInfo(
              err,
              t('admin.communications_campaigns.errors.history', {
                defaultValue: 'Failed to load versions/runs',
              }),
              t,
            ),
          )
        }
      }
    })()
    return () => {
      mounted = false
    }
  }, [selected, t])

  const upsertLocal = (bundle: CommunicationCampaignBundle) => {
    setItems((prev) => {
      const next = prev.filter((x) => x.id !== bundle.id)
      if (!includeArchived && bundle.status === 'archived') return next
      return [...next, bundle].sort((a, b) => a.key.localeCompare(b.key))
    })
    setSelectedId(bundle.id)
  }

  const handleCreate = async () => {
    const key = createKey.trim()
    const name = createName.trim() || key
    const intent_key = createIntent.trim()
    if (!key || !intent_key) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const created = await createCommunicationCampaign({
        key,
        name,
        intent_key,
        channel: 'email',
        audience: {
          definition_type: 'static_list',
          definition: DEFAULT_AUDIENCE,
        },
      })
      upsertLocal(created)
      setCreateKey('')
      setCreateName('')
      setNotice(
        t('admin.communications_campaigns.notices.created', {
          defaultValue: 'Campaign created',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_campaigns.errors.create', {
            defaultValue: 'Failed to create campaign',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const handleSaveDraft = async () => {
    if (!selected) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      let definition: Record<string, unknown>
      try {
        definition = JSON.parse(draftForm.audienceJson) as Record<string, unknown>
      } catch {
        throw new Error('Audience definition must be valid JSON')
      }
      const updated = await updateCommunicationCampaignDraft(selected.id, {
        intent_key: draftForm.intent_key.trim(),
        preferred_template_key: draftForm.preferred_template_key.trim() || null,
        channel: draftForm.channel.trim() || null,
        audience: {
          definition_type: draftForm.audienceType.trim() || 'static_list',
          definition,
        },
        clear_preferred_template_key: !draftForm.preferred_template_key.trim(),
      })
      upsertLocal(updated)
      setNotice(
        t('admin.communications_campaigns.notices.draft_saved', {
          defaultValue: 'Draft saved',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_campaigns.errors.save', {
            defaultValue: 'Failed to save draft',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const handlePublish = async () => {
    if (!selected) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const published = await publishCommunicationCampaign(selected.id)
      upsertLocal(published)
      const vers = await listCommunicationCampaignVersions(selected.id)
      setVersions(vers)
      setNotice(
        t('admin.communications_campaigns.notices.published', {
          defaultValue: 'Published immutable version',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_campaigns.errors.publish', {
            defaultValue: 'Failed to publish',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const handleArchive = async () => {
    if (!selected) return
    setBusy(true)
    setError(null)
    try {
      const archived = await archiveCommunicationCampaign(selected.id)
      upsertLocal(archived)
      setNotice(
        t('admin.communications_campaigns.notices.archived', {
          defaultValue: 'Campaign archived',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_campaigns.errors.archive', {
            defaultValue: 'Failed to archive',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const handleDryRun = async () => {
    if (!selected) return
    setBusy(true)
    setError(null)
    setDryRunSummary(null)
    try {
      const result = await dryRunCommunicationCampaignAudience(selected.id)
      setDryRunSummary(
        result.ok
          ? `ok · ${result.recipients.length} recipient(s)`
          : `failed · ${(result.diagnostics || []).map((d) => d.code).join(', ')}`,
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_campaigns.errors.dry_run', {
            defaultValue: 'Audience dry-run failed',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const handleCreateAndExecuteRun = async () => {
    if (!selected?.latest_published) {
      setError({
        title: t('admin.communications_campaigns.errors.need_publish', {
          defaultValue: 'Publish a version before running',
        }),
        hint: t('admin.communications_campaigns.errors.need_publish_hint', {
          defaultValue: 'Use Publish, then Run (request_only).',
        }),
      })
      return
    }
    setBusy(true)
    setError(null)
    setLastRunResult(null)
    try {
      const run = await createCommunicationCampaignRun(selected.id, {
        idempotency_key: `ui-${selected.id}-${Date.now()}`,
      })
      const executed = await executeCommunicationCampaignRun(selected.id, run.id, {
        mode: 'request_only',
      })
      const summary = executed.orchestration.summary
      setLastRunResult(
        `${executed.orchestration.status} · emitted ${summary.emitted}/${summary.total}` +
          (summary.failed ? ` · failed ${summary.failed}` : ''),
      )
      setRuns(await listCommunicationCampaignRuns(selected.id, 10))
      setNotice(
        t('admin.communications_campaigns.notices.run_done', {
          defaultValue: 'Run executed (request_only — no transport)',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_campaigns.errors.run', {
            defaultValue: 'Failed to run campaign',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <SettingsSubpageHeader
      backHref={CRM_APP_PATHS.settingsCommunications}
      backLabel={t('admin.communications_campaigns.back', {
        defaultValue: 'Communications',
      })}
      kicker="campaigns"
      title={t('admin.communications_campaigns.title', {
        defaultValue: 'Communication campaigns',
      })}
      subtitle={t('admin.communications_campaigns.subtitle', {
        defaultValue:
          'Audience + plan → Intent per recipient. No shared campaign thread, no N× Write.',
      })}
      actions={
        <Link to={CRM_APP_PATHS.settingsCommunicationsAutomation} className="btn-secondary">
          {t('admin.communications_campaigns.link_automation', {
            defaultValue: 'Automation',
          })}
        </Link>
      }
    >
      {error ? (
        <div className="mb-3">
          <ErrorRecoveryBanner error={error} onRetry={() => void refresh()} />
        </div>
      ) : null}
      {notice ? (
        <p className="mb-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {notice}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Key
          <input
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={createKey}
            onChange={(e) => setCreateKey(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Name
          <input
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Intent key
          <input
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={createIntent}
            onChange={(e) => setCreateIntent(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="btn-primary btn-sm"
          disabled={busy || !createKey.trim() || !createIntent.trim()}
          onClick={() => void handleCreate()}
        >
          {t('admin.communications_campaigns.create.submit', {
            defaultValue: 'Create draft',
          })}
        </button>
        <label className="ml-auto flex items-center gap-2 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => setIncludeArchived(e.target.checked)}
          />
          {t('admin.communications_campaigns.include_archived', {
            defaultValue: 'Include archived',
          })}
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <section className="rounded-lg border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('admin.communications_campaigns.list_title', {
              defaultValue: 'Campaigns',
            })}
          </div>
          {loading ? (
            <p className="p-3 text-sm text-slate-500">
              {t('common.loading', { defaultValue: 'Loading…' })}
            </p>
          ) : items.length === 0 ? (
            <p className="p-3 text-sm text-slate-500">
              {t('admin.communications_campaigns.empty', {
                defaultValue: 'No campaigns yet.',
              })}
            </p>
          ) : (
            <ul className="max-h-[70vh] overflow-auto text-sm">
              {items.map((row) => (
                <li key={row.id}>
                  <button
                    type="button"
                    className={`flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left hover:bg-slate-50 ${
                      row.id === selectedId ? 'bg-slate-100' : ''
                    }`}
                    onClick={() => setSelectedId(row.id)}
                  >
                    <span className="font-medium text-slate-900">{row.name}</span>
                    <span className="font-mono text-xs text-slate-500">{row.key}</span>
                    <span className="text-xs text-slate-500">
                      {row.status}
                      {row.latest_published
                        ? ` · v${row.latest_published.version_number}`
                        : ' · draft only'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="space-y-4">
          {!selected ? (
            <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-500">
              {t('admin.communications_campaigns.select_prompt', {
                defaultValue: 'Select or create a campaign.',
              })}
            </section>
          ) : (
            <>
              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">{selected.name}</h2>
                    <p className="font-mono text-xs text-slate-500">{selected.key}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={busy}
                      onClick={() => void handleSaveDraft()}
                    >
                      Save draft
                    </button>
                    <button
                      type="button"
                      className="btn-primary btn-sm"
                      disabled={busy}
                      onClick={() => void handlePublish()}
                    >
                      Publish
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={busy}
                      onClick={() => void handleDryRun()}
                    >
                      Audience dry-run
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={busy || !selected.latest_published}
                      onClick={() => void handleCreateAndExecuteRun()}
                    >
                      Run (request_only)
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={busy || selected.status === 'archived'}
                      onClick={() => void handleArchive()}
                    >
                      Archive
                    </button>
                  </div>
                </div>

                {dryRunSummary ? (
                  <p className="mb-3 text-xs text-slate-600">Dry-run: {dryRunSummary}</p>
                ) : null}
                {lastRunResult ? (
                  <p className="mb-3 text-xs text-slate-600">Last run: {lastRunResult}</p>
                ) : null}

                <div className="grid gap-3 md:grid-cols-2">
                  <label className="flex flex-col gap-1 text-xs text-slate-600">
                    Intent key
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.intent_key}
                      onChange={(e) =>
                        setDraftForm((f) => ({ ...f, intent_key: e.target.value }))
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600">
                    Preferred template key
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.preferred_template_key}
                      onChange={(e) =>
                        setDraftForm((f) => ({
                          ...f,
                          preferred_template_key: e.target.value,
                        }))
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600">
                    Channel
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.channel}
                      onChange={(e) =>
                        setDraftForm((f) => ({ ...f, channel: e.target.value }))
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600">
                    Audience type
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.audienceType}
                      onChange={(e) =>
                        setDraftForm((f) => ({ ...f, audienceType: e.target.value }))
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    Audience definition (JSON)
                    <textarea
                      className="min-h-[140px] rounded border border-slate-300 px-2 py-1 font-mono text-xs"
                      value={draftForm.audienceJson}
                      onChange={(e) =>
                        setDraftForm((f) => ({ ...f, audienceJson: e.target.value }))
                      }
                    />
                  </label>
                </div>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="mb-2 text-sm font-semibold text-slate-900">Versions</h3>
                {versions.length === 0 ? (
                  <p className="text-xs text-slate-500">No versions yet.</p>
                ) : (
                  <ul className="space-y-1 text-xs text-slate-600">
                    {versions.map((v) => (
                      <li key={v.id} className="font-mono">
                        v{v.version_number} · {v.status} · {v.intent_key}
                        {v.published_at ? ` · ${v.published_at}` : ''}
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="mb-2 text-sm font-semibold text-slate-900">Recent runs</h3>
                {runs.length === 0 ? (
                  <p className="text-xs text-slate-500">No runs yet.</p>
                ) : (
                  <ul className="space-y-1 text-xs text-slate-600">
                    {runs.map((r) => (
                      <li key={r.id} className="font-mono">
                        {r.status} · recipients {r.recipient_count ?? '—'} · {r.idempotency_key}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </SettingsSubpageHeader>
  )
}
