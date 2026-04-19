// src/modules/candidates/filterNormalizers.ts
//
// Pure normalisation helpers for filter values arriving from arbitrary
// sources (saved-view JSON, deep-link URL params, persisted localStorage).
// Extracted from inline `useCallback` blocks in `src/pages/Candidates.tsx`
// (Phase 1 #4 god-component split).
//
// All helpers are referentially stable (no React deps) and side-effect-free
// — safe to import and call from anywhere.

import { makeEmptyTextFilters } from './types'
import type { CandidateOpsMode, ColumnTextFilters, DateRangeFilter } from './types'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeReasonList(value: any): string[] {
  if (value == null) return []
  const parts = new Set<string>()
  const push = (input: unknown): void => {
    if (input == null) return
    if (Array.isArray(input)) {
      input.forEach((entry) => push(entry))
      return
    }
    if (typeof input === 'object') {
      const obj = input as Record<string, unknown>
      const candidate =
        obj.code ??
        obj.value ??
        obj.id ??
        obj.reason ??
        obj.label ??
        obj.name ??
        (typeof obj.text === 'string' ? obj.text : undefined)
      if (candidate) {
        push(candidate)
      }
      if (Array.isArray(obj.codes)) {
        obj.codes.forEach((entry) => push(entry))
      }
      return
    }
    const str = String(input)
    str
      .split(',')
      .map((chunk) => chunk.trim())
      .filter(Boolean)
      .forEach((chunk) => parts.add(chunk))
  }
  push(value)
  return Array.from(parts)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeArrayFilter(value: any): string[] {
  if (!value) return []
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter((item) => item.trim().length > 0)
  }
  if (typeof value === 'string') {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  }
  return [String(value)]
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeRangeFilter(value: any): DateRangeFilter {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sanitize = (input: any): string | null => {
    if (typeof input !== 'string') return null
    const trimmed = input.trim()
    return trimmed ? trimmed.slice(0, 10) : null
  }
  if (!value || typeof value !== 'object') {
    return { from: null, to: null }
  }
  return {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    from: sanitize((value as any).from),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    to: sanitize((value as any).to),
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeTextFilterState(value: any): ColumnTextFilters {
  if (!value || typeof value !== 'object') return makeEmptyTextFilters()
  return {
    name: typeof value.name === 'string' ? value.name : '',
    email: typeof value.email === 'string' ? value.email : '',
    phone: typeof value.phone === 'string' ? value.phone : '',
    citizenship: typeof value.citizenship === 'string' ? value.citizenship : '',
    short: typeof value.short === 'string' ? value.short : '',
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeOpsModeList(value: any): CandidateOpsMode[] {
  return normalizeArrayFilter(value).filter(
    (item): item is CandidateOpsMode =>
      item === 'in_work' || item === 'later' || item === 'no_reply_needed' || item === 'escalated',
  )
}
