// src/modules/candidates/hooks/useCandidatesFilterOptions.ts
//
// Builds 13 column-filter dropdown option lists from the enriched
// candidate list only. Each list is built from `enrichedItems`, so the UI
// shows only values that currently exist in data.
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
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, vacancyLabelMap, t])

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
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, resolveManagerLabel])

  const reasonFilterOptions = useMemo<FilterOption[]>(() => {
    const present = new Set<string>()
    enrichedItems.forEach((item) => {
      item.__reasonCodes.forEach((code) => present.add(code))
    })
    return reasonOptions
      .filter((option) => present.has(option.code))
      .map((option) => ({
        value: option.code,
        label: `${option.label} (${option.stageLabel})`,
      }))
  }, [enrichedItems, reasonOptions])

  const docsStatusPresence = useMemo(() => {
    const set = new Set<string>()
    enrichedItems.forEach((item) => set.add(item.__docsMeta.readinessKey))
    return set
  }, [enrichedItems])

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
    const set = new Set<string>()
    enrichedItems.forEach((item) => set.add(item.__docsMeta.isOrdered ? 'ordered' : 'not_ordered'))
    return set
  }, [enrichedItems])

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
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, t])

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
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, preferredChannelLabelMap])

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
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, inPolandLabelMap])

  const opsModeOptions = useMemo<OpsModeOption[]>(() => {
    const map = new Map<CandidateOpsMode, string>()
    const ensure = (value: CandidateOpsMode) => {
      if (map.has(value)) return
      map.set(value, opsModeLabelMap[value])
    }
    enrichedItems.forEach((item) => {
      if (item.__extra.opsMode) ensure(item.__extra.opsMode)
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, opsModeLabelMap])

  const polandBasisOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (map.has(value)) return
      map.set(value, value === EMPTY_OPTION_VALUE ? t('common.labels.not_available') : getPolandBasisLabel(value))
    }
    enrichedItems.forEach((item) => {
      ensure(item.__extra.polandStayBasis ?? EMPTY_OPTION_VALUE)
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, getPolandBasisLabel, t])

  const trailerTypesOptions = useMemo<FilterOption[]>(() => {
    const map = new Map<string, string>()
    const ensure = (value: string) => {
      if (!value || map.has(value)) return
      map.set(value, getTrailerTypeLabel(value))
    }
    enrichedItems.forEach((item) => {
      item.__extra.trailerTypes.forEach((code) => ensure(code))
    })
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }))
  }, [enrichedItems, getTrailerTypeLabel])

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
