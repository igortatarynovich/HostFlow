import { useCallback, useEffect, useMemo, useState } from 'react'
import { IconDeviceFloppy, IconPlayerPlay, IconPlus, IconTrash, IconWand } from '@tabler/icons-react'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'
import { intakePresentationFieldLabel } from '../../utils/intakePresentationI18n'
import { useToast } from '../../components/Toast'
import { CRM_APP_PATHS, marketingSourceMappingPath } from '../../app/crmAppPaths'
import {
  getEntityProfileFields,
  getIntakeFormMapping,
  previewIntakeFormMapping,
  putIntakeFormMapping,
  testIntakeFormMappingIngest,
  type EntityProfileFieldOption,
  type IntakeFormMappingPreviewResult,
  type IntakeFormMappingTestResult,
  type MappingRuleInput,
} from '../../api/intakeForms'
import { legacyTargetFromQualified } from '../../utils/intakeMappingUtils'

export type MappingRowDraft = {
  id: string
  source: string
  qualified_field_code: string
  format: 'string' | 'lower' | 'upper' | 'csv'
}

const DEFAULT_SAMPLE = `{
  "first_name": "Anna",
  "phone_number": "+48123456789",
  "email": "anna@example.com"
}`

function newRowId(): string {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `row-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function sourceToText(source: string | string[]): string {
  if (Array.isArray(source)) return source.join(', ')
  return String(source || '')
}

function rulesToRows(rules: MappingRuleInput[]): MappingRowDraft[] {
  return rules.map((rule) => ({
    id: newRowId(),
    source: sourceToText(rule.source),
    qualified_field_code: String(rule.qualified_field_code || '').trim(),
    format: (rule.format as MappingRowDraft['format']) || 'string',
  }))
}

function rowsToRules(rows: MappingRowDraft[]): MappingRuleInput[] {
  return rows
    .filter((row) => row.source.trim() && row.qualified_field_code.trim())
    .map((row) => {
      const qualified = row.qualified_field_code.trim()
      return {
        source: row.source.trim(),
        qualified_field_code: qualified,
        target: legacyTargetFromQualified(qualified) || undefined,
        format: row.format,
        overwrite: true,
      }
    })
}

type Props = {
  formId: string
  entityProfileCode: string
  disabled?: boolean
}

export function IntakeFormMappingEditor({ formId, entityProfileCode, disabled = false }: Props) {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const [loading, setLoading] = useState(true)
  const [provider, setProvider] = useState('')
  const [workspaceSourceId, setWorkspaceSourceId] = useState<string | null>(null)
  const [profileFields, setProfileFields] = useState<EntityProfileFieldOption[]>([])
  const [rows, setRows] = useState<MappingRowDraft[]>([])
  const [sampleJson, setSampleJson] = useState(DEFAULT_SAMPLE)
  const [saving, setSaving] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [testing, setTesting] = useState(false)
  const [preview, setPreview] = useState<IntakeFormMappingPreviewResult | null>(null)
  const [testResult, setTestResult] = useState<IntakeFormMappingTestResult | null>(null)

  const mappingRules = useMemo(() => rowsToRules(rows), [rows])

  const load = useCallback(async () => {
    if (!formId || !entityProfileCode) return
    setLoading(true)
    try {
      const [ctx, fieldsPayload] = await Promise.all([
        getIntakeFormMapping(formId),
        getEntityProfileFields(entityProfileCode),
      ])
      setProvider(ctx.provider)
      setWorkspaceSourceId(ctx.intake_source_profile_id)
      setProfileFields(fieldsPayload.fields)
      setRows(rulesToRows(ctx.mapping_rules || []))
    } catch {
      notify({
        title: t('admin.intake_forms.errors.load_mapping', { defaultValue: 'Failed to load mapping' }),
        variant: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [entityProfileCode, formId, notify, t])

  useEffect(() => {
    void load()
  }, [load])

  const parseSample = (): Record<string, unknown> | null => {
    try {
      const parsed = JSON.parse(sampleJson) as unknown
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('object expected')
      }
      return parsed as Record<string, unknown>
    } catch {
      notify({
        title: t('admin.intake_forms.errors.sample_json', { defaultValue: 'Sample payload must be valid JSON object' }),
        variant: 'error',
      })
      return null
    }
  }

  const saveMapping = async () => {
    if (disabled || !formId) return
    setSaving(true)
    setPreview(null)
    setTestResult(null)
    try {
      const updated = await putIntakeFormMapping(formId, { mapping_rules: mappingRules })
      setRows(rulesToRows(updated.mapping_rules || []))
      notify({
        title: t('admin.intake_forms.toast.mapping_saved', { defaultValue: 'Provider mapping saved' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('admin.intake_forms.errors.save_mapping', { defaultValue: 'Failed to save mapping' }),
        variant: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const runPreview = async () => {
    if (disabled || !formId) return
    const sample = parseSample()
    if (!sample) return
    setPreviewing(true)
    setPreview(null)
    setTestResult(null)
    try {
      const result = await previewIntakeFormMapping(formId, {
        sample_payload: sample,
        mapping_rules: mappingRules,
      })
      setPreview(result)
      if (result.source_fields.length > 0) {
        setRows((prev) => {
          const existing = new Set(prev.map((row) => row.source.trim().toLowerCase()))
          const additions = result.source_fields
            .filter((field) => !existing.has(field.source.trim().toLowerCase()))
            .map((field) => ({
              id: newRowId(),
              source: field.source,
              qualified_field_code: '',
              format: 'string' as const,
            }))
          return additions.length ? [...prev, ...additions] : prev
        })
      }
    } catch {
      notify({
        title: t('admin.intake_forms.errors.preview_mapping', { defaultValue: 'Mapping preview failed' }),
        variant: 'error',
      })
    } finally {
      setPreviewing(false)
    }
  }

  const runTestIngest = async () => {
    if (disabled || !formId) return
    const sample = parseSample()
    if (!sample) return
    setTesting(true)
    setTestResult(null)
    try {
      const result = await testIntakeFormMappingIngest(formId, {
        sample_payload: sample,
        mapping_rules: mappingRules,
      })
      setTestResult(result)
      notify({
        title: t('admin.intake_forms.toast.mapping_test_ok', { defaultValue: 'Test lead draft created from mapping' }),
        variant: 'success',
      })
    } catch {
      notify({
        title: t('admin.intake_forms.errors.test_mapping', { defaultValue: 'Mapping test ingest failed' }),
        variant: 'error',
      })
    } finally {
      setTesting(false)
    }
  }

  const addRow = () => {
    setRows((prev) => [...prev, { id: newRowId(), source: '', qualified_field_code: '', format: 'string' }])
  }

  const removeRow = (id: string) => {
    setRows((prev) => prev.filter((row) => row.id !== id))
  }

  if (loading) {
    return <p className="text-sm text-slate-500">{t('common.loading')}</p>
  }

  if (workspaceSourceId) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm" data-testid="intake-form-mapping-workspace">
        <p className="text-slate-700">
          {t('admin.intake_forms.mapping_workspace.body', {
            defaultValue: 'Edit mapping for this form in the Mapping workspace — one editor for every intake source.',
          })}
        </p>
        <Link
          className="btn-primary btn-sm mt-3 inline-flex"
          to={marketingSourceMappingPath(workspaceSourceId)}
        >
          {t('admin.intake_forms.mapping_workspace.open', { defaultValue: 'Open mapping' })}
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        {t('admin.intake_forms.mapping_hint', {
          defaultValue:
            'Map provider source fields to Entity Profile qualified_code only. Mapping does not create canonical fields.',
        })}
        {provider ? (
          <span className="ml-2 font-mono text-slate-600">
            {t('admin.intake_forms.mapping_provider', { defaultValue: 'Provider' })}: {provider}
          </span>
        ) : null}
      </p>

      <div className="overflow-x-auto rounded-xl border border-slate-100">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-500">
              <th className="px-2 py-2">{t('admin.intake_forms.columns.source_field', { defaultValue: 'Source field' })}</th>
              <th className="px-2 py-2">{t('admin.intake_forms.columns.target_field', { defaultValue: 'Target (Entity Profile)' })}</th>
              <th className="px-2 py-2">{t('admin.intake_forms.columns.format', { defaultValue: 'Format' })}</th>
              <th className="px-2 py-2" />
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-2 py-4 text-sm text-slate-500">
                  {t('admin.intake_forms.mapping_empty', { defaultValue: 'No mapping rules yet. Add a row or run preview with sample JSON.' })}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-b border-slate-50">
                  <td className="px-2 py-2">
                    <input
                      className="w-full min-w-[140px] rounded-lg border border-slate-200 px-2 py-1 font-mono text-xs"
                      value={row.source}
                      disabled={disabled}
                      placeholder="first_name"
                      onChange={(event) =>
                        setRows((prev) =>
                          prev.map((item) => (item.id === row.id ? { ...item, source: event.target.value } : item)),
                        )
                      }
                    />
                  </td>
                  <td className="px-2 py-2">
                    <select
                      className="w-full min-w-[220px] rounded-lg border border-slate-200 px-2 py-1 text-sm"
                      value={row.qualified_field_code}
                      disabled={disabled}
                      onChange={(event) =>
                        setRows((prev) =>
                          prev.map((item) =>
                            item.id === row.id ? { ...item, qualified_field_code: event.target.value } : item,
                          ),
                        )
                      }
                    >
                      <option value="">
                        {t('admin.intake_forms.mapping_select_target', { defaultValue: 'Select target field…' })}
                      </option>
                      {profileFields.map((field) => (
                        <option key={field.qualified_code} value={field.qualified_code}>
                          {intakePresentationFieldLabel(t, field, locale)} ({field.qualified_code})
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-2 py-2">
                    <select
                      className="rounded-lg border border-slate-200 px-2 py-1 text-sm"
                      value={row.format}
                      disabled={disabled}
                      onChange={(event) =>
                        setRows((prev) =>
                          prev.map((item) =>
                            item.id === row.id
                              ? { ...item, format: event.target.value as MappingRowDraft['format'] }
                              : item,
                          ),
                        )
                      }
                    >
                      <option value="string">string</option>
                      <option value="lower">lower</option>
                      <option value="upper">upper</option>
                      <option value="csv">csv</option>
                    </select>
                  </td>
                  <td className="px-2 py-2">
                    <button
                      type="button"
                      className="rounded border border-slate-200 p-1 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                      disabled={disabled}
                      onClick={() => removeRow(row.id)}
                    >
                      <IconTrash size={14} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-secondary inline-flex items-center gap-1 text-sm" disabled={disabled} onClick={addRow}>
          <IconPlus size={14} />
          {t('admin.intake_forms.mapping_add_row', { defaultValue: 'Add row' })}
        </button>
        <button
          type="button"
          className="btn-primary inline-flex items-center gap-2"
          disabled={disabled || saving}
          onClick={() => void saveMapping()}
        >
          <IconDeviceFloppy size={16} />
          {saving ? t('common.loading') : t('admin.intake_forms.save_mapping', { defaultValue: 'Save mapping' })}
        </button>
      </div>

      <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
        <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('admin.intake_forms.sections.sample_payload', { defaultValue: 'Sample raw payload' })}
        </label>
        <textarea
          className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-mono text-xs"
          rows={6}
          value={sampleJson}
          disabled={disabled}
          onChange={(event) => setSampleJson(event.target.value)}
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary inline-flex items-center gap-2"
            disabled={disabled || previewing}
            onClick={() => void runPreview()}
          >
            <IconWand size={16} />
            {previewing ? t('common.loading') : t('admin.intake_forms.preview_mapping', { defaultValue: 'Preview normalized' })}
          </button>
          <button
            type="button"
            className="btn-primary inline-flex items-center gap-2"
            disabled={disabled || testing || mappingRules.length === 0}
            onClick={() => void runTestIngest()}
          >
            <IconPlayerPlay size={16} />
            {testing ? t('common.loading') : t('admin.intake_forms.test_mapping', { defaultValue: 'Test ingest (Lead draft)' })}
          </button>
        </div>
      </div>

      {preview && (
        <div className="rounded-xl border border-brand-100 bg-brand-50/30 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
            {t('admin.intake_forms.sections.normalized_preview', { defaultValue: 'Normalized payload preview' })}
          </h4>
          <p className="mt-1 text-xs text-slate-500">
            {t('admin.intake_forms.mapping_preview_meta', {
              defaultValue: 'Accepted rules: {{count}}',
              count: String((preview.mapping_validation as { accepted_count?: number }).accepted_count ?? 0),
            })}
          </p>
          <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-800">
            {JSON.stringify(preview.normalized_payload, null, 2)}
          </pre>
          {preview.source_fields.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-medium text-slate-600">
                {t('admin.intake_forms.discovered_sources', { defaultValue: 'Discovered source fields' })}
              </p>
              <ul className="mt-1 list-disc pl-5 text-xs text-slate-600">
                {preview.source_fields.map((field) => (
                  <li key={field.source}>
                    <span className="font-mono">{field.source}</span>
                    {field.sample_value ? ` — ${field.sample_value}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {testResult && (
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4 text-sm">
          <p className="font-medium text-emerald-900">{testResult.message}</p>
          <dl className="mt-2 grid gap-1 text-xs text-emerald-950 sm:grid-cols-2">
            <div>
              <dt className="text-emerald-700">lead_id</dt>
              <dd className="font-mono">{testResult.lead_id}</dd>
            </div>
            <div>
              <dt className="text-emerald-700">candidate_id</dt>
              <dd className="font-mono">{testResult.candidate_id ?? 'null'}</dd>
            </div>
          </dl>
          {testResult.lead_id && (
            <Link
              to={`${CRM_APP_PATHS.leads}/${testResult.lead_id}`}
              className="mt-2 inline-block text-xs font-medium text-brand-700 hover:underline"
            >
              {t('admin.intake_forms.open_lead', { defaultValue: 'Open lead' })}
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
