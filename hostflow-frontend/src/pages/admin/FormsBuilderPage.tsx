import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  IconArrowDown,
  IconArrowUp,
  IconDeviceFloppy,
  IconForms,
  IconPlus,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react'
import { useI18n } from '../../i18n'
import { usePermissions } from '../../hooks/usePermissions'
import ErrorRecoveryBanner from '../../components/ErrorRecoveryBanner'
import { SettingsSubpageHeader } from '../../components/settings/SettingsSubpageHeader'
import { useToast } from '../../components/Toast'
import { CRM_APP_PATHS } from '../../app/crmAppPaths'
import { getIntakeFormDetail } from '../../api/intakeForms'
import {
  fetchBuilderComponent,
  fetchBuilderPalette,
  fetchFormBuilderDraft,
  isDraftRevisionConflict,
  newInstanceId,
  saveFormBuilderDraft,
  type BuilderComponentView,
  type BuilderPaletteItem,
  type CompositionInstance,
  type FormComposition,
} from '../../api/formsBuilder'
import {
  friendlyErrorBannerSecondary,
  getFriendlyErrorInfo,
  type FriendlyErrorInfo,
} from '../../utils/friendlyError'

function emptyComposition(draftId: string): FormComposition {
  return {
    contract: 'forms.builder.composition.v1',
    draft_id: draftId,
    instances: [],
  }
}

function labelFor(item: { label_key?: string | null; component_id: string }, t: (k: string, o?: object) => string) {
  if (item.label_key) {
    return t(item.label_key, { defaultValue: item.component_id })
  }
  return item.component_id
}

export default function FormsBuilderPage() {
  const { formId = '' } = useParams<{ formId: string }>()
  const { t } = useI18n()
  const { role } = usePermissions()
  const { notify } = useToast()
  const canMutate = role === 'administrator'

  const [palette, setPalette] = useState<BuilderPaletteItem[]>([])
  const [search, setSearch] = useState('')
  const [composition, setComposition] = useState<FormComposition | null>(null)
  const [savedSnapshot, setSavedSnapshot] = useState<string>('')
  const [revision, setRevision] = useState(0)
  const [exists, setExists] = useState(false)
  const [builderState, setBuilderState] = useState<string | undefined>()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [descriptor, setDescriptor] = useState<BuilderComponentView | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [conflict, setConflict] = useState(false)
  const [pageError, setPageError] = useState<FriendlyErrorInfo | null>(null)
  const [formTitle, setFormTitle] = useState('')

  const dirty = useMemo(() => {
    if (!composition) return false
    return JSON.stringify(composition) !== savedSnapshot
  }, [composition, savedSnapshot])

  const selected = useMemo(
    () => composition?.instances.find((i) => i.instance_id === selectedId) || null,
    [composition, selectedId],
  )

  const loadPalette = useCallback(async (q: string) => {
    const items = await fetchBuilderPalette(q.trim() ? { query: q.trim() } : undefined)
    setPalette(items)
  }, [])

  const loadDraft = useCallback(async () => {
    if (!formId) return
    setPageError(null)
    setConflict(false)
    try {
      setLoading(true)
      const draft = await fetchFormBuilderDraft(formId)
      const comp = draft.composition || emptyComposition(draft.draft_id)
      setComposition(comp)
      setSavedSnapshot(JSON.stringify(comp))
      setRevision(draft.revision)
      setExists(draft.exists)
      setBuilderState(draft.builder_state)
      setSelectedId(comp.instances[0]?.instance_id ?? null)
      await loadPalette('')
      try {
        const detail = await getIntakeFormDetail(formId)
        setFormTitle(String(detail.form?.title || '').trim())
      } catch {
        setFormTitle('')
      }
    } catch (err: unknown) {
      setPageError(
        getFriendlyErrorInfo(
          err,
          t('admin.forms_builder.errors.load', { defaultValue: 'Failed to load Builder draft' }),
          t,
        ),
      )
      setComposition(null)
    } finally {
      setLoading(false)
    }
  }, [formId, loadPalette, t])

  useEffect(() => {
    void loadDraft()
  }, [loadDraft])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadPalette(search).catch(() => undefined)
    }, 200)
    return () => window.clearTimeout(handle)
  }, [search, loadPalette])

  useEffect(() => {
    if (!selected) {
      setDescriptor(null)
      return
    }
    let cancelled = false
    void fetchBuilderComponent(selected.component_id, selected.component_version)
      .then((view) => {
        if (!cancelled) setDescriptor(view)
      })
      .catch(() => {
        if (!cancelled) setDescriptor(null)
      })
    return () => {
      cancelled = true
    }
  }, [selected])

  const addComponent = (item: BuilderPaletteItem) => {
    if (!composition || !canMutate) return
    const inst: CompositionInstance = {
      instance_id: newInstanceId(),
      component_id: item.component_id,
      component_version: item.component_version,
      config: {},
    }
    setComposition({
      ...composition,
      instances: [...composition.instances, inst],
    })
    setSelectedId(inst.instance_id)
  }

  const removeSelected = () => {
    if (!composition || !selectedId || !canMutate) return
    const next = composition.instances.filter((i) => i.instance_id !== selectedId)
    setComposition({ ...composition, instances: next })
    setSelectedId(next[0]?.instance_id ?? null)
  }

  const moveSelected = (delta: number) => {
    if (!composition || !selectedId || !canMutate) return
    const idx = composition.instances.findIndex((i) => i.instance_id === selectedId)
    if (idx < 0) return
    const to = idx + delta
    if (to < 0 || to >= composition.instances.length) return
    const items = [...composition.instances]
    const [row] = items.splice(idx, 1)
    items.splice(to, 0, row)
    setComposition({ ...composition, instances: items })
  }

  const updateSelectedConfig = (key: string, value: unknown) => {
    if (!composition || !selectedId || !canMutate) return
    setComposition({
      ...composition,
      instances: composition.instances.map((inst) =>
        inst.instance_id === selectedId
          ? { ...inst, config: { ...inst.config, [key]: value } }
          : inst,
      ),
    })
  }

  const save = async () => {
    if (!formId || !composition || !canMutate) return
    setSaving(true)
    setPageError(null)
    setConflict(false)
    try {
      const payload = {
        composition,
        expected_revision: exists ? revision : null,
      }
      const saved = await saveFormBuilderDraft(formId, payload)
      setComposition(saved.composition)
      setSavedSnapshot(JSON.stringify(saved.composition))
      setRevision(saved.revision)
      setExists(true)
      setBuilderState(saved.builder_state)
      notify({
        variant: 'success',
        title: t('admin.forms_builder.saved', { defaultValue: 'Draft saved' }),
      })
    } catch (err: unknown) {
      if (isDraftRevisionConflict(err)) {
        setConflict(true)
        setBuilderState('conflict')
        notify({
          variant: 'error',
          title: t('admin.forms_builder.conflict', {
            defaultValue: 'Revision conflict — reload the server draft to continue.',
          }),
        })
      } else {
        setPageError(
          getFriendlyErrorInfo(
            err,
            t('admin.forms_builder.errors.save', { defaultValue: 'Failed to save draft' }),
            t,
          ),
        )
      }
    } finally {
      setSaving(false)
    }
  }

  const backHref = CRM_APP_PATHS.settingsLeadForms

  return (
    <SettingsSubpageHeader
      backLabel={t('admin.forms_builder.back', { defaultValue: 'All forms' })}
      backHref={backHref}
      kicker={t('admin.forms_builder.kicker', { defaultValue: 'Forms' })}
      title={
        <span className="inline-flex items-center gap-2">
          <IconForms size={22} stroke={1.9} className="text-brand-600" />
          {formTitle || t('admin.forms_builder.title', { defaultValue: 'Form Builder' })}
        </span>
      }
      subtitle={t('admin.forms_builder.subtitle', {
        defaultValue: 'Palette from Field Catalog · canvas order · properties · save draft.',
      })}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              dirty ? 'bg-amber-100 text-amber-900' : 'bg-slate-100 text-slate-600'
            }`}
          >
            {dirty
              ? t('admin.forms_builder.dirty', { defaultValue: 'Unsaved changes' })
              : t('admin.forms_builder.clean', { defaultValue: 'Saved' })}
          </span>
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
            rev {revision}
            {builderState ? ` · ${builderState}` : ''}
          </span>
          <button
            type="button"
            className="btn btn-secondary inline-flex items-center gap-1.5"
            onClick={() => void loadDraft()}
            disabled={loading}
          >
            <IconRefresh size={16} />
            {t('admin.forms_builder.reload', { defaultValue: 'Reload' })}
          </button>
          {canMutate && (
            <button
              type="button"
              className="btn btn-primary inline-flex items-center gap-1.5"
              onClick={() => void save()}
              disabled={loading || saving || !dirty || conflict}
            >
              <IconDeviceFloppy size={16} />
              {saving
                ? t('common.saving', { defaultValue: 'Saving…' })
                : t('admin.forms_builder.save', { defaultValue: 'Save draft' })}
            </button>
          )}
        </div>
      }
    >
      <section className="settings-panel">
        {pageError && (
          <div className="mb-4">
            <ErrorRecoveryBanner
              info={pageError}
              {...friendlyErrorBannerSecondary(
                pageError,
                backHref,
                t('admin.forms_builder.back', { defaultValue: 'All forms' }),
              )}
            />
          </div>
        )}

        {conflict && (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            <p className="font-medium">
              {t('admin.forms_builder.conflict_title', {
                defaultValue: 'Server draft changed (revision conflict)',
              })}
            </p>
            <p className="mt-1 text-amber-900/80">
              {t('admin.forms_builder.conflict_help', {
                defaultValue: 'Reload to take the server tip, then re-apply your edits.',
              })}
            </p>
            <button
              type="button"
              className="btn btn-secondary mt-3"
              onClick={() => void loadDraft()}
            >
              {t('admin.forms_builder.reload_server', { defaultValue: 'Reload server draft' })}
            </button>
          </div>
        )}

        {loading || !composition ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : (
          <div className="grid gap-4 xl:grid-cols-[240px_minmax(0,1fr)_280px]">
            {/* Palette */}
            <aside className="rounded-xl border border-slate-200 bg-white p-3">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('admin.forms_builder.palette', { defaultValue: 'Palette' })}
              </h3>
              <input
                className="mt-2 w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t('admin.forms_builder.search', { defaultValue: 'Search components…' })}
              />
              <ul className="mt-3 max-h-[60vh] space-y-1 overflow-auto">
                {palette.map((item) => (
                  <li key={`${item.component_id}@${item.component_version}`}>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-slate-50 disabled:opacity-50"
                      disabled={!canMutate}
                      onClick={() => addComponent(item)}
                    >
                      <span className="min-w-0 truncate font-medium text-slate-800">
                        {labelFor(item, t)}
                      </span>
                      <IconPlus size={14} className="shrink-0 text-slate-400" />
                    </button>
                    <p className="px-2 pb-1 font-mono text-[10px] text-slate-400">
                      {item.component_id}@{item.component_version}
                    </p>
                  </li>
                ))}
                {palette.length === 0 && (
                  <li className="px-2 py-3 text-xs text-slate-500">
                    {t('admin.forms_builder.palette_empty', { defaultValue: 'No components' })}
                  </li>
                )}
              </ul>
            </aside>

            {/* Canvas */}
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('admin.forms_builder.canvas', { defaultValue: 'Canvas' })}
                </h3>
                <div className="flex gap-1">
                  <button
                    type="button"
                    className="btn btn-secondary !px-2 !py-1"
                    disabled={!canMutate || !selectedId}
                    onClick={() => moveSelected(-1)}
                    title="Move up"
                  >
                    <IconArrowUp size={14} />
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary !px-2 !py-1"
                    disabled={!canMutate || !selectedId}
                    onClick={() => moveSelected(1)}
                    title="Move down"
                  >
                    <IconArrowDown size={14} />
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary !px-2 !py-1"
                    disabled={!canMutate || !selectedId}
                    onClick={removeSelected}
                    title="Remove"
                  >
                    <IconTrash size={14} />
                  </button>
                </div>
              </div>
              {composition.instances.length === 0 ? (
                <p className="rounded-lg border border-dashed border-slate-200 px-3 py-8 text-center text-sm text-slate-500">
                  {t('admin.forms_builder.canvas_empty', {
                    defaultValue: 'Add components from the palette.',
                  })}
                </p>
              ) : (
                <ol className="space-y-1">
                  {composition.instances.map((inst, index) => (
                    <li key={inst.instance_id}>
                      <button
                        type="button"
                        className={`flex w-full items-start gap-3 rounded-lg border px-3 py-2 text-left text-sm ${
                          selectedId === inst.instance_id
                            ? 'border-brand-300 bg-brand-50/50'
                            : 'border-slate-100 hover:border-slate-200'
                        }`}
                        onClick={() => setSelectedId(inst.instance_id)}
                      >
                        <span className="mt-0.5 font-mono text-xs text-slate-400">{index + 1}</span>
                        <span className="min-w-0 flex-1">
                          <span className="block font-medium text-slate-800">
                            {String(inst.config.label || inst.component_id)}
                          </span>
                          <span className="font-mono text-[10px] text-slate-400">
                            {inst.component_id}@{inst.component_version}
                          </span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </div>

            {/* Properties */}
            <aside className="rounded-xl border border-slate-200 bg-white p-3">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('admin.forms_builder.properties', { defaultValue: 'Properties' })}
              </h3>
              {!selected ? (
                <p className="mt-3 text-sm text-slate-500">
                  {t('admin.forms_builder.select_instance', {
                    defaultValue: 'Select a canvas instance.',
                  })}
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  <p className="font-mono text-[10px] text-slate-400">
                    {selected.component_id}@{selected.component_version}
                  </p>
                  {(descriptor?.config_fields || []).map((field) => {
                    const value = selected.config[field.key]
                    const label = field.label_key
                      ? t(field.label_key, { defaultValue: field.key })
                      : field.key
                    if (field.value_type === 'boolean') {
                      return (
                        <label key={field.key} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={Boolean(value)}
                            disabled={!canMutate}
                            onChange={(e) => updateSelectedConfig(field.key, e.target.checked)}
                          />
                          <span>{label}</span>
                        </label>
                      )
                    }
                    if (field.value_type === 'enum' && field.enum_values) {
                      return (
                        <label key={field.key} className="block text-sm">
                          <span className="mb-1 block text-slate-600">{label}</span>
                          <select
                            className="w-full rounded-lg border border-slate-200 px-2 py-1.5"
                            disabled={!canMutate}
                            value={String(value ?? '')}
                            onChange={(e) => updateSelectedConfig(field.key, e.target.value)}
                          >
                            <option value="">—</option>
                            {field.enum_values.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        </label>
                      )
                    }
                    if (field.value_type === 'number') {
                      return (
                        <label key={field.key} className="block text-sm">
                          <span className="mb-1 block text-slate-600">{label}</span>
                          <input
                            type="number"
                            className="w-full rounded-lg border border-slate-200 px-2 py-1.5"
                            disabled={!canMutate}
                            value={value === undefined || value === null ? '' : String(value)}
                            onChange={(e) =>
                              updateSelectedConfig(
                                field.key,
                                e.target.value === '' ? null : Number(e.target.value),
                              )
                            }
                          />
                        </label>
                      )
                    }
                    return (
                      <label key={field.key} className="block text-sm">
                        <span className="mb-1 block text-slate-600">{label}</span>
                        <input
                          type="text"
                          className="w-full rounded-lg border border-slate-200 px-2 py-1.5"
                          disabled={!canMutate}
                          value={value === undefined || value === null ? '' : String(value)}
                          onChange={(e) => updateSelectedConfig(field.key, e.target.value)}
                        />
                      </label>
                    )
                  })}
                  {descriptor && descriptor.config_fields.length === 0 && (
                    <p className="text-xs text-slate-500">
                      {t('admin.forms_builder.no_config', {
                        defaultValue: 'No config_fields on this component.',
                      })}
                    </p>
                  )}
                </div>
              )}
            </aside>
          </div>
        )}

        <p className="mt-4 text-xs text-slate-500">
          <Link className="text-brand-700 underline" to={backHref}>
            {t('admin.forms_builder.back', { defaultValue: 'All forms' })}
          </Link>
          {' · '}
          {t('admin.forms_builder.no_publish', {
            defaultValue: 'Save draft only — publish remains a separate action (P3 locked).',
          })}
        </p>
      </section>
    </SettingsSubpageHeader>
  )
}
