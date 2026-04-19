// src/modules/candidates/components/CandidatesFiltersToolbar.tsx
//
// The full filters toolbar shown above the Candidates table:
//   1. Free-text search input
//   2. Quick-views bar (saved views, favourite, doc-status pills)
//   3. Three quick-filter dropdowns (stage / manager / vacancy)
//   4. <FilterBadges /> strip (only when at least one filter is active)
//
// Extracted from `src/pages/Candidates.tsx` (Phase 1 #4 god-component
// split) — about 150 LOC of JSX moved here behind a single `ctx` prop
// so the call site stays a one-liner.

import { type Dispatch, type Ref, type SetStateAction } from 'react'
import { CandidatesQuickViewsBar, type QuickDocFilter, type QuickViewKey } from './CandidatesQuickViewsBar'
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
  savedViews: UserSavedView[]
  applyView: (view: UserSavedView) => void
  deleteView: (id: string) => void | Promise<void>

  // ---- quick-filter selects ------------------------------------------
  stageOptions: string[]
  stageLabelMap: Record<string, string>
  managers: ManagerItem[]
  vacancies: VacancyLite[]

  // ---- filter values + setters ---------------------------------------
  stageFilter: string[]
  setStageFilter: Dispatch<SetStateAction<string[]>>
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
}

export function CandidatesFiltersToolbar(props: CandidatesFiltersToolbarProps) {
  const {
    t, locale,
    q, setQ, searchRef,
    quickViewParam, applyQuickViewFilters,
    isFavoriteFilter, setIsFavoriteFilter,
    quickDocFilters, quickFiltersExpanded,
    toggleQuickDocFilter, setQuickFiltersExpanded,
    savedViews, applyView, deleteView,
    stageOptions, stageLabelMap, managers, vacancies,
    stageFilter, setStageFilter,
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
  } = props

  return (
    <div className="mx-4 mb-1.5 shrink-0 rounded-xl border border-slate-200/90 bg-gradient-to-b from-white to-slate-50/90 px-3 py-2.5 shadow-sm">
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
          savedViews={savedViews}
          onApplySavedView={applyView}
          onDeleteSavedView={(id) => {
            void deleteView(id)
          }}
        />
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-slate-200/80 pt-2">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          {t('app.candidates.quick_filters.label', { defaultValue: 'Quick filters' })}
        </span>
        <select
          className="input h-9 max-w-[11rem] py-1 text-xs"
          aria-label={t('app.candidates.quick_filters.stage', { defaultValue: 'Stage' })}
          value={stageFilter.length === 1 ? stageFilter[0] : ''}
          onChange={(e) => {
            const v = e.target.value.trim()
            setStageFilter(v ? [v] : [])
          }}
        >
          <option value="">{t('app.candidates.quick_filters.all_stages', { defaultValue: 'All stages' })}</option>
          {stageOptions.map((s) => (
            <option key={s} value={s}>
              {stageLabelMap[s] ?? s}
            </option>
          ))}
        </select>
        <select
          className="input h-9 max-w-[11rem] py-1 text-xs"
          aria-label={t('app.candidates.quick_filters.manager', { defaultValue: 'Manager' })}
          value={managerFilter.length === 1 ? managerFilter[0] : ''}
          onChange={(e) => {
            const v = e.target.value.trim()
            setManagerFilter(v ? [v] : [])
          }}
        >
          <option value="">{t('app.candidates.quick_filters.all_managers', { defaultValue: 'All managers' })}</option>
          {managers.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name || m.id}
            </option>
          ))}
        </select>
        <select
          className="input h-9 max-w-[12rem] py-1 text-xs"
          aria-label={t('app.candidates.quick_filters.vacancy', { defaultValue: 'Vacancy' })}
          value={vacancyFilter.length === 1 ? vacancyFilter[0] : ''}
          onChange={(e) => {
            const v = e.target.value.trim()
            setVacancyFilter(v ? [v] : [])
          }}
        >
          <option value="">{t('app.candidates.quick_filters.all_vacancies', { defaultValue: 'All vacancies' })}</option>
          {vacancies.map((v) => (
            <option key={v.id} value={v.id}>
              {v.title || v.id}
            </option>
          ))}
        </select>
      </div>
      {hasFilterBadges ? (
        <div className="mt-2 border-t border-slate-200/90 pt-2">
          <FilterBadges
            embedded
            q={q}
            textFilters={textFilters}
            stageFilter={stageFilter}
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
            locale={locale}
            onQChange={setQ}
            onTextFilterChange={setTextFilter}
            onStageFilterChange={setStageFilter}
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
