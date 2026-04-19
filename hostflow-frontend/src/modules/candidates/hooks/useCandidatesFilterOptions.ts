// src/modules/candidates/hooks/useCandidatesFilterOptions.ts
//
// Builds 13 column-filter dropdown option lists from the enriched
// candidate list + currently-selected filter values. Each list is built
// from `enrichedItems` (so options never disappear when a filter is
// applied) and augmented with currently-selected values that are not
// present in the dataset (so the user can still see and clear them).
//
// Extracted from inline `useMemo` blocks in `src/pages/Candidates.tsx`
// (Phase 1 #4 god-component split).

import { useMemo } from 'react'
import type { TranslateFn } from '../../../i18n'
import {
  DOC_ORDER_FILTERS,
  DOC_READINESS_META,
  EMPTY_OPTION_VALUE,
} from '../constants'
import { getCandidateManagerId, getCandidateVacancyId } from '../utils'
import type {
  AugmentedCandidate,
  CandidateOpsMode,
  UICandidate,
} from '../types'

interface FilterOption {
  value: string
  label: string
}

interface OpsModeOption {
  value: CandidateOpsMode
  label: string
}

export interface CandidatesFilterOptionsCtx {
  t: TranslateFn
  enrichedItems: AugmentedCandidate[]

  // ---- catalog label lookups -----------------------------------------
  vacancyLabelMap: Map<string, string>
  managerLabelMap: Map<string, string>
  resolveManagerLabel: (candidate: UICandidate) => string | null
  preferredChannelLabelMap: Record<string, string>
  inPolandLabelMap: Record<string, string>
  opsModeLabelMap: Record<CandidateOpsMode, string>
  getPolandBasisLabel: (basis: string | null) => string
  getTrailerTypeLabel: (kind: string) => string

  // ---- catalog: reason vocabulary (for code → label + stage) ---------
  reasonOptions: Array<{
    code: string
    label: string
    stageLabel: string
  }>

  // ---- currently-selected filter values ------------------------------
  vacancyFilter: string[]
  managerFilter: string[]
  statusReasonFilter: string[]
  docsStatusFilter: string[]
  docsOrderedFilter: string[]
  docsHasFilesFilter: string[]
  preferredChannelFilter: string[]
  inPolandFilter: string[]
  opsModeFilter: CandidateOpsMode[]
  polandBasisFilter: string[]
  trailerTypesFilter: string[]
}

export interface CandidatesFilterOptionsResult {
  vacancyFilterOptions: FilterOption[]
  managerFilterOptions: FilterOption[]
  reasonFilterOptions: FilterOption[]
  docsStatusPresence: Set<string>
  allDocsStatusOptions: FilterOption[]
  docsStatusFilterOptions: FilterOption[]
  docsOrderPresence: Set<string>
  docsOrderFilterOptions: FilterOption[]
  docsHasFilesOptions: FilterOption[]
  preferredChannelOptions: FilterOption[]
  inPolandOptions: FilterOption[]
  opsModeOptions: OpsModeOption[]
  polandBasisOptions: FilterOption[]
  trailerTypesOptions: FilterOption[]
}

export function useCandidatesFilterOptions(ctx: CandidatesFilterOptionsCtx): CandidatesFilterOptionsResult {
  const {
    t, enrichedItems,
    vacancyLabelMap, managerLabelMap, resolveManagerLabel,
    preferredChannelLabelMap, inPolandLabelMap, opsModeLabelMap,
    getPolandBasisLabel, getTrailerTypeLabel,
    reasonOptions,
    vacancyFilter, managerFilter, statusReasonFilter, docsStatusFilter,
    docsOrderedFilter, docsHasFilesFilter, preferredChannelFilter,
    inPolandFilter, opsModeFilter, polandBasisFilter, trailerTypesFilter,
  } = ctx

  const vacancyFilterOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: string | null, label: string) => {
      if (!value || map.has(value)) return
      map.set(value, label || t('app.candidates.labels.untitled'))
    }
    enrichedItems.forEach((item) => {
      const id = getCandidateVacancyId(item)
      if (!id) return
      const title =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (item as any)?.vacancy?.title ||
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (item as any)?.vacancy_title ||
        vacancyLabelMap.get(id) ||
        t('app.candidates.labels.untitled')
      ensure(id, title)
    })
    vacancyFilter.forEach((value) => ensure(value, vacancyLabelMap.get(value) || value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, vacancyFilter, vacancyLabelMap, t])

  const managerFilterOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: string | null, label: string) => {
      if (!value || map.has(value)) return
      map.set(value, label || '—')
    }
    enrichedItems.forEach((item) => {
      const id = getCandidateManagerId(item)
      if (!id) return
      const label = resolveManagerLabel(item) || id
      ensure(id, label)
    })
    managerFilter.forEach((value) => ensure(value, managerLabelMap.get(value) || value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, managerFilter, managerLabelMap, resolveManagerLabel])

  const reasonFilterOptions = useMemo<FilterOption[]>(() => {
    const present = new Set<string>(statusReasonFilter)
    enrichedItems.forEach((item) => {
      item.__reasonCodes.forEach((code) => present.add(code))
    })
    return reasonOptions
      .filter((option) => present.has(option.code))
      .map((option) => ({
        value: option.code,
        label: `${option.label} (${option.stageLabel})`,
      }))
  }, [enrichedItems, reasonOptions, statusReasonFilter])

  const docsStatusPresence = useMemo(() => {
    const set = new Set<string>(docsStatusFilter)
    enrichedItems.forEach((item) => set.add(item.__docsMeta.readinessKey))
    return set
  }, [enrichedItems, docsStatusFilter])

  const allDocsStatusOptions = useMemo<FilterOption[]>(
    () =>
      Object.entries(DOC_READINESS_META).map(([value, meta]) => ({
        value,
        label: t(meta.labelKey),
      })),
    [t],
  )

  const docsStatusFilterOptions = useMemo<FilterOption[]>(
    () => allDocsStatusOptions.filter((option) => docsStatusPresence.has(option.value)),
    [allDocsStatusOptions, docsStatusPresence],
  )

  const docsOrderPresence = useMemo(() => {
    const set = new Set<string>(docsOrderedFilter)
    enrichedItems.forEach((item) => set.add(item.__docsMeta.isOrdered ? 'ordered' : 'not_ordered'))
    return set
  }, [enrichedItems, docsOrderedFilter])

  const docsOrderFilterOptions = useMemo<FilterOption[]>(
    () =>
      DOC_ORDER_FILTERS.map((option) => ({ value: option.value, label: t(option.labelKey) })).filter(
        (option) => docsOrderPresence.has(option.value),
      ),
    [docsOrderPresence, t],
  )

  const docsHasFilesOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: 'with' | 'without') => {
      if (map.has(value)) return
      map.set(
        value,
        value === 'with'
          ? t('app.candidates.filters.docs_files_with')
          : t('app.candidates.filters.docs_files_without'),
      )
    }
    enrichedItems.forEach((item) => ensure(item.__docsMeta.hasFiles ? 'with' : 'without'))
    docsHasFilesFilter.forEach((value) => {
      if (value === 'with' || value === 'without') ensure(value)
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, docsHasFilesFilter, t])

  const preferredChannelOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: string, label: string) => {
      if (map.has(value)) return
      map.set(value, label)
    }
    enrichedItems.forEach((item) => {
      const key = item.__extra.preferredContact ?? EMPTY_OPTION_VALUE
      ensure(key, preferredChannelLabelMap[key] ?? key)
    })
    preferredChannelFilter.forEach((value) => {
      ensure(value, preferredChannelLabelMap[value] ?? value)
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, preferredChannelFilter, preferredChannelLabelMap])

  const inPolandOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (map.has(value)) return
      map.set(value, inPolandLabelMap[value] ?? inPolandLabelMap.unknown)
    }
    enrichedItems.forEach((item) => {
      const key = item.__extra.inPoland === true ? 'yes' : item.__extra.inPoland === false ? 'no' : 'unknown'
      ensure(key)
    })
    inPolandFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, inPolandFilter, inPolandLabelMap])

  const opsModeOptions = useMemo<OpsModeOption[]>(() => {
    const map = new Map<CandidateOpsMode, string>()
    const ensure = (value: CandidateOpsMode) => {
      if (map.has(value)) return
      map.set(value, opsModeLabelMap[value])
    }
    enrichedItems.forEach((item) => {
      if (item.__extra.opsMode) ensure(item.__extra.opsMode)
    })
    opsModeFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, opsModeFilter, opsModeLabelMap])

  const polandBasisOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (map.has(value)) return
      map.set(value, value === EMPTY_OPTION_VALUE ? t('common.labels.not_available') : getPolandBasisLabel(value))
    }
    enrichedItems.forEach((item) => {
      ensure(item.__extra.polandStayBasis ?? EMPTY_OPTION_VALUE)
    })
    polandBasisFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, polandBasisFilter, getPolandBasisLabel, t])

  const trailerTypesOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (!value || map.has(value)) return
      map.set(value, getTrailerTypeLabel(value))
    }
    enrichedItems.forEach((item) => {
      item.__extra.trailerTypes.forEach((code) => ensure(code))
    })
    trailerTypesFilter.forEach((value) => ensure(value))
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, getTrailerTypeLabel, trailerTypesFilter])

  return {
    vacancyFilterOptions,
    managerFilterOptions,
    reasonFilterOptions,
    docsStatusPresence,
    allDocsStatusOptions,
    docsStatusFilterOptions,
    docsOrderPresence,
    docsOrderFilterOptions,
    docsHasFilesOptions,
    preferredChannelOptions,
    inPolandOptions,
    opsModeOptions,
    polandBasisOptions,
    trailerTypesOptions,
  }
}
