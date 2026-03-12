import { memo, useState, useCallback } from 'react'
import { IconBriefcase2, IconChevronDown } from '@tabler/icons-react'
import type { CandidateExtra } from '../../api/types'
import type { RefObject } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import { useI18n } from '../../i18n'
import { Input, CheckboxMultiSelect } from './shared/FormComponents'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'

type Option = { value: string; label: string; extra?: any }
type EmploymentRow = {
  id?: string
  localId: string
  employer_name: string
  country: string
  position: string
  start_date: string
  end_date: string
}

const MAX_EMPLOYMENTS = 3

interface CandidateExperienceSectionProps {
  extra: CandidateExtra
  experienceRef: RefObject<HTMLDivElement>
  experienceTotalDisplay: string | number
  trailerTypeOptions: Option[]
  routeTypeOptions: Option[]
  employmentHistory: EmploymentRow[]
  employmentLoading: boolean
  employmentError: string | null
  selectTexts: {
    search: string
    noResults: string
    multiNone: string
    multiSelected: (count: number) => string
  }
  onExtraChange: (patch: Partial<CandidateExtra>) => void
  onExperienceChange: (field: 'experience_eu_years' | 'experience_non_eu_years', raw: string) => void
  onAddEmploymentRow: () => void
  onUpdateEmploymentHistory: (localId: string, key: keyof Pick<EmploymentRow, 'employer_name' | 'country' | 'position' | 'start_date' | 'end_date'>, value: string) => void
  onRemoveEmploymentRow: (localId: string) => void
  candidateProfile?: CandidateProfile | null
  candidateDataReadOnly?: boolean
}

function CandidateExperienceSection({
  extra,
  experienceRef,
  experienceTotalDisplay,
  trailerTypeOptions,
  routeTypeOptions,
  employmentHistory,
  employmentLoading,
  employmentError,
  selectTexts,
  onExtraChange,
  onExperienceChange,
  onAddEmploymentRow,
  onUpdateEmploymentHistory,
  onRemoveEmploymentRow,
  candidateProfile,
  candidateDataReadOnly = false,
}: CandidateExperienceSectionProps) {
  const { t } = useI18n()
  const [collapsed, setCollapsed] = useState(() => {
    try { const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}'); return !!s.experience } catch { return false }
  })
  const toggle = useCallback(() => {
    setCollapsed((p) => {
      const next = !p
      try { const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}'); s.experience = next; localStorage.setItem('hf:card-sections', JSON.stringify(s)) } catch {}
      return next
    })
  }, [])

  return (
    <section
      ref={experienceRef}
      id="section-experience"
      className="group app-surface p-6 scroll-mt-24 transition-all hover:-translate-y-0.5 hover:shadow-xl"
    >
      <button type="button" onClick={toggle} className="flex w-full items-center justify-between gap-3 text-left">
        <div className="flex items-center gap-3">
          <IconBriefcase2 size={22} className="text-slate-600" />
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{t('app.candidate_card.sections.experience.title')}</h2>
            <p className="text-sm text-slate-500">{t('app.candidate_card.sections.experience.description')}</p>
          </div>
        </div>
        <IconChevronDown size={16} className={`shrink-0 text-slate-400 transition-transform ${collapsed ? '' : 'rotate-180'}`} />
      </button>
      {!collapsed && (!candidateProfile || isFieldVisible(candidateProfile, 'experience_eu_years') || isFieldVisible(candidateProfile, 'experience_non_eu_years')) && (
        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          {(!candidateProfile || isFieldVisible(candidateProfile, 'experience_eu_years')) && (
            <Input
              label={getFieldLabel(candidateProfile, 'experience_eu_years', t('app.candidate_card.fields.experience_eu'))}
              type="number"
              value={
                typeof extra.experience_eu_years === 'number' && !Number.isNaN(extra.experience_eu_years)
                  ? String(extra.experience_eu_years)
                  : ''
              }
              onChange={(e) => onExperienceChange('experience_eu_years', e.target.value)}
              readOnly={candidateDataReadOnly}
              required={isFieldRequired(candidateProfile, 'experience_eu_years')}
            />
          )}
          {(!candidateProfile || isFieldVisible(candidateProfile, 'experience_non_eu_years')) && (
            <Input
              label={getFieldLabel(candidateProfile, 'experience_non_eu_years', t('app.candidate_card.fields.experience_non_eu'))}
              type="number"
              value={
                typeof extra.experience_non_eu_years === 'number' && !Number.isNaN(extra.experience_non_eu_years)
                  ? String(extra.experience_non_eu_years)
                  : ''
              }
              onChange={(e) => onExperienceChange('experience_non_eu_years', e.target.value)}
              readOnly={candidateDataReadOnly}
              required={isFieldRequired(candidateProfile, 'experience_non_eu_years')}
            />
          )}
          {experienceTotalDisplay !== '' && (
            <div className="md:col-span-2 mt-1">
              <p className="text-xs text-slate-500">
                {t('app.candidate_card.fields.experience_total_hint', { values: { total: experienceTotalDisplay } })}
              </p>
            </div>
          )}
        </div>
      )}

      {!collapsed && (!candidateProfile || isFieldVisible(candidateProfile, 'trailer_types') || isFieldVisible(candidateProfile, 'route_types')) && (
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          {(!candidateProfile || isFieldVisible(candidateProfile, 'trailer_types')) && (
            <div>
              <div className="label">
                {getFieldLabel(candidateProfile, 'trailer_types', t('app.candidate_card.intake.fields.trailer_types'))}
                {isFieldRequired(candidateProfile, 'trailer_types') && <span className="text-red-600">*</span>}
              </div>
              <CheckboxMultiSelect
                options={trailerTypeOptions}
                values={Array.isArray(extra.trailer_types) ? extra.trailer_types : []}
                onChange={(vals) => onExtraChange({ trailer_types: vals })}
                disabled={candidateDataReadOnly}
                placeholder={selectTexts.multiNone}
                searchPlaceholder={selectTexts.search}
                noResultsLabel={selectTexts.noResults}
                multiSelectedLabel={selectTexts.multiSelected}
              />
            </div>
          )}
          {(!candidateProfile || isFieldVisible(candidateProfile, 'route_types')) && (
            <div>
              <div className="label">
                {getFieldLabel(candidateProfile, 'route_types', t('app.candidate_card.intake.fields.route_types'))}
                {isFieldRequired(candidateProfile, 'route_types') && <span className="text-red-600">*</span>}
              </div>
              <CheckboxMultiSelect
                options={routeTypeOptions}
                values={Array.isArray(extra.route_types) ? extra.route_types : []}
                onChange={(vals) => onExtraChange({ route_types: vals })}
                disabled={candidateDataReadOnly}
                placeholder={selectTexts.multiNone}
                searchPlaceholder={selectTexts.search}
                noResultsLabel={selectTexts.noResults}
                multiSelectedLabel={selectTexts.multiSelected}
              />
            </div>
          )}
        </div>
      )}

      {!collapsed && (!candidateProfile || isFieldVisible(candidateProfile, 'employment_history')) && (
        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-slate-800">
              {getFieldLabel(candidateProfile, 'employment_history', t('app.candidate_card.employment.title'))}
              {isFieldRequired(candidateProfile, 'employment_history') && <span className="text-red-600">*</span>}
            </div>
          <button
            type="button"
            className="btn-secondary text-sm shadow-sm transition hover:shadow disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={onAddEmploymentRow}
            disabled={candidateDataReadOnly || employmentHistory.length >= MAX_EMPLOYMENTS}
          >
            {t('app.candidate_card.employment.add')}
          </button>
        </div>
        {employmentHistory.length >= MAX_EMPLOYMENTS && (
          <p className="text-xs text-slate-500">{t('app.candidate_card.employment.limit', { values: { count: MAX_EMPLOYMENTS } })}</p>
        )}
        {employmentError && (
          <div className="rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {employmentError}
          </div>
        )}
        {employmentLoading ? (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white/70 px-4 py-3 text-sm text-slate-500">
            {t('app.candidate_card.employment.loading')}
          </div>
        ) : employmentHistory.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white/70 px-4 py-3 text-sm text-slate-500">
            {t('app.candidate_card.employment.empty')}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-brand-50 bg-white/95 shadow-card">
            <table className="min-w-full divide-y divide-brand-100/70 text-sm">
              <thead className="bg-brand-50/60">
                <tr>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.employer')}</th>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.country')}</th>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.position')}</th>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.start')}</th>
                  <th className="px-3 py-2 text-left">{t('app.candidate_card.employment.columns.end')}</th>
                  <th className="px-3 py-2 text-right"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-100/70 bg-white/95">
                {employmentHistory.map((entry) => (
                  <tr key={entry.id ?? entry.localId}>
                    <td className="px-3 py-2">
                      <input
                        className="input"
                        value={entry.employer_name || ''}
                        onChange={(e) => onUpdateEmploymentHistory(entry.localId, 'employer_name', e.target.value)}
                        readOnly={candidateDataReadOnly}
                        placeholder={t('app.candidate_card.employment.placeholders.employer')}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className="input"
                        value={entry.country || ''}
                        onChange={(e) => onUpdateEmploymentHistory(entry.localId, 'country', e.target.value.toUpperCase())}
                        readOnly={candidateDataReadOnly}
                        placeholder={t('app.candidate_card.employment.placeholders.country')}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className="input"
                        value={entry.position || ''}
                        onChange={(e) => onUpdateEmploymentHistory(entry.localId, 'position', e.target.value)}
                        readOnly={candidateDataReadOnly}
                        placeholder={t('app.candidate_card.employment.placeholders.position')}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className="input"
                        type="date"
                        value={entry.start_date || ''}
                        disabled={candidateDataReadOnly}
                        onChange={(e) => onUpdateEmploymentHistory(entry.localId, 'start_date', e.target.value)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className="input"
                        type="date"
                        value={entry.end_date || ''}
                        disabled={candidateDataReadOnly}
                        onChange={(e) => onUpdateEmploymentHistory(entry.localId, 'end_date', e.target.value)}
                      />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        type="button"
                        className="btn-danger btn-sm"
                        disabled={candidateDataReadOnly}
                        onClick={() => onRemoveEmploymentRow(entry.localId)}
                      >
                        {t('common.actions.delete')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        </div>
      )}
    </section>
  )
}

export default memo(CandidateExperienceSection)
