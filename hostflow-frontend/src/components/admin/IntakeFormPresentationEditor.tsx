import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { IconArrowDown, IconArrowUp, IconDeviceFloppy } from '@tabler/icons-react'
import { useI18n, type LocaleCode } from '../../i18n'
import { useToast } from '../../components/Toast'
import {
  getEntityProfileFields,
  getEntityProfilePresentationPreset,
  listIntakeFormEntityProfiles,
  type EntityProfileFieldOption,
  type PresentationFieldInput,
} from '../../api/intakeForms'
import { intakePresentationFieldLabel, intakePresentationProfileTitle } from '../../utils/intakePresentationI18n'
import { entityProfileLabel } from '../../utils/intakeFormRoutingSummary'
import {
  fieldAnswersHint,
  fieldTypeLabel,
  fieldsToPayload,
  looksLikeI18nKey,
  mergeCatalogWithPreset,
  slugifyFieldCodeFromLabel,
  type PresentationFieldDraft,
} from '../../utils/intakeFormPresentationDraft'

import type { PresentationRules } from '../../utils/presentationRules'

export type { PresentationFieldDraft }

const RULE_KEYS = ['show_if', 'hide_if', 'required_if', 'readonly_if'] as const

const SERVICE_SALES_PROFILE_PREFIX = 'service_sales.'

type Props = {
  entityProfileCode: string
  initialFields?: PresentationFieldDraft[]
  onEntityProfileChange?: (code: string) => void
  onChange: (fields: PresentationFieldInput[]) => void
  disabled?: boolean
  hideProfileSelect?: boolean
  autoLoadPreset?: boolean
  variant?: 'full' | 'wizard'
  displayLocale?: LocaleCode
}

export function IntakeFormPresentationEditor({
  entityProfileCode,
  initialFields,
  onEntityProfileChange,
  onChange,
  disabled = false,
  hideProfileSelect = false,
  autoLoadPreset = false,
  variant = 'full',
  displayLocale,
}: Props) {
  const { t, locale } = useI18n()
  const { notify } = useToast()
  const labelLocale = displayLocale || locale
  const [profiles, setProfiles] = useState<Array<{ code: string; name: string }>>([])
  const [profileCode, setProfileCode] = useState(entityProfileCode)
  const [catalog, setCatalog] = useState<EntityProfileFieldOption[]>([])
  const [rows, setRows] = useState<PresentationFieldDraft[]>(initialFields ?? [])
  const [loading, setLoading] = useState(true)
  const [loadingPreset, setLoadingPreset] = useState(false)
  const autoLoadedFor = useRef<string | null>(null)
  const pendingPresetRef = useRef<PresentationFieldInput[] | null>(null)
  const compact = variant === 'wizard'

  const catalogLabel = useCallback(
    (field: Pick<EntityProfileFieldOption, 'qualified_code' | 'label'>) =>
      intakePresentationFieldLabel(t, field, labelLocale),
    [labelLocale, t],
  )

  const loadCatalog = useCallback(
    async (code: string) => {
      if (!code) return
      setLoading(true)
      try {
        const payload = await getEntityProfileFields(code)
        setCatalog(payload.fields)
        setRows((prev) => {
          if (pendingPresetRef.current?.length) {
            return mergeCatalogWithPreset(payload.fields, pendingPresetRef.current, prev)
          }
          const prevByCode = new Map(prev.map((row) => [row.qualified_code, row]))
          return payload.fields.map((field, index) => {
            const existing = prevByCode.get(field.qualified_code)
            if (existing) return existing
            return {
              qualified_code: field.qualified_code,
              label_override: '',
              intake_level: (field.intake_level === 'required' ? 'required' : 'optional') as
                | 'required'
                | 'optional'
                | 'hidden',
              sort_order: (index + 1) * 10,
              selected: false,
            }
          })
        })
      } catch {
        notify({
          title: t('admin.intake_forms.errors.load_fields', { defaultValue: 'Failed to load profile fields' }),
          variant: 'error',
        })
      } finally {
        setLoading(false)
      }
    },
    [notify, t],
  )

  useEffect(() => {
    if (hideProfileSelect) return
    void listIntakeFormEntityProfiles()
      .then((items) => setProfiles(items.map((item) => ({ code: item.code, name: item.name }))))
      .catch(() => undefined)
  }, [hideProfileSelect])

  useEffect(() => {
    setProfileCode(entityProfileCode)
    autoLoadedFor.current = null
    pendingPresetRef.current = null
  }, [entityProfileCode])

  useEffect(() => {
    if (profileCode) void loadCatalog(profileCode)
  }, [profileCode, loadCatalog])

  useEffect(() => {
    if (initialFields?.length) setRows(initialFields)
  }, [initialFields])

  useEffect(() => {
    onChange(fieldsToPayload(rows))
  }, [rows, onChange])

  const selectedRows = useMemo(
    () => [...rows].filter((row) => row.selected).sort((a, b) => a.sort_order - b.sort_order),
    [rows],
  )

  const visibleRows = useMemo(() => {
    if (!compact) return catalog
    const catalogCodes = new Set(catalog.map((field) => field.qualified_code))
    const extras: EntityProfileFieldOption[] = rows
      .filter((row) => !catalogCodes.has(row.qualified_code))
      .map((row) => ({
        qualified_code: row.qualified_code,
        label: row.label_override || row.qualified_code,
        intake_level: row.intake_level,
        field_type: null,
        sort_order: row.sort_order,
      }))
    return extras.length ? [...catalog, ...extras] : catalog
  }, [catalog, compact, rows])

  const applyPresetFields = useCallback((presetFields: PresentationFieldInput[]) => {
    pendingPresetRef.current = presetFields
    setRows((prev) => mergeCatalogWithPreset(catalog, presetFields, prev))
  }, [catalog])

  const loadPlatformPreset = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!profileCode || disabled) return
      setLoadingPreset(true)
      try {
        const preset = await getEntityProfilePresentationPreset(profileCode)
        applyPresetFields(preset.fields)
        if (!opts?.silent) {
          notify({
            title: t('admin.intake_forms.toast.preset_loaded', { defaultValue: 'Company questionnaire loaded' }),
            variant: 'success',
          })
        }
      } catch {
        if (!opts?.silent) {
          notify({
            title: t('admin.intake_forms.errors.load_preset', { defaultValue: 'Failed to load company questionnaire' }),
            variant: 'error',
          })
        }
      } finally {
        setLoadingPreset(false)
      }
    },
    [applyPresetFields, disabled, notify, profileCode, t],
  )

  useEffect(() => {
    if (!autoLoadPreset) return
    if (loadingPreset) return
    if (profileCode.startsWith(SERVICE_SALES_PROFILE_PREFIX) === false) return
    if (autoLoadedFor.current === profileCode) return
    autoLoadedFor.current = profileCode
    void loadPlatformPreset({ silent: true })
  }, [autoLoadPreset, loadPlatformPreset, loadingPreset, profileCode])

  const moveRow = (qualifiedCode: string, direction: -1 | 1) => {
    const ordered = selectedRows
    const index = ordered.findIndex((row) => row.qualified_code === qualifiedCode)
    const swapIndex = index + direction
    if (index < 0 || swapIndex < 0 || swapIndex >= ordered.length) return
    const nextOrder = ordered.map((row, idx) => {
      if (idx === index) return { ...row, sort_order: ordered[swapIndex].sort_order }
      if (idx === swapIndex) return { ...row, sort_order: ordered[index].sort_order }
      return row
    })
    const orderMap = new Map(nextOrder.map((row) => [row.qualified_code, row.sort_order]))
    setRows((prev) =>
      prev.map((row) =>
        orderMap.has(row.qualified_code) ? { ...row, sort_order: orderMap.get(row.qualified_code)! } : row,
      ),
    )
  }

  const displayQuestion = (row: PresentationFieldDraft, field: EntityProfileFieldOption) => {
    const override = row.label_override.trim()
    if (override && !looksLikeI18nKey(override)) return override
    return catalogLabel(field)
  }

  return (
    <div className="space-y-4">
      {!hideProfileSelect ? (
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('admin.intake_forms.fields.entity_profile', { defaultValue: 'Question set' })}
          </label>
          <select
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={profileCode}
            disabled={disabled}
            onChange={(event) => {
              const next = event.target.value
              setProfileCode(next)
              onEntityProfileChange?.(next)
            }}
          >
            {profiles.map((profile) => (
              <option key={profile.code} value={profile.code}>
                {intakePresentationProfileTitle(
                  t,
                  { entity_profile_code: profile.code, profile_name: entityProfileLabel(profile.code) },
                  locale,
                )}
              </option>
            ))}
          </select>
        </div>
      ) : null}
      {profileCode.startsWith(SERVICE_SALES_PROFILE_PREFIX) && (
        <button
          type="button"
          className="btn-secondary"
          disabled={disabled || loadingPreset || loading}
          onClick={() => void loadPlatformPreset()}
        >
          {loadingPreset
            ? t('common.loading')
            : t(
                profileCode === 'service_sales.driver_hiring'
                  ? 'admin.intake_forms.load_driver_hiring_preset'
                  : profileCode === 'service_sales.warehouse_hiring'
                    ? 'admin.intake_forms.load_warehouse_hiring_preset'
                    : 'admin.intake_forms.load_b2b_preset',
                {
                  defaultValue:
                    profileCode === 'service_sales.driver_hiring'
                      ? 'Load questionnaire for companies hiring drivers'
                      : profileCode === 'service_sales.warehouse_hiring'
                        ? 'Load questionnaire for companies hiring warehouse workers'
                        : 'Load ready questionnaire for companies',
                },
              )}
        </button>
      )}

      {selectedRows.length > 0 ? (
        <p className="text-xs text-slate-600">
          {t('admin.intake_forms.selected_count', {
            defaultValue: '{count} questions included',
            values: { count: selectedRows.length },
          })}
        </p>
      ) : (
        <p className="text-xs text-amber-700">
          {t('admin.intake_forms.none_selected', {
            defaultValue: 'Select at least one question, or load a ready questionnaire.',
          })}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">{t('common.loading')}</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-100">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-2 py-2">{t('admin.intake_forms.columns.include', { defaultValue: 'Include' })}</th>
                <th className="px-2 py-2">{t('admin.intake_forms.columns.type', { defaultValue: 'Type' })}</th>
                <th className="px-2 py-2">{t('admin.intake_forms.columns.label', { defaultValue: 'Question' })}</th>
                <th className="px-2 py-2">{t('admin.intake_forms.columns.answers', { defaultValue: 'Answers' })}</th>
                <th className="px-2 py-2">{t('admin.intake_forms.columns.level', { defaultValue: 'Required?' })}</th>
                <th className="px-2 py-2">{t('admin.intake_forms.columns.order', { defaultValue: 'Order' })}</th>
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((field) => {
                const row = rows.find((item) => item.qualified_code === field.qualified_code)
                if (!row) return null
                const selectedIndex = selectedRows.findIndex((item) => item.qualified_code === row.qualified_code)
                const derivedCode = slugifyFieldCodeFromLabel(displayQuestion(row, field))
                return (
                  <tr key={field.qualified_code} className="border-b border-slate-50">
                    <td className="px-2 py-2">
                      <input
                        type="checkbox"
                        checked={row.selected}
                        disabled={disabled}
                        onChange={(event) =>
                          setRows((prev) =>
                            prev.map((item) =>
                              item.qualified_code === row.qualified_code
                                ? { ...item, selected: event.target.checked }
                                : item,
                            ),
                          )
                        }
                      />
                    </td>
                    <td className="px-2 py-2 text-xs font-medium text-slate-600">
                      {fieldTypeLabel(field.field_type, t)}
                    </td>
                    <td className="px-2 py-2">
                      <input
                        className="w-full rounded-lg border border-slate-200 px-2 py-1 text-sm"
                        value={displayQuestion(row, field)}
                        disabled={disabled || !row.selected}
                        title={field.qualified_code}
                        onChange={(event) =>
                          setRows((prev) =>
                            prev.map((item) =>
                              item.qualified_code === row.qualified_code
                                ? { ...item, label_override: event.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                      {compact ? null : (
                        <p className="mt-0.5 font-mono text-[10px] text-slate-400" title={field.qualified_code}>
                          {field.qualified_code || derivedCode}
                        </p>
                      )}
                    </td>
                    <td className="max-w-xs px-2 py-2 text-xs text-slate-600">
                      {fieldAnswersHint(field, t, labelLocale)}
                    </td>
                    <td className="px-2 py-2">
                      <select
                        className="rounded-lg border border-slate-200 px-2 py-1 text-sm"
                        value={row.intake_level}
                        disabled={disabled || !row.selected}
                        onChange={(event) =>
                          setRows((prev) =>
                            prev.map((item) =>
                              item.qualified_code === row.qualified_code
                                ? {
                                    ...item,
                                    intake_level: event.target.value as 'required' | 'optional' | 'hidden',
                                  }
                                : item,
                            ),
                          )
                        }
                      >
                        <option value="required">{t('admin.intake_forms.level.required', { defaultValue: 'Required' })}</option>
                        <option value="optional">{t('admin.intake_forms.level.optional', { defaultValue: 'Optional' })}</option>
                        <option value="hidden">{t('admin.intake_forms.level.hidden', { defaultValue: 'Hidden' })}</option>
                      </select>
                    </td>
                    <td className="px-2 py-2">
                      {row.selected ? (
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            className="rounded border border-slate-200 p-1 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                            disabled={disabled || selectedIndex <= 0}
                            onClick={() => moveRow(row.qualified_code, -1)}
                          >
                            <IconArrowUp size={14} />
                          </button>
                          <button
                            type="button"
                            className="rounded border border-slate-200 p-1 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                            disabled={disabled || selectedIndex < 0 || selectedIndex >= selectedRows.length - 1}
                            onClick={() => moveRow(row.qualified_code, 1)}
                          >
                            <IconArrowDown size={14} />
                          </button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {!compact && selectedRows.length > 0 && (
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('admin.intake_forms.sections.presentation_rules', { defaultValue: 'Presentation rules (P10A)' })}
          </h4>
          <p className="mt-1 text-xs text-slate-500">
            {t('admin.intake_forms.presentation_rules_hint', {
              defaultValue: 'UI-only show/hide/required-if/readonly-if. Not business requirements (P10B).',
            })}
          </p>
          <div className="mt-3 space-y-3">
            {selectedRows.map((row) => (
              <div key={row.qualified_code} className="rounded-lg border border-slate-100 bg-white p-3">
                <p className="text-xs font-medium text-slate-700">
                  {catalogLabel({ qualified_code: row.qualified_code, label: row.label_override })}
                </p>
                <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  {RULE_KEYS.map((ruleKey) => {
                    const condition = row.presentation_rules?.[ruleKey]
                    const sourceOptions = selectedRows
                      .map((item) => item.qualified_code)
                      .filter((code) => code !== row.qualified_code)
                    return (
                      <label key={ruleKey} className="block text-xs">
                        <span className="text-slate-500">{ruleKey}</span>
                        <select
                          className="mt-1 w-full rounded-lg border border-slate-200 px-2 py-1"
                          disabled={disabled || sourceOptions.length === 0}
                          value={condition?.source_field || ''}
                          onChange={(event) => {
                            const source = event.target.value
                            setRows((prev) =>
                              prev.map((item) => {
                                if (item.qualified_code !== row.qualified_code) return item
                                const nextRules = { ...(item.presentation_rules || {}) }
                                if (!source) {
                                  delete nextRules[ruleKey]
                                } else {
                                  nextRules[ruleKey] = {
                                    source_field: source,
                                    operator: condition?.operator || 'truthy',
                                  }
                                }
                                return {
                                  ...item,
                                  presentation_rules: Object.keys(nextRules).length ? nextRules : undefined,
                                }
                              }),
                            )
                          }}
                        >
                          <option value="">
                            {t('admin.intake_forms.rules_off', { defaultValue: 'Off' })}
                          </option>
                          {sourceOptions.map((code) => (
                            <option key={code} value={code}>
                              {catalogLabel({ qualified_code: code, label: code })}
                            </option>
                          ))}
                        </select>
                      </label>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function detailFieldsToDraft(detail: {
  presentation: {
    fields: Array<{
      qualified_code: string
      label: string
      intake_level: string
      sort_order: number
      presentation_rules?: PresentationRules
    }>
  }
}): PresentationFieldDraft[] {
  return detail.presentation.fields.map((field) => ({
    qualified_code: field.qualified_code,
    label_override: looksLikeI18nKey(field.label) ? '' : field.label,
    intake_level: (field.intake_level === 'required'
      ? 'required'
      : field.intake_level === 'hidden'
        ? 'hidden'
        : 'optional') as 'required' | 'optional' | 'hidden',
    sort_order: field.sort_order,
    selected: true,
    presentation_rules: field.presentation_rules,
  }))
}

export function SavePresentationButton({
  saving,
  onClick,
  disabled,
}: {
  saving: boolean
  onClick: () => void
  disabled?: boolean
}) {
  const { t } = useI18n()
  return (
    <button type="button" className="btn-primary inline-flex items-center gap-2" disabled={disabled || saving} onClick={onClick}>
      <IconDeviceFloppy size={16} />
      {saving ? t('common.loading') : t('admin.intake_forms.save_presentation', { defaultValue: 'Save presentation' })}
    </button>
  )
}
