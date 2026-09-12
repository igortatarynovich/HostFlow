import { useMemo } from 'react'
import { Controller, type Control, useWatch } from 'react-hook-form'
import MultiSelect from '../../controls/MultiSelect'
import { SectionCard } from '../../ui/SectionCard'

export type RecruitmentRequirementsLabels = {
  title: string
  intro: string
  yearsCe: string
  yearsCeHint: string
  documents: string
  documentsHint: string
  profileNote: string
  inheritedDocs: string
  inheritedYears: string
}

type DocOption = { value: string; label: string }

type Props = {
  control: Control<any>
  documentOptions: DocOption[]
  labels: RecruitmentRequirementsLabels
}

/**
 * Operator asks: what is required for this vacancy?
 * Shows effective requirements (Profile/Pack ∪ Overlay).
 * Writes Overlay via API recruitment_requirements — not lead_criteria / Profiling.
 * Backend persists only minimal Overlay delta (inherited never copied wholesale).
 */
export function VacancyRecruitmentRequirementsPanel({ control, documentOptions, labels }: Props) {
  const options = useMemo(() => documentOptions, [documentOptions])
  const inheritedDocs = useWatch({ control, name: 'recruitment_inherited_documents' }) || []
  const inheritedYears = useWatch({ control, name: 'recruitment_inherited_years_ce_min' })
  const inheritedList = Array.isArray(inheritedDocs) ? inheritedDocs.map(String) : []
  const labelByCode = useMemo(() => {
    const map = new Map(options.map((o) => [o.value, o.label]))
    return map
  }, [options])

  return (
    <div className="space-y-4" data-testid="vacancy-recruitment-requirements">
      <SectionCard title={labels.title}>
        <p className="mb-3 text-sm text-slate-600">{labels.intro}</p>
        <p className="mb-4 text-xs text-slate-500">{labels.profileNote}</p>

        {inheritedYears !== '' && inheritedYears != null ? (
          <p className="mb-3 text-xs text-slate-500" data-testid="vacancy-req-inherited-years">
            {labels.inheritedYears}: {String(inheritedYears)}
          </p>
        ) : null}

        {inheritedList.length > 0 ? (
          <div className="mb-4" data-testid="vacancy-req-inherited-docs">
            <span className="mb-1 block text-xs font-medium text-slate-600">{labels.inheritedDocs}</span>
            <ul className="list-inside list-disc text-xs text-slate-500">
              {inheritedList.map((code) => (
                <li key={code}>{labelByCode.get(code) || code}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <label className="mb-4 block text-sm">
          <span className="mb-1 block font-medium text-slate-700">{labels.yearsCe}</span>
          <span className="mb-1 block text-xs text-slate-500">{labels.yearsCeHint}</span>
          <Controller
            name="recruitment_years_ce_min"
            control={control}
            render={({ field }) => (
              <input
                type="number"
                min={0}
                step={1}
                className="input w-full max-w-xs"
                value={field.value ?? ''}
                onChange={(e) => field.onChange(e.target.value === '' ? '' : e.target.value)}
              />
            )}
          />
        </label>

        <div className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">{labels.documents}</span>
          <span className="mb-1 block text-xs text-slate-500">{labels.documentsHint}</span>
          <Controller
            name="recruitment_required_documents"
            control={control}
            render={({ field }) => (
              <MultiSelect
                options={options}
                values={Array.isArray(field.value) ? field.value : []}
                onChange={field.onChange}
              />
            )}
          />
        </div>
      </SectionCard>
    </div>
  )
}
