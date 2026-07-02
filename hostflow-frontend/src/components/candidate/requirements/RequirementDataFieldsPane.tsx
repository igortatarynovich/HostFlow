import clsx from 'clsx'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Candidate } from '../../../api/types'
import type { WorkspaceFieldRequirement } from '../../../api/candidateRequirements'
import { Input, SearchableSelect } from '../shared/FormComponents'
import { usePatchRequirementField } from '../../../hooks/usePatchRequirementField'
import { usePlatformCountryOptions } from '../../../hooks/usePlatformCatalogOptions'
import { useI18n } from '../../../i18n'
import {
  readRequirementFieldValue,
  requirementFieldInputKind,
  requirementFieldLabelKey,
} from '../../../utils/requirementFieldPatch'

type Props = {
  candidate: Candidate | null
  fieldRequirements: WorkspaceFieldRequirement[]
  canEdit: boolean
  onSaved?: (candidate: Candidate) => void
  className?: string
}

function fieldLabel(t: ReturnType<typeof useI18n>['t'], row: WorkspaceFieldRequirement): string {
  const key = requirementFieldLabelKey(row.qualified_code)
  const tail = row.qualified_code.split('.').pop()?.replace('[]', '') || row.qualified_code
  return t(key, { defaultValue: tail.replace(/_/g, ' ') })
}

export default function RequirementDataFieldsPane({
  candidate,
  fieldRequirements,
  canEdit,
  onSaved,
  className,
}: Props) {
  const { t, locale } = useI18n()
  const countryOptions = usePlatformCountryOptions(locale)
  const { saveField, savingCode, error, clearError } = usePatchRequirementField(candidate?.id)
  const [drafts, setDrafts] = useState<Record<string, string>>({})

  const rows = fieldRequirements || []

  const seedDrafts = useCallback(() => {
    if (!candidate) {
      setDrafts({})
      return
    }
    const next: Record<string, string> = {}
    for (const row of rows) {
      next[row.qualified_code] = readRequirementFieldValue(candidate, row.qualified_code)
    }
    setDrafts(next)
  }, [candidate, rows])

  useEffect(() => {
    seedDrafts()
  }, [seedDrafts])

  const openCount = useMemo(() => rows.filter((row) => !row.satisfied).length, [rows])

  const handleSave = useCallback(
    async (row: WorkspaceFieldRequirement) => {
      if (!candidate || !canEdit) return
      clearError()
      const value = drafts[row.qualified_code] ?? ''
      const updated = await saveField(row.qualified_code, value, candidate)
      if (updated) {
        onSaved?.(updated)
      }
    },
    [canEdit, candidate, clearError, drafts, onSaved, saveField],
  )

  if (!rows.length) return null

  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white p-4', className)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">
            {t('app.candidate_requirements.workspace.data_fields_title', { defaultValue: 'Required data' })}
          </h2>
          <p className="mt-0.5 text-xs text-slate-600">
            {t('app.candidate_requirements.workspace.data_fields_subtitle', {
              defaultValue: 'Fill missing candidate fields — requirements engine re-evaluates after save.',
            })}
          </p>
        </div>
        <span
          className={clsx(
            'rounded-full px-2.5 py-1 text-xs font-semibold',
            openCount === 0 ? 'bg-emerald-100 text-emerald-900' : 'bg-amber-100 text-amber-900',
          )}
        >
          {openCount === 0
            ? t('app.candidate_requirements.workspace.all_data_filled', { defaultValue: 'All filled' })
            : t('app.candidate_requirements.workspace.data_open_count', {
                defaultValue: '{count} missing',
                values: { count: openCount },
              })}
        </span>
      </div>

      {error ? (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800">
          {error}
        </div>
      ) : null}

      <ul className="mt-4 space-y-3">
        {rows.map((row) => {
          const inputKind = requirementFieldInputKind(row.qualified_code)
          const draftValue = drafts[row.qualified_code] ?? ''
          const busy = savingCode === row.qualified_code
          const editable = canEdit && row.level !== 'informational'
          const dirty =
            candidate != null &&
            draftValue.trim() !== readRequirementFieldValue(candidate, row.qualified_code).trim()

          return (
            <li
              key={row.qualified_code}
              className="rounded-lg border border-slate-200 bg-slate-50/60 p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-medium text-slate-900">{fieldLabel(t, row)}</div>
                <span
                  className={clsx(
                    'rounded-full border px-2 py-0.5 text-[10px] font-medium',
                    row.satisfied
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                      : 'border-amber-200 bg-amber-50 text-amber-950',
                  )}
                >
                  {row.satisfied
                    ? t('app.candidate_requirements.workspace.data_ok', { defaultValue: 'Filled' })
                    : t('app.candidate_requirements.workspace.data_missing', { defaultValue: 'Missing' })}
                </span>
              </div>

              <div className="mt-2 flex flex-wrap items-end gap-2">
                <div className="min-w-[12rem] flex-1">
                  {inputKind === 'country' ? (
                    <label className="block">
                      <div className="sr-only">{fieldLabel(t, row)}</div>
                      <SearchableSelect
                        options={countryOptions}
                        value={draftValue}
                        onChange={(next) =>
                          setDrafts((prev) => ({ ...prev, [row.qualified_code]: next }))
                        }
                        disabled={!editable || busy}
                        placeholder={t('common.actions.select', { defaultValue: 'Select…' })}
                        searchPlaceholder={t('common.search', { defaultValue: 'Search…' })}
                        noResultsLabel={t('common.no_results', { defaultValue: 'No results' })}
                      />
                    </label>
                  ) : (
                    <Input
                      type={
                        inputKind === 'number'
                          ? 'number'
                          : inputKind === 'date'
                            ? 'date'
                            : inputKind === 'email'
                              ? 'email'
                              : inputKind === 'phone'
                                ? 'tel'
                                : 'text'
                      }
                      value={draftValue}
                      onChange={(e) =>
                        setDrafts((prev) => ({ ...prev, [row.qualified_code]: e.target.value }))
                      }
                      readOnly={!editable}
                      disabled={busy}
                      min={inputKind === 'number' ? 0 : undefined}
                      step={inputKind === 'number' ? 1 : undefined}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && editable && dirty) {
                          e.preventDefault()
                          void handleSave(row)
                        }
                      }}
                    />
                  )}
                </div>

                {editable ? (
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    disabled={busy || !dirty}
                    onClick={() => void handleSave(row)}
                  >
                    {busy
                      ? t('common.saving', { defaultValue: 'Saving…' })
                      : t('app.candidate_requirements.workspace.data_field_save', {
                          defaultValue: 'Save',
                        })}
                  </button>
                ) : null}
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
