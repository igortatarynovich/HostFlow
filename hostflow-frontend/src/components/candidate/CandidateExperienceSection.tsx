import { memo, useState, useCallback, useEffect, useRef, type ReactNode } from 'react'
import { api } from '../../api/client'
import { IconBriefcase2, IconChevronDown } from '@tabler/icons-react'
import type { CandidateExtra } from '../../api/types'
import type { RefObject } from 'react'
import type { CandidateProfile } from '../../api/candidate_profiles'
import type { EffectiveCardLayout } from '../../api/fieldRegistry'
import DateInput from '../controls/DateInput'
import { useI18n } from '../../i18n'
import { Input, CheckboxMultiSelect } from './shared/FormComponents'
import { ChipFieldEditor } from '../ui/ChipFieldEditor'
import { Combobox } from '../ui/Combobox'
import { MultiCombobox } from '../ui/MultiCombobox'
import { FieldGrid } from '../ui/FieldGrid'
import { InlineFieldRow } from '../ui/InlineFieldRow'
import { isFieldVisible, isFieldRequired, getFieldLabel } from '../../utils/profileUtils'
import { formatYearsCount } from '../../modules/candidate-card/utils'
import { presentProfessionalCode } from '../../modules/professional-profile/presentation'

type Option = { value: string; label: string; extra?: any }
type EmploymentRow = {
  id?: string
  localId: string
  employer_name: string
  country: string
  position: string
  start_date: string
  end_date: string
  driving_categories?: string[]
  operation_scopes?: string[]
  movement_patterns?: string[]
  crew_modes?: string[]
  trailer_types?: string[]
  work_areas?: Array<{ kind: 'country' | 'region'; code: string }>
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
  onUpdateEmploymentFacets?: (
    localId: string,
    patch: Partial<Pick<EmploymentRow, 'driving_categories' | 'operation_scopes' | 'movement_patterns' | 'crew_modes' | 'trailer_types' | 'work_areas'>>,
  ) => void
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
  /** ISO country catalog already loaded for the card. */
  countryOptions?: Option[]
  candidateId?: string | null
}

function LabeledControl({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="label">{label}</span>
      {children}
    </label>
  )
}

const FALLBACK_DRIVING_CATEGORIES = ['B', 'C', 'C1', 'C1E', 'CE', 'D', 'DE']

function EmploymentEditorCard({
  entry,
  readOnly,
  countryOptions,
  drivingCategoryOptions,
  onUpdateEmploymentHistory,
  onUpdateEmploymentFacets,
  onRemoveEmploymentRow,
}: {
  entry: EmploymentRow
  readOnly: boolean
  countryOptions: Option[]
  drivingCategoryOptions: Option[]
  onUpdateEmploymentHistory: CandidateExperienceSectionProps['onUpdateEmploymentHistory']
  onUpdateEmploymentFacets?: CandidateExperienceSectionProps['onUpdateEmploymentFacets']
  onRemoveEmploymentRow: (localId: string) => void
}) {
  const { t, locale } = useI18n()
  const codes = (vocabulary: string, values: string[]) => values.map((code) => ({
    value: code,
    label: presentProfessionalCode(vocabulary, code, locale) || code,
  }))
  const areas = entry.work_areas?.filter((area) => area.kind === 'region').map((area) => area.code) ?? []
  const drivingCatalog = drivingCategoryOptions.length
    ? drivingCategoryOptions
    : FALLBACK_DRIVING_CATEGORIES.map((code) => ({ value: code, label: code }))
  const drivingOptions = [
    ...drivingCatalog,
    ...(entry.driving_categories ?? [])
      .filter((code) => !drivingCatalog.some((option) => option.value === code))
      .map((code) => ({ value: code, label: code })),
  ]
  const knownCountries = entry.country && !countryOptions.some((option) => option.value === entry.country)
    ? [{ value: entry.country, label: entry.country }, ...countryOptions]
    : countryOptions
  const character = [
    {
      label: t('app.candidate_card.profile_projection.licence', { defaultValue: 'Категории' }),
      control: (
        <MultiCombobox
          options={drivingOptions}
          values={entry.driving_categories ?? []}
          disabled={readOnly}
          placeholder={t('app.candidate_card.ia.not_filled')}
          onChange={(values) => onUpdateEmploymentFacets?.(entry.localId, { driving_categories: values })}
        />
      ),
    },
    {
      label: t('app.candidate_card.profile_projection.operation_scope', { defaultValue: 'Тип рейсов' }),
      control: (
        <MultiCombobox
          options={codes('operation_scope', ['international', 'domestic'])}
          values={entry.operation_scopes ?? []}
          disabled={readOnly}
          placeholder={t('app.candidate_card.ia.not_filled')}
          onChange={(values) => onUpdateEmploymentFacets?.(entry.localId, { operation_scopes: values })}
        />
      ),
    },
    {
      label: t('app.candidate_card.profile_projection.movement', { defaultValue: 'Характер рейсов' }),
      control: (
        <MultiCombobox
          options={codes('movement_pattern', ['long_haul', 'distribution'])}
          values={entry.movement_patterns ?? []}
          disabled={readOnly}
          placeholder={t('app.candidate_card.ia.not_filled')}
          onChange={(values) => onUpdateEmploymentFacets?.(entry.localId, { movement_patterns: values })}
        />
      ),
    },
    {
      label: t('app.candidate_card.profile_projection.crew', { defaultValue: 'Экипаж' }),
      control: (
        <MultiCombobox
          options={codes('crew_mode', ['solo', 'double'])}
          values={entry.crew_modes ?? []}
          disabled={readOnly}
          placeholder={t('app.candidate_card.ia.not_filled')}
          onChange={(values) => onUpdateEmploymentFacets?.(entry.localId, { crew_modes: values })}
        />
      ),
    },
    {
      label: t('app.candidate_card.profile_projection.trailers', { defaultValue: 'Прицепы' }),
      control: (
        <MultiCombobox
          options={codes('trailer_hiring', ['curtain', 'reefer', 'container', 'tanker', 'dump', 'platform'])}
          values={entry.trailer_types ?? []}
          disabled={readOnly}
          placeholder={t('app.candidate_card.ia.not_filled')}
          onChange={(values) => onUpdateEmploymentFacets?.(entry.localId, { trailer_types: values })}
        />
      ),
    },
    {
      label: t('app.candidate_card.profile_projection.geography', { defaultValue: 'География' }),
      control: (
        <MultiCombobox
          options={codes('work_area_region', ['eu', 'cis', 'uk', 'scandi', 'local'])}
          values={areas}
          disabled={readOnly}
          placeholder={t('app.candidate_card.ia.not_filled')}
          onChange={(values) => onUpdateEmploymentFacets?.(entry.localId, {
            work_areas: values.map((code) => ({ kind: 'region' as const, code })),
          })}
        />
      ),
    },
  ]
  return (
    <div className="space-y-3" data-testid={`employment-editor-${entry.localId}`}>
      <div className="grid gap-3 md:grid-cols-4">
        <LabeledControl label={t('app.candidate_card.employment.columns.employer')}>
          <input
            className="input w-full"
            value={entry.employer_name || ''}
            onChange={(e) => onUpdateEmploymentHistory(entry.localId, 'employer_name', e.target.value)}
            readOnly={readOnly}
          />
        </LabeledControl>
        <LabeledControl label={t('app.candidate_card.employment.columns.country')}>
          {knownCountries.length ? (
            <Combobox
              options={knownCountries}
              value={entry.country || ''}
              disabled={readOnly}
              placeholder={t('app.candidate_card.select.empty')}
              searchPlaceholder={t('app.candidate_card.select.search')}
              noResultsLabel={t('app.candidate_card.select.no_results')}
              onChange={(next) => onUpdateEmploymentHistory(entry.localId, 'country', next)}
            />
          ) : (
            <input
              className="input w-full"
              value={entry.country || ''}
              onChange={(e) => onUpdateEmploymentHistory(entry.localId, 'country', e.target.value.toUpperCase())}
              readOnly={readOnly}
            />
          )}
        </LabeledControl>
        <LabeledControl label={t('app.candidate_card.employment.columns.position')}>
          <input
            className="input w-full"
            value={entry.position || ''}
            onChange={(e) => onUpdateEmploymentHistory(entry.localId, 'position', e.target.value)}
            readOnly={readOnly}
          />
        </LabeledControl>
        <LabeledControl label={t('app.candidate_card.profile_projection.period', { defaultValue: 'Период' })}>
          <div className="grid grid-cols-2 gap-2">
            <DateInput
              value={entry.start_date || ''}
              disabled={readOnly}
              onValueChange={(next) => onUpdateEmploymentHistory(entry.localId, 'start_date', next)}
            />
            <DateInput
              value={entry.end_date || ''}
              disabled={readOnly}
              onValueChange={(next) => onUpdateEmploymentHistory(entry.localId, 'end_date', next)}
            />
          </div>
        </LabeledControl>
      </div>
      <div className="space-y-3 bg-slate-50 p-3">
        <div className="text-sm font-medium text-slate-700">
          {t('app.candidate_card.profile_projection.work_character', { defaultValue: 'Характер работы' })}
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {character.map((field) => (
            <LabeledControl key={field.label} label={field.label}>
              {field.control}
            </LabeledControl>
          ))}
        </div>
      </div>
      <button
        type="button"
        className="btn-danger btn-sm"
        disabled={readOnly}
        onClick={() => onRemoveEmploymentRow(entry.localId)}
      >
        {t('common.actions.delete')}
      </button>
    </div>
  )
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
  onUpdateEmploymentFacets,
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
  countryOptions = [],
  candidateId,
}: CandidateExperienceSectionProps) {
  const { t, locale } = useI18n()
  const [drivingCategoryOptions, setDrivingCategoryOptions] = useState<Option[]>([])
  useEffect(() => {
    if (!editHistory || !candidateId) return
    let cancelled = false
    void api.get<{ licence_category_codes?: string[] }>(`/candidates/${candidateId}/operator-facts`)
      .then((response) => {
        if (cancelled) return
        const codes = response.data.licence_category_codes ?? []
        setDrivingCategoryOptions(codes.map((code) => ({ value: code, label: code })))
      })
      .catch(() => {
        if (!cancelled) setDrivingCategoryOptions([])
      })
    return () => {
      cancelled = true
    }
  }, [editHistory, candidateId])
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
          <div className="space-y-4">
            {employmentHistory.map((entry) => (
              <EmploymentEditorCard
                key={entry.id ?? entry.localId}
                entry={entry}
                readOnly={candidateDataReadOnly}
                countryOptions={countryOptions}
                drivingCategoryOptions={drivingCategoryOptions}
                onUpdateEmploymentHistory={onUpdateEmploymentHistory}
                onUpdateEmploymentFacets={onUpdateEmploymentFacets}
                onRemoveEmploymentRow={onRemoveEmploymentRow}
              />
            ))}
          </div>
        )}
        </div>
      )}
    </section>
  )
}

export default memo(CandidateExperienceSection)
