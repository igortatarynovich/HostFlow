/**
 * Document Runtime Filters Track A — filter predicates over document_runtime_v1.
 * See docs/specs/platform/document-runtime-filters-p0.md
 */

import type { DocumentRuntimeV1 } from './runtimeBadgePresentation'

export const RUNTIME_DOCUMENT_FILTERS = [
  'expired',
  'expiring_soon',
  'missing',
  'pending_review',
  'rejected',
  'satisfied',
] as const

export type RuntimeDocumentFilter = (typeof RUNTIME_DOCUMENT_FILTERS)[number]

export type RuntimeDocumentFilterSelection = RuntimeDocumentFilter | 'all'

export const RUNTIME_FILTER_LABEL_KEYS: Record<RuntimeDocumentFilter, string> = {
  expired: 'admin.documents.runtime_filters.expired',
  expiring_soon: 'admin.documents.runtime_filters.expiring_soon',
  missing: 'admin.documents.runtime_filters.missing',
  pending_review: 'admin.documents.runtime_filters.pending_review',
  rejected: 'admin.documents.runtime_filters.rejected',
  satisfied: 'admin.documents.runtime_filters.satisfied',
}

/** Legacy registry quick keys → runtime filter (URL compat). */
export const LEGACY_QUICK_FILTER_TO_RUNTIME: Record<string, RuntimeDocumentFilter> = {
  missing: 'missing',
  ready: 'satisfied',
  in_progress: 'pending_review',
  requested: 'pending_review',
}

function norm(value: unknown): string {
  return String(value ?? '').trim().toLowerCase()
}

export function isRuntimeDocumentFilter(value: string): value is RuntimeDocumentFilter {
  return (RUNTIME_DOCUMENT_FILTERS as readonly string[]).includes(value)
}

export function resolveRuntimeDocumentFilter(value: string | null | undefined): RuntimeDocumentFilter | null {
  const trimmed = String(value ?? '').trim()
  if (!trimmed) return null
  if (isRuntimeDocumentFilter(trimmed)) return trimmed
  return LEGACY_QUICK_FILTER_TO_RUNTIME[trimmed] ?? null
}

/** Single predicate: runtime ↔ filter vocabulary v1. */
export function runtimeMatchesFilter(
  runtime: DocumentRuntimeV1 | null | undefined,
  filter: RuntimeDocumentFilter,
): boolean {
  if (!runtime || typeof runtime !== 'object') {
    return false
  }

  const workflow = norm(runtime.workflow_status)
  const expiry = norm(runtime.expiry_status)
  const signal = norm(runtime.runtime_signal)

  switch (filter) {
    case 'expired':
      return expiry === 'expired'
    case 'expiring_soon':
      return expiry === 'expiring_soon'
    case 'missing':
      return workflow === 'missing'
    case 'pending_review':
      return signal === 'pending_verification'
    case 'rejected':
      return workflow === 'rejected'
    case 'satisfied':
      return runtime.satisfies_requirement === true
    default:
      return false
  }
}

export function documentMatchesRuntimeFilter(
  doc: { document_runtime?: DocumentRuntimeV1 | null } | null | undefined,
  filter: RuntimeDocumentFilter,
): boolean {
  return runtimeMatchesFilter(doc?.document_runtime, filter)
}

export function documentMatchesRuntimeFilterSelection(
  doc: { document_runtime?: DocumentRuntimeV1 | null } | null | undefined,
  filter: RuntimeDocumentFilterSelection,
): boolean {
  if (filter === 'all') return true
  return documentMatchesRuntimeFilter(doc, filter)
}
