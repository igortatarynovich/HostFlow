/**
 * Track D — Candidate Workspace runtime readiness surface.
 * See docs/specs/platform/document-candidate-workspace-p0.md
 */

import {
  extractRuntimeItemsFromSummary,
  runtimeBadgeFromRuntime,
  type DocumentRuntimeV1,
  type RuntimeBadgePresentation,
} from './runtimeBadgePresentation'

export type RuntimeWorkspaceSignal = {
  code: string
  message?: string
}

export type RuntimeWorkspaceItem = {
  documentTypeCode: string
  runtime: DocumentRuntimeV1
  badge: RuntimeBadgePresentation
  blockers: RuntimeWorkspaceSignal[]
  warnings: RuntimeWorkspaceSignal[]
}

export type RuntimeWorkspacePipelineBlockers = {
  missing: string[]
  problematic: string[]
  inProgress: string[]
}

export type RuntimeWorkspaceSnapshot = {
  source: 'runtime'
  totalRequired: number
  satisfiedCount: number
  percentReady: number
  readinessKey: string
  items: RuntimeWorkspaceItem[]
  blockingItems: RuntimeWorkspaceItem[]
  warningOnlyItems: RuntimeWorkspaceItem[]
  pipelineBlockers: RuntimeWorkspacePipelineBlockers
}

type RuntimeChecklistRow = {
  document_type_code?: string | null
  document_runtime?: DocumentRuntimeV1 | null
}

function normType(value: unknown): string {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

function readSignals(raw: unknown): RuntimeWorkspaceSignal[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map((row) => {
      if (!row || typeof row !== 'object') return null
      const code = String((row as Record<string, unknown>).code || '').trim()
      if (!code) return null
      const message = String((row as Record<string, unknown>).message || '').trim()
      return { code, message: message || undefined }
    })
    .filter((row): row is RuntimeWorkspaceSignal => Boolean(row))
}

function pipelineBlockersFromItems(items: RuntimeWorkspaceItem[]): RuntimeWorkspacePipelineBlockers {
  const missing: string[] = []
  const problematic: string[] = []
  const inProgress: string[] = []

  for (const item of items) {
    const code = item.documentTypeCode
    switch (item.badge.badge) {
      case 'missing':
        missing.push(code)
        break
      case 'rejected':
      case 'expired':
        problematic.push(code)
        break
      case 'pending':
        inProgress.push(code)
        break
      default:
        break
    }
  }

  return {
    missing: [...new Set(missing)],
    problematic: [...new Set(problematic)],
    inProgress: [...new Set(inProgress)],
  }
}

function deriveReadinessKey(items: RuntimeWorkspaceItem[], satisfiedCount: number, totalRequired: number): string {
  if (totalRequired === 0) return 'pending'

  const badges = items.map((item) => item.badge.badge)
  if (badges.some((badge) => badge === 'rejected' || badge === 'expired' || badge === 'missing')) {
    return 'problem'
  }
  if (satisfiedCount === totalRequired) {
    return badges.some((badge) => badge === 'expiring_soon') ? 'awaiting_review' : 'ready'
  }
  if (badges.some((badge) => badge === 'pending')) return 'in_progress'
  if (badges.some((badge) => badge === 'expiring_soon')) return 'awaiting_review'
  return 'pending'
}

function mapRuntimeItem(row: RuntimeChecklistRow): RuntimeWorkspaceItem | null {
  const documentTypeCode = normType(row.document_type_code)
  const runtime = row.document_runtime
  if (!documentTypeCode || !runtime || typeof runtime !== 'object') return null

  const blockers = readSignals(runtime.blockers)
  const warnings = readSignals(runtime.warnings)

  return {
    documentTypeCode,
    runtime,
    badge: runtimeBadgeFromRuntime(runtime),
    blockers,
    warnings,
  }
}

/** Build Candidate Workspace snapshot from documents summary payload. */
export function buildRuntimeWorkspaceFromSummary(
  summary: Record<string, unknown> | null | undefined,
): RuntimeWorkspaceSnapshot | null {
  const rows = extractRuntimeItemsFromSummary(summary)
  if (!rows.length) return null

  const items = rows
    .map((row) => mapRuntimeItem(row))
    .filter((item): item is RuntimeWorkspaceItem => Boolean(item))

  if (!items.length) return null

  const totalRequired = items.length
  const satisfiedCount = items.filter((item) => item.runtime.satisfies_requirement === true).length
  const percentReady = totalRequired === 0 ? 0 : Math.round((100 * satisfiedCount) / totalRequired)

  const blockingItems = items.filter((item) => item.blockers.length > 0)
  const warningOnlyItems = items.filter((item) => item.blockers.length === 0 && item.warnings.length > 0)

  return {
    source: 'runtime',
    totalRequired,
    satisfiedCount,
    percentReady,
    readinessKey: deriveReadinessKey(items, satisfiedCount, totalRequired),
    items,
    blockingItems,
    warningOnlyItems,
    pipelineBlockers: pipelineBlockersFromItems(items),
  }
}

export function workspaceHasPipelineBlockers(workspace: RuntimeWorkspaceSnapshot): boolean {
  const { missing, problematic, inProgress } = workspace.pipelineBlockers
  return missing.length > 0 || problematic.length > 0 || inProgress.length > 0
}
