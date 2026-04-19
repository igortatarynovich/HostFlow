// src/modules/candidates/candidateFilters.ts
//
// Pure client-side filtering for the Candidates list.
// Extracted from the inline `filterCandidates` callback in
// `src/pages/Candidates.tsx` (Phase 1 #4 god-component split).
//
// The function is intentionally framework-agnostic and side-effect-free
// (apart from optional debug logging gated by `debug`), so it can be
// memoised by the caller and unit-tested in isolation.

import { EMPTY_OPTION_VALUE } from './constants'
import {
  matchesDateRange,
  normalizeSearchValue,
  phoneTextMatches,
  textMatches,
} from './candidateUtils'
import { getCandidateManagerId } from './utils'
import type { AugmentedCandidate, CandidateFilterSnapshot } from './types'

export interface FilterCandidatesOptions {
  /** When true, emits `console.warn` traces for every filtered-out candidate. */
  debug?: boolean
}

/**
 * Apply a snapshot of UI filters to a candidate list. Returns a new array
 * containing only the candidates that pass every active predicate.
 */
export function filterCandidates(
  source: AugmentedCandidate[],
  snapshot: CandidateFilterSnapshot,
  options: FilterCandidatesOptions = {},
): AugmentedCandidate[] {
  const { debug = false } = options

  const shouldFilterDocsOrdered = snapshot.docsOrdered.length === 1
  const orderedTarget = shouldFilterDocsOrdered ? snapshot.docsOrdered[0] : null
  const normalizedQuery = normalizeSearchValue(snapshot.query ?? '')
  const textQueries = {
    name: normalizeSearchValue(snapshot.textFilters.name ?? ''),
    email: normalizeSearchValue(snapshot.textFilters.email ?? ''),
    phone: normalizeSearchValue(snapshot.textFilters.phone ?? ''),
    citizenship: normalizeSearchValue(snapshot.textFilters.citizenship ?? ''),
    short: normalizeSearchValue(snapshot.textFilters.short ?? ''),
  }

  return source.filter((item) => {
    if (normalizedQuery) {
      const haystacks = [
        `${item.first_name ?? ''} ${item.last_name ?? ''}`.trim(),
        item.email ?? '',
        item.phone ?? '',
        item.short_id ?? '',
        item.stage ?? '',
        item.__extra.citizenship ?? '',
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (item as any)?.vacancy?.title ?? (item as any)?.vacancy_title ?? '',
      ]
      const queryMatch = haystacks.some((value, idx) =>
        idx === 2 ? phoneTextMatches(value, normalizedQuery) : textMatches(value, normalizedQuery),
      )
      if (!queryMatch) return false
    }

    if (textQueries.name && !textMatches(`${item.first_name ?? ''} ${item.last_name ?? ''}`.trim(), textQueries.name)) {
      return false
    }
    if (textQueries.email && !textMatches(item.email ?? '', textQueries.email)) {
      return false
    }
    if (textQueries.phone && !phoneTextMatches(item.phone ?? '', snapshot.textFilters.phone ?? '')) {
      return false
    }
    if (textQueries.citizenship && !textMatches(item.__extra.citizenship ?? '', textQueries.citizenship)) {
      return false
    }
    if (textQueries.short && !textMatches(item.short_id ?? '', textQueries.short)) {
      return false
    }

    if (snapshot.stage.length && (!item.stage || !snapshot.stage.includes(item.stage))) {
      return false
    }

    if (snapshot.vacancy.length) {
      const candidateVacancy =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (item as any)?.vacancy_id || (item as any)?.vacancy?.id || (item as any)?.vacancy_uuid || null
      if (!candidateVacancy || !snapshot.vacancy.includes(String(candidateVacancy))) {
        return false
      }
    }

    if (snapshot.manager.length) {
      const candidateManager = getCandidateManagerId(item)
      if (!candidateManager || !snapshot.manager.includes(String(candidateManager))) {
        return false
      }
    }

    if (snapshot.statusReasons.length) {
      if (!item.__reasonCodes.some((code) => snapshot.statusReasons.includes(code))) {
        return false
      }
    }

    if (snapshot.docsStatus.length && !snapshot.docsStatus.includes(item.__docsMeta.readinessKey)) {
      return false
    }

    if (shouldFilterDocsOrdered) {
      if (orderedTarget === 'ordered' && !item.__docsMeta.isOrdered) return false
      if (orderedTarget === 'not_ordered' && item.__docsMeta.isOrdered) return false
    }

    if (snapshot.docsHasFiles.length) {
      const bucket = item.__docsMeta.hasFiles ? 'with' : 'without'
      if (!snapshot.docsHasFiles.includes(bucket)) {
        return false
      }
    }

    if (!matchesDateRange(item.created_at ?? null, snapshot.createdRange)) {
      if (debug) console.warn('[Candidates] Filtered by createdRange:', { item_id: item.id, created_at: item.created_at, range: snapshot.createdRange })
      return false
    }

    if (!matchesDateRange(item.__extra.firstContactAt, snapshot.firstContactRange)) {
      if (debug) console.warn('[Candidates] Filtered by firstContactRange:', { item_id: item.id, firstContactAt: item.__extra.firstContactAt, range: snapshot.firstContactRange })
      return false
    }

    if (!matchesDateRange(item.__docsMeta.validFrom, snapshot.docsValidRange)) {
      if (debug) console.warn('[Candidates] Filtered by docsValidRange:', { item_id: item.id, validFrom: item.__docsMeta.validFrom, range: snapshot.docsValidRange })
      return false
    }

    if (snapshot.preferredChannels.length) {
      const channel = item.__extra.preferredContact ?? EMPTY_OPTION_VALUE
      if (!snapshot.preferredChannels.includes(channel)) {
        return false
      }
    }

    if (snapshot.polandPresence.length) {
      const presence = item.__extra.inPoland === true ? 'yes' : item.__extra.inPoland === false ? 'no' : 'unknown'
      if (!snapshot.polandPresence.includes(presence)) {
        return false
      }
    }
    if (snapshot.opsModes.length) {
      const mode = item.__extra.opsMode
      if (!mode || !snapshot.opsModes.includes(mode)) {
        return false
      }
    }

    if (snapshot.polandBasis.length) {
      const basis = item.__extra.polandStayBasis ?? EMPTY_OPTION_VALUE
      if (!snapshot.polandBasis.includes(basis)) {
        return false
      }
    }

    if (snapshot.trailerTypes.length) {
      if (!item.__extra.trailerTypes.some((code) => snapshot.trailerTypes.includes(code))) {
        return false
      }
    }

    if (snapshot.isFavorite !== null && snapshot.isFavorite !== undefined) {
      const isFavorite = item.is_favorite ?? false
      if (snapshot.isFavorite !== isFavorite) {
        if (debug) console.warn('[Candidates] Filtered by isFavorite:', { item_id: item.id, item_is_favorite: item.is_favorite, filter_isFavorite: snapshot.isFavorite })
        return false
      }
    }

    if (snapshot.tags.length > 0) {
      const candidateTags = Array.isArray(item.tags) ? item.tags : []
      if (!snapshot.tags.some((tag) => candidateTags.includes(tag))) {
        return false
      }
    }

    return true
  })
}
