import type { DocumentPackProjection, ReminderWorkQueueItem, ReminderWorkQueueSeverity } from '../api/types'
import type { HrReviewPanel, WorkforceEligibilityRuntime } from '../api/workforce'
import {
  documentsFromPanel,
  isDocumentVerified,
  requiredPlanDocuments,
  sequentialDocumentQueue,
} from '../components/hr/hrDocumentVerificationFields'
import { isVerificationPlanReady } from '../components/hr/hrVerificationReadySummary'
import { DOCUMENT_ACTION_LABEL, humanizeDocumentCode, humanizePackCode } from './documentActionsPanel'
import {
  isPackCodePendingVerification,
  isPackCodeVerifiedInHrReview,
  normDocumentToken,
  resolveDocumentLabel,
  resolveFocusDocumentKey,
} from './documentReadinessLabels'

export type ReadinessTier =
  | 'critical_blocker'
  | 'eligibility_blocker'
  | 'verify_document'
  | 'expired_required'
  | 'missing_required'
  | 'expiring'
  | 'admin_warning'

export type ReadinessStatus = 'ready' | 'not_ready' | 'attention'

export type ReadinessCandidate = {
  tier: ReadinessTier
  tierOrder: number
  actionTitle: string
  reason: string
  missingItems: string[]
  responsible: string
  blocksEmployment: boolean
  blockLabel: string
  dueDate?: string | null
  dueLabel: string
  sourcePack?: string
  documentCode?: string
  scrollAnchor: string
  severity: ReminderWorkQueueSeverity | 'high' | 'medium' | 'low'
}

export type PackStripItem = {
  code: string
  label: string
  statusLabel: string
  tone: 'emerald' | 'amber' | 'rose' | 'slate'
}

export type EmployeeReadinessSummary = {
  status: ReadinessStatus
  statusLabel: string
  primary: ReadinessCandidate | null
  primaryCta: ReadinessPrimaryCta | null
  packStrip: PackStripItem[]
  remainingBlockingCount: number
  readyNextStep: string | null
  verificationProgress: { verified: number; total: number } | null
}

export type ReadinessCtaKind = 'verify' | 'obtain' | 'renew' | 'admin' | 'approval' | 'documents'

export type ReadinessPrimaryCta = {
  kind: ReadinessCtaKind
  label: string
  focusDocumentKey?: string | null
  focusPackCode?: string | null
  scrollTarget: string
}

const TIER_ORDER: Record<ReadinessTier, number> = {
  critical_blocker: 10,
  eligibility_blocker: 20,
  verify_document: 25,
  expired_required: 30,
  missing_required: 40,
  expiring: 50,
  admin_warning: 60,
}

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

type LabelContext = {
  hrReview?: HrReviewPanel | null
}

function labelFor(code: string, ctx: LabelContext): string {
  return resolveDocumentLabel(code, ctx.hrReview)
}

function actionTitleForDocument(
  code: string,
  kind: 'missing' | 'expired' | 'expiring' | 'blocker' | 'verify',
  ctx: LabelContext,
): string {
  const doc = labelFor(code, ctx)
  switch (kind) {
    case 'missing':
      return `Obtain ${doc}`
    case 'expired':
      return `Renew ${doc}`
    case 'expiring':
      return `Prepare renewal: ${doc}`
    case 'verify':
      return `Verify ${doc}`
    default:
      return `Resolve ${doc}`
  }
}

function normSeverity(value: unknown): ReminderWorkQueueSeverity | 'high' | 'medium' | 'low' {
  const raw = String(value || '').toLowerCase()
  if (raw === 'critical' || raw === 'high' || raw === 'medium' || raw === 'low') return raw
  return 'medium'
}

function tierForQueueItem(item: ReminderWorkQueueItem): ReadinessTier {
  if (item.severity === 'critical') return 'critical_blocker'
  const reason = String(item.reason || '').toLowerCase()
  if (reason === 'expired') return 'expired_required'
  if (reason === 'missing') return 'missing_required'
  if (reason === 'expiring_soon') return 'expiring'
  return 'admin_warning'
}

function actionTitleForQueue(item: ReminderWorkQueueItem, ctx: LabelContext): string {
  if (item.title?.trim()) {
    const title = item.title.trim()
    const doc = labelFor(item.document_code, ctx)
    if (title.toLowerCase().includes(item.document_code.replace(/_/g, ' '))) {
      return title.replace(new RegExp(humanizeDocumentCode(item.document_code), 'i'), doc)
    }
    return title
  }
  const label = DOCUMENT_ACTION_LABEL[item.action] || item.action
  return `${label}: ${labelFor(item.document_code, ctx)}`
}

export function formatReadinessDueLabel(value?: string | null, now = new Date()): string {
  if (!value) return '—'
  const parsed = Date.parse(String(value).slice(0, 10))
  if (!Number.isFinite(parsed)) return String(value).slice(0, 10)
  const due = new Date(parsed)
  const today = new Date(now)
  today.setHours(0, 0, 0, 0)
  due.setHours(0, 0, 0, 0)
  const diffDays = Math.round((due.getTime() - today.getTime()) / 86400000)
  if (diffDays < 0) return 'Overdue'
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'short' }).format(due)
  } catch {
    return String(value).slice(0, 10)
  }
}

function candidateKey(candidate: Pick<ReadinessCandidate, 'tier' | 'documentCode' | 'actionTitle'>): string {
  return `${candidate.tier}:${candidate.documentCode || ''}:${candidate.actionTitle}`
}

function upsertCandidate(pool: Map<string, ReadinessCandidate>, candidate: ReadinessCandidate) {
  const key = candidateKey(candidate)
  const existing = pool.get(key)
  if (!existing || candidate.tierOrder < existing.tierOrder) {
    pool.set(key, candidate)
  }
}

function shouldSkipPackCode(code: string, hrReview?: HrReviewPanel | null): boolean {
  if (isPackCodeVerifiedInHrReview(code, hrReview)) return true
  if (isPackCodePendingVerification(code, hrReview)) return true
  return false
}

function openPackCodes(pack: DocumentPackProjection, hrReview?: HrReviewPanel | null): string[] {
  const raw = [...(pack.blockers ?? []), ...(pack.expired ?? []), ...(pack.missing ?? [])]
  return [...new Set(raw.map(normDocumentToken).filter(Boolean))].filter((code) => !shouldSkipPackCode(code, hrReview))
}

function buildPackCandidates(packs: DocumentPackProjection[], ctx: LabelContext): ReadinessCandidate[] {
  const out: ReadinessCandidate[] = []
  for (const pack of packs) {
    if (!pack.applies || pack.skeleton) continue
    const packLabel = pack.label || humanizePackCode(pack.code)
    const packReason =
      pack.status === 'gaps'
        ? `${packLabel} incomplete`
        : pack.status === 'warnings'
          ? `${packLabel} needs attention`
          : packLabel
    const openCodes = openPackCodes(pack, ctx.hrReview)
    const openLabels = openCodes.map((code) => labelFor(code, ctx))

    for (const code of pack.blockers ?? []) {
      if (shouldSkipPackCode(code, ctx.hrReview)) continue
      out.push({
        tier: 'critical_blocker',
        tierOrder: TIER_ORDER.critical_blocker,
        actionTitle: actionTitleForDocument(code, 'blocker', ctx),
        reason: `${packLabel} incomplete`,
        missingItems: openLabels,
        responsible: 'HR',
        blocksEmployment: true,
        blockLabel: 'Blocks employment readiness',
        dueDate: null,
        dueLabel: 'Today',
        sourcePack: pack.code,
        documentCode: code,
        scrollAnchor: '#dossier-documents',
        severity: 'critical',
      })
    }

    for (const code of pack.expired ?? []) {
      if (shouldSkipPackCode(code, ctx.hrReview)) continue
      out.push({
        tier: 'expired_required',
        tierOrder: TIER_ORDER.expired_required,
        actionTitle: actionTitleForDocument(code, 'expired', ctx),
        reason: packReason,
        missingItems: openLabels,
        responsible: 'HR',
        blocksEmployment: true,
        blockLabel: 'Blocks employment transition',
        dueDate: null,
        dueLabel: 'Today',
        sourcePack: pack.code,
        documentCode: code,
        scrollAnchor: '#dossier-documents',
        severity: 'critical',
      })
    }

    for (const code of pack.missing ?? []) {
      if (shouldSkipPackCode(code, ctx.hrReview)) continue
      out.push({
        tier: 'missing_required',
        tierOrder: TIER_ORDER.missing_required,
        actionTitle: actionTitleForDocument(code, 'missing', ctx),
        reason: `${packLabel} incomplete`,
        missingItems: openLabels,
        responsible: 'HR',
        blocksEmployment: true,
        blockLabel: 'Blocks employment transition',
        dueDate: null,
        dueLabel: '—',
        sourcePack: pack.code,
        documentCode: code,
        scrollAnchor: '#dossier-documents',
        severity: 'high',
      })
    }

    for (const row of pack.expiring_soon ?? []) {
      const code = row.document_code
      if (!code || shouldSkipPackCode(code, ctx.hrReview)) continue
      out.push({
        tier: 'expiring',
        tierOrder: TIER_ORDER.expiring,
        actionTitle: actionTitleForDocument(code, 'expiring', ctx),
        reason: `${packLabel} expiring soon`,
        missingItems: [labelFor(code, ctx)],
        responsible: 'HR',
        blocksEmployment: false,
        blockLabel: 'Does not block yet',
        dueDate: row.expires_on || null,
        dueLabel: formatReadinessDueLabel(row.expires_on),
        sourcePack: pack.code,
        documentCode: code,
        scrollAnchor: '#dossier-documents',
        severity: 'medium',
      })
    }

    for (const code of pack.missing_expiry ?? []) {
      if (isPackCodeVerifiedInHrReview(code, ctx.hrReview)) continue
      out.push({
        tier: 'admin_warning',
        tierOrder: TIER_ORDER.admin_warning,
        actionTitle: `Capture expiry date: ${labelFor(code, ctx)}`,
        reason: `${packLabel} missing expiry metadata`,
        missingItems: [labelFor(code, ctx)],
        responsible: 'HR',
        blocksEmployment: false,
        blockLabel: 'Administrative follow-up',
        dueDate: null,
        dueLabel: '—',
        sourcePack: pack.code,
        documentCode: code,
        scrollAnchor: '#dossier-documents',
        severity: 'low',
      })
    }
  }
  return out
}

function buildVerificationCandidates(hrReview: HrReviewPanel, ctx: LabelContext): ReadinessCandidate[] {
  const docs = documentsFromPanel(hrReview)
  const queue = sequentialDocumentQueue(requiredPlanDocuments(docs))
  return queue
    .filter((doc) => !isDocumentVerified(doc) && Boolean(doc.document_id))
    .map((doc) => {
      const code = String(doc.document_type || doc.document_key || doc.label || '')
      const label = doc.label?.trim() || labelFor(code, ctx)
      return {
        tier: 'verify_document' as const,
        tierOrder: TIER_ORDER.verify_document,
        actionTitle: `Verify ${label}`,
        reason: 'Uploaded — HR confirmation required',
        missingItems: [],
        responsible: 'HR',
        blocksEmployment: true,
        blockLabel: 'Blocks employment transition',
        dueDate: null,
        dueLabel: 'Today',
        documentCode: code || doc.document_key,
        scrollAnchor: '#dossier-documents',
        severity: 'high' as const,
      }
    })
}

function buildQueueCandidates(queue: ReminderWorkQueueItem[], ctx: LabelContext): ReadinessCandidate[] {
  return queue
    .filter((item) => !isPackCodeVerifiedInHrReview(item.document_code, ctx.hrReview))
    .map((item) => {
      const tier = tierForQueueItem(item)
      const packLabel = humanizePackCode(item.source_pack)
      return {
        tier,
        tierOrder: TIER_ORDER[tier],
        actionTitle: actionTitleForQueue(item, ctx),
        reason:
          tier === 'admin_warning'
            ? `${packLabel} administrative follow-up`
            : `${packLabel} incomplete`,
        missingItems: [labelFor(item.document_code, ctx)],
        responsible: String(item.recipient_role || 'HR').toUpperCase(),
        blocksEmployment: tier !== 'expiring' && tier !== 'admin_warning',
        blockLabel:
          tier === 'expiring' || tier === 'admin_warning'
            ? 'Does not block yet'
            : 'Blocks employment transition',
        dueDate: item.due_date || null,
        dueLabel: formatReadinessDueLabel(item.due_date),
        sourcePack: item.source_pack,
        documentCode: item.document_code,
        scrollAnchor: '#dossier-documents',
        severity: normSeverity(item.severity),
      }
    })
}

function buildEligibilityCandidates(
  eligibility: WorkforceEligibilityRuntime | null | undefined,
  ctx: LabelContext,
): ReadinessCandidate[] {
  if (!eligibility) return []
  const out: ReadinessCandidate[] = []

  for (const blocker of eligibility.blocking_reasons ?? []) {
    const severity = normSeverity(blocker.severity)
    const tier: ReadinessTier =
      severity === 'critical' || severity === 'high' ? 'critical_blocker' : 'eligibility_blocker'
    const docCode = blocker.document_code || ''
    if (docCode && isPackCodeVerifiedInHrReview(docCode, ctx.hrReview)) continue
    out.push({
      tier,
      tierOrder: TIER_ORDER[tier],
      actionTitle:
        blocker.resolution_action ||
        (docCode ? actionTitleForDocument(docCode, 'blocker', ctx) : 'Resolve eligibility blocker'),
      reason: blocker.block_type?.replace(/_/g, ' ') || 'Workforce eligibility blocker',
      missingItems: docCode ? [labelFor(docCode, ctx)] : [],
      responsible: 'HR',
      blocksEmployment: true,
      blockLabel: 'Blocks employment transition',
      dueDate: null,
      dueLabel: 'Today',
      documentCode: docCode || undefined,
      scrollAnchor: '#dossier-documents',
      severity,
    })
  }

  for (const code of eligibility.expired_documents ?? []) {
    if (shouldSkipPackCode(code, ctx.hrReview)) continue
    out.push({
      tier: 'expired_required',
      tierOrder: TIER_ORDER.expired_required,
      actionTitle: actionTitleForDocument(code, 'expired', ctx),
      reason: 'Required document expired',
      missingItems: [labelFor(code, ctx)],
      responsible: 'HR',
      blocksEmployment: true,
      blockLabel: 'Blocks employment transition',
      dueDate: null,
      dueLabel: 'Today',
      documentCode: code,
      scrollAnchor: '#dossier-documents',
      severity: 'critical',
    })
  }

  for (const code of eligibility.missing_documents ?? []) {
    if (shouldSkipPackCode(code, ctx.hrReview)) continue
    out.push({
      tier: 'missing_required',
      tierOrder: TIER_ORDER.missing_required,
      actionTitle: actionTitleForDocument(code, 'missing', ctx),
      reason: 'Required document missing',
      missingItems: [labelFor(code, ctx)],
      responsible: 'HR',
      blocksEmployment: true,
      blockLabel: 'Blocks employment transition',
      dueDate: null,
      dueLabel: '—',
      documentCode: code,
      scrollAnchor: '#dossier-documents',
      severity: 'high',
    })
  }

  for (const row of eligibility.soon_expiring_documents ?? []) {
    const code = String((row as Record<string, unknown>).document_code || (row as Record<string, unknown>).type || '')
    if (!code || shouldSkipPackCode(code, ctx.hrReview)) continue
    const expiresOn = String(
      (row as Record<string, unknown>).expires_at || (row as Record<string, unknown>).expires_on || '',
    )
    out.push({
      tier: 'expiring',
      tierOrder: TIER_ORDER.expiring,
      actionTitle: actionTitleForDocument(code, 'expiring', ctx),
      reason: 'Document expiring soon',
      missingItems: [labelFor(code, ctx)],
      responsible: 'HR',
      blocksEmployment: false,
      blockLabel: 'Does not block yet',
      dueDate: expiresOn || null,
      dueLabel: formatReadinessDueLabel(expiresOn),
      documentCode: code,
      scrollAnchor: '#dossier-documents',
      severity: 'medium',
    })
  }

  for (const warning of eligibility.warnings ?? []) {
    out.push({
      tier: 'admin_warning',
      tierOrder: TIER_ORDER.admin_warning,
      actionTitle: warning,
      reason: 'Administrative warning',
      missingItems: [],
      responsible: 'HR',
      blocksEmployment: false,
      blockLabel: 'Administrative follow-up',
      dueDate: null,
      dueLabel: '—',
      scrollAnchor: '#dossier-documents',
      severity: 'low',
    })
  }

  return out
}

function pickPrimary(candidates: ReadinessCandidate[]): ReadinessCandidate | null {
  if (!candidates.length) return null
  const sorted = [...candidates].sort((a, b) => {
    if (a.tierOrder !== b.tierOrder) return a.tierOrder - b.tierOrder
    const sevA = SEVERITY_ORDER[a.severity] ?? 9
    const sevB = SEVERITY_ORDER[b.severity] ?? 9
    if (sevA !== sevB) return sevA - sevB
    if (a.blocksEmployment !== b.blocksEmployment) return a.blocksEmployment ? -1 : 1
    return String(a.dueDate || '').localeCompare(String(b.dueDate || ''))
  })
  return sorted[0] ?? null
}

function countRemainingBlockers(
  candidates: ReadinessCandidate[],
  packs: DocumentPackProjection[],
  hrReview?: HrReviewPanel | null,
): number {
  const blocking = candidates.filter((c) => c.blocksEmployment && c.tierOrder <= TIER_ORDER.missing_required)
  const codes = new Set(blocking.map((c) => normDocumentToken(c.documentCode || '')).filter(Boolean))
  if (codes.size > 0) return codes.size

  let maxOpen = 0
  for (const pack of packs) {
    if (!pack.applies || pack.skeleton) continue
    maxOpen = Math.max(maxOpen, openPackCodes(pack, hrReview).length)
  }
  return maxOpen
}

function buildVerificationProgress(hrReview?: HrReviewPanel | null): { verified: number; total: number } | null {
  if (!hrReview) return null
  const docs = sequentialDocumentQueue(requiredPlanDocuments(documentsFromPanel(hrReview)))
  if (!docs.length) return null
  const verified = docs.filter(isDocumentVerified).length
  return { verified, total: docs.length }
}

export function buildPackStrip(packs: DocumentPackProjection[], hrReview?: HrReviewPanel | null): PackStripItem[] {
  return (packs || [])
    .filter((pack) => pack.applies && !pack.skeleton)
    .map((pack) => {
      const label = pack.label || humanizePackCode(pack.code)
      const openCount = openPackCodes(pack, hrReview).length
      if (pack.status === 'valid' || openCount === 0) {
        return { code: pack.code, label, statusLabel: 'Ready', tone: 'emerald' as const }
      }
      if (pack.status === 'gaps' || openCount > 0) {
        return {
          code: pack.code,
          label,
          statusLabel: openCount > 0 ? `Missing ${openCount}` : 'Gaps',
          tone: 'rose' as const,
        }
      }
      if (pack.status === 'warnings') {
        return { code: pack.code, label, statusLabel: 'Partial', tone: 'amber' as const }
      }
      return { code: pack.code, label, statusLabel: '—', tone: 'slate' as const }
    })
}

function resolveStatus(
  primary: ReadinessCandidate | null,
  hrReview?: HrReviewPanel | null,
): { status: ReadinessStatus; statusLabel: string; readyNextStep: string | null } {
  if (!primary) {
    const readyNextStep = hrReview && isVerificationPlanReady(hrReview) ? 'HR Approval' : null
    return { status: 'ready', statusLabel: 'READY', readyNextStep }
  }
  if (primary.tier === 'expiring' || primary.tier === 'admin_warning') {
    return { status: 'attention', statusLabel: 'ATTENTION', readyNextStep: null }
  }
  return { status: 'not_ready', statusLabel: 'NOT READY', readyNextStep: null }
}

export function buildReadinessPrimaryCta(
  primary: ReadinessCandidate | null,
  hrReview?: HrReviewPanel | null,
  readyNextStep?: string | null,
): ReadinessPrimaryCta | null {
  if (!primary) {
    if (readyNextStep) {
      return {
        kind: 'approval',
        label: `Continue to ${readyNextStep}`,
        scrollTarget: '#dossier-documents',
      }
    }
    return null
  }

  const packCode = primary.documentCode || ''
  const focusDocumentKey = resolveFocusDocumentKey(packCode, hrReview)
  const docLabel = packCode ? resolveDocumentLabel(packCode, hrReview) : primary.actionTitle

  if (primary.tier === 'verify_document' || (packCode && isPackCodePendingVerification(packCode, hrReview))) {
    return {
      kind: 'verify',
      label: `Verify ${docLabel}`,
      focusDocumentKey,
      focusPackCode: packCode || null,
      scrollTarget: '#dossier-documents',
    }
  }

  if (primary.tier === 'expired_required' || primary.actionTitle.toLowerCase().includes('renew')) {
    if (focusDocumentKey && isPackCodePendingVerification(packCode, hrReview)) {
      return {
        kind: 'verify',
        label: `Verify ${docLabel}`,
        focusDocumentKey,
        focusPackCode: packCode || null,
        scrollTarget: '#dossier-documents',
      }
    }
    return {
      kind: 'renew',
      label: primary.actionTitle,
      focusPackCode: packCode || null,
      scrollTarget: '#hr-employee-linked-documents',
    }
  }

  if (
    primary.tier === 'missing_required' ||
    primary.tier === 'critical_blocker' ||
    primary.tier === 'eligibility_blocker'
  ) {
    return {
      kind: 'obtain',
      label: primary.actionTitle,
      focusPackCode: packCode || null,
      scrollTarget: '#hr-employee-linked-documents',
    }
  }

  if (primary.tier === 'admin_warning') {
    return {
      kind: 'admin',
      label: primary.actionTitle,
      focusDocumentKey,
      focusPackCode: packCode || null,
      scrollTarget: '#dossier-documents',
    }
  }

  return {
    kind: 'documents',
    label: primary.actionTitle,
    scrollTarget: '#dossier-documents',
  }
}

export function buildEmployeeReadinessSummary(input: {
  packs?: DocumentPackProjection[] | null
  reminderWorkQueue?: ReminderWorkQueueItem[] | null
  eligibility?: WorkforceEligibilityRuntime | null
  hrReview?: HrReviewPanel | null
}): EmployeeReadinessSummary {
  const ctx: LabelContext = { hrReview: input.hrReview }
  const pool = new Map<string, ReadinessCandidate>()
  const packs = input.packs ?? []

  const allCandidates = [
    ...(input.hrReview ? buildVerificationCandidates(input.hrReview, ctx) : []),
    ...buildPackCandidates(packs, ctx),
    ...buildQueueCandidates(input.reminderWorkQueue ?? [], ctx),
    ...buildEligibilityCandidates(input.eligibility, ctx),
  ]

  for (const candidate of allCandidates) {
    upsertCandidate(pool, candidate)
  }

  const candidates = [...pool.values()]
  const primary = pickPrimary(candidates)
  const { status, statusLabel, readyNextStep } = resolveStatus(primary, input.hrReview)
  const primaryCta = buildReadinessPrimaryCta(primary, input.hrReview, readyNextStep)

  return {
    status,
    statusLabel,
    primary,
    primaryCta,
    packStrip: buildPackStrip(packs, input.hrReview),
    remainingBlockingCount: countRemainingBlockers(candidates, packs, input.hrReview),
    readyNextStep,
    verificationProgress: buildVerificationProgress(input.hrReview),
  }
}

export function buildReadinessFollowUpMessage(
  summary: EmployeeReadinessSummary,
  completedLabel: string,
): string | null {
  if (summary.status === 'ready') {
    return summary.readyNextStep
      ? `${completedLabel} confirmed. Next step: ${summary.readyNextStep}.`
      : `${completedLabel} confirmed. Employment readiness looks clear.`
  }
  if (!summary.primary) return `${completedLabel} confirmed.`
  const remaining =
    summary.remainingBlockingCount > 1
      ? `${summary.remainingBlockingCount} documents remaining`
      : summary.remainingBlockingCount === 1
        ? '1 document remaining'
        : null
  const next = summary.primary.actionTitle
  return remaining ? `${completedLabel} confirmed. Next: ${next} (${remaining}).` : `${completedLabel} confirmed. Next: ${next}.`
}
