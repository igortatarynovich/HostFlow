/**
 * C2.1 PR-5 — thin Template Platform UI over `/communications/templates`.
 * No client-side composition, channel policy, or versioning rules.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  archiveCommunicationTemplate,
  createCommunicationTemplate,
  diffCommunicationTemplateVersions,
  listCommunicationTemplates,
  listCommunicationTemplateVersions,
  previewCommunicationTemplate,
  publishCommunicationTemplate,
  updateCommunicationTemplateDraft,
  type CommunicationTemplateBundle,
  type CommunicationTemplateDiff,
  type CommunicationTemplatePreviewResult,
  type CommunicationTemplateVariable,
  type CommunicationTemplateVersion,
} from '../../api/communications/templates'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { useI18n } from '../../i18n'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { getFriendlyErrorInfo } from '../../utils/friendlyError'

type DraftForm = {
  subject: string
  body_text: string
  body_html: string
  locale: string
  channels: string
  intent_keys: string
  variablesJson: string
}

function draftFromBundle(bundle: CommunicationTemplateBundle | null): DraftForm {
  const d = bundle?.draft
  return {
    subject: d?.subject ?? '',
    body_text: d?.body_text ?? '',
    body_html: d?.body_html ?? '',
    locale: d?.locale ?? 'pl',
    channels: (d?.channels || ['email']).join(', '),
    intent_keys: (d?.intent_keys || []).join(', '),
    variablesJson: JSON.stringify(
      (d?.variables || []).map((v) => ({
        name: v.name,
        var_type: v.var_type,
        required: Boolean(v.required),
        description: v.description ?? null,
        default_value: v.default_value ?? null,
      })),
      null,
      2,
    ),
  }
}

function parseCsv(value: string): string[] {
  return value
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
}

function parseVariables(raw: string, invalidMessage: string): CommunicationTemplateVariable[] {
  const parsed = JSON.parse(raw || '[]')
  if (!Array.isArray(parsed)) throw new Error(invalidMessage)
  return parsed.map((row) => ({
    name: String(row?.name || '').trim(),
    var_type: String(row?.var_type || 'string').trim() || 'string',
    required: row?.required !== false,
    description: row?.description ?? null,
    default_value: row?.default_value ?? null,
  }))
}

export default function CommunicationTemplatesPage() {
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [includeArchived, setIncludeArchived] = useState(false)
  const [items, setItems] = useState<CommunicationTemplateBundle[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [draftForm, setDraftForm] = useState<DraftForm>(draftFromBundle(null))
  const [versions, setVersions] = useState<CommunicationTemplateVersion[]>([])
  const [diffFrom, setDiffFrom] = useState('')
  const [diffTo, setDiffTo] = useState('')
  const [diffResult, setDiffResult] = useState<CommunicationTemplateDiff | null>(null)
  const [previewVarsJson, setPreviewVarsJson] = useState('{\n  "name": "Ada"\n}')
  const [previewChannel, setPreviewChannel] = useState('email')
  const [previewResult, setPreviewResult] = useState<CommunicationTemplatePreviewResult | null>(null)

  const [createKey, setCreateKey] = useState('')
  const [createName, setCreateName] = useState('')

  const selected = useMemo(
    () => items.find((x) => x.id === selectedId) || null,
    [items, selectedId],
  )

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await listCommunicationTemplates({ includeArchived })
      setItems(rows)
      setSelectedId((prev) => {
        if (prev && rows.some((r) => r.id === prev)) return prev
        return rows[0]?.id ?? null
      })
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_templates.errors.load'),
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
    setPreviewResult(null)
    setDiffResult(null)
    if (!selected) {
      setVersions([])
      return
    }
    let mounted = true
    ;(async () => {
      try {
        const rows = await listCommunicationTemplateVersions(selected.id)
        if (!mounted) return
        setVersions(rows)
        const published = rows.filter((v) => v.status === 'published')
        if (published.length >= 2) {
          setDiffFrom(published[published.length - 2].id)
          setDiffTo(published[published.length - 1].id)
        } else if (published.length === 1) {
          setDiffFrom(published[0].id)
          setDiffTo(published[0].id)
        } else {
          setDiffFrom('')
          setDiffTo('')
        }
      } catch (err: unknown) {
        if (mounted) {
          setError(
            getFriendlyErrorInfo(
              err,
              t('admin.communications_templates.errors.versions'),
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

  const upsertLocal = (bundle: CommunicationTemplateBundle) => {
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
    if (!key) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const created = await createCommunicationTemplate({
        key,
        name,
        locale: 'pl',
        subject: 'Hello {{name}}',
        body_text: 'Hi {{name}}',
        channels: ['email'],
        variables: [{ name: 'name', var_type: 'string', required: true }],
      })
      upsertLocal(created)
      setCreateKey('')
      setCreateName('')
      setNotice(
        t('admin.communications_templates.notices.created'),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_templates.errors.create'),
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
      const variables = parseVariables(
        draftForm.variablesJson,
        t('admin.communications_templates.errors.variables_json'),
      )
      const updated = await updateCommunicationTemplateDraft(selected.id, {
        subject: draftForm.subject,
        body_text: draftForm.body_text,
        body_html: draftForm.body_html || null,
        locale: draftForm.locale || 'pl',
        channels: parseCsv(draftForm.channels),
        intent_keys: parseCsv(draftForm.intent_keys),
        variables,
      })
      upsertLocal(updated)
      setNotice(
        t('admin.communications_templates.notices.draft_saved'),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_templates.errors.save_draft'),
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
      const published = await publishCommunicationTemplate(selected.id)
      upsertLocal(published)
      setNotice(
        t('admin.communications_templates.notices.published'),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_templates.errors.publish'),
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
      const archived = await archiveCommunicationTemplate(selected.id)
      upsertLocal(archived)
      setNotice(
        t('admin.communications_templates.notices.archived'),
      )
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_templates.errors.archive'),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const handlePreview = async () => {
    if (!selected) return
    setBusy(true)
    setError(null)
    try {
      const variables = JSON.parse(previewVarsJson || '{}') as Record<string, unknown>
      const result = await previewCommunicationTemplate(selected.id, {
        variables,
        channel: previewChannel || 'email',
        version_id: selected.draft?.id || null,
      })
      setPreviewResult(result)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_templates.errors.preview'),
          t,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  const handleDiff = async () => {
    if (!selected || !diffFrom || !diffTo) return
    setBusy(true)
    setError(null)
    try {
      const result = await diffCommunicationTemplateVersions(selected.id, diffFrom, diffTo)
      setDiffResult(result)
    } catch (err: unknown) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.communications_templates.errors.diff'),
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
      backLabel={t('admin.communications_templates.actions.back')}
      kicker={t('admin.communications_templates.header_kicker')}
      title={t('admin.communications_templates.title')}
      subtitle={t('admin.communications_templates.subtitle')}
      actions={
        <Link to={CRM_APP_PATHS.settingsCommunicationsMessengers} className="btn-secondary">
          {t('admin.communications_templates.actions.messenger_snippets')}
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
          {t('admin.communications_templates.create.key')}
          <input
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={createKey}
            onChange={(e) => setCreateKey(e.target.value)}
            placeholder="welcome_email"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-600">
          {t('admin.communications_templates.create.name')}
          <input
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            placeholder={t('admin.communications_templates.create.name_placeholder')}
          />
        </label>
        <button type="button" className="btn-primary btn-sm" disabled={busy || !createKey.trim()} onClick={() => void handleCreate()}>
          {t('admin.communications_templates.create.submit')}
        </button>
        <label className="ml-auto flex items-center gap-2 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(e) => setIncludeArchived(e.target.checked)}
          />
          {t('admin.communications_templates.include_archived')}
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <section className="rounded-lg border border-slate-200 bg-white">
          <div className="border-b border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('admin.communications_templates.list_title')}
          </div>
          {loading ? (
            <p className="p-3 text-sm text-slate-500">
              {t('common.loading')}
            </p>
          ) : items.length === 0 ? (
            <p className="p-3 text-sm text-slate-500">
              {t('admin.communications_templates.empty')}
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
                        ? t('admin.communications_templates.list.version', {
                            version: row.latest_published.version_number,
                          })
                        : t('admin.communications_templates.list.draft_only')}
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
              {t('admin.communications_templates.select_prompt')}
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
                    <button type="button" className="btn-secondary btn-sm" disabled={busy} onClick={() => void handleSaveDraft()}>
                      {t('admin.communications_templates.actions.save_draft')}
                    </button>
                    <button type="button" className="btn-primary btn-sm" disabled={busy} onClick={() => void handlePublish()}>
                      {t('admin.communications_templates.actions.publish')}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      disabled={busy || selected.status === 'archived'}
                      onClick={() => void handleArchive()}
                    >
                      {t('admin.communications_templates.actions.archive')}
                    </button>
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    {t('admin.communications_templates.fields.subject')}
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.subject}
                      onChange={(e) => setDraftForm((f) => ({ ...f, subject: e.target.value }))}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    {t('admin.communications_templates.fields.body_text')}
                    <textarea
                      className="min-h-[120px] rounded border border-slate-300 px-2 py-1 font-mono text-sm"
                      value={draftForm.body_text}
                      onChange={(e) => setDraftForm((f) => ({ ...f, body_text: e.target.value }))}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    {t('admin.communications_templates.fields.body_html')}
                    <textarea
                      className="min-h-[80px] rounded border border-slate-300 px-2 py-1 font-mono text-sm"
                      value={draftForm.body_html}
                      onChange={(e) => setDraftForm((f) => ({ ...f, body_html: e.target.value }))}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600">
                    {t('admin.communications_templates.fields.locale')}
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.locale}
                      onChange={(e) => setDraftForm((f) => ({ ...f, locale: e.target.value }))}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600">
                    {t('admin.communications_templates.fields.channels')}
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.channels}
                      onChange={(e) => setDraftForm((f) => ({ ...f, channels: e.target.value }))}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    {t('admin.communications_templates.fields.intent_keys')}
                    <input
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={draftForm.intent_keys}
                      onChange={(e) => setDraftForm((f) => ({ ...f, intent_keys: e.target.value }))}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600 md:col-span-2">
                    {t('admin.communications_templates.fields.variables')}
                    <textarea
                      className="min-h-[120px] rounded border border-slate-300 px-2 py-1 font-mono text-xs"
                      value={draftForm.variablesJson}
                      onChange={(e) =>
                        setDraftForm((f) => ({ ...f, variablesJson: e.target.value }))
                      }
                    />
                  </label>
                </div>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="mb-2 text-sm font-semibold text-slate-900">
                  {t('admin.communications_templates.preview_title')}
                </h3>
                <div className="mb-3 grid gap-3 md:grid-cols-[1fr_140px_auto]">
                  <textarea
                    className="min-h-[80px] rounded border border-slate-300 px-2 py-1 font-mono text-xs"
                    value={previewVarsJson}
                    onChange={(e) => setPreviewVarsJson(e.target.value)}
                  />
                  <input
                    className="rounded border border-slate-300 px-2 py-1 text-sm"
                    value={previewChannel}
                    onChange={(e) => setPreviewChannel(e.target.value)}
                    placeholder="email"
                  />
                  <button type="button" className="btn-secondary btn-sm h-fit" disabled={busy} onClick={() => void handlePreview()}>
                    {t('admin.communications_templates.actions.preview')}
                  </button>
                </div>
                {previewResult ? (
                  <div className="space-y-2 text-sm">
                    <p className="text-xs text-slate-500">
                      {t('admin.communications_templates.preview.meta', {
                        ok: String(previewResult.ok),
                        version: previewResult.template_version_id,
                      })}
                    </p>
                    <pre className="overflow-auto rounded bg-slate-50 p-2 text-xs text-slate-800">
                      {t('admin.communications_templates.preview.rendered', {
                        subject: previewResult.subject ?? '',
                        body: previewResult.body_text ?? '',
                      })}
                    </pre>
                    {(previewResult.diagnostics || []).length > 0 ? (
                      <ul className="text-xs text-amber-800">
                        {(previewResult.diagnostics || []).map((d, idx) => (
                          <li key={`${d.code}-${idx}`}>
                            [{d.severity || 'info'}] {d.code}: {d.message}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="mb-2 text-sm font-semibold text-slate-900">
                  {t('admin.communications_templates.history_title')}
                </h3>
                <div className="overflow-auto">
                  <table className="min-w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 text-left text-slate-500">
                        <th className="px-2 py-1">{t('admin.communications_templates.history.col_number')}</th>
                        <th className="px-2 py-1">{t('common.labels.status')}</th>
                        <th className="px-2 py-1">{t('admin.communications_templates.history.col_locale')}</th>
                        <th className="px-2 py-1">{t('admin.communications_templates.history.col_published')}</th>
                        <th className="px-2 py-1">{t('common.labels.id')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {versions.map((v) => (
                        <tr key={v.id} className="border-b border-slate-50">
                          <td className="px-2 py-1">{v.version_number}</td>
                          <td className="px-2 py-1">{v.status}</td>
                          <td className="px-2 py-1">{v.locale}</td>
                          <td className="px-2 py-1">{v.published_at || t('common.labels.not_available')}</td>
                          <td className="px-2 py-1 font-mono">{v.id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 flex flex-wrap items-end gap-2">
                  <label className="flex flex-col gap-1 text-xs text-slate-600">
                    {t('admin.communications_templates.history.from')}
                    <select
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={diffFrom}
                      onChange={(e) => setDiffFrom(e.target.value)}
                    >
                      <option value="">{t('common.labels.not_available')}</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          {t('admin.communications_templates.history.version_option', {
                            version: v.version_number,
                            status: v.status,
                          })}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-slate-600">
                    {t('admin.communications_templates.history.to')}
                    <select
                      className="rounded border border-slate-300 px-2 py-1 text-sm"
                      value={diffTo}
                      onChange={(e) => setDiffTo(e.target.value)}
                    >
                      <option value="">{t('common.labels.not_available')}</option>
                      {versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          {t('admin.communications_templates.history.version_option', {
                            version: v.version_number,
                            status: v.status,
                          })}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button type="button" className="btn-secondary btn-sm" disabled={busy || !diffFrom || !diffTo} onClick={() => void handleDiff()}>
                    {t('admin.communications_templates.history.diff')}
                  </button>
                </div>
                {diffResult ? (
                  <pre className="mt-3 overflow-auto rounded bg-slate-50 p-2 text-xs text-slate-800">
                    {JSON.stringify(diffResult, null, 2)}
                  </pre>
                ) : null}
              </section>
            </>
          )}
        </div>
      </div>
    </SettingsSubpageHeader>
  )
}
