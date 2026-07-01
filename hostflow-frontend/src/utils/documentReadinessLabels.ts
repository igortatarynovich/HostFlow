import type { HrReviewDocumentRow, HrReviewPanel } from '../api/workforce'
import { documentsFromPanel, isDocumentVerified } from '../components/hr/hrDocumentVerificationFields'
import { humanizeDocumentCode } from './documentActionsPanel'

const IDENTITY_ALIASES = new Set([
  'passport',
  'id_card',
  'national_id',
  'passport_scan',
  'identity_card',
  'identity_document',
])

export function normDocumentToken(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
    .replace(/\s+/g, '_')
}

export function reviewDocCoversPackCode(reviewDoc: HrReviewDocumentRow, packCode: string): boolean {
  const code = normDocumentToken(packCode)
  if (!code) return false
  const key = normDocumentToken(reviewDoc.document_key)
  const dtype = normDocumentToken(reviewDoc.document_type || '')
  if (code === dtype || code === key) return true
  if (key.includes(code) || code.includes(key)) return true
  if (dtype && (code.includes(dtype) || dtype.includes(code))) return true
  if (IDENTITY_ALIASES.has(code) && (IDENTITY_ALIASES.has(dtype) || key.includes('passport') || key.includes('id'))) {
    return true
  }
  return false
}

export function findReviewDocForPackCode(
  hrReview: HrReviewPanel | null | undefined,
  packCode: string,
): HrReviewDocumentRow | null {
  if (!hrReview) return null
  return documentsFromPanel(hrReview).find((doc) => reviewDocCoversPackCode(doc, packCode)) ?? null
}

export function resolveDocumentLabel(
  packCode: string,
  hrReview?: HrReviewPanel | null,
): string {
  const reviewDoc = findReviewDocForPackCode(hrReview, packCode)
  if (reviewDoc?.label?.trim()) return reviewDoc.label.trim()
  return humanizeDocumentCode(packCode)
}

export function isPackCodeVerifiedInHrReview(
  packCode: string,
  hrReview?: HrReviewPanel | null,
): boolean {
  const reviewDoc = findReviewDocForPackCode(hrReview, packCode)
  return reviewDoc ? isDocumentVerified(reviewDoc) : false
}

export function isPackCodePendingVerification(
  packCode: string,
  hrReview?: HrReviewPanel | null,
): boolean {
  const reviewDoc = findReviewDocForPackCode(hrReview, packCode)
  if (!reviewDoc || isDocumentVerified(reviewDoc)) return false
  return Boolean(reviewDoc.document_id)
}

export function resolveFocusDocumentKey(
  packCode: string | undefined,
  hrReview?: HrReviewPanel | null,
): string | null {
  if (!packCode) return null
  return findReviewDocForPackCode(hrReview, packCode)?.document_key ?? null
}
