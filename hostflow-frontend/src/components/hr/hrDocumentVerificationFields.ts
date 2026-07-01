import type { HrDocumentFieldReview, HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import { reviewDocCoversPackCode } from '../../utils/documentReadinessLabels'
import { dossierFileRequiredForConfirm } from './dossierBlockKind'
import { profileValueForField } from './hrVerificationFieldMeta'

export type DocumentFieldEdit = {
  value: string
  comment: string
  confirmed: boolean
}

export function isDocumentVerified(doc: HrReviewDocumentRow): boolean {
  const raw = String(doc.verification_status || doc.status || '').toLowerCase()
  return Boolean(doc.verified) || raw === 'verified'
}

export function isDocumentRequiredForReview(d: HrReviewDocumentRow): boolean {
  return d.required !== false
}

/** Prefer calculated verification plan documents when present (PR13). */
export function documentsFromPanel(panel: {
  verification_plan?: { documents?: HrReviewDocumentRow[] } | null
  documents_for_approval?: HrReviewDocumentRow[]
}): HrReviewDocumentRow[] {
  const planDocs = panel.verification_plan?.documents
  if (planDocs && planDocs.length > 0) {
    return planDocs.filter((d) => d.requirement_level !== 'not_required')
  }
  return panel.documents_for_approval ?? []
}

export function documentRequirementTier(d: HrReviewDocumentRow): string {
  if (d.requirement_tier) return d.requirement_tier
  if (d.requirement_level === 'optional') return 'recommended'
  return d.required === false ? 'recommended' : 'required'
}

export function isHardBlockerDocument(d: HrReviewDocumentRow): boolean {
  return documentRequirementTier(d) === 'hard_blocker'
}

export function isDocumentRequirementWaived(d: HrReviewDocumentRow): boolean {
  const waiver = d.reviewed_fields?._requirement_waiver
  if (!waiver || typeof waiver !== 'object') return false
  const reason = (waiver as { reason?: string }).reason
  return Boolean(String(reason || '').trim())
}

/** Waive only for plan rows marked overridable — never hard blockers or HR-requested. */
export function isDocumentWaivable(d: HrReviewDocumentRow): boolean {
  if (isHardBlockerDocument(d)) return false
  if (documentRequirementTier(d) === 'hr_requested') return false
  if (isDocumentRequirementWaived(d)) return false
  return d.overridable === true
}

export function isPlanRecommendedDocument(d: HrReviewDocumentRow): boolean {
  return documentRequirementTier(d) === 'recommended'
}

/** Main HR queue: hard blockers + vacancy/client required + HR-requested + recommended handoff blocks. */
export function requiredPlanDocuments(docs: HrReviewDocumentRow[]): HrReviewDocumentRow[] {
  return docs.filter((d) => {
    if (d.requirement_level === 'not_required') return false
    const tier = documentRequirementTier(d)
    return tier !== 'not_required'
  })
}

export function recommendedPlanDocuments(docs: HrReviewDocumentRow[]): HrReviewDocumentRow[] {
  return docs.filter(isPlanRecommendedDocument)
}

/** @deprecated use recommendedPlanDocuments */
export function optionalPlanDocuments(docs: HrReviewDocumentRow[]): HrReviewDocumentRow[] {
  return recommendedPlanDocuments(docs)
}

/** Documents in the sequential walkthrough (required always; optional only when uploaded). */
export function sequentialDocumentQueue(docs: HrReviewDocumentRow[]): HrReviewDocumentRow[] {
  return docs
    .filter((d) => {
      const hasWork = Boolean(d.document_id) || (d.fields_to_review?.length ?? 0) > 0
      if (hasWork) return true
      const tier = documentRequirementTier(d)
      if (tier === 'hard_blocker' || tier === 'required' || tier === 'hr_requested') return true
      if (!isDocumentRequiredForReview(d)) return false
      return true
    })
    .sort((a, b) => {
      const stepA = a.step_order ?? 99
      const stepB = b.step_order ?? 99
      if (stepA !== stepB) return stepA - stepB
      return (a.slot_order ?? 99) - (b.slot_order ?? 99)
    })
}

/** Required documents for progress — required slots plus optional uploads already on file. */
export function requiredDocumentQueue(docs: HrReviewDocumentRow[]): HrReviewDocumentRow[] {
  return sequentialDocumentQueue(docs)
}

/** All required documents for the dossier — including slots without a file yet. */
export function dossierDocumentList(docs: HrReviewDocumentRow[]): HrReviewDocumentRow[] {
  return requiredPlanDocuments(docs)
    .slice()
    .sort((a, b) => {
      const stepA = a.step_order ?? 99
      const stepB = b.step_order ?? 99
      if (stepA !== stepB) return stepA - stepB
      return (a.slot_order ?? 99) - (b.slot_order ?? 99)
    })
}

export function buildInitialFieldEdits(doc: HrReviewDocumentRow): Record<string, DocumentFieldEdit> {
  const fields = doc.fields_to_review || []
  const reviewed = doc.reviewed_fields || {}
  const init: Record<string, DocumentFieldEdit> = {}
  for (const f of fields) {
    const prev = reviewed[f.field_code]
    const p = prev && typeof prev === 'object' ? (prev as Record<string, unknown>) : {}
    const fallback = profileValueForField(f, reviewed)
    init[f.field_code] = {
      value: String(p.value ?? f.reviewed_value ?? fallback),
      comment: String(p.comment ?? f.review_comment ?? ''),
      confirmed: Boolean(p.confirmed ?? f.confirmed),
    }
  }
  return init
}

export function buildConfirmedReviewedPayload(
  fieldEdits: Record<string, DocumentFieldEdit>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [code, ed] of Object.entries(fieldEdits)) {
    out[code] = {
      value: ed.value,
      comment: ed.comment,
      confirmed: true,
    }
  }
  return out
}

export function recruiterDisplayForField(f: HrDocumentFieldReview): string {
  const entries = Object.entries(f.current_profile_values || {})
  if (entries.length === 0) return ''
  return entries.map(([, v]) => String(v)).join(' · ')
}

export function countVerifiedDocuments(docs: HrReviewDocumentRow[]): { verified: number; total: number } {
  const queue = dossierDocumentList(docs)
  const total = queue.length
  const verified = queue.filter(isDocumentVerified).length
  return { verified, total }
}

export function firstPendingDocumentIndex(queue: HrReviewDocumentRow[]): number {
  const idx = queue.findIndex((d) => !isDocumentVerified(d))
  return idx >= 0 ? idx : Math.max(0, queue.length - 1)
}

function normDocToken(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

/** Match a linked employee document row to an HR review verification card. */
export function findReviewDocumentForEmployeeDoc(
  panel: HrReviewPanel,
  doc: { id?: string | null; doc_type?: string | null; title?: string | null },
): HrReviewDocumentRow | null {
  const docs = documentsFromPanel(panel)
  const docId = String(doc.id || '').trim()
  const docType = normDocToken(doc.doc_type)
  const title = normDocToken(doc.title)

  if (docId) {
    const byId = docs.find((row) => String(row.document_id || '').trim() === docId)
    if (byId) return byId
  }

  if (docType) {
    const byType = docs.find((row) => {
      const key = normDocToken(row.document_key)
      const dtype = normDocToken(row.document_type)
      const label = normDocToken(row.label)
      return dtype === docType || key === docType || key.includes(docType) || docType.includes(key) || label === title
    })
    if (byType) return byType
  }

  if (title) {
    const byTitle = docs.find((row) => normDocToken(row.label) === title)
    if (byTitle) return byTitle
  }

  return null
}

export function findQueueIndexForDocumentFocus(
  queue: HrReviewDocumentRow[],
  focus: { documentKey?: string | null; packCode?: string | null },
): number {
  if (focus.documentKey) {
    const byKey = queue.findIndex((doc) => doc.document_key === focus.documentKey)
    if (byKey >= 0) return byKey
  }
  if (focus.packCode) {
    const byPack = queue.findIndex((doc) => reviewDocCoversPackCode(doc, focus.packCode!))
    if (byPack >= 0) return byPack
  }
  return -1
}

export function countMissingFieldsOnDocument(doc: HrReviewDocumentRow): number {
  const fields = doc.fields_to_review || []
  let missing = 0
  for (const f of fields) {
    const vals = f.current_profile_values || {}
    const hasRecruiter = Object.values(vals).some((v) => v != null && String(v).trim())
    const reviewed = doc.reviewed_fields?.[f.field_code]
    const rv =
      reviewed && typeof reviewed === 'object'
        ? String((reviewed as Record<string, unknown>).value ?? '').trim()
        : ''
    if (!hasRecruiter && !rv && !String(f.reviewed_value ?? '').trim()) missing += 1
  }
  return missing
}

const OPTIONAL_VERIFICATION_FIELD_CODES = new Set(['address_apt'])

export function countUnfilledFieldEdits(
  doc: HrReviewDocumentRow,
  fieldEdits: Record<string, DocumentFieldEdit>,
): number {
  const fields = doc.fields_to_review || []
  let missing = 0
  for (const f of fields) {
    if (OPTIONAL_VERIFICATION_FIELD_CODES.has(f.field_code)) continue
    const value = (fieldEdits[f.field_code]?.value ?? '').trim()
    if (!value) missing += 1
  }
  return missing
}

export function canConfirmHrVerificationDocument(
  doc: HrReviewDocumentRow,
  manage: boolean,
  fieldEdits: Record<string, DocumentFieldEdit>,
): boolean {
  if (!manage) return false
  if (isDocumentVerified(doc)) return false
  if (doc.actions?.can_verify === false) return false
  const status = String(doc.verification_status || doc.status || '').toLowerCase()
  if (status === 'needs_correction') return false
  if (dossierFileRequiredForConfirm(doc) && !doc.document_id) return false
  const fields = doc.fields_to_review ?? []
  if (fields.length > 0 && countUnfilledFieldEdits(doc, fieldEdits) > 0) return false
  return true
}
