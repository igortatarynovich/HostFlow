// src/modules/candidates/components/CandidatesFiltersToolbar.tsx
//
// The full filters toolbar shown above the Candidates table:
//   1. Free-text search input
//   2. Quick-views bar (hidden when work-panel rail is open — rail owns those controls)
//   3. <FilterBadges /> strip (only when at least one filter is active)
//
// Extracted from `src/pages/Candidates.tsx` (Phase 1 #4 god-component
// split) — about 150 LOC of JSX moved here behind a single `ctx` prop
// so the call site stays a one-liner.

import { type Dispatch, type Ref, type SetStateAction } from 'react'
import { CandidatesQuickViewsBar, type QuickDocFilter, type QuickViewKey, type OperationalChip } from './CandidatesQuickViewsBar'
import { FilterBadges } from './FilterBadges'
import type { TranslateFn, LocaleCode } from '../../../i18n'
import type { UserSavedView } from '../../../api/types'
import type {
  CandidateOpsMode,
  ColumnTextFilters,
  DateRangeFilter,
  ManagerItem,
} from '../types'

interface VacancyLite {
  id: string
  title?: string
}

interface FilterOption {
  value: string
  label: string
}

export interface CandidatesFiltersToolbarProps {
  t: TranslateFn
  locale: LocaleCode

  // ---- search ---------------------------------------------------------
  q: string
  setQ: Dispatch<SetStateAction<string>>
  searchRef: Ref<HTMLInputElement>

  // ---- quick views bar -----------------------------------------------
  quickViewParam: string
  applyQuickViewFilters: (key: QuickViewKey, opts: { syncUrl: boolean }) => void | Promise<void>
  isFavoriteFilter: boolean | null
  setIsFavoriteFilter: Dispatch<SetStateAction<boolean | null>>
  quickDocFilters: QuickDocFilter[]
  quickFiltersExpanded: boolean
  toggleQuickDocFilter: (statuses: string[], active: boolean) => void
  setQuickFiltersExpanded: (updater: (prev: boolean) => boolean) => void
  /** Replaces favorites + doc chips in the table toolbar when non-empty. */
  operationalChips?: OperationalChip[]
  savedViews: UserSavedView[]
  applyView: (view: UserSavedView) => void
  deleteView: (id: string) => void | Promise<void>

  /** Hide quick-view chips / saved views (shown in the work-panel rail instead). */
  hideQuickViews?: boolean

  // ---- quick-filter selects ------------------------------------------
  stageOptions: string[]
  stageLabelMap: Record<string, string>
  managers: ManagerItem[]
  vacancies: VacancyLite[]

  // ---- filter values + setters ---------------------------------------
  stageFilter: string[]
  setStageFilter: Dispatch<SetStateAction<string[]>>
  candidateRowStatusFilter: string[]
  setCandidateRowStatusFilter: Dispatch<SetStateAction<string[]>>
  managerFilter: string[]
  setManagerFilter: Dispatch<SetStateAction<string[]>>
  vacancyFilter: string[]
  setVacancyFilter: Dispatch<SetStateAction<string[]>>

  // ---- filter badges (full filter state) -----------------------------
  hasFilterBadges: boolean
  textFilters: ColumnTextFilters
  setTextFilter: (key: keyof ColumnTextFilters, value: string) => void
  statusReasonFilter: string[]
  setStatusReasonFilter: Dispatch<SetStateAction<string[]>>
  docsStatusFilter: string[]
  setDocsStatusFilter: Dispatch<SetStateAction<string[]>>
  docsOrderedFilter: string[]
  setDocsOrderedFilter: Dispatch<SetStateAction<string[]>>
  preferredChannelFilter: string[]
  setPreferredChannelFilter: Dispatch<SetStateAction<string[]>>
  inPolandFilter: string[]
  setInPolandFilter: Dispatch<SetStateAction<string[]>>
  opsModeFilter: CandidateOpsMode[]
  setOpsModeFilter: Dispatch<SetStateAction<CandidateOpsMode[]>>
  polandBasisFilter: string[]
  setPolandBasisFilter: Dispatch<SetStateAction<string[]>>
  trailerTypesFilter: string[]
  setTrailerTypesFilter: Dispatch<SetStateAction<string[]>>
  createdRange: DateRangeFilter
  setCreatedRange: Dispatch<SetStateAction<DateRangeFilter>>
  firstContactRange: DateRangeFilter
  setFirstContactRange: Dispatch<SetStateAction<DateRangeFilter>>
  docsValidRange: DateRangeFilter
  setDocsValidRange: Dispatch<SetStateAction<DateRangeFilter>>
  docsHasFilesFilter: string[]
  setDocsHasFilesFilter: Dispatch<SetStateAction<string[]>>
  handoffStatusFilter: string
  setHandoffStatusFilter: Dispatch<SetStateAction<string>>
  contactAttemptsFilter: string
  setContactAttemptsFilter: Dispatch<SetStateAction<string>>
  processorFilter: string
  setProcessorFilter: Dispatch<SetStateAction<string>>
  intakeApplicationKindFilter: '' | 'client' | 'candidate'
  setIntakeApplicationKindFilter: Dispatch<SetStateAction<'' | 'client' | 'candidate'>>

  // ---- label / option maps for badges --------------------------------
  vacancyLabelMap: Map<string, string>
  managerLabelMap: Map<string, string>
  reasonLabelMap: Map<string, string>
  reasonStageMap: Map<string, string>
  preferredChannelLabelMap: Record<string, string>
  inPolandLabelMap: Record<string, string>
  opsModeLabelMap: Record<CandidateOpsMode, string>
  getPolandBasisLabel: (basis: string | null) => string
  getTrailerTypeLabel: (kind: string) => string
  docsStatusFilterOptions: FilterOption[]
  docsOrderFilterOptions: FilterOption[]
  candidateRowStatusLabel: (code: string) => string
}

export function CandidatesFiltersToolbar(props: CandidatesFiltersToolbarProps) {
  const {
    t, locale,
    q, setQ, searchRef,
    quickViewParam, applyQuickViewFilters,
    isFavoriteFilter, setIsFavoriteFilter,
    quickDocFilters, quickFiltersExpanded,
    toggleQuickDocFilter, setQuickFiltersExpanded,
    operationalChips,
    hideQuickViews = false,
    savedViews, applyView, deleteView,
    stageOptions: _stageOptions,
    stageLabelMap,
    managers: _managers,
    vacancies: _vacancies,
    stageFilter, setStageFilter,
    candidateRowStatusFilter, setCandidateRowStatusFilter,
    managerFilter, setManagerFilter,
    vacancyFilter, setVacancyFilter,
    hasFilterBadges, textFilters, setTextFilter,
    statusReasonFilter, setStatusReasonFilter,
    docsStatusFilter, setDocsStatusFilter,
    docsOrderedFilter, setDocsOrderedFilter,
    preferredChannelFilter, setPreferredChannelFilter,
    inPolandFilter, setInPolandFilter,
    opsModeFilter, setOpsModeFilter,
    polandBasisFilter, setPolandBasisFilter,
    trailerTypesFilter, setTrailerTypesFilter,
    createdRange, setCreatedRange,
    firstContactRange, setFirstContactRange,
    docsValidRange, setDocsValidRange,
    docsHasFilesFilter, setDocsHasFilesFilter,
    handoffStatusFilter, setHandoffStatusFilter,
    contactAttemptsFilter, setContactAttemptsFilter,
    processorFilter, setProcessorFilter,
    intakeApplicationKindFilter, setIntakeApplicationKindFilter,
    vacancyLabelMap, managerLabelMap, reasonLabelMap, reasonStageMap,
    preferredChannelLabelMap, inPolandLabelMap, opsModeLabelMap,
    getPolandBasisLabel, getTrailerTypeLabel,
    docsStatusFilterOptions, docsOrderFilterOptions,
    candidateRowStatusLabel,
  } = props

  return (
    <div className="mx-4 mb-2 shrink-0 rounded-xl border border-slate-200/90 bg-gradient-to-b from-white to-slate-50/90 px-3 py-3 shadow-sm">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
        <input
          id="candidates-search"
          ref={searchRef}
          className="input min-h-[40px] min-w-0 flex-1 rounded-lg border-slate-200/90 bg-white py-2 text-sm shadow-sm focus:border-brand-400 focus:ring-2 focus:ring-brand-500/15"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('app.candidates.search.placeholder')}
          autoComplete="off"
          aria-label={t('app.candidates.search.label')}
        />
        {!hideQuickViews ? (
          <CandidatesQuickViewsBar
            variant="tableToolbar"
            t={t}
            quickViewParam={quickViewParam}
            onApplyQuickViewFilters={(key) => {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              void applyQuickViewFilters(key as any, { syncUrl: true })
            }}
            isFavoriteFilter={isFavoriteFilter}
            onFavoriteFilterToggle={() => setIsFavoriteFilter((prev) => (prev === true ? null : true))}
            quickDocFilters={quickDocFilters}
            quickFiltersExpanded={quickFiltersExpanded}
            onToggleQuickDocFilter={toggleQuickDocFilter}
            onQuickFiltersExpandedChange={setQuickFiltersExpanded}
            operationalChips={operationalChips}
            savedViews={savedViews}
            onApplySavedView={applyView}
            onDeleteSavedView={(id) => {
              void deleteView(id)
            }}
          />
        ) : null}
      </div>
      {hasFilterBadges ? (
        <div className="mt-2 border-t border-slate-200/90 pt-2">
          <FilterBadges
            embedded
            q={q}
            textFilters={textFilters}
            stageFilter={stageFilter}
            candidateRowStatusFilter={candidateRowStatusFilter}
            vacancyFilter={vacancyFilter}
            managerFilter={managerFilter}
            statusReasonFilter={statusReasonFilter}
            docsStatusFilter={docsStatusFilter}
            docsOrderedFilter={docsOrderedFilter}
            preferredChannelFilter={preferredChannelFilter}
            inPolandFilter={inPolandFilter}
            opsModeFilter={opsModeFilter}
            polandBasisFilter={polandBasisFilter}
            trailerTypesFilter={trailerTypesFilter}
            createdRange={createdRange}
            firstContactRange={firstContactRange}
            docsValidRange={docsValidRange}
            docsHasFilesFilter={docsHasFilesFilter}
            handoffStatusFilter={handoffStatusFilter}
            contactAttemptsFilter={contactAttemptsFilter}
            processorFilter={processorFilter}
            intakeApplicationKindFilter={intakeApplicationKindFilter}
            onIntakeApplicationKindFilterChange={setIntakeApplicationKindFilter}
            stageLabelMap={stageLabelMap}
            vacancyLabelMap={vacancyLabelMap}
            managerLabelMap={managerLabelMap}
            reasonLabelMap={reasonLabelMap}
            reasonStageMap={reasonStageMap}
            preferredChannelLabelMap={preferredChannelLabelMap}
            inPolandLabelMap={inPolandLabelMap}
            opsModeLabelMap={opsModeLabelMap}
            getPolandBasisLabel={getPolandBasisLabel}
            getTrailerTypeLabel={getTrailerTypeLabel}
            docsStatusOptions={docsStatusFilterOptions}
            docsOrderFilterOptions={docsOrderFilterOptions}
            candidateRowStatusLabel={candidateRowStatusLabel}
            locale={locale}
            onQChange={setQ}
            onTextFilterChange={setTextFilter}
            onStageFilterChange={setStageFilter}
            onCandidateRowStatusFilterChange={setCandidateRowStatusFilter}
            onVacancyFilterChange={setVacancyFilter}
            onManagerFilterChange={setManagerFilter}
            onStatusReasonFilterChange={setStatusReasonFilter}
            onDocsStatusFilterChange={setDocsStatusFilter}
            onDocsOrderedFilterChange={setDocsOrderedFilter}
            onPreferredChannelFilterChange={setPreferredChannelFilter}
            onInPolandFilterChange={setInPolandFilter}
            onOpsModeFilterChange={setOpsModeFilter}
            onPolandBasisFilterChange={setPolandBasisFilter}
            onTrailerTypesFilterChange={setTrailerTypesFilter}
            onCreatedRangeChange={setCreatedRange}
            onFirstContactRangeChange={setFirstContactRange}
            onDocsValidRangeChange={setDocsValidRange}
            onDocsHasFilesFilterChange={setDocsHasFilesFilter}
            onHandoffStatusFilterChange={setHandoffStatusFilter}
            onContactAttemptsFilterChange={setContactAttemptsFilter}
            onProcessorFilterChange={setProcessorFilter}
          />
        </div>
      ) : null}
    </div>
  )
}
