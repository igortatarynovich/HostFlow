// src/modules/candidates/hooks/useCandidatesUrlSync.ts
//
// Bundles the URL-driven side-effects on the Candidates page:
//
//   1. View-mode sync — keeps `viewMode` (`table` | `kanban`) in sync with
//      `?view=…` on the URL.
//   2. Operational-queue safety net — if the user lands on `?queue=…` while
//      the kanban view is selected, switch back to the table view (queues
//      only make sense in table mode) and strip `view` from the URL.
//   3. Deep-link decoder — when arriving from a Dashboard / Overview pivot
//      (e.g. `?stages=…&manager_id=…`), reset filters and apply the params
//      so the user sees a deterministic drill-down result.
//
// Extracted from inline `useEffect` blocks in `src/pages/Candidates.tsx`
// (Phase 1 #4 god-component split).

import type { Dispatch, SetStateAction } from 'react'
import { useEffect } from 'react'
import type { SetURLSearchParams } from 'react-router-dom'
import {
  normalizeArrayFilter,
  normalizeOpsModeList,
  normalizeReasonList,
} from '../filterNormalizers'
import type { CandidateOpsMode, ColumnTextFilters } from '../types'

const HANDOFF_STATUS_VALUES = new Set(['none', 'pending', 'accepted', 'returned', 'rejected'])
const CONTACT_ATTEMPTS_VALUES = new Set(['none', 'some', 'limit_reached'])

function mapWorkHubStage(code: string): string {
  const x = String(code || '').trim().toLowerCase()
  if (x === 'waiting_documents') return 'docs_wait'
  return String(code || '').trim()
}

export interface CandidatesUrlSyncCtx {
  // ---- URL state ------------------------------------------------------
  searchParams: URLSearchParams
  setSearchParams: SetURLSearchParams

  // ---- view-mode toggle ----------------------------------------------
  setViewMode: Dispatch<SetStateAction<'kanban' | 'table'>>
  operationalQueue: 'no_next_action' | null

  // ---- deep-link gating ----------------------------------------------
  filtersHydrated: boolean
  resetCandidatesFiltersCore: () => void

  // ---- deep-link target setters --------------------------------------
  setQ: Dispatch<SetStateAction<string>>
  setStageFilter: Dispatch<SetStateAction<string[]>>
  setVacancyFilter: Dispatch<SetStateAction<string[]>>
  setStatusReasonFilter: Dispatch<SetStateAction<string[]>>
  setTextFilter: (key: keyof ColumnTextFilters, value: string) => void
  setManagerFilter: Dispatch<SetStateAction<string[]>>
  setPreferredChannelFilter: Dispatch<SetStateAction<string[]>>
  setOpsModeFilter: Dispatch<SetStateAction<CandidateOpsMode[]>>
  setInPolandFilter: Dispatch<SetStateAction<string[]>>
  setHandoffStatusFilter: Dispatch<SetStateAction<string>>
  setContactAttemptsFilter: Dispatch<SetStateAction<string>>
}

export function useCandidatesUrlSync(ctx: CandidatesUrlSyncCtx): void {
  const {
    searchParams, setSearchParams,
    setViewMode, operationalQueue,
    filtersHydrated, resetCandidatesFiltersCore,
    setQ, setStageFilter, setVacancyFilter, setStatusReasonFilter,
    setTextFilter, setManagerFilter, setPreferredChannelFilter,
    setOpsModeFilter, setInPolandFilter,
    setHandoffStatusFilter, setContactAttemptsFilter,
  } = ctx

  // 1) Mirror `?view=` into local state.
  useEffect(() => {
    setViewMode(searchParams.get('view') === 'kanban' ? 'kanban' : 'table')
  }, [searchParams, setViewMode])

  // 2) Operational-queue + kanban incompatibility.
  useEffect(() => {
    if (!operationalQueue) return
    if (searchParams.get('view') !== 'kanban') return
    const next = new URLSearchParams(searchParams)
    next.delete('view')
    setSearchParams(next, { replace: true })
    setViewMode('table')
  }, [operationalQueue, searchParams, setSearchParams, setViewMode])

  // 3) Deep-link drill-down (Dashboard pivot / digest links).
  useEffect(() => {
    if (!filtersHydrated) return
    const qParam = searchParams.get('q') || searchParams.get('query')
    const stagesQuery = searchParams.get('stages') || searchParams.get('stage')
    const filterParam = (searchParams.get('filter') || '').trim()
    const recruiterUnassignedParam = (searchParams.get('recruiter_unassigned') || '').trim()
    const vacancyParam = searchParams.get('vacancy_id') || searchParams.get('vacancy')
    const reasonParam = searchParams.get('status_reason')
    const citizenshipParam = searchParams.get('citizenship')
    const managerParam = searchParams.get('manager_id') || searchParams.get('manager')
    const preferredChannelParam = searchParams.get('preferred_channel')
    const opsModeParam = searchParams.get('ops_mode') || searchParams.get('opsMode')
    const inPolandParam = searchParams.get('in_poland')
    const handoffStatusParam = searchParams.get('handoff_status') || searchParams.get('handoffStatus')
    const contactAttemptsParam = searchParams.get('contact_attempts') || searchParams.get('contactAttempts')
    const shadowBucketParam = searchParams.get('shadow_bucket')?.trim() || ''

    const hasDeepLink =
      Boolean(qParam && String(qParam).trim()) ||
      stagesQuery ||
      Boolean(filterParam) ||
      Boolean(recruiterUnassignedParam) ||
      vacancyParam ||
      reasonParam ||
      citizenshipParam ||
      managerParam ||
      preferredChannelParam ||
      opsModeParam ||
      inPolandParam ||
      handoffStatusParam ||
      contactAttemptsParam ||
      Boolean(shadowBucketParam)
    if (!hasDeepLink) return

    // Drill-down must be deterministic: ignore previously persisted filters.
    // Do not strip shadow_bucket here (digest drill-down); full reset uses handleResetFilters.
    resetCandidatesFiltersCore()
    if (qParam && String(qParam).trim()) setQ(String(qParam).trim())
    if (stagesQuery) {
      setStageFilter(normalizeArrayFilter(stagesQuery).map(mapWorkHubStage))
    }
    if (vacancyParam) setVacancyFilter(normalizeArrayFilter([vacancyParam]))
    if (reasonParam) setStatusReasonFilter(normalizeReasonList([reasonParam]))
    if (citizenshipParam) setTextFilter('citizenship', String(citizenshipParam).trim())

    if (managerParam) setManagerFilter(normalizeArrayFilter([managerParam]))
    if (preferredChannelParam) setPreferredChannelFilter(normalizeArrayFilter([preferredChannelParam]))
    if (opsModeParam) setOpsModeFilter(normalizeOpsModeList([opsModeParam]))
    if (inPolandParam) setInPolandFilter(normalizeArrayFilter([inPolandParam]))

    if (handoffStatusParam) {
      const v = String(handoffStatusParam).trim()
      if (HANDOFF_STATUS_VALUES.has(v)) setHandoffStatusFilter(v)
    }
    if (contactAttemptsParam) {
      const v = String(contactAttemptsParam).trim()
      if (CONTACT_ATTEMPTS_VALUES.has(v)) setContactAttemptsFilter(v)
    }
  }, [
    filtersHydrated,
    searchParams,
    setTextFilter,
    setQ,
    setStageFilter,
    setVacancyFilter,
    setStatusReasonFilter,
    setManagerFilter,
    setPreferredChannelFilter,
    setOpsModeFilter,
    setInPolandFilter,
    setHandoffStatusFilter,
    setContactAttemptsFilter,
    resetCandidatesFiltersCore,
  ])
}
