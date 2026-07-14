import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  activateRulesetVersion,
  createRulesetVersion,
  getRuleset,
  getRulesetDiff,
  getRulesetUsage,
  listRulesetVersions,
  rollbackRulesetVersion,
} from '../../api/documents'
import type { RulesetDiff, RulesetUsageResponse, RulesetVersion } from '../../api/types'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useI18n } from '../../i18n'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary } from '../../utils/friendlyError'

function formatDate(value?: string | null): string {
  if (!value) return '—'
  const timestamp = Date.parse(value)
  if (Number.isNaN(timestamp)) return value
  return new Date(timestamp).toLocaleString()
}

function toPrettyJson(source: Record<string, any> | null | undefined): string {
  try {
    return JSON.stringify(source ?? {}, null, 2)
  } catch (error) {
    return JSON.stringify({ error: 'Unable to stringify payload', raw: source }, null, 2)
  }
}

type DiffState = {
  versionId: string | null
  payload: RulesetDiff | null
  loading: boolean
  error: string | null
}

const INITIAL_DIFF: DiffState = { versionId: null, payload: null, loading: false, error: null }

export default function RulesetVersionsPage() {
  const { t } = useI18n()
  const [versions, setVersions] = useState<RulesetVersion[]>([])
  const [active, setActive] = useState<RulesetVersion | null>(null)
  const [draftJson, setDraftJson] = useState<string>('')
  const [draftComment, setDraftComment] = useState<string>('')
  const [draftActivate, setDraftActivate] = useState<boolean>(false)
  const [prefilled, setPrefilled] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [diffState, setDiffState] = useState<DiffState>(INITIAL_DIFF)
  const [usage, setUsage] = useState<RulesetUsageResponse | null>(null)
  const [usageLoading, setUsageLoading] = useState<boolean>(false)
  const [usageError, setUsageError] = useState<string | null>(null)

  const summarizeError = useCallback((err: any): string => {
    if (!err) return t('app.admin.ruleset.errors.unknown')
    if (typeof err === 'string') return err
    const response = err.response
    if (response?.data) {
      const data = response.data
      if (typeof data === 'string') return data
      if (typeof data.detail === 'string') return data.detail
      if (Array.isArray(data.detail)) {
        return data.detail.map((item: any) => item?.msg || item?.message || JSON.stringify(item)).join('; ')
      }
      if (typeof data.message === 'string') return data.message
    }
    if (err.message) return err.message
    return t('app.admin.ruleset.errors.request_failed')
  }, [t])

  const refreshVersions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [current, list] = await Promise.all([
        getRuleset(),
        listRulesetVersions(),
      ])
      setActive(current)
      setVersions(list)
      if (!prefilled) {
        setDraftJson(toPrettyJson(current.ruleset))
        setPrefilled(true)
      }
    } catch (err) {
      setError(summarizeError(err))
    } finally {
      setLoading(false)
    }
  }, [prefilled])

  const refreshUsage = useCallback(async () => {
    setUsageLoading(true)
    setUsageError(null)
    try {
      const data = await getRulesetUsage({ limit: 50 })
      setUsage(data)
    } catch (err) {
      setUsageError(summarizeError(err))
    } finally {
      setUsageLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshVersions()
    refreshUsage()
  }, [refreshVersions, refreshUsage])

  const handleCreateDraft = async () => {
    setError(null)
    try {
      const parsed = JSON.parse(draftJson || '{}')
      const payload = {
        ruleset: parsed,
        comment: draftComment || undefined,
        activate: draftActivate,
      }
      await createRulesetVersion(payload)
      setDraftComment('')
      if (!draftActivate) {
        setDraftActivate(false)
      }
      setDiffState(INITIAL_DIFF)
      setPrefilled(false)
      await refreshVersions()
      await refreshUsage()
    } catch (err) {
      setError(summarizeError(err))
    }
  }

  const handleActivate = async (version: RulesetVersion) => {
    if (!window.confirm(t('app.admin.ruleset.actions.confirm_activate', { values: { version: version.version } }))) return
    try {
      await activateRulesetVersion(version.id)
      setDiffState(INITIAL_DIFF)
      setPrefilled(false)
      await refreshVersions()
    } catch (err) {
      setError(summarizeError(err))
    }
  }

  const handleRollback = async (version: RulesetVersion) => {
    const comment = window.prompt(
      t('app.admin.ruleset.actions.rollback_prompt', { values: { version: version.version } }),
      t('app.admin.ruleset.actions.rollback_default_comment'),
    )
    if (!comment || comment.trim().length < 3) {
      if (comment !== null) {
        setError(t('app.admin.ruleset.errors.comment_short'))
      }
      return
    }
    try {
      await rollbackRulesetVersion(version.id, { comment: comment.trim() })
      setDiffState(INITIAL_DIFF)
      setPrefilled(false)
      await refreshVersions()
      await refreshUsage()
    } catch (err) {
      setError(summarizeError(err))
    }
  }

  const handleShowDiff = async (version: RulesetVersion) => {
    setDiffState({ versionId: version.id, payload: null, loading: true, error: null })
    try {
      const payload = await getRulesetDiff(version.id)
      setDiffState({ versionId: version.id, payload, loading: false, error: null })
    } catch (err) {
      setDiffState({ versionId: version.id, payload: null, loading: false, error: summarizeError(err) })
    }
  }

  const handleUseAsDraft = (version: RulesetVersion) => {
    setDraftJson(toPrettyJson(version.ruleset))
    setDraftComment(version.comment ?? '')
    setDraftActivate(false)
  }

  const diffSummary = useMemo(() => {
    const summary = diffState.payload?.diff?.summary
    if (!summary) return null
    return {
      added: summary.added ?? 0,
      removed: summary.removed ?? 0,
      changed: summary.changed ?? 0,
    }
  }, [diffState])

  const rulesetLoadErrorBanner = useMemo<FriendlyErrorInfo | null>(
    () =>
      error
        ? {
            title: error,
            hint: t('app.common.retry_hint'),
          }
        : null,
    [error, t],
  )
  const rulesetUsageErrorBanner = useMemo<FriendlyErrorInfo | null>(
    () =>
      usageError
        ? {
            title: usageError,
            hint: t('app.common.retry_hint'),
          }
        : null,
    [usageError, t],
  )

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.settings.subpage.back_all')}
      kicker={t('app.admin.ruleset.header.kicker')}
      title={t('app.admin.ruleset.header.title')}
      subtitle={t('app.admin.ruleset.header.subtitle')}
      actions={
        <div className="flex gap-2">
          <button type="button" className="btn-secondary" onClick={refreshVersions} disabled={loading}>
            {loading ? t('app.admin.ruleset.header.refresh.loading') : t('app.admin.ruleset.header.refresh.action')}
          </button>
          <button type="button" className="btn-secondary" onClick={refreshUsage} disabled={usageLoading}>
            {usageLoading
              ? t('app.admin.ruleset.header.usage_refresh.loading')
              : t('app.admin.ruleset.header.usage_refresh.action')}
          </button>
        </div>
      }
    >

      {rulesetLoadErrorBanner && (
        <ErrorRecoveryBanner
          info={rulesetLoadErrorBanner}
          onRetry={refreshVersions}
          retryLabel={t('app.admin.ruleset.header.refresh.action')}
          {...friendlyErrorBannerSecondary(
            rulesetLoadErrorBanner,
            CRM_APP_PATHS.settingsRuleset,
            t('app.admin.ruleset.header.title'),
          )}
          compact
        />
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-medium text-slate-900">{t('app.admin.ruleset.create.title')}</h2>
        <p className="mt-1 text-sm text-slate-500">
          {t('app.admin.ruleset.create.description')}
        </p>

        <div className="mt-4 space-y-4">
          <div>
            <label htmlFor="ruleset-json" className="mb-1 block text-sm font-medium text-slate-700">
              {t('app.admin.ruleset.create.json_label')}
            </label>
            <textarea
              id="ruleset-json"
              className="textarea font-mono"
              rows={12}
              value={draftJson}
              onChange={(event) => setDraftJson(event.target.value)}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-[2fr_1fr]">
            <div>
              <label htmlFor="ruleset-comment" className="mb-1 block text-sm font-medium text-slate-700">
                {t('app.admin.ruleset.create.comment_label')}
              </label>
              <input
                id="ruleset-comment"
                className="input"
                placeholder={t('app.admin.ruleset.create.comment_placeholder')}
                value={draftComment}
                onChange={(event) => setDraftComment(event.target.value)}
              />
            </div>
            <label className="mt-6 flex items-start gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={draftActivate}
                onChange={(event) => setDraftActivate(event.target.checked)}
              />
              <span>{t('app.admin.ruleset.create.activate_toggle')}</span>
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary"
              onClick={handleCreateDraft}
            >
              {t('app.admin.ruleset.create.save')}
            </button>
            {active && (
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleUseAsDraft(active)}
              >
                {t('app.admin.ruleset.create.copy_active')}
              </button>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-medium text-slate-900">{t('app.admin.ruleset.history.title')}</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                <th className="px-3 py-2">{t('app.admin.ruleset.history.columns.version')}</th>
                <th className="px-3 py-2">{t('app.admin.ruleset.history.columns.status')}</th>
                <th className="px-3 py-2">{t('app.admin.ruleset.history.columns.comment')}</th>
                <th className="px-3 py-2">{t('app.admin.ruleset.history.columns.signature')}</th>
                <th className="px-3 py-2">{t('app.admin.ruleset.history.columns.author')}</th>
                <th className="px-3 py-2">{t('app.admin.ruleset.history.columns.created')}</th>
                <th className="px-3 py-2">{t('app.admin.ruleset.history.columns.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {versions.map((version) => (
                <tr
                  key={version.id}
                  className={version.is_active ? 'bg-brand-50/40' : ''}
                >
                  <td className="px-3 py-2 font-medium text-slate-900">v{version.version}</td>
                  <td className="px-3 py-2">
                    {version.is_active ? (
                      <span className="rounded-md bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">
                        {t('app.admin.ruleset.history.status.active')}
                      </span>
                    ) : (
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                        {t('app.admin.ruleset.history.status.draft')}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {version.comment || <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-slate-600">
                    {version.signature.slice(0, 12)}…
                  </td>
                  <td className="px-3 py-2 text-slate-600">{version.created_by || '—'}</td>
                  <td className="px-3 py-2 text-slate-600">{formatDate(version.created_at)}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        className="btn-secondary btn-xs"
                        onClick={() => handleUseAsDraft(version)}
                      >
                        {t('app.admin.ruleset.history.actions.use_as_draft')}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary btn-xs"
                        onClick={() => handleShowDiff(version)}
                      >
                        {t('app.admin.ruleset.history.actions.diff')}
                      </button>
                      {!version.is_active && (
                        <button
                          type="button"
                          className="btn-secondary btn-xs"
                          onClick={() => handleActivate(version)}
                        >
                          {t('app.admin.ruleset.history.actions.activate')}
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn-danger btn-xs"
                        onClick={() => handleRollback(version)}
                      >
                        {t('app.admin.ruleset.history.actions.rollback')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {versions.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-4 text-center text-sm text-slate-500">
                    {t('app.admin.ruleset.history.empty')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {diffState.versionId && (
        <section className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-indigo-900">
                {t('app.admin.ruleset.diff.title', {
                  values: { version: versions.find((v) => v.id === diffState.versionId)?.version ?? '' },
                })}
              </h2>
              <p className="text-sm text-indigo-700">
                {diffState.payload?.computed_with
                  ? t('app.admin.ruleset.diff.subtitle_engine', { values: { engine: diffState.payload.computed_with } })
                  : t('app.admin.ruleset.diff.subtitle_previous')}
              </p>
            </div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => setDiffState(INITIAL_DIFF)}
            >
              {t('common.actions.close')}
            </button>
          </div>

          {diffState.loading && <p className="mt-3 text-sm text-indigo-700">{t('app.admin.ruleset.diff.loading')}</p>}
          {diffState.error && (
            <div className="mt-3">
              <ErrorRecoveryBanner
                info={{
                  title: diffState.error,
                  hint: t('app.common.retry_hint'),
                }}
                onRetry={() => {
                  if (!diffState.versionId) return
                  const version = versions.find((item) => item.id === diffState.versionId)
                  if (version) void handleShowDiff(version)
                }}
                retryLabel={t('common.actions.retry')}
                compact
              />
            </div>
          )}
          {!diffState.loading && diffState.payload && (
            <div className="mt-4 space-y-4 text-sm">
              {diffSummary && (
                <div className="flex flex-wrap gap-4 text-indigo-900">
                  <span>{t('app.admin.ruleset.diff.summary.added', { values: { count: diffSummary.added } })}</span>
                  <span>{t('app.admin.ruleset.diff.summary.removed', { values: { count: diffSummary.removed } })}</span>
                  <span>{t('app.admin.ruleset.diff.summary.changed', { values: { count: diffSummary.changed } })}</span>
                </div>
              )}
              <div className="grid gap-4 md:grid-cols-3">
                <DiffList
                  title={t('app.admin.ruleset.diff.lists.added')}
                  entries={diffState.payload?.diff?.added}
                  emptyLabel={t('app.admin.ruleset.diff.list_empty')}
                />
                <DiffList
                  title={t('app.admin.ruleset.diff.lists.removed')}
                  entries={diffState.payload?.diff?.removed}
                  emptyLabel={t('app.admin.ruleset.diff.list_empty')}
                />
                <DiffList
                  title={t('app.admin.ruleset.diff.lists.changed')}
                  entries={diffState.payload?.diff?.changed}
                  emptyLabel={t('app.admin.ruleset.diff.list_empty')}
                />
              </div>
            </div>
          )}
        </section>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium text-slate-900">{t('app.admin.ruleset.usage.title')}</h2>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={refreshUsage}
            disabled={usageLoading}
          >
            {usageLoading ? t('app.admin.ruleset.usage.refresh.loading') : t('app.admin.ruleset.usage.refresh.action')}
          </button>
        </div>
        {rulesetUsageErrorBanner && (
          <div className="mt-3">
            <ErrorRecoveryBanner
              info={rulesetUsageErrorBanner}
              onRetry={refreshUsage}
              retryLabel={t('app.admin.ruleset.usage.refresh.action')}
              {...friendlyErrorBannerSecondary(
                rulesetUsageErrorBanner,
                CRM_APP_PATHS.settingsRuleset,
                t('app.admin.ruleset.usage.title'),
              )}
              compact
            />
          </div>
        )}
        {!usageLoading && usage && (
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            <div>
              <h3 className="font-medium text-slate-900">{t('app.admin.ruleset.usage.summary_title')}</h3>
              <div className="mt-2 flex flex-wrap gap-3">
                {Object.entries(usage.summary || {}).map(([key, value]) => (
                  <span key={key} className="badge">
                    {key}: {value}
                  </span>
                ))}
                {Object.keys(usage.summary || {}).length === 0 && (
                  <span className="text-xs text-slate-500">{t('app.admin.ruleset.usage.summary_empty')}</span>
                )}
              </div>
            </div>
            <div>
              <h3 className="font-medium text-slate-900">{t('app.admin.ruleset.usage.events_title')}</h3>
              <ul className="mt-2 space-y-2">
                {(usage.items || []).slice(0, 10).map((item) => (
                  <li key={item.id} className="rounded border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-800">{item.used_in}</span>
                      <span>v{versions.find((v) => v.id === item.ruleset_version_id)?.version ?? item.ruleset_version_id}</span>
                      {item.reference_id && (
                        <span>{t('app.admin.ruleset.usage.event_ref', { values: { ref: item.reference_id } })}</span>
                      )}
                      <span>{formatDate(item.used_at)}</span>
                    </div>
                    {item.meta && Object.keys(item.meta).length > 0 && (
                      <pre className="mt-1 overflow-auto rounded bg-white/70 p-2 text-[11px] leading-snug text-slate-700">
                        {JSON.stringify(item.meta, null, 2)}
                      </pre>
                    )}
                  </li>
                ))}
                {(usage.items || []).length === 0 && (
                  <li className="text-xs text-slate-500">{t('app.admin.ruleset.usage.events_empty')}</li>
                )}
              </ul>
            </div>
          </div>
        )}
      </section>
    </SettingsSubpageHeader>
  )
}

function DiffList({ title, entries, emptyLabel }: { title: string; entries?: Record<string, any> | null; emptyLabel: string }) {
  const pairs = useMemo(() => {
    if (!entries) return []
    return Object.entries(entries)
  }, [entries])

  if (pairs.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-700">
        <h3 className="mb-2 font-medium text-slate-900">{title}</h3>
        <p className="text-slate-500">{emptyLabel}</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-700">
      <h3 className="mb-2 font-medium text-slate-900">{title}</h3>
      <ul className="space-y-1">
        {pairs.map(([key, value]) => (
          <li key={key}>
            <span className="font-semibold text-slate-900">{key}</span>
            <pre className="mt-1 overflow-auto rounded bg-slate-50 px-2 py-1 text-[11px] leading-snug text-slate-700">
              {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
            </pre>
          </li>
        ))}
      </ul>
    </div>
  )
}
