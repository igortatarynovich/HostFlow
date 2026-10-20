import { memo, useState, useCallback, useRef } from 'react'
import { IconBriefcase2, IconChevronDown } from '@tabler/icons-react'
import type { CandidateExtra } from '../../api/types'
import type { RefObject } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import DateInput from '../controls/DateInput'
import { useI18n } from '../../i18n'
import { Input, CheckboxMultiSelect } from './shared/FormComponents'
import { ChipFieldEditor } from '../ui/ChipFieldEditor'
import { FieldGrid } from '../ui/FieldGrid'
import { InlineFieldRow } from '../ui/InlineFieldRow'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'
import { formatYearsCount } from '../../modules/candidate-card/utils'

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
  effectiveLayout?: EffectiveCardLayout | null
  candidateDataReadOnly?: boolean
  embedded?: boolean
  part?: 'skills' | 'history'
  plain?: boolean
  /** Read rows until the operator edits one field or the history group. */
  rowEdit?: boolean
  /** Split driver experience from trailer and route preferences. */
  focus?: 'experience' | 'mobility'
  /** The profile tab owns the employment roster. This section is only the editor. */
  editHistory?: boolean
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
  effectiveLayout,
  candidateDataReadOnly = false,
  embedded = false,
  part,
  plain = false,
  rowEdit = false,
  focus,
  editHistory = false,
}: CandidateExperienceSectionProps) {
  const { t, locale } = useI18n()
  const [openField, setOpenField] = useState<string | null>(null)
  const snapshot = useRef<CandidateExtra | null>(null)
  const beginRow = (key: string) => {
    snapshot.current = extra
    setOpenField(key)
  }
  const cancelRow = () => {
    if (snapshot.current) onExtraChange(snapshot.current)
    setOpenField(null)
  }
  const layoutVisible = (fieldKey: string) => isFieldVisible(candidateProfile, fieldKey, effectiveLayout)
  const layoutRequired = (fieldKey: string) => isFieldRequired(candidateProfile, fieldKey, effectiveLayout)
  const layoutLabel = (fieldKey: string, defaultLabel: string) =>
    getFieldLabel(candidateProfile, fieldKey, defaultLabel, effectiveLayout)
  const [collapsed, setCollapsed] = useState(() => {
    if (plain || embedded) return false
    try { const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}'); return !!s.experience } catch { return false }
  })
  const toggle = useCallback(() => {
    if (embedded) return
    setCollapsed((p) => {
      const next = !p
      try { const s = JSON.parse(localStorage.getItem('hf:card-sections') || '{}'); s.experience = next; localStorage.setItem('hf:card-sections', JSON.stringify(s)) } catch {}
      return next
    })
  }, [embedded])

  if (rowEdit && part !== 'history') {
    const showExperience = focus !== 'mobility'
    const showMobility = focus !== 'experience'
    const years = (value: unknown) => (typeof value === 'number' && !Number.isNaN(value) ? formatYearsCount(value, locale) : '')
    const labels = (keys: string[] | undefined, options: Option[]) =>
      (keys || []).map((key) => options.find((item) => item.value === key)?.label || key).join(' · ')
    return (
      <FieldGrid dense>
        {showExperience && (!candidateProfile || layoutVisible('experience_eu_years')) ? (
          <InlineFieldRow
            label={layoutLabel('experience_eu_years', t('app.candidate_card.fields.experience_eu'))}
            value={years(extra.experience_eu_years)}
            editing={openField === 'experience_eu_years'}
            canEdit={!candidateDataReadOnly}
            onEdit={() => beginRow('experience_eu_years')}
            onDone={() => setOpenField(null)}
            onCancel={cancelRow}
          >
            <Input
              aria-label={layoutLabel('experience_eu_years', t('app.candidate_card.fields.experience_eu'))}
              type="number"
              value={typeof extra.experience_eu_years === 'number' ? String(extra.experience_eu_years) : ''}
              onChange={(e) => onExperienceChange('experience_eu_years', e.target.value)}
              readOnly={candidateDataReadOnly}
            />
          </InlineFieldRow>
        ) : null}
        {showExperience && (!candidateProfile || layoutVisible('experience_non_eu_years')) ? (
          <InlineFieldRow
            label={layoutLabel('experience_non_eu_years', t('app.candidate_card.fields.experience_non_eu'))}
            value={years(extra.experience_non_eu_years)}
            editing={openField === 'experience_non_eu_years'}
            canEdit={!candidateDataReadOnly}
            onEdit={() => beginRow('experience_non_eu_years')}
            onDone={() => setOpenField(null)}
            onCancel={cancelRow}
          >
            <Input
              aria-label={layoutLabel('experience_non_eu_years', t('app.candidate_card.fields.experience_non_eu'))}
              type="number"
              value={typeof extra.experience_non_eu_years === 'number' ? String(extra.experience_non_eu_years) : ''}
              onChange={(e) => onExperienceChange('experience_non_eu_years', e.target.value)}
              readOnly={candidateDataReadOnly}
            />
          </InlineFieldRow>
        ) : null}
        {showMobility && (!candidateProfile || layoutVisible('trailer_types')) ? (
          <InlineFieldRow
            interaction="direct"
            contentEditor
            label={layoutLabel('trailer_types', t('app.candidate_card.ia.sections.transport_experience', { defaultValue: 'Trailer experience' }))}
            value={labels(Array.isArray(extra.trailer_types) ? extra.trailer_types : [], trailerTypeOptions)}
            editing={false}
            canEdit={!candidateDataReadOnly}
            onEdit={() => undefined}
            onDone={() => undefined}
          >
            <ChipFieldEditor
              options={trailerTypeOptions}
              values={Array.isArray(extra.trailer_types) ? extra.trailer_types : []}
              onChange={(vals) => onExtraChange({ trailer_types: vals })}
              disabled={candidateDataReadOnly}
              addLabel={t('common.actions.add')}
              dismissLabel={t('common.actions.dismiss')}
            />
          </InlineFieldRow>
        ) : null}
        {showMobility && (!candidateProfile || layoutVisible('route_types')) ? (
          <InlineFieldRow
            interaction="direct"
            contentEditor
            label={layoutLabel('route_types', t('app.candidate_card.ia.sections.route_experience', { defaultValue: 'Routes worked' }))}
            value={labels(Array.isArray(extra.route_types) ? extra.route_types : [], routeTypeOptions)}
            editing={false}
            canEdit={!candidateDataReadOnly}
            onEdit={() => undefined}
            onDone={() => undefined}
          >
            <ChipFieldEditor
              options={routeTypeOptions}
              values={Array.isArray(extra.route_types) ? extra.route_types : []}
              onChange={(vals) => onExtraChange({ route_types: vals })}
              disabled={candidateDataReadOnly}
              addLabel={t('common.actions.add')}
              dismissLabel={t('common.actions.dismiss')}
            />
          </InlineFieldRow>
        ) : null}
      </FieldGrid>
    )
  }

  if (rowEdit && part === 'history' && !editHistory && openField !== 'history') {
    return (
      <div className="space-y-1">
        {employmentHistory.length ? employmentHistory.map((entry) => (
          <InlineFieldRow
            key={entry.localId}
            label={entry.employer_name || t('app.candidate_card.employment.title')}
            value={[entry.position, entry.country].filter(Boolean).join(' · ')}
            editing={false}
            canEdit={!candidateDataReadOnly}
            onEdit={() => setOpenField('history')}
            onDone={() => setOpenField(null)}
          >
            {null}
          </InlineFieldRow>
        )) : (
          <InlineFieldRow
            label={t('app.candidate_card.employment.title')}
            value=""
            editing={false}
            canEdit={!candidateDataReadOnly}
            onEdit={() => setOpenField('history')}
            onDone={() => setOpenField(null)}
            emptyLabel={t('app.candidate_card.ia.not_filled')}
          >
            {null}
          </InlineFieldRow>
        )}
      </div>
    )
  }

  return (
    <section
      ref={experienceRef}
      id={part === 'history' ? undefined : 'section-experience'}
      className={
        plain
          ? 'scroll-mt-24'
          : embedded
            ? 'scroll-mt-24 rounded-2xl border border-slate-200 bg-white p-4'
            : 'group app-surface p-4 scroll-mt-24 transition-shadow hover:shadow-xl'
      }
    >
      {plain ? null : !embedded ? (
        <button type="button" onClick={toggle} className="flex w-full items-center justify-between gap-3 text-left">
          <div className="flex items-center gap-3">
            <IconBriefcase2 size={20} className="text-slate-600" />
            <div>
              <h2 className="text-base font-semibold text-slate-900">{t('app.candidate_card.sections.experience.title')}</h2>
            </div>
          </div>
          <IconChevronDown size={16} className={`shrink-0 text-slate-400 transition-transform ${collapsed ? '' : 'rotate-180'}`} />
        </button>
      ) : (
        <div className="flex items-center gap-3">
          <IconBriefcase2 size={20} className="text-slate-600" />
          <h2 className="text-base font-semibold text-slate-900">{t('app.candidate_card.sections.experience.title')}</h2>
        </div>
      )}

      {part !== 'history' && (embedded || !collapsed) && (!candidateProfile || layoutVisible('experience_eu_years') || layoutVisible('experience_non_eu_years')) && (
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          {(!candidateProfile || layoutVisible('experience_eu_years')) && (
            <Input
              label={layoutLabel('experience_eu_years', t('app.candidate_card.fields.experience_eu'))}
              type="number"
              value={
                typeof extra.experience_eu_years === 'number' && !Number.isNaN(extra.experience_eu_years)
                  ? String(extra.experience_eu_years)
                  : ''
              }
              onChange={(e) => onExperienceChange('experience_eu_years', e.target.value)}
              readOnly={candidateDataReadOnly}
              required={layoutRequired('experience_eu_years')}
            />
          )}
          {(!candidateProfile || layoutVisible('experience_non_eu_years')) && (
            <Input
              label={layoutLabel('experience_non_eu_years', t('app.candidate_card.fields.experience_non_eu'))}
              type="number"
              value={
                typeof extra.experience_non_eu_years === 'number' && !Number.isNaN(extra.experience_non_eu_years)
                  ? String(extra.experience_non_eu_years)
                  : ''
              }
              onChange={(e) => onExperienceChange('experience_non_eu_years', e.target.value)}
              readOnly={candidateDataReadOnly}
              required={layoutRequired('experience_non_eu_years')}
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

      {part !== 'history' && (embedded || !collapsed) && (!candidateProfile || layoutVisible('trailer_types') || layoutVisible('route_types')) && (
        <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
          {(!candidateProfile || layoutVisible('trailer_types')) && (
            <div>
              <div className="label">
                {layoutLabel('trailer_types', t('app.candidate_card.intake.fields.trailer_types'))}
                {layoutRequired('trailer_types') && <span className="text-red-600">*</span>}
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
          {(!candidateProfile || layoutVisible('route_types')) && (
            <div>
              <div className="label">
                {layoutLabel('route_types', t('app.candidate_card.intake.fields.route_types'))}
                {layoutRequired('route_types') && <span className="text-red-600">*</span>}
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

      {part !== 'skills' && (embedded || !collapsed) && (!candidateProfile || layoutVisible('employment_history')) && (
        <div className="mt-6 space-y-3">
          {rowEdit && openField === 'history' ? (
            <button type="button" className="btn-secondary btn-compact" onClick={() => setOpenField(null)}>
              {t('app.candidate_card.ia.done')}
            </button>
          ) : null}
          <div className="flex items-center justify-between">
            <div className="font-semibold text-slate-800">
              {layoutLabel('employment_history', t('app.candidate_card.employment.title'))}
              {layoutRequired('employment_history') && <span className="text-red-600">*</span>}
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
          <div className="card overflow-x-auto">
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
                      <DateInput
                        value={entry.start_date || ''}
                        disabled={candidateDataReadOnly}
                        onValueChange={(next) => onUpdateEmploymentHistory(entry.localId, 'start_date', next)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <DateInput
                        value={entry.end_date || ''}
                        disabled={candidateDataReadOnly}
                        onValueChange={(next) => onUpdateEmploymentHistory(entry.localId, 'end_date', next)}
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
