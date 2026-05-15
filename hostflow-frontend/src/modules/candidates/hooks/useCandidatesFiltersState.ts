// src/modules/candidates/hooks/useCandidatesFiltersState.ts
//
// Owns the three filter-mutation entry points used across the Candidates
// page: applying a saved view, resetting filter state to defaults, and
// the `handleResetFilters` wrapper that also strips a few query-string
// keys (digest drill-down + quick-view shortcut).
//
// The setters live on the page component (so they can also be wired into
// other places — URL sync effects, persistence, etc.); this hook receives
// them via a single `ctx` object and exposes three stable callbacks.
//
// Extracted from inline `useCallback` blocks in `src/pages/Candidates.tsx`
// (Phase 1 #4 god-component split).

import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import { useCallback } from 'react'
import type { SetURLSearchParams } from 'react-router-dom'
import {
  normalizeArrayFilter,
  normalizeOpsModeList,
  normalizeRangeFilter,
  normalizeReasonList,
  normalizeTextFilterState,
} from '../filterNormalizers'
import { makeEmptyTextFilters } from '../types'
import type { CandidateOpsMode, ColumnTextFilters, DateRangeFilter, SortKey } from '../types'

export interface CandidatesFiltersStateCtx {
  // ---- text query / arrays --------------------------------------------
  setQ: Dispatch<SetStateAction<string>>
  setStageFilter: Dispatch<SetStateAction<string[]>>
  setCandidateRowStatusFilter: Dispatch<SetStateAction<string[]>>
  setVacancyFilter: Dispatch<SetStateAction<string[]>>
  setManagerFilter: Dispatch<SetStateAction<string[]>>
  setStatusReasonFilter: Dispatch<SetStateAction<string[]>>
  setTagsFilter: Dispatch<SetStateAction<string[]>>
  setIsFavoriteFilter: Dispatch<SetStateAction<boolean | null>>
  setDocsStatusFilter: Dispatch<SetStateAction<string[]>>
  setDocsOrderedFilter: Dispatch<SetStateAction<string[]>>
  setPreferredChannelFilter: Dispatch<SetStateAction<string[]>>
  setInPolandFilter: Dispatch<SetStateAction<string[]>>
  setOpsModeFilter: Dispatch<SetStateAction<CandidateOpsMode[]>>
  setPolandBasisFilter: Dispatch<SetStateAction<string[]>>
  setTrailerTypesFilter: Dispatch<SetStateAction<string[]>>
  setDocsHasFilesFilter: Dispatch<SetStateAction<string[]>>

  // ---- date ranges ----------------------------------------------------
  setCreatedRange: Dispatch<SetStateAction<DateRangeFilter>>
  setFirstContactRange: Dispatch<SetStateAction<DateRangeFilter>>
  setDocsValidRange: Dispatch<SetStateAction<DateRangeFilter>>

  // ---- string-typed filters ------------------------------------------
  setHandoffStatusFilter: Dispatch<SetStateAction<string>>
  setContactAttemptsFilter: Dispatch<SetStateAction<string>>
  setProcessorFilter: Dispatch<SetStateAction<string>>
  setIntakeApplicationKindFilter: Dispatch<SetStateAction<'' | 'client' | 'candidate'>>

  // ---- text filters ---------------------------------------------------
  setTextFilters: Dispatch<SetStateAction<ColumnTextFilters>>

  // ---- sort -----------------------------------------------------------
  setSortKey: Dispatch<SetStateAction<SortKey>>
  setSortDir: Dispatch<SetStateAction<'asc' | 'desc'>>

  // ---- side-effects on reset -----------------------------------------
  filterStorageKey: string
  persistedFiltersRef: MutableRefObject<boolean>
  applyTableLayoutFromViewRef: MutableRefObject<
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (filters: Record<string, any> | undefined) => void
  >

  // ---- URL params (for handleResetFilters) ---------------------------
  searchParams: URLSearchParams
  setSearchParams: SetURLSearchParams
}

export interface CandidatesFiltersStateActions {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  applyViewFilters: (filters: Record<string, any> | undefined) => void
  /** Hard reset of all filter UI state + persisted localStorage entry. */
  resetCandidatesFiltersCore: () => void
  /** Same as `resetCandidatesFiltersCore` but also strips digest/qv query params. */
  handleResetFilters: () => void
}

const RESET_QUERY_KEYS = [
  'shadow_bucket',
  'shadow_min_band',
  'shadow_bucket_min_band',
  'qv',
  'candidate_statuses',
] as const

export function useCandidatesFiltersState(ctx: CandidatesFiltersStateCtx): CandidatesFiltersStateActions {
  const {
    setQ, setStageFilter, setCandidateRowStatusFilter, setVacancyFilter, setManagerFilter, setStatusReasonFilter,
    setTagsFilter, setIsFavoriteFilter, setDocsStatusFilter, setDocsOrderedFilter,
    setPreferredChannelFilter, setInPolandFilter, setOpsModeFilter, setPolandBasisFilter,
    setTrailerTypesFilter, setDocsHasFilesFilter,
    setCreatedRange, setFirstContactRange, setDocsValidRange,
    setHandoffStatusFilter, setContactAttemptsFilter, setProcessorFilter,
    setIntakeApplicationKindFilter,
    setTextFilters,
    setSortKey, setSortDir,
    filterStorageKey, persistedFiltersRef, applyTableLayoutFromViewRef,
    searchParams, setSearchParams,
  } = ctx

  const applyViewFilters = useCallback<CandidatesFiltersStateActions['applyViewFilters']>(
    (filters) => {
      setQ(filters?.q ?? '')
      setStageFilter(normalizeArrayFilter(filters?.stage ?? filters?.stages))
      setCandidateRowStatusFilter(
        normalizeArrayFilter(filters?.candidateRowStatus ?? filters?.candidate_row_status),
      )
      setVacancyFilter(normalizeArrayFilter(filters?.vacancy ?? filters?.vacancyId ?? filters?.vacancies))
      setManagerFilter(normalizeArrayFilter(filters?.managers ?? filters?.manager))
      setStatusReasonFilter(normalizeReasonList(filters?.statusReason ?? filters?.status_reason))
      setTagsFilter(normalizeArrayFilter(filters?.tags))
      setDocsStatusFilter(normalizeArrayFilter(filters?.docsStatus))
      setDocsOrderedFilter(normalizeArrayFilter(filters?.docsOrdered))
      setPreferredChannelFilter(normalizeArrayFilter(filters?.preferredChannel ?? filters?.preferred_contact))
      setInPolandFilter(normalizeArrayFilter(filters?.inPoland ?? filters?.in_poland))
      setOpsModeFilter(normalizeOpsModeList(filters?.opsMode ?? filters?.ops_mode))
      setPolandBasisFilter(normalizeArrayFilter(filters?.polandBasis ?? filters?.poland_basis))
      setTrailerTypesFilter(normalizeArrayFilter(filters?.trailerTypes ?? filters?.trailer_types))
      setCreatedRange(normalizeRangeFilter(filters?.createdRange ?? filters?.created_at))
      setFirstContactRange(normalizeRangeFilter(filters?.firstContactRange ?? filters?.first_contact_at))
      setDocsValidRange(normalizeRangeFilter(filters?.docsValidRange ?? filters?.docs_valid_from))
      setDocsHasFilesFilter(normalizeArrayFilter(filters?.docsHasFiles ?? filters?.docs_has_files))
      setTextFilters(normalizeTextFilterState(filters?.textFilters))
      const rawIak = filters?.intakeApplicationKind ?? filters?.intake_application_kind
      setIntakeApplicationKindFilter(
        rawIak === 'client' || rawIak === 'candidate' ? rawIak : '',
      )
      applyTableLayoutFromViewRef.current(filters)
    },
    [
      setQ, setStageFilter, setCandidateRowStatusFilter, setVacancyFilter, setManagerFilter, setStatusReasonFilter,
      setTagsFilter, setDocsStatusFilter, setDocsOrderedFilter, setPreferredChannelFilter,
      setInPolandFilter, setOpsModeFilter, setPolandBasisFilter, setTrailerTypesFilter,
      setCreatedRange, setFirstContactRange, setDocsValidRange, setDocsHasFilesFilter,
      setTextFilters, setIntakeApplicationKindFilter, applyTableLayoutFromViewRef,
    ],
  )

  const resetCandidatesFiltersCore = useCallback<CandidatesFiltersStateActions['resetCandidatesFiltersCore']>(() => {
    setQ('')
    setStageFilter([])
    setCandidateRowStatusFilter([])
    setVacancyFilter([])
    setManagerFilter([])
    setStatusReasonFilter([])
    setTagsFilter([])
    setIsFavoriteFilter(null)
    setDocsStatusFilter([])
    setDocsOrderedFilter([])
    setPreferredChannelFilter([])
    setInPolandFilter([])
    setOpsModeFilter([])
    setPolandBasisFilter([])
    setTrailerTypesFilter([])
    setCreatedRange({ from: null, to: null })
    setFirstContactRange({ from: null, to: null })
    setDocsValidRange({ from: null, to: null })
    setDocsHasFilesFilter([])
    setHandoffStatusFilter('')
    setContactAttemptsFilter('')
    setProcessorFilter('')
    setIntakeApplicationKindFilter('')
    setTextFilters(makeEmptyTextFilters())
    setSortKey('created_at')
    setSortDir('desc')
    persistedFiltersRef.current = false
    try {
      localStorage.removeItem(filterStorageKey)
    } catch {
      /* ignore */
    }
  }, [
    setQ, setStageFilter, setCandidateRowStatusFilter, setVacancyFilter, setManagerFilter, setStatusReasonFilter,
    setTagsFilter, setIsFavoriteFilter, setDocsStatusFilter, setDocsOrderedFilter,
    setPreferredChannelFilter, setInPolandFilter, setOpsModeFilter, setPolandBasisFilter,
    setTrailerTypesFilter, setCreatedRange, setFirstContactRange, setDocsValidRange,
    setDocsHasFilesFilter, setHandoffStatusFilter, setContactAttemptsFilter,
    setProcessorFilter, setIntakeApplicationKindFilter, setTextFilters,
    setSortKey, setSortDir, persistedFiltersRef, filterStorageKey,
  ])

  const handleResetFilters = useCallback<CandidatesFiltersStateActions['handleResetFilters']>(() => {
    resetCandidatesFiltersCore()
    try {
      const next = new URLSearchParams(searchParams)
      let changed = false
      for (const key of RESET_QUERY_KEYS) {
        if (next.has(key)) {
          next.delete(key)
          changed = true
        }
      }
      if (changed) setSearchParams(next, { replace: true })
    } catch {
      /* ignore */
    }
  }, [resetCandidatesFiltersCore, searchParams, setSearchParams])

  return { applyViewFilters, resetCandidatesFiltersCore, handleResetFilters }
}
