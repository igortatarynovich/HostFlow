import type { HrDocumentFieldReview, HrReviewDocumentRow } from '../../api/workforce'

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

export function isPlanRecommendedDocument(d: HrReviewDocumentRow): boolean {
  return documentRequirementTier(d) === 'recommended'
}

/** Main HR queue: hard blockers + vacancy/client required + HR-requested. */
export function requiredPlanDocuments(docs: HrReviewDocumentRow[]): HrReviewDocumentRow[] {
  return docs.filter((d) => {
    const tier = documentRequirementTier(d)
    return tier === 'hard_blocker' || tier === 'required' || tier === 'hr_requested'
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
  return docs.filter((d) => {
    const hasWork = Boolean(d.document_id) || (d.fields_to_review?.length ?? 0) > 0
    if (!hasWork) return false
    if (!isDocumentRequiredForReview(d)) return Boolean(d.document_id)
    return true
  })
}

/** Required documents only — used for progress and approve readiness in the UI. */
export function requiredDocumentQueue(docs: HrReviewDocumentRow[]): HrReviewDocumentRow[] {
  return sequentialDocumentQueue(docs).filter(isDocumentRequiredForReview)
}

export function buildInitialFieldEdits(doc: HrReviewDocumentRow): Record<string, DocumentFieldEdit> {
  const fields = doc.fields_to_review || []
  const reviewed = doc.reviewed_fields || {}
  const init: Record<string, DocumentFieldEdit> = {}
  for (const f of fields) {
    const prev = reviewed[f.field_code]
    const p = prev && typeof prev === 'object' ? (prev as Record<string, unknown>) : {}
    const profileVals = Object.values(f.current_profile_values || {})
    const fallback = profileVals.length > 0 ? String(profileVals[0]) : ''
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
  const queue = requiredDocumentQueue(docs)
  const total = queue.length
  const verified = queue.filter(isDocumentVerified).length
  return { verified, total }
}

export function firstPendingDocumentIndex(queue: HrReviewDocumentRow[]): number {
  const idx = queue.findIndex((d) => !isDocumentVerified(d))
  return idx >= 0 ? idx : Math.max(0, queue.length - 1)
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
