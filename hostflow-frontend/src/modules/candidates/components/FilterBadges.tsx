import clsx from 'clsx'
import type { ReactNode } from 'react'
import { useI18n } from '../../../i18n'
import type { DateRangeFilter, ColumnTextFilters, CandidateOpsMode } from '../types'
import { EMPTY_OPTION_VALUE } from '../constants'
import { isRangeActive, formatDateSafe } from '../candidateUtils'

interface FilterBadgesProps {
  q: string
  textFilters: ColumnTextFilters
  stageFilter: string[]
  vacancyFilter: string[]
  managerFilter: string[]
  statusReasonFilter: string[]
  docsStatusFilter: string[]
  docsOrderedFilter: string[]
  preferredChannelFilter: string[]
  inPolandFilter: string[]
  polandBasisFilter: string[]
  trailerTypesFilter: string[]
  opsModeFilter: CandidateOpsMode[]
  createdRange: DateRangeFilter
  firstContactRange: DateRangeFilter
  docsValidRange: DateRangeFilter
  docsHasFilesFilter: string[]
  handoffStatusFilter?: string
  contactAttemptsFilter?: string
  processorFilter?: string
  intakeApplicationKindFilter?: '' | 'client' | 'candidate'
  stageLabelMap: Record<string, string>
  vacancyLabelMap: Map<string, string>
  managerLabelMap: Map<string, string>
  reasonLabelMap: Map<string, string>
  reasonStageMap: Map<string, string>
  preferredChannelLabelMap: Record<string, string>
  inPolandLabelMap: Record<string, string>
  opsModeLabelMap: Record<CandidateOpsMode, string>
  getPolandBasisLabel: (code: string) => string
  getTrailerTypeLabel: (code: string) => string
  docsStatusOptions: Array<{ value: string; label: string }>
  docsOrderFilterOptions: Array<{ value: string; label: string }>
  locale: string
  onQChange: (value: string) => void
  onTextFilterChange: (key: keyof ColumnTextFilters, value: string) => void
  onStageFilterChange: (filter: (prev: string[]) => string[]) => void
  onVacancyFilterChange: (filter: (prev: string[]) => string[]) => void
  onManagerFilterChange: (filter: (prev: string[]) => string[]) => void
  onStatusReasonFilterChange: (filter: (prev: string[]) => string[]) => void
  onDocsStatusFilterChange: (filter: (prev: string[]) => string[]) => void
  onDocsOrderedFilterChange: (filter: (prev: string[]) => string[]) => void
  onPreferredChannelFilterChange: (filter: (prev: string[]) => string[]) => void
  onInPolandFilterChange: (filter: (prev: string[]) => string[]) => void
  onPolandBasisFilterChange: (filter: (prev: string[]) => string[]) => void
  onTrailerTypesFilterChange: (filter: (prev: string[]) => string[]) => void
  onOpsModeFilterChange: (filter: (prev: CandidateOpsMode[]) => CandidateOpsMode[]) => void
  onCreatedRangeChange: (range: DateRangeFilter) => void
  onFirstContactRangeChange: (range: DateRangeFilter) => void
  onDocsValidRangeChange: (range: DateRangeFilter) => void
  onDocsHasFilesFilterChange: (filter: (prev: string[]) => string[]) => void
  onHandoffStatusFilterChange?: (value: string) => void
  onContactAttemptsFilterChange?: (value: string) => void
  onProcessorFilterChange?: (value: string) => void
  onIntakeApplicationKindFilterChange?: (value: '' | 'client' | 'candidate') => void
  /** When true: compact row inside filter toolbar card (no sticky, less padding). */
  embedded?: boolean
}

export function FilterBadges({
  q,
  textFilters,
  stageFilter,
  vacancyFilter,
  managerFilter,
  statusReasonFilter,
  docsStatusFilter,
  docsOrderedFilter,
  preferredChannelFilter,
  inPolandFilter,
  polandBasisFilter,
  trailerTypesFilter,
  opsModeFilter,
  createdRange,
  firstContactRange,
  docsValidRange,
  docsHasFilesFilter,
  handoffStatusFilter = '',
  contactAttemptsFilter = '',
  processorFilter = '',
  intakeApplicationKindFilter = '',
  stageLabelMap,
  vacancyLabelMap,
  managerLabelMap,
  reasonLabelMap,
  reasonStageMap,
  preferredChannelLabelMap,
  inPolandLabelMap,
  opsModeLabelMap,
  getPolandBasisLabel,
  getTrailerTypeLabel,
  docsStatusOptions,
  docsOrderFilterOptions,
  locale,
  onQChange,
  onTextFilterChange,
  onStageFilterChange,
  onVacancyFilterChange,
  onManagerFilterChange,
  onStatusReasonFilterChange,
  onDocsStatusFilterChange,
  onDocsOrderedFilterChange,
  onPreferredChannelFilterChange,
  onInPolandFilterChange,
  onPolandBasisFilterChange,
  onTrailerTypesFilterChange,
  onOpsModeFilterChange,
  onCreatedRangeChange,
  onFirstContactRangeChange,
  onDocsValidRangeChange,
  onDocsHasFilesFilterChange,
  onHandoffStatusFilterChange,
  onContactAttemptsFilterChange,
  onProcessorFilterChange,
  onIntakeApplicationKindFilterChange,
  embedded = false,
}: FilterBadgesProps) {
  const { t } = useI18n()
  const removeGlyph = '\u00D7'

  return (
    <div
      className={clsx(
        'flex flex-wrap items-center bg-white',
        embedded
          ? 'gap-1 border-t border-slate-100 px-2 py-1 sm:px-2.5 sm:py-1.5'
          : 'sticky top-0 z-10 gap-2 border-b p-4',
      )}
    >
      {q && (
        <span className="badge">
          {t('app.candidates.filters.search', { values: { value: q } })}
          <button className="ml-2 text-xs" onClick={() => onQChange('')}>{removeGlyph}</button>
        </span>
      )}
      {textFilters.name.trim() && (
        <span className="badge">
          {t('app.candidates.filters.name_badge', { values: { value: textFilters.name } })}
          <button className="ml-2 text-xs" onClick={() => onTextFilterChange('name', '')}>{removeGlyph}</button>
        </span>
      )}
      {textFilters.email.trim() && (
        <span className="badge">
          {t('app.candidates.filters.email_badge', { values: { value: textFilters.email } })}
          <button className="ml-2 text-xs" onClick={() => onTextFilterChange('email', '')}>{removeGlyph}</button>
        </span>
      )}
      {textFilters.phone.trim() && (
        <span className="badge">
          {t('app.candidates.filters.phone_badge', { values: { value: textFilters.phone } })}
          <button className="ml-2 text-xs" onClick={() => onTextFilterChange('phone', '')}>{removeGlyph}</button>
        </span>
      )}
      {textFilters.citizenship.trim() && (
        <span className="badge">
          {t('app.candidates.filters.citizenship_badge', { values: { value: textFilters.citizenship } })}
          <button className="ml-2 text-xs" onClick={() => onTextFilterChange('citizenship', '')}>{removeGlyph}</button>
        </span>
      )}
      {textFilters.short.trim() && (
        <span className="badge">
          {t('app.candidates.filters.short_badge', { values: { value: textFilters.short } })}
          <button className="ml-2 text-xs" onClick={() => onTextFilterChange('short', '')}>{removeGlyph}</button>
        </span>
      )}
      {stageFilter.map((code) => (
        <span className="badge" key={`stage-${code}`}>
          {t('app.candidates.filters.stage', { values: { value: stageLabelMap[code] || code } })}
          <button className="ml-2 text-xs" onClick={() => onStageFilterChange((prev) => prev.filter((item) => item !== code))}>{removeGlyph}</button>
        </span>
      ))}
      {vacancyFilter.map((id) => (
        <span className="badge" key={`vacancy-${id}`}>
          {t('app.candidates.filters.vacancy', { values: { value: vacancyLabelMap.get(id) || '—' } })}
          <button className="ml-2 text-xs" onClick={() => onVacancyFilterChange((prev) => prev.filter((item) => item !== id))}>{removeGlyph}</button>
        </span>
      ))}
      {managerFilter.map((id) => (
        <span className="badge" key={`manager-${id}`}>
          {t('app.candidates.filters.manager', { values: { value: managerLabelMap.get(id) || '—' } })}
          <button className="ml-2 text-xs" onClick={() => onManagerFilterChange((prev) => prev.filter((item) => item !== id))}>{removeGlyph}</button>
        </span>
      ))}
      {statusReasonFilter.map((code) => (
        <span className="badge" key={`reason-${code}`}>
          {t('app.candidates.filters.reason', { values: { value: reasonLabelMap.get(code) || code } })}
          <span className="ml-1 text-xs text-slate-500">
            {t('app.candidates.filters.reason_stage', { values: { stage: reasonStageMap.get(code) || '—' } })}
          </span>
          <button
            className="ml-2 text-xs"
            onClick={() => onStatusReasonFilterChange((prev) => prev.filter((item) => item !== code))}
          >
            {removeGlyph}
          </button>
        </span>
      ))}
      {docsStatusFilter.map((value) => {
        const entry = docsStatusOptions.find((option) => option.value === value)
        return (
          <span className="badge" key={`docs-status-${value}`}>
            {t('app.candidates.filters.docs_status', { values: { value: entry?.label || value } })}
            <button className="ml-2 text-xs" onClick={() => onDocsStatusFilterChange((prev) => prev.filter((item) => item !== value))}>{removeGlyph}</button>
          </span>
        )
      })}
      {docsOrderedFilter.map((value) => {
        const entry = docsOrderFilterOptions.find((option) => option.value === value)
        return (
          <span className="badge" key={`docs-ordered-${value}`}>
            {t('app.candidates.filters.docs_order', { values: { value: entry?.label || value } })}
            <button className="ml-2 text-xs" onClick={() => onDocsOrderedFilterChange((prev) => prev.filter((item) => item !== value))}>{removeGlyph}</button>
          </span>
        )
      })}
      {preferredChannelFilter.map((value) => (
        <span className="badge" key={`preferred-${value}`}>
          {t('app.candidates.filters.preferred_channel', {
            values: { value: preferredChannelLabelMap[value] ?? value },
          })}
          <button className="ml-2 text-xs" onClick={() => onPreferredChannelFilterChange((prev) => prev.filter((item) => item !== value))}>{removeGlyph}</button>
        </span>
      ))}
      {inPolandFilter.map((value) => (
        <span className="badge" key={`poland-now-${value}`}>
          {t('app.candidates.filters.in_poland', { values: { value: inPolandLabelMap[value] || value } })}
          <button className="ml-2 text-xs" onClick={() => onInPolandFilterChange((prev) => prev.filter((item) => item !== value))}>{removeGlyph}</button>
        </span>
      ))}
      {polandBasisFilter.map((value) => (
        <span className="badge" key={`poland-basis-${value}`}>
          {t('app.candidates.filters.poland_basis', {
            values: { value: value === EMPTY_OPTION_VALUE ? t('common.labels.not_available') : getPolandBasisLabel(value) },
          })}
          <button className="ml-2 text-xs" onClick={() => onPolandBasisFilterChange((prev) => prev.filter((item) => item !== value))}>{removeGlyph}</button>
        </span>
      ))}
      {trailerTypesFilter.map((value) => (
        <span className="badge" key={`trailer-${value}`}>
          {t('app.candidates.filters.trailer_types', { values: { value: getTrailerTypeLabel(value) } })}
          <button className="ml-2 text-xs" onClick={() => onTrailerTypesFilterChange((prev) => prev.filter((item) => item !== value))}>{removeGlyph}</button>
        </span>
      ))}
      {opsModeFilter.map((value) => (
        <span className="badge" key={`ops-mode-${value}`}>
          {t('app.candidates.filters.ops_mode', { values: { value: opsModeLabelMap[value] || value } })}
          <button className="ml-2 text-xs" onClick={() => onOpsModeFilterChange((prev) => prev.filter((item) => item !== value))}>{removeGlyph}</button>
        </span>
      ))}
      {isRangeActive(createdRange) && (
        <span className="badge">
          {t('app.candidates.filters.created_range', {
            values: { from: createdRange.from || '—', to: createdRange.to || '—' },
          })}
          <button className="ml-2 text-xs" onClick={() => onCreatedRangeChange({ from: null, to: null })}>{removeGlyph}</button>
        </span>
      )}
      {isRangeActive(firstContactRange) && (
        <span className="badge">
          {t('app.candidates.filters.first_contact_range', {
            values: { from: firstContactRange.from || '—', to: firstContactRange.to || '—' },
          })}
          <button className="ml-2 text-xs" onClick={() => onFirstContactRangeChange({ from: null, to: null })}>{removeGlyph}</button>
        </span>
      )}
      {isRangeActive(docsValidRange) && (
        <span className="badge">
          {t('app.candidates.filters.docs_valid_range', {
            values: { from: docsValidRange.from || '—', to: docsValidRange.to || '—' },
          })}
          <button className="ml-2 text-xs" onClick={() => onDocsValidRangeChange({ from: null, to: null })}>{removeGlyph}</button>
        </span>
      )}
      {docsHasFilesFilter.map((value) => (
        <span className="badge" key={`docs-files-${value}`}>
          {t('app.candidates.filters.docs_files_badge', {
            values: {
              value:
                value === 'with'
                  ? t('app.candidates.filters.docs_files_with')
                  : t('app.candidates.filters.docs_files_without'),
            },
          })}
          <button className="ml-2 text-xs" onClick={() => onDocsHasFilesFilterChange((prev) => prev.filter((item) => item !== value))}>{removeGlyph}</button>
        </span>
      ))}
      {handoffStatusFilter && onHandoffStatusFilterChange && (
        <span className="badge">
          {t('app.candidates.filters.handoff_badge', {
            values: { value: t(`app.candidates.filters.handoff_${handoffStatusFilter}` as any) || handoffStatusFilter },
          })}
          <button className="ml-2 text-xs" onClick={() => onHandoffStatusFilterChange('')}>{removeGlyph}</button>
        </span>
      )}
      {contactAttemptsFilter && onContactAttemptsFilterChange && (
        <span className="badge">
          {t('app.candidates.filters.contact_attempts_badge', {
            values: {
              value:
                contactAttemptsFilter === 'limit_reached'
                  ? (t('app.candidates.filters.contact_limit') as string)
                  : (t(`app.candidates.filters.contact_${contactAttemptsFilter}` as any) as string) || contactAttemptsFilter,
            },
          })}
          <button className="ml-2 text-xs" onClick={() => onContactAttemptsFilterChange('')}>{removeGlyph}</button>
        </span>
      )}
      {intakeApplicationKindFilter && onIntakeApplicationKindFilterChange && (
        <span className="badge">
          {t('app.candidates.filters.intake_kind_badge', {
            values: {
              value:
                intakeApplicationKindFilter === 'client'
                  ? (t('app.candidates.filters.intake_kind_client') as string)
                  : (t('app.candidates.filters.intake_kind_candidate') as string),
            },
          })}
          <button className="ml-2 text-xs" onClick={() => onIntakeApplicationKindFilterChange('')}>{removeGlyph}</button>
        </span>
      )}
    </div>
  )
}
