import type { HrReviewDocumentRow, HrReviewPanel } from '../../api/workforce'
import {
  documentRequirementTier,
  documentsFromPanel,
  isDocumentRequirementWaived,
  isDocumentVerified,
  isPlanRecommendedDocument,
} from './hrDocumentVerificationFields'

export function isVerificationPlanReady(panel: HrReviewPanel): boolean {
  if (panel?.verification_plan?.can_approve === true) return true
  const readiness = panel?.decision_readiness
  if (readiness && readiness.can_approve === true) return true
  return false
}

export type ReadyDocRow = { key: string; label: string; reason?: string }

export function verificationReadyGroups(panel: HrReviewPanel): {
  confirmed: ReadyDocRow[]
  waived: ReadyDocRow[]
  hrRequested: ReadyDocRow[]
  recommendedPending: ReadyDocRow[]
} {
  const docs = documentsFromPanel(panel)
  const confirmed: ReadyDocRow[] = []
  const waived: ReadyDocRow[] = []
  const hrRequested: ReadyDocRow[] = []
  const recommendedPending: ReadyDocRow[] = []

  for (const doc of docs) {
    const key = doc.document_key
    const label = doc.label || doc.document_key
    const tier = documentRequirementTier(doc)

    if (isDocumentRequirementWaived(doc)) {
      const waiver = doc.reviewed_fields?._requirement_waiver as { reason?: string } | undefined
      waived.push({ key, label, reason: waiver?.reason?.trim() || undefined })
      continue
    }

    if (tier === 'hr_requested') {
      hrRequested.push({
        key,
        label,
        reason: isDocumentVerified(doc)
          ? undefined
          : 'pending',
      })
      continue
    }

    if (isPlanRecommendedDocument(doc) && !isDocumentVerified(doc)) {
      recommendedPending.push({ key, label })
      continue
    }

    if (isDocumentVerified(doc)) {
      confirmed.push({ key, label })
    }
  }

  return { confirmed, waived, hrRequested, recommendedPending }
}
