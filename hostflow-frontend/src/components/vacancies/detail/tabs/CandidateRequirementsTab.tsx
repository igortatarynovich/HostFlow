import React, { useEffect, useMemo, useState } from 'react'
import { Controller, type Control, type UseFormSetValue } from 'react-hook-form'
import { SectionCard } from '../../ui/SectionCard'
import MultiSelect from '../../controls/MultiSelect'
import { buildCountryOptions } from '../../../data/countries'
import { getDocumentTypes, type DocType } from '../../../api/documents/catalog'
import { DOC_OK_STATUSES } from '../criteriaForm'
import type { VacancyRequirementsPreset } from '../../../api/tenants'
import type { LocaleCode } from '../../../i18n'

type Props = {
  control: Control<any>
  setValue: UseFormSetValue<any>
  locale: LocaleCode
  requirementsPresets: VacancyRequirementsPreset[]
  labels: {
    section: string
    mandatory: string
    preferred: string
    preferredNote: string
    experience: string
    documents: string
    candidateDocs: string
    allowStatuses: string
    allowedGeo: string
    blockedGeo: string
    preferredDocs: string
    preferredLang: string
    preferredLangHint: string
    enableFit: string
    enableFitHint: string
    disableConvert: string
    disableConvertHint: string
    preset: string
    applyPreset: string
  }
}

export function CandidateRequirementsTab({
  control,
  setValue,
  locale,
  requirementsPresets,
  labels,
}: Props) {
  const [docTypes, setDocTypes] = useState<DocType[]>([])
  const [selectedPresetId, setSelectedPresetId] = useState('')

  useEffect(() => {
    let cancelled = false
    getDocumentTypes()
      .then((rows) => {
        if (!cancelled) setDocTypes(Array.isArray(rows) ? rows : [])
      })
      .catch(() => {
        if (!cancelled) setDocTypes([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  const countryOptions = useMemo(() => buildCountryOptions(locale), [locale])
  const docOptions = useMemo(
    () =>
      docTypes.map((d) => ({
        value: d.code || d.id,
        label: d.name || d.code || d.id,
      })),
    [docTypes],
  )
  const statusOptions = useMemo(
    () => DOC_OK_STATUSES.map((s) => ({ value: s, label: s })),
    [],
  )

  return (
    <div className="space-y-4">
      <SectionCard title={labels.section}>
        <Controller
          control={control}
          name="lead_fit_evaluation_enabled"
          render={({ field }) => (
            <label className="mb-4 flex cursor-pointer items-start gap-2 text-sm text-slate-800">
              <input
                type="checkbox"
                className="mt-1"
                checked={!!field.value}
                onChange={(e) => field.onChange(e.target.checked)}
              />
              <span>
                <span className="font-medium">{labels.enableFit}</span>
                <span className="mt-0.5 block text-xs font-normal text-slate-500">
                  {labels.enableFitHint}
                </span>
              </span>
            </label>
          )}
        />

        {requirementsPresets.length > 0 ? (
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <select
              className="input h-9 max-w-xs text-sm"
              value={selectedPresetId}
              onChange={(e) => setSelectedPresetId(e.target.value)}
            >
              <option value="">{labels.preset}</option>
              {requirementsPresets.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-secondary btn-sm"
              disabled={!selectedPresetId}
              onClick={() => {
                const preset = requirementsPresets.find((p) => p.id === selectedPresetId)
                const crit: any = preset?.criteria || {}
                const min = crit?.min_experience_eu_years
                setValue(
                  'criteria_min_experience_eu_years',
                  typeof min !== 'undefined' ? String(min) : '',
                )
                setValue(
                  'criteria_requires_documents',
                  Array.isArray(crit?.requires_documents) ? crit.requires_documents : [],
                )
                setValue(
                  'criteria_requires_candidate_documents_v1',
                  Array.isArray(crit?.requires_candidate_documents_v1)
                    ? crit.requires_candidate_documents_v1
                    : [],
                )
                setValue(
                  'criteria_allowed_geo_countries',
                  Array.isArray(crit?.allowed_geo_countries)
                    ? crit.allowed_geo_countries.map((c: string) => String(c).toUpperCase())
                    : [],
                )
                setValue(
                  'criteria_blocked_geo_countries',
                  Array.isArray(crit?.blocked_geo_countries)
                    ? crit.blocked_geo_countries.map((c: string) => String(c).toUpperCase())
                    : [],
                )
                setValue(
                  'criteria_preferred_documents',
                  Array.isArray(crit?.preferred_documents) ? crit.preferred_documents : [],
                )
              }}
            >
              {labels.applyPreset}
            </button>
          </div>
        ) : null}

        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {labels.mandatory}
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="block">
            <div className="label">{labels.experience}</div>
            <Controller
              control={control}
              name="criteria_min_experience_eu_years"
              render={({ field }) => (
                <input
                  type="number"
                  min={0}
                  className="input"
                  value={field.value ?? ''}
                  onChange={(e) => field.onChange(e.target.value)}
                />
              )}
            />
          </label>

          <div className="block md:col-span-2">
            <div className="label">{labels.documents}</div>
            <Controller
              control={control}
              name="criteria_requires_documents"
              render={({ field }) => (
                <MultiSelect
                  options={docOptions}
                  values={Array.isArray(field.value) ? field.value : []}
                  onChange={field.onChange}
                />
              )}
            />
          </div>

          <div className="block md:col-span-2">
            <div className="label">{labels.candidateDocs}</div>
            <Controller
              control={control}
              name="criteria_requires_candidate_documents_v1"
              render={({ field }) => (
                <MultiSelect
                  options={docOptions}
                  values={Array.isArray(field.value) ? field.value : []}
                  onChange={field.onChange}
                />
              )}
            />
          </div>

          <div className="block md:col-span-2">
            <div className="label">{labels.allowStatuses}</div>
            <Controller
              control={control}
              name="criteria_candidate_documents_allow_statuses"
              render={({ field }) => (
                <MultiSelect
                  options={statusOptions}
                  values={Array.isArray(field.value) ? field.value : []}
                  onChange={field.onChange}
                />
              )}
            />
          </div>

          <div className="block md:col-span-2">
            <div className="label">{labels.allowedGeo}</div>
            <Controller
              control={control}
              name="criteria_allowed_geo_countries"
              render={({ field }) => (
                <MultiSelect
                  options={countryOptions}
                  values={Array.isArray(field.value) ? field.value : []}
                  onChange={field.onChange}
                />
              )}
            />
          </div>

          <div className="block md:col-span-2">
            <div className="label">{labels.blockedGeo}</div>
            <Controller
              control={control}
              name="criteria_blocked_geo_countries"
              render={({ field }) => (
                <MultiSelect
                  options={countryOptions}
                  values={Array.isArray(field.value) ? field.value : []}
                  onChange={field.onChange}
                />
              )}
            />
          </div>
        </div>

        <div className="mb-2 mt-6 text-xs font-semibold uppercase tracking-wide text-slate-500">
          {labels.preferred}
        </div>
        <p className="mb-3 text-xs text-slate-500">{labels.preferredNote}</p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="block md:col-span-2">
            <div className="label">{labels.preferredDocs}</div>
            <Controller
              control={control}
              name="criteria_preferred_documents"
              render={({ field }) => (
                <MultiSelect
                  options={docOptions}
                  values={Array.isArray(field.value) ? field.value : []}
                  onChange={field.onChange}
                />
              )}
            />
          </div>
          <div className="block md:col-span-2">
            <div className="label">{labels.preferredLang}</div>
            <Controller
              control={control}
              name="criteria_preferred_languages"
              render={({ field }) => (
                <input
                  className="input"
                  placeholder="pl, en"
                  value={(Array.isArray(field.value) ? field.value : []).join(', ')}
                  onChange={(e) => {
                    const arr = e.target.value
                      .split(',')
                      .map((s) => s.trim())
                      .filter(Boolean)
                    field.onChange(arr)
                  }}
                />
              )}
            />
            <p className="mt-1 text-xs text-slate-500">{labels.preferredLangHint}</p>
          </div>
        </div>

        <Controller
          control={control}
          name="vacancy_disable_auto_convert_on_fit"
          render={({ field }) => (
            <label className="mt-4 flex cursor-pointer items-start gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                className="mt-1"
                checked={!!field.value}
                onChange={(e) => field.onChange(e.target.checked)}
              />
              <span>
                <span className="font-medium">{labels.disableConvert}</span>
                <span className="mt-0.5 block text-xs text-slate-500">{labels.disableConvertHint}</span>
              </span>
            </label>
          )}
        />
      </SectionCard>
    </div>
  )
}
