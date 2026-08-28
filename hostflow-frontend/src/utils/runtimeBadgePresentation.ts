/**
 * Document UI Status Badges P1 — read-only projection of document_runtime_v1.
 * See docs/specs/platform/document-ui-status-badges-p0.md
 */

export type RuntimeBadgeKind =
  | 'approved'
  | 'pending'
  | 'rejected'
  | 'expired'
  | 'expiring_soon'
  | 'missing'

export type DocumentRuntimeV1 = {
  evaluation_version?: string
  workflow_status?: string | null
  expiry_status?: string | null
  runtime_signal?: string | null
  satisfies_requirement?: boolean
  document_type_code?: string | null
  document_id?: string | null
  expires_on?: string | null
  days_left?: number | null
}

export type RuntimeBadgePresentation = {
  badge: RuntimeBadgeKind
  labelKey: string
  className: string
  satisfiesRequirement: boolean
  showSatisfactionIndicator: boolean
}

export const RUNTIME_BADGE_META: Record<RuntimeBadgeKind, { labelKey: string; className: string }> = {
  approved: {
    labelKey: 'admin.documents.status_labels.approved',
    className: 'bg-green-50 text-green-700',
  },
  pending: {
    labelKey: 'admin.documents.status_labels.in_progress',
    className: 'bg-blue-50 text-blue-700',
  },
  rejected: {
    labelKey: 'admin.documents.status_labels.rejected',
    className: 'bg-rose-50 text-rose-700',
  },
  expired: {
    labelKey: 'admin.documents.status_labels.expired',
    className: 'bg-amber-50 text-amber-700',
  },
  expiring_soon: {
    labelKey: 'admin.documents.runtime_badges.expiring_soon',
    className: 'bg-amber-50 text-amber-700',
  },
  missing: {
    labelKey: 'admin.documents.status_labels.missing',
    className: 'bg-gray-100 text-gray-700',
  },
}

const PENDING_WORKFLOW = new Set(['uploaded', 'pending_review'])
const PENDING_SIGNALS = new Set(['pending_verification', 'missing_expiry'])

function norm(value: unknown): string {
  return String(value ?? '').trim().toLowerCase()
}

/** Map canonical document_runtime_v1 → badge vocabulary v1. */
export function runtimeBadgeFromRuntime(
  runtime: DocumentRuntimeV1 | null | undefined,
): RuntimeBadgePresentation {
  if (!runtime || typeof runtime !== 'object') {
    return presentationFor('missing', false)
  }

  const workflow = norm(runtime.workflow_status)
  const expiry = norm(runtime.expiry_status)
  const signal = norm(runtime.runtime_signal)
  const satisfies = runtime.satisfies_requirement === true

  if (workflow === 'missing' || signal === 'missing') {
    return presentationFor('missing', satisfies)
  }
  if (workflow === 'rejected' || signal === 'rejected') {
    return presentationFor('rejected', satisfies)
  }
  if (expiry === 'expired' || signal === 'expired') {
    return presentationFor('expired', satisfies)
  }
  if (signal === 'expiring_soon' || expiry === 'expiring_soon') {
    return presentationFor('expiring_soon', satisfies)
  }
  if (PENDING_WORKFLOW.has(workflow) || PENDING_SIGNALS.has(signal)) {
    return presentationFor('pending', satisfies)
  }
  if (workflow === 'approved') {
    return presentationFor('approved', satisfies)
  }

  return presentationFor('missing', satisfies)
}

function documentPayloadHasFiles(doc: {
  has_files?: boolean | null
  files?: unknown[] | null
} | null | undefined): boolean {
  if (!doc) return false
  if (Array.isArray(doc.files) && doc.files.length > 0) return true
  return Boolean(doc.has_files)
}

function badgeWhenFilePresent(status: string | null | undefined): RuntimeBadgeKind {
  const normalized = String(status ?? '').trim().toLowerCase()
  if (['approved', 'verified', 'completed', 'delivered', 'received'].includes(normalized)) {
    return 'approved'
  }
  return 'pending'
}

export function runtimeBadgeFromDocument(
  doc:
    | {
        document_runtime?: DocumentRuntimeV1 | null
        has_files?: boolean | null
        files?: unknown[] | null
        status?: string | null
      }
    | null
    | undefined,
): RuntimeBadgePresentation {
  const hasFiles = documentPayloadHasFiles(doc)
  if (doc?.document_runtime && typeof doc.document_runtime === 'object') {
    const fromRuntime = runtimeBadgeFromRuntime(doc.document_runtime)
    // Runtime may still say "missing" for a stale snapshot. A stored file is never "no file".
    if (fromRuntime.badge === 'missing' && hasFiles) {
      return presentationFor(badgeWhenFilePresent(doc.status), false)
    }
    return fromRuntime
  }
  if (hasFiles) {
    return presentationFor(badgeWhenFilePresent(doc?.status), false)
  }
  return presentationFor('missing', false)
}

export function runtimeBadgeKindFromDocument(
  doc: { document_runtime?: DocumentRuntimeV1 | null } | null | undefined,
): RuntimeBadgeKind {
  return runtimeBadgeFromDocument(doc).badge
}

/** Thin adapter — replaces date-based isExpiringSoon for badge/filter paths. */
export function isRuntimeExpiringSoon(
  doc: { document_runtime?: DocumentRuntimeV1 | null } | null | undefined,
): boolean {
  return runtimeBadgeFromDocument(doc).badge === 'expiring_soon'
}

/** Thin adapter — replaces date-based isExpired for badge paths. */
export function isRuntimeExpired(
  doc: { document_runtime?: DocumentRuntimeV1 | null } | null | undefined,
): boolean {
  return runtimeBadgeFromDocument(doc).badge === 'expired'
}

export type RuntimeChecklistItem = {
  document_type_code?: string | null
  document_runtime?: DocumentRuntimeV1 | null
}

export function indexRuntimeItemsByType(
  items: RuntimeChecklistItem[] | null | undefined,
): Map<string, DocumentRuntimeV1> {
  const out = new Map<string, DocumentRuntimeV1>()
  for (const row of items ?? []) {
    if (!row || typeof row !== 'object') continue
    const code = norm(row.document_type_code)
    if (!code) continue
    const runtime = row.document_runtime
    if (runtime && typeof runtime === 'object') {
      out.set(code, runtime)
    }
  }
  return out
}

export function extractRuntimeItemsFromSummary(summary: Record<string, unknown> | null | undefined): RuntimeChecklistItem[] {
  if (!summary || typeof summary !== 'object') return []
  const checklist = summary.checklist as Record<string, unknown> | undefined
  const runtimeItems = checklist?.runtimeItems
  if (Array.isArray(runtimeItems) && runtimeItems.length > 0) {
    return runtimeItems as RuntimeChecklistItem[]
  }
  const documentRuntime = summary.document_runtime as Record<string, unknown> | undefined
  const items = documentRuntime?.items
  if (Array.isArray(items)) {
    return items as RuntimeChecklistItem[]
  }
  return []
}

export function runtimeBadgeForDocumentType(
  summary: Record<string, unknown> | null | undefined,
  typeCode: string,
): RuntimeBadgePresentation {
  const normalized = norm(typeCode).replace(/-/g, '_')
  const index = indexRuntimeItemsByType(extractRuntimeItemsFromSummary(summary))
  return runtimeBadgeFromRuntime(index.get(normalized))
}

function presentationFor(badge: RuntimeBadgeKind, satisfiesRequirement: boolean): RuntimeBadgePresentation {
  const meta = RUNTIME_BADGE_META[badge]
  return {
    badge,
    labelKey: meta.labelKey,
    className: meta.className,
    satisfiesRequirement,
    showSatisfactionIndicator: satisfiesRequirement && badge === 'approved',
  }
}
