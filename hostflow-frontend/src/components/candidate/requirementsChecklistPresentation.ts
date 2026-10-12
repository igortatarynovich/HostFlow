import type { RequirementChecklistItem } from '../../api/candidateRequirements'
import type { RequirementRowStatus } from '../../platform/entity-workspace/requirementRowStatus'

export type { RequirementRowStatus } from '../../platform/entity-workspace/requirementRowStatus'
export {
  evidenceStatusLabelKey,
  requirementStatusBadgeClass,
} from '../../platform/entity-workspace/requirementRowStatus'

export function variantDocumentTypeCodes(variant: {
  document_type_codes?: string[]
  any_of?: string[]
  all_of?: string[]
}): string[] {
  const raw =
    variant.document_type_codes?.length
      ? variant.document_type_codes
      : variant.all_of?.length
        ? variant.all_of
        : variant.any_of || []
  return raw.map((code) => String(code || '').trim()).filter(Boolean)
}

export function resolveRequirementRowStatus(item: RequirementChecklistItem): RequirementRowStatus {
  if (item.evaluation?.status === 'not_applicable') return 'not_applicable'
  const evidenceStatus = String(item.candidate_evidence?.status || '').toLowerCase()
  if (!evidenceStatus) return 'missing'
  if (
    evidenceStatus === 'missing' ||
    evidenceStatus === 'selected' ||
    evidenceStatus === 'pending_review' ||
    evidenceStatus === 'approved' ||
    evidenceStatus === 'rejected' ||
    evidenceStatus === 'superseded'
  ) {
    return evidenceStatus as RequirementRowStatus
  }
  return 'missing'
}

export function normDocType(code: string): string {
  return String(code || '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_')
}

export function documentMatchesVariantTypes(
  docType: string,
  allowedTypes: string[],
): boolean {
  const normalizedAllowed = new Set(allowedTypes.map(normDocType))
  const docNorm = normDocType(docType)
  return normalizedAllowed.has(docNorm)
}
