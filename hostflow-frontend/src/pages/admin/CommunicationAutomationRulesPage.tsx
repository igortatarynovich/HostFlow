/**
 * C2.2 PR-5 — thin Automation Engine UI over `/communications/automation/rules`.
 * No client-owned send loop, composition, or channel policy.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  archiveCommunicationAutomationRule,
  createCommunicationAutomationRule,
  dryRunCommunicationAutomationRule,
  listCommunicationAutomationDecisions,
  listCommunicationAutomationRules,
  listCommunicationAutomationVersions,
  publishCommunicationAutomationRule,
  setCommunicationAutomationRuleEnabled,
  updateCommunicationAutomationDraft,
  type CommunicationAutomationDecision,
  type CommunicationAutomationDryRunResult,
  type CommunicationAutomationRuleBundle,
  type CommunicationAutomationVersion,
} from '../../api/communications/automation'
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
  recipient_strategy: string
  conditionsJson: string
  variablesJson: string
  triggersJson: string
}

function draftFromBundle(bundle: CommunicationAutomationRuleBundle | null): DraftForm {
  const d = bundle?.draft
  return {
    intent_key: d?.intent_key ?? '',
    preferred_template_key: d?.preferred_template_key ?? '',
    channel: d?.channel ?? 'email',
    recipient_strategy: d?.recipient_strategy ?? 'origin_primary',
    conditionsJson: JSON.stringify(d?.conditions || {}, null, 2),
    variablesJson: JSON.stringify(d?.variables_mapping || {}, null, 2),
    triggersJson: JSON.stringify(
      (d?.triggers || []).map((t) => ({
        event_type: t.event_type,
        event_filter: t.event_filter || {},
      })),
      null,
      2,
    ),
  }
}

export default function CommunicationAutomationRulesPage() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [includeArchived, setIncludeArchived] = useState(false)
  const [items, setItems] = useState<CommunicationAutomationRuleBundle[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [draftForm, setDraftForm] = useState<DraftForm>(draftFromBundle(null))
  const [versions, setVersions] = useState<CommunicationAutomationVersion[]>([])
  const [decisions, setDecisions] = useState<CommunicationAutomationDecision[]>([])
  const [dryRunEventType, setDryRunEventType] = useState('candidate.stage_changed')
  const [dryRunDataJson, setDryRunDataJson] = useState(
    '{\n  "stage": "interview"\n}',
  )
  const [dryRunResult, setDryRunResult] = useState<CommunicationAutomationDryRunResult | null>(
    null,
  )

  const [createKey, setCreateKey] = useState('')
  const [createName, setCreateName] = useState('')
  const [createIntent, setCreateIntent] = useState('manual_outbound')

  const selected = useMemo(
    () => items.find((x) => x.id === selectedId) || null,
    [items, selectedId],
  )

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await listCommunicationAutomationRules({ includeArchived })
      setItems(rows)
      setSelectedId((prev) => {
        if (prev && rows.some((r) => r.id === prev)) return prev
        return rows[0]?.id ?? null
      })
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_automation.errors.load', {
            defaultValue: 'Failed to load automation rules',
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
    setDryRunResult(null)
    if (!selected) {
      setVersions([])
      setDecisions([])
      return
    }
    let mounted = true
    ;(async () => {
      try {
        const [vers, decs] = await Promise.all([
          listCommunicationAutomationVersions(selected.id),
          listCommunicationAutomationDecisions(selected.id, 20),
        ])
        if (!mounted) return
        setVersions(vers)
        setDecisions(decs)
      } catch (err: unknown) {
        if (mounted) {
          setError(
            getFriendlyErrorInfo(
              err,
              t('admin.communications_automation.errors.history', {
                defaultValue: 'Failed to load history',
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

  const upsertLocal = (bundle: CommunicationAutomationRuleBundle) => {
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
      const created = await createCommunicationAutomationRule({
        key,
        name,
        intent_key,
        channel: 'email',
        conditions: {},
        triggers: [{ event_type: 'candidate.stage_changed', event_filter: {} }],
        variables_mapping: {},
      })
      upsertLocal(created)
      setCreateKey('')
      setCreateName('')
      setNotice(
        t('admin.communications_automation.notices.created', {
          defaultValue: 'Rule created',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_automation.errors.create', {
            defaultValue: 'Failed to create rule',
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
      const conditions = JSON.parse(draftForm.conditionsJson || '{}') as Record<string, unknown>
      const variables_mapping = JSON.parse(draftForm.variablesJson || '{}') as Record<
        string,
        unknown
      >
      const triggersRaw = JSON.parse(draftForm.triggersJson || '[]') as Array<{
        event_type?: string
        event_filter?: Record<string, unknown>
      }>
      if (!Array.isArray(triggersRaw)) throw new Error('triggers must be a JSON array')
      const updated = await updateCommunicationAutomationDraft(selected.id, {
        intent_key: draftForm.intent_key,
        preferred_template_key: draftForm.preferred_template_key || null,
        channel: draftForm.channel || null,
        recipient_strategy: draftForm.recipient_strategy || 'origin_primary',
        conditions,
        variables_mapping,
        triggers: triggersRaw.map((t) => ({
          event_type: String(t.event_type || '').trim(),
          event_filter: t.event_filter || {},
        })),
        clear_preferred_template_key: !draftForm.preferred_template_key.trim(),
        clear_channel: !draftForm.channel.trim(),
      })
      upsertLocal(updated)
      setNotice(
        t('admin.communications_automation.notices.draft_saved', {
          defaultValue: 'Draft saved',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_automation.errors.save_draft', {
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
      const published = await publishCommunicationAutomationRule(selected.id)
      upsertLocal(published)
      setNotice(
        t('admin.communications_automation.notices.published', {
          defaultValue: 'Published',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_automation.errors.publish', {
            defaultValue: 'Failed to publish',
          }),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const handleToggleEnabled = async () => {
    if (!selected) return
    setBusy(true)
    setError(null)
    try {
      const next = await setCommunicationAutomationRuleEnabled(selected.id, !selected.enabled)
      upsertLocal(next)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_automation.errors.enable', {
            defaultValue: 'Failed to update enabled flag',
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
    setNotice(null)
    try {
      const archived = await archiveCommunicationAutomationRule(selected.id)
      upsertLocal(archived)
      setNotice(
        t('admin.communications_automation.notices.archived', {
          defaultValue: 'Archived',
        }),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_automation.errors.archive', {
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
    try {
      const data = JSON.parse(dryRunDataJson || '{}') as Record<string, unknown>
      const result = await dryRunCommunicationAutomationRule(selected.id, {
        event_id: `ui-${Date.now()}`,
        event_type: dryRunEventType.trim() || 'candidate.stage_changed',
        data,
        version_id: selected.draft?.id || null,
      })
      setDryRunResult(result)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_automation.errors.dry_run', {
            defaultValue: 'Dry-run failed',
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
      backLabel={t('admin.communications_automation.actions.back', {
        defaultValue: '← Communications admin',
      })}
      kicker={t('admin.communications_automation.header_kicker', {
        defaultValue: 'automation',
      })}
      title={t('admin.communications_automation.title', {
        defaultValue: 'Communication automation',
      })}
      subtitle={t('admin.communications_automation.subtitle', {
        defaultValue:
          'Event → Rules → Intent only. Not legacy reminder automations and not a send path.',
      })}
      actions={
        <Link to={CRM_APP_PATHS.settingsCommunicationsTemplates} className="btn-secondary">
          {t('admin.communications_automation.actions.templates', {
            defaultValue: 'Communication templates',
          })}
        </Link>
      }
    >
      {error ? (
        <div className="mb-4">
          <ErrorRecoveryBanner error={error} onRetry={() => void refresh()} />
        </div>
      ) : null}
      {notice ? <p className="mb-3 text-sm text-emerald-700">{notice}</p> : null}

      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          Key
          <input
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={createKey}
            onChange={(e) => setCreateKey(e.target.value)}
            placeholder="follow_up_on_interview"
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
          {t('admin.communications_automation.create.submit', {
            defaultValue: 'Create draft',
          })}
        </button>
        <label className="ml-auto flex items-center gap-2 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => setIncludeArchived(e.target.checked)}
          />
          {t('admin.communications_automation.include_archived', {
            defaultValue: 'Include archived',
          })}
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <section className="rounded-lg border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('admin.communications_automation.list_title', { defaultValue: 'Rules' })}
          </div>
          {loading ? (
            <p className="p-3 text-sm text-slate-500">
              {t('common.loading', { defaultValue: 'Loading…' })}
            </p>
          ) : items.length === 0 ? (
            <p className="p-3 text-sm text-slate-500">
              {t('admin.communications_automation.empty', {
                defaultValue: 'No automation rules yet.',
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
                      {row.enabled ? ' · on' : ' · off'}
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
              {t('admin.communications_automation.select_prompt', {
                defaultValue: 'Select or create a rule.',
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
                      disabled={busy || selected.status === 'archived'}
                      onClick={() => void handleToggleEnabled()}
                    >
                      {selected.enabled ? 'Disable' : 'Enable'}
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
                    Recipient strategy
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.recipient_strategy}
                      onChange={(e) =>
                        setDraftForm((f) => ({
                          ...f,
                          recipient_strategy: e.target.value,
                        }))
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    Conditions (JSON)
                    <textarea
                      className="min-h-[100px] rounded border border-slate-300 px-2 py-1 font-mono text-xs"
                      value={draftForm.conditionsJson}
                      onChange={(e) =>
                        setDraftForm((f) => ({ ...f, conditionsJson: e.target.value }))
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    Variables mapping (JSON)
                    <textarea
                      className="min-h-[80px] rounded border border-slate-300 px-2 py-1 font-mono text-xs"
                      value={draftForm.variablesJson}
                      onChange={(e) =>
                        setDraftForm((f) => ({ ...f, variablesJson: e.target.value }))
                      }
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    Triggers (JSON array)
                    <textarea
                      className="min-h-[100px] rounded border border-slate-300 px-2 py-1 font-mono text-xs"
                      value={draftForm.triggersJson}
                      onChange={(e) =>
                        setDraftForm((f) => ({ ...f, triggersJson: e.target.value }))
                      }
                    />
                  </label>
                </div>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="mb-2 text-sm font-semibold text-slate-900">Dry-run</h3>
                <div className="mb-3 grid gap-3 md:grid-cols-[180px_1fr_auto]">
                  <input
                    className="rounded border border-slate-300 px-2 py-1 text-sm"
                    value={dryRunEventType}
                    onChange={(e) => setDryRunEventType(e.target.value)}
                    placeholder="event_type"
                  />
                  <textarea
                    className="min-h-[80px] rounded border border-slate-300 px-2 py-1 font-mono text-xs"
                    value={dryRunDataJson}
                    onChange={(e) => setDryRunDataJson(e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn-secondary btn-sm h-fit"
                    disabled={busy}
                    onClick={() => void handleDryRun()}
                  >
                    Run
                  </button>
                </div>
                {dryRunResult ? (
                  <pre className="overflow-auto rounded bg-slate-50 p-2 text-xs text-slate-800">
                    {JSON.stringify(dryRunResult, null, 2)}
                  </pre>
                ) : null}
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="mb-2 text-sm font-semibold text-slate-900">Versions</h3>
                <div className="overflow-auto">
                  <table className="min-w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-slate-500">
                        <th className="px-2 py-1">#</th>
                        <th className="px-2 py-1">Status</th>
                        <th className="px-2 py-1">Intent</th>
                        <th className="px-2 py-1">Published</th>
                      </tr>
                    </thead>
                    <tbody>
                      {versions.map((v) => (
                        <tr key={v.id} className="border-b border-slate-50">
                          <td className="px-2 py-1">{v.version_number}</td>
                          <td className="px-2 py-1">{v.status}</td>
                          <td className="px-2 py-1">{v.intent_key}</td>
                          <td className="px-2 py-1">{v.published_at || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="mb-2 text-sm font-semibold text-slate-900">
                  Recent decisions
                </h3>
                {decisions.length === 0 ? (
                  <p className="text-xs text-slate-500">No decisions yet (dry-run does not persist).</p>
                ) : (
                  <div className="overflow-auto">
                    <table className="min-w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-100 text-left text-slate-500">
                          <th className="px-2 py-1">Outcome</th>
                          <th className="px-2 py-1">Event</th>
                          <th className="px-2 py-1">Reasons</th>
                          <th className="px-2 py-1">At</th>
                        </tr>
                      </thead>
                      <tbody>
                        {decisions.map((d) => (
                          <tr key={d.id} className="border-b border-slate-50">
                            <td className="px-2 py-1">{d.outcome}</td>
                            <td className="px-2 py-1">{d.event_type}</td>
                            <td className="px-2 py-1">{(d.reason_codes || []).join(', ')}</td>
                            <td className="px-2 py-1">{d.created_at || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </SettingsSubpageHeader>
  )
}
