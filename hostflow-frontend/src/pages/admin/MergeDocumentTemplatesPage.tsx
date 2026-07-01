import { useCallback, useEffect, useMemo, useState } from 'react'
import { useI18n } from '../../i18n'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import type { FriendlyErrorInfo } from '../../utils/friendlyError'
import { friendlyErrorBannerSecondary, getFriendlyErrorInfo } from '../../utils/friendlyError'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import {
  createMergeDocumentTemplate,
  deleteMergeDocumentTemplate,
  listMergeDocumentTemplates,
  patchMergeDocumentTemplate,
  type MergeDocumentTemplate,
} from '../../api/documentMergeTemplates'

export default function MergeDocumentTemplatesPage() {
  const { t } = useI18n()
  const [templates, setTemplates] = useState<MergeDocumentTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FriendlyErrorInfo | null>(null)
  const [includeInactive, setIncludeInactive] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draftCode, setDraftCode] = useState('')
  const [draftName, setDraftName] = useState('')
  const [draftBody, setDraftBody] = useState('')
  const [draftMime, setDraftMime] = useState('text/plain')
  const [draftOc, setDraftOc] = useState('')
  const [draftFilenamePattern, setDraftFilenamePattern] = useState('')
  const [draftBindings, setDraftBindings] = useState('')
  const [saving, setSaving] = useState(false)

  const loadTemplates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await listMergeDocumentTemplates({ include_inactive: includeInactive })
      setTemplates(rows)
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.documents.merge.error_load'),
          t,
        ),
      )
    } finally {
      setLoading(false)
    }
  }, [includeInactive, t])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates])

  const sorted = useMemo(
    () =>
      [...templates].sort((a, b) => {
        if (a.is_active !== b.is_active) return a.is_active ? -1 : 1
        return String(a.code || '').localeCompare(String(b.code || ''))
      }),
    [templates],
  )

  const resetDraft = () => {
    setDraftCode('')
    setDraftName('')
    setDraftBody('')
    setDraftMime('text/plain')
    setDraftOc('')
    setDraftFilenamePattern('')
    setDraftBindings('')
    setEditingId(null)
  }

  const startEdit = (row: MergeDocumentTemplate) => {
    setEditingId(row.id)
    setDraftCode(row.code)
    setDraftName(row.name)
    setDraftBody(row.body_text)
    setDraftMime(row.output_mime || 'text/plain')
    setDraftOc(row.own_company_id || '')
    setDraftFilenamePattern(row.output_filename_pattern || '')
    setDraftBindings(row.variable_bindings ? JSON.stringify(row.variable_bindings, null, 2) : '')
  }

  const parseBindings = (): Record<string, unknown> | undefined => {
    const raw = draftBindings.trim()
    if (!raw) return undefined
    try {
      const parsed = JSON.parse(raw) as unknown
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>
      }
      throw new Error('not_object')
    } catch {
      throw new Error(t('admin.documents.merge.bindings_invalid'))
    }
  }

  const saveCurrent = async () => {
    setSaving(true)
    setError(null)
    try {
      const bindings = draftBindings.trim() ? parseBindings() : undefined
      const oc = draftOc.trim() || null
      if (editingId) {
        await patchMergeDocumentTemplate(editingId, {
          code: draftCode.trim(),
          name: draftName.trim(),
          body_text: draftBody,
          output_mime: draftMime.trim() || 'text/plain',
          own_company_id: oc,
          output_filename_pattern: draftFilenamePattern.trim() || null,
          variable_bindings: bindings ?? null,
        })
      } else {
        await createMergeDocumentTemplate({
          code: draftCode.trim(),
          name: draftName.trim(),
          body_text: draftBody,
          output_mime: draftMime.trim() || 'text/plain',
          own_company_id: oc,
          output_filename_pattern: draftFilenamePattern.trim() || null,
          variable_bindings: bindings,
        })
      }
      resetDraft()
      await loadTemplates()
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.documents.merge.error_save'),
          t,
        ),
      )
    } finally {
      setSaving(false)
    }
  }

  const onDelete = async (id: string) => {
    if (!window.confirm(t('admin.documents.merge.confirm_delete'))) {
      return
    }
    setError(null)
    try {
      await deleteMergeDocumentTemplate(id)
      if (editingId === id) resetDraft()
      await loadTemplates()
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.documents.merge.error_delete'),
          t,
        ),
      )
    }
  }

  const toggleActive = async (row: MergeDocumentTemplate) => {
    setError(null)
    try {
      await patchMergeDocumentTemplate(row.id, { is_active: !row.is_active })
      await loadTemplates()
    } catch (err) {
      setError(
        getFriendlyErrorInfo(
          err,
          t('admin.documents.merge.error_save'),
          t,
        ),
      )
    }
  }

  return (
    <div className="space-y-4">
      <section className="settings-panel">
        <div className="mb-2">
          <SettingsSubpageHeader
            backLabel={t('admin.settings.subpage.back_all')}
            kicker={t('admin.documents.merge.header_kicker')}
            title={t('admin.documents.merge.title')}
            subtitle={t('admin.documents.merge.description')}
          />
        </div>

        <label className="mb-3 flex cursor-pointer items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
          />
          {t('admin.documents.merge.include_inactive')}
        </label>

        {error ? (
          <ErrorRecoveryBanner
            info={error}
            onRetry={loadTemplates}
            retryLabel={t('common.actions.retry')}
            {...friendlyErrorBannerSecondary(
              error,
              CRM_APP_PATHS.settingsMergeTemplates,
              t('admin.documents.merge.title'),
            )}
            compact
          />
        ) : null}

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500">
                <th className="px-3 py-2 font-medium">{t('admin.documents.merge.table.code')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.merge.table.name')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.merge.table.oc')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.merge.table.mime')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.merge.table.status')}</th>
                <th className="px-3 py-2 font-medium">{t('admin.documents.merge.table.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr className="border-t">
                  <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                    {t('common.loading')}
                  </td>
                </tr>
              ) : null}
              {!loading && !sorted.length ? (
                <tr className="border-t">
                  <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                    {t('admin.documents.merge.empty')}
                  </td>
                </tr>
              ) : null}
              {!loading
                ? sorted.map((row) => (
                    <tr key={row.id} className="border-t">
                      <td className="px-3 py-2 font-mono text-xs uppercase text-slate-600">{row.code}</td>
                      <td className="px-3 py-2">{row.name}</td>
                      <td className="max-w-[140px] truncate px-3 py-2 font-mono text-xs text-slate-500">
                        {row.own_company_id || '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-600">{row.output_mime}</td>
                      <td className="px-3 py-2">
                        {row.is_active ? (
                          <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                            {t('common.active')}
                          </span>
                        ) : (
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                            {t('common.inactive')}
                          </span>
                        )}
                      </td>
                      <td className="space-x-2 px-3 py-2">
                        <button
                          type="button"
                          className="text-xs text-indigo-600 hover:underline"
                          onClick={() => startEdit(row)}
                        >
                          {t('common.actions.edit')}
                        </button>
                        <button
                          type="button"
                          className="text-xs text-slate-600 hover:underline"
                          onClick={() => toggleActive(row)}
                        >
                          {row.is_active ? t('admin.documents.merge.deactivate') : t('admin.documents.merge.activate')}
                        </button>
                        <button
                          type="button"
                          className="text-xs text-red-600 hover:underline"
                          onClick={() => onDelete(row.id)}
                        >
                          {t('common.actions.delete')}
                        </button>
                      </td>
                    </tr>
                  ))
                : null}
            </tbody>
          </table>
        </div>

        <div className="mt-6 space-y-3 rounded-lg border border-slate-200 bg-slate-50/80 p-4">
          <h3 className="text-sm font-semibold text-slate-800">
            {editingId ? t('admin.documents.merge.form_edit_title') : t('admin.documents.merge.form_new_title')}
          </h3>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="block text-xs font-medium text-slate-600">
              {t('admin.documents.merge.field_code')}
              <input
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={draftCode}
                onChange={(e) => setDraftCode(e.target.value)}
                disabled={Boolean(editingId)}
              />
            </label>
            <label className="block text-xs font-medium text-slate-600">
              {t('admin.documents.merge.field_name')}
              <input
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
              />
            </label>
            <label className="block text-xs font-medium text-slate-600">
              {t('admin.documents.merge.field_mime')}
              <input
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={draftMime}
                onChange={(e) => setDraftMime(e.target.value)}
              />
            </label>
            <label className="block text-xs font-medium text-slate-600">
              {t('admin.documents.merge.field_oc')}
              <input
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm font-mono text-xs"
                value={draftOc}
                onChange={(e) => setDraftOc(e.target.value)}
              />
            </label>
          </div>
          <label className="block text-xs font-medium text-slate-600">
            {t('admin.documents.merge.field_filename')}
            <input
              className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm font-mono text-xs"
              value={draftFilenamePattern}
              onChange={(e) => setDraftFilenamePattern(e.target.value)}
              placeholder="{{ candidate.last_name }}_contract.txt"
            />
          </label>
          <label className="block text-xs font-medium text-slate-600">
            {t('admin.documents.merge.field_bindings')}
            <textarea
              className="mt-1 w-full rounded border border-slate-200 px-2 py-2 font-mono text-xs"
              rows={4}
              value={draftBindings}
              onChange={(e) => setDraftBindings(e.target.value)}
              placeholder='{"signing.city": "Warsaw"}'
            />
          </label>
          <label className="block text-xs font-medium text-slate-600">
            {t('admin.documents.merge.field_body')}
            <textarea
              className="mt-1 w-full rounded border border-slate-200 px-2 py-2 font-mono text-xs"
              rows={12}
              value={draftBody}
              onChange={(e) => setDraftBody(e.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary btn-sm disabled:opacity-50"
              disabled={saving || !draftCode.trim() || !draftName.trim() || !draftBody.trim()}
              onClick={() => saveCurrent()}
            >
              {saving ? t('common.saving') : t('common.actions.save')}
            </button>
            <button type="button" className="btn-secondary btn-sm" onClick={resetDraft}>
              {t('common.actions.cancel')}
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
