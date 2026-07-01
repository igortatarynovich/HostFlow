import clsx from 'clsx'
import type { ReactNode } from 'react'
import { Chip } from '../../../components/ui/Chip'
import { useI18n } from '../../../i18n'
import type { DateRangeFilter, ColumnTextFilters, CandidateOpsMode } from '../types'
import { EMPTY_OPTION_VALUE } from '../constants'
import { isRangeActive } from '../candidateUtils'

function DismissFilterChip({
  label,
  onDismiss,
  dismissLabel,
}: {
  label: ReactNode
  onDismiss: () => void
  dismissLabel: string
}) {
  return (
    <Chip
      behavior="dismissible"
      label={label}
      onDismiss={onDismiss}
      dismissLabel={dismissLabel}
    />
  )
}

interface FilterBadgesProps {
  q: string
  textFilters: ColumnTextFilters
  stageFilter: string[]
  vacancyFilter: string[]
  candidateRowStatusFilter?: string[]
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
  /** Human-readable label for row-level ``status`` filter codes (never raw JSON in badges). */
  candidateRowStatusLabel?: (code: string) => string
  locale: string
  onQChange: (value: string) => void
  onTextFilterChange: (key: keyof ColumnTextFilters, value: string) => void
  onStageFilterChange: (filter: (prev: string[]) => string[]) => void
  onCandidateRowStatusFilterChange?: (filter: (prev: string[]) => string[]) => void
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
  candidateRowStatusFilter = [],
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
  candidateRowStatusLabel,
  locale,
  onQChange,
  onTextFilterChange,
  onStageFilterChange,
  onCandidateRowStatusFilterChange,
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
  const dismissLabel = t('common.actions.remove', { defaultValue: 'Remove' })

  const chip = (label: ReactNode, onDismiss: () => void) => (
    <DismissFilterChip label={label} onDismiss={onDismiss} dismissLabel={dismissLabel} />
  )

  return (
    <div
      className={clsx(
        'flex flex-wrap items-center bg-white',
        embedded
          ? 'gap-1 border-t border-slate-100 px-2 py-1 sm:px-2.5 sm:py-1.5'
          : 'sticky top-0 z-10 gap-2 border-b p-4',
      )}
    >
      {q && chip(t('app.candidates.filters.search', { values: { value: q } }), () => onQChange(''))}
      {textFilters.name.trim() &&
        chip(t('app.candidates.filters.name_badge', { values: { value: textFilters.name } }), () =>
          onTextFilterChange('name', ''),
        )}
      {textFilters.email.trim() &&
        chip(t('app.candidates.filters.email_badge', { values: { value: textFilters.email } }), () =>
          onTextFilterChange('email', ''),
        )}
      {textFilters.phone.trim() &&
        chip(t('app.candidates.filters.phone_badge', { values: { value: textFilters.phone } }), () =>
          onTextFilterChange('phone', ''),
        )}
      {textFilters.citizenship.trim() &&
        chip(t('app.candidates.filters.citizenship_badge', { values: { value: textFilters.citizenship } }), () =>
          onTextFilterChange('citizenship', ''),
        )}
      {textFilters.short.trim() &&
        chip(t('app.candidates.filters.short_badge', { values: { value: textFilters.short } }), () =>
          onTextFilterChange('short', ''),
        )}
      {stageFilter.map((code) => (
        <DismissFilterChip
          key={`stage-${code}`}
          label={t('app.candidates.filters.stage', { values: { value: stageLabelMap[code] || code } })}
          onDismiss={() => onStageFilterChange((prev) => prev.filter((item) => item !== code))}
          dismissLabel={dismissLabel}
        />
      ))}
      {candidateRowStatusFilter.map((code) => (
        <DismissFilterChip
          key={`row-status-${code}`}
          label={t('app.candidates.filters.row_status_badge', {
            values: { value: candidateRowStatusLabel ? candidateRowStatusLabel(code) : code },
          })}
          onDismiss={() => onCandidateRowStatusFilterChange?.((prev) => prev.filter((item) => item !== code))}
          dismissLabel={dismissLabel}
        />
      ))}
      {vacancyFilter.map((id) => (
        <DismissFilterChip
          key={`vacancy-${id}`}
          label={t('app.candidates.filters.vacancy', { values: { value: vacancyLabelMap.get(id) || '—' } })}
          onDismiss={() => onVacancyFilterChange((prev) => prev.filter((item) => item !== id))}
          dismissLabel={dismissLabel}
        />
      ))}
      {managerFilter.map((id) => (
        <DismissFilterChip
          key={`manager-${id}`}
          label={t('app.candidates.filters.manager', { values: { value: managerLabelMap.get(id) || '—' } })}
          onDismiss={() => onManagerFilterChange((prev) => prev.filter((item) => item !== id))}
          dismissLabel={dismissLabel}
        />
      ))}
      {statusReasonFilter.map((code) => (
        <DismissFilterChip
          key={`reason-${code}`}
          label={
            <>
              {t('app.candidates.filters.reason', { values: { value: reasonLabelMap.get(code) || code } })}
              <span className="ml-1 text-xs text-slate-500">
                {t('app.candidates.filters.reason_stage', { values: { stage: reasonStageMap.get(code) || '—' } })}
              </span>
            </>
          }
          onDismiss={() => onStatusReasonFilterChange((prev) => prev.filter((item) => item !== code))}
          dismissLabel={dismissLabel}
        />
      ))}
      {docsStatusFilter.map((value) => {
        const entry = docsStatusOptions.find((option) => option.value === value)
        return (
          <DismissFilterChip
            key={`docs-status-${value}`}
            label={t('app.candidates.filters.docs_status', { values: { value: entry?.label || value } })}
            onDismiss={() => onDocsStatusFilterChange((prev) => prev.filter((item) => item !== value))}
            dismissLabel={dismissLabel}
          />
        )
      })}
      {docsOrderedFilter.map((value) => {
        const entry = docsOrderFilterOptions.find((option) => option.value === value)
        return (
          <DismissFilterChip
            key={`docs-ordered-${value}`}
            label={t('app.candidates.filters.docs_order', { values: { value: entry?.label || value } })}
            onDismiss={() => onDocsOrderedFilterChange((prev) => prev.filter((item) => item !== value))}
            dismissLabel={dismissLabel}
          />
        )
      })}
      {preferredChannelFilter.map((value) => (
        <DismissFilterChip
          key={`preferred-${value}`}
          label={t('app.candidates.filters.preferred_channel', {
            values: { value: preferredChannelLabelMap[value] ?? value },
          })}
          onDismiss={() => onPreferredChannelFilterChange((prev) => prev.filter((item) => item !== value))}
          dismissLabel={dismissLabel}
        />
      ))}
      {inPolandFilter.map((value) => (
        <DismissFilterChip
          key={`poland-now-${value}`}
          label={t('app.candidates.filters.in_poland', { values: { value: inPolandLabelMap[value] || value } })}
          onDismiss={() => onInPolandFilterChange((prev) => prev.filter((item) => item !== value))}
          dismissLabel={dismissLabel}
        />
      ))}
      {polandBasisFilter.map((value) => (
        <DismissFilterChip
          key={`poland-basis-${value}`}
          label={t('app.candidates.filters.poland_basis', {
            values: { value: value === EMPTY_OPTION_VALUE ? t('common.labels.not_available') : getPolandBasisLabel(value) },
          })}
          onDismiss={() => onPolandBasisFilterChange((prev) => prev.filter((item) => item !== value))}
          dismissLabel={dismissLabel}
        />
      ))}
      {trailerTypesFilter.map((value) => (
        <DismissFilterChip
          key={`trailer-${value}`}
          label={t('app.candidates.filters.trailer_types', { values: { value: getTrailerTypeLabel(value) } })}
          onDismiss={() => onTrailerTypesFilterChange((prev) => prev.filter((item) => item !== value))}
          dismissLabel={dismissLabel}
        />
      ))}
      {opsModeFilter.map((value) => (
        <DismissFilterChip
          key={`ops-mode-${value}`}
          label={t('app.candidates.filters.ops_mode', { values: { value: opsModeLabelMap[value] || value } })}
          onDismiss={() => onOpsModeFilterChange((prev) => prev.filter((item) => item !== value))}
          dismissLabel={dismissLabel}
        />
      ))}
      {isRangeActive(createdRange) &&
        chip(
          t('app.candidates.filters.created_range', {
            values: { from: createdRange.from || '—', to: createdRange.to || '—' },
          }),
          () => onCreatedRangeChange({ from: null, to: null }),
        )}
      {isRangeActive(firstContactRange) &&
        chip(
          t('app.candidates.filters.first_contact_range', {
            values: { from: firstContactRange.from || '—', to: firstContactRange.to || '—' },
          }),
          () => onFirstContactRangeChange({ from: null, to: null }),
        )}
      {isRangeActive(docsValidRange) &&
        chip(
          t('app.candidates.filters.docs_valid_range', {
            values: { from: docsValidRange.from || '—', to: docsValidRange.to || '—' },
          }),
          () => onDocsValidRangeChange({ from: null, to: null }),
        )}
      {docsHasFilesFilter.map((value) => (
        <DismissFilterChip
          key={`docs-files-${value}`}
          label={t('app.candidates.filters.docs_files_badge', {
            values: {
              value:
                value === 'with'
                  ? t('app.candidates.filters.docs_files_with')
                  : t('app.candidates.filters.docs_files_without'),
            },
          })}
          onDismiss={() => onDocsHasFilesFilterChange((prev) => prev.filter((item) => item !== value))}
          dismissLabel={dismissLabel}
        />
      ))}
      {handoffStatusFilter &&
        onHandoffStatusFilterChange &&
        chip(
          t('app.candidates.filters.handoff_badge', {
            values: { value: t(`app.candidates.filters.handoff_${handoffStatusFilter}` as any) || handoffStatusFilter },
          }),
          () => onHandoffStatusFilterChange(''),
        )}
      {contactAttemptsFilter &&
        onContactAttemptsFilterChange &&
        chip(
          t('app.candidates.filters.contact_attempts_badge', {
            values: {
              value:
                contactAttemptsFilter === 'limit_reached'
                  ? (t('app.candidates.filters.contact_limit') as string)
                  : (t(`app.candidates.filters.contact_${contactAttemptsFilter}` as any) as string) ||
                    contactAttemptsFilter,
            },
          }),
          () => onContactAttemptsFilterChange(''),
        )}
      {intakeApplicationKindFilter &&
        onIntakeApplicationKindFilterChange &&
        chip(
          t('app.candidates.filters.intake_kind_badge', {
            values: {
              value:
                intakeApplicationKindFilter === 'client'
                  ? (t('app.candidates.filters.intake_kind_client') as string)
                  : (t('app.candidates.filters.intake_kind_candidate') as string),
            },
          }),
          () => onIntakeApplicationKindFilterChange(''),
        )}
    </div>
  )
}
