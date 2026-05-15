// src/modules/candidates/hooks/useCandidatesFiltersPersistence.ts
//
// Persists the full Candidates filter state (filters + text-filters +
// sort + favourite + intake-kind) to `localStorage` and restores it on
// mount. Two paired effects:
//
//   1. Hydration — runs once on mount (also when `storageKey` changes,
//      e.g. on tenant switch). Reads the JSON blob, normalises every
//      field through the same helpers used by `applyViewFilters`, and
//      flips `setFiltersHydrated(true)` so dependent effects can
//      proceed. Marks `persistedFiltersRef.current = true` if anything
//      non-default was restored.
//
//   2. Persistence — runs whenever any filter field changes (after
//      hydration completes), serialising the full snapshot back to
//      `localStorage`.
//
// Extracted from inline `useEffect` blocks in `src/pages/Candidates.tsx`
// (Phase 1 #4 god-component split).

import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import { useEffect } from 'react'
import { isSortKey } from '../constants'
import {
  normalizeArrayFilter,
  normalizeOpsModeList,
  normalizeRangeFilter,
  normalizeReasonList,
  normalizeTextFilterState,
} from '../filterNormalizers'
import { isRangeActive } from '../candidateUtils'
import type {
  CandidateOpsMode,
  ColumnTextFilters,
  DateRangeFilter,
  SortKey,
} from '../types'

const HANDOFF_STATUS_VALUES = new Set(['none', 'pending', 'accepted', 'returned', 'rejected'])
const CONTACT_ATTEMPTS_VALUES = new Set(['none', 'some', 'limit_reached'])

export interface CandidatesFiltersPersistenceCtx {
  storageKey: string
  filtersHydrated: boolean
  setFiltersHydrated: Dispatch<SetStateAction<boolean>>
  persistedFiltersRef: MutableRefObject<boolean>

  // ---- hydration setters --------------------------------------------
  setQ: Dispatch<SetStateAction<string>>
  setStageFilter: Dispatch<SetStateAction<string[]>>
  setCandidateRowStatusFilter: Dispatch<SetStateAction<string[]>>
  setVacancyFilter: Dispatch<SetStateAction<string[]>>
  setManagerFilter: Dispatch<SetStateAction<string[]>>
  setStatusReasonFilter: Dispatch<SetStateAction<string[]>>
  setDocsStatusFilter: Dispatch<SetStateAction<string[]>>
  setDocsOrderedFilter: Dispatch<SetStateAction<string[]>>
  setPreferredChannelFilter: Dispatch<SetStateAction<string[]>>
  setInPolandFilter: Dispatch<SetStateAction<string[]>>
  setOpsModeFilter: Dispatch<SetStateAction<CandidateOpsMode[]>>
  setPolandBasisFilter: Dispatch<SetStateAction<string[]>>
  setTrailerTypesFilter: Dispatch<SetStateAction<string[]>>
  setCreatedRange: Dispatch<SetStateAction<DateRangeFilter>>
  setFirstContactRange: Dispatch<SetStateAction<DateRangeFilter>>
  setDocsValidRange: Dispatch<SetStateAction<DateRangeFilter>>
  setDocsHasFilesFilter: Dispatch<SetStateAction<string[]>>
  setHandoffStatusFilter: Dispatch<SetStateAction<string>>
  setContactAttemptsFilter: Dispatch<SetStateAction<string>>
  setProcessorFilter: Dispatch<SetStateAction<string>>
  setTextFilters: Dispatch<SetStateAction<ColumnTextFilters>>
  setIsFavoriteFilter: Dispatch<SetStateAction<boolean | null>>
  setIntakeApplicationKindFilter: Dispatch<SetStateAction<'' | 'client' | 'candidate'>>
  setSortKey: Dispatch<SetStateAction<SortKey>>
  setSortDir: Dispatch<SetStateAction<'asc' | 'desc'>>

  // ---- persistence values --------------------------------------------
  q: string
  stageFilter: string[]
  candidateRowStatusFilter: string[]
  vacancyFilter: string[]
  managerFilter: string[]
  statusReasonFilter: string[]
  tagsFilter: string[]
  docsStatusFilter: string[]
  docsOrderedFilter: string[]
  preferredChannelFilter: string[]
  inPolandFilter: string[]
  opsModeFilter: CandidateOpsMode[]
  polandBasisFilter: string[]
  trailerTypesFilter: string[]
  createdRange: DateRangeFilter
  firstContactRange: DateRangeFilter
  docsValidRange: DateRangeFilter
  docsHasFilesFilter: string[]
  handoffStatusFilter: string
  contactAttemptsFilter: string
  processorFilter: string
  textFilters: ColumnTextFilters
  isFavoriteFilter: boolean | null
  intakeApplicationKindFilter: '' | 'client' | 'candidate'
  sortKey: SortKey
  sortDir: 'asc' | 'desc'
}

export function useCandidatesFiltersPersistence(ctx: CandidatesFiltersPersistenceCtx): void {
  const {
    storageKey, filtersHydrated, setFiltersHydrated, persistedFiltersRef,
    setQ, setStageFilter, setCandidateRowStatusFilter, setVacancyFilter, setManagerFilter, setStatusReasonFilter,
    setDocsStatusFilter, setDocsOrderedFilter, setPreferredChannelFilter,
    setInPolandFilter, setOpsModeFilter, setPolandBasisFilter, setTrailerTypesFilter,
    setCreatedRange, setFirstContactRange, setDocsValidRange, setDocsHasFilesFilter,
    setHandoffStatusFilter, setContactAttemptsFilter, setProcessorFilter,
    setTextFilters, setIsFavoriteFilter, setIntakeApplicationKindFilter,
    setSortKey, setSortDir,
    q, stageFilter, candidateRowStatusFilter, vacancyFilter, managerFilter, statusReasonFilter, tagsFilter,
    docsStatusFilter, docsOrderedFilter, preferredChannelFilter, inPolandFilter,
    opsModeFilter, polandBasisFilter, trailerTypesFilter,
    createdRange, firstContactRange, docsValidRange, docsHasFilesFilter,
    handoffStatusFilter, contactAttemptsFilter, processorFilter,
    textFilters, isFavoriteFilter, intakeApplicationKindFilter,
    sortKey, sortDir,
  } = ctx

  // Hydrate from localStorage on mount (and on storageKey change).
  useEffect(() => {
    let applied = false
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed && typeof parsed === 'object') {
          if (typeof parsed.q === 'string') {
            setQ(parsed.q)
            applied = applied || Boolean(parsed.q)
          }
          const restoredStage = normalizeArrayFilter(parsed.stage ?? parsed.stages)
          setStageFilter(restoredStage)
          applied = applied || restoredStage.length > 0

          const restoredRowStatus = normalizeArrayFilter(
            parsed.candidateRowStatus ?? parsed.candidate_row_status,
          )
          setCandidateRowStatusFilter(restoredRowStatus)
          applied = applied || restoredRowStatus.length > 0

          const restoredVacancies = normalizeArrayFilter(parsed.vacancy ?? parsed.vacancyId ?? parsed.vacancies)
          setVacancyFilter(restoredVacancies)
          applied = applied || restoredVacancies.length > 0

          const restoredManagers = normalizeArrayFilter(parsed.managers ?? parsed.manager)
          setManagerFilter(restoredManagers)
          applied = applied || restoredManagers.length > 0

          const reasonList = normalizeReasonList(parsed.statusReason ?? parsed.status_reason)
          setStatusReasonFilter(reasonList)
          applied = applied || reasonList.length > 0

          const restoredDocsStatus = normalizeArrayFilter(parsed.docsStatus)
          setDocsStatusFilter(restoredDocsStatus)
          applied = applied || restoredDocsStatus.length > 0

          const restoredDocsOrdered = normalizeArrayFilter(parsed.docsOrdered ?? parsed.documents_ordered)
          setDocsOrderedFilter(restoredDocsOrdered)
          applied = applied || restoredDocsOrdered.length > 0

          const restoredPreferred = normalizeArrayFilter(parsed.preferredChannel ?? parsed.preferred_contact)
          setPreferredChannelFilter(restoredPreferred)
          applied = applied || restoredPreferred.length > 0

          const restoredInPoland = normalizeArrayFilter(parsed.inPoland ?? parsed.in_poland)
          setInPolandFilter(restoredInPoland)
          applied = applied || restoredInPoland.length > 0

          const restoredOpsMode = normalizeOpsModeList(parsed.opsMode ?? parsed.ops_mode)
          setOpsModeFilter(restoredOpsMode)
          applied = applied || restoredOpsMode.length > 0

          const restoredPolandBasis = normalizeArrayFilter(parsed.polandBasis ?? parsed.poland_basis)
          setPolandBasisFilter(restoredPolandBasis)
          applied = applied || restoredPolandBasis.length > 0

          const restoredTrailerTypes = normalizeArrayFilter(parsed.trailerTypes ?? parsed.trailer_types)
          setTrailerTypesFilter(restoredTrailerTypes)
          applied = applied || restoredTrailerTypes.length > 0

          const restoredCreated = normalizeRangeFilter(parsed.createdRange ?? parsed.created_at)
          setCreatedRange(restoredCreated)
          applied = applied || isRangeActive(restoredCreated)

          const restoredFirstContact = normalizeRangeFilter(parsed.firstContactRange ?? parsed.first_contact_at)
          setFirstContactRange(restoredFirstContact)
          applied = applied || isRangeActive(restoredFirstContact)

          const restoredDocsValid = normalizeRangeFilter(parsed.docsValidRange ?? parsed.docs_valid_from)
          setDocsValidRange(restoredDocsValid)
          applied = applied || isRangeActive(restoredDocsValid)

          const restoredDocsFiles = normalizeArrayFilter(parsed.docsHasFiles ?? parsed.docs_has_files)
          setDocsHasFilesFilter(restoredDocsFiles)
          applied = applied || restoredDocsFiles.length > 0

          const restoredHandoffStatus =
            typeof parsed.handoffStatus === 'string' ? parsed.handoffStatus.trim() : ''
          if (HANDOFF_STATUS_VALUES.has(restoredHandoffStatus)) {
            setHandoffStatusFilter(restoredHandoffStatus)
            applied = true
          }
          const restoredContactAttempts =
            typeof parsed.contactAttempts === 'string' ? parsed.contactAttempts.trim() : ''
          if (CONTACT_ATTEMPTS_VALUES.has(restoredContactAttempts)) {
            setContactAttemptsFilter(restoredContactAttempts)
            applied = true
          }
          const restoredProcessorId =
            typeof parsed.processorId === 'string' ? parsed.processorId.trim() : ''
          if (restoredProcessorId) {
            setProcessorFilter(restoredProcessorId)
            applied = true
          }

          const restoredTextFilters = normalizeTextFilterState(parsed.textFilters)
          setTextFilters(restoredTextFilters)
          applied = applied || Object.values(restoredTextFilters).some((value) => value.trim().length > 0)

          const restoredIsFavorite =
            typeof parsed.isFavorite === 'boolean'
              ? parsed.isFavorite
              : parsed.is_favorite === true
                ? true
                : null
          setIsFavoriteFilter(restoredIsFavorite)
          applied = applied || restoredIsFavorite === true

          const restoredIak = parsed.intakeApplicationKind ?? parsed.intake_application_kind
          if (restoredIak === 'client' || restoredIak === 'candidate') {
            setIntakeApplicationKindFilter(restoredIak)
            applied = true
          }

          if (isSortKey(parsed.sortKey)) {
            setSortKey(parsed.sortKey)
            applied = applied || parsed.sortKey !== 'created_at'
          }
          if (parsed.sortDir === 'asc' || parsed.sortDir === 'desc') {
            setSortDir(parsed.sortDir)
            applied = applied || parsed.sortDir !== 'desc'
          }
        }
      }
    } catch (err) {
      console.warn('[Candidates] failed to restore filters', err)
    } finally {
      persistedFiltersRef.current = applied
      setFiltersHydrated(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey])

  // Persist on every filter change (after hydration completes).
  useEffect(() => {
    if (!filtersHydrated) return
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          q,
          stage: stageFilter,
          candidateRowStatus: candidateRowStatusFilter,
          vacancies: vacancyFilter,
          managers: managerFilter,
          statusReason: statusReasonFilter,
          tags: tagsFilter,
          docsStatus: docsStatusFilter,
          docsOrdered: docsOrderedFilter,
          preferredChannel: preferredChannelFilter,
          inPoland: inPolandFilter,
          opsMode: opsModeFilter,
          polandBasis: polandBasisFilter,
          trailerTypes: trailerTypesFilter,
          createdRange,
          firstContactRange,
          docsValidRange,
          docsHasFiles: docsHasFilesFilter,
          handoffStatus: handoffStatusFilter,
          contactAttempts: contactAttemptsFilter,
          processorId: processorFilter,
          textFilters,
          isFavorite: isFavoriteFilter,
          intakeApplicationKind: intakeApplicationKindFilter,
          sortKey,
          sortDir,
        }),
      )
    } catch (err) {
      console.warn('[Candidates] failed to persist filters', err)
    }
  }, [
    storageKey, filtersHydrated,
    q, stageFilter, candidateRowStatusFilter, vacancyFilter, managerFilter, statusReasonFilter, tagsFilter,
    docsStatusFilter, docsOrderedFilter, preferredChannelFilter, inPolandFilter,
    opsModeFilter, polandBasisFilter, trailerTypesFilter,
    createdRange, firstContactRange, docsValidRange, docsHasFilesFilter,
    handoffStatusFilter, contactAttemptsFilter, processorFilter,
    textFilters, isFavoriteFilter, intakeApplicationKindFilter,
    sortKey, sortDir,
  ])
}
