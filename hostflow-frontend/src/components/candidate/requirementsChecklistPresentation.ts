import type { CandidateEvidenceStatus, RequirementChecklistItem } from '../../api/candidateRequirements'

export type RequirementRowStatus =
  | 'missing'
  | 'selected'
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'superseded'
  | 'not_applicable'

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

export function evidenceStatusLabelKey(status: CandidateEvidenceStatus | RequirementRowStatus): string {
  return `app.candidate_card.requirements_checklist.status.${status}`
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

/** Evaluated evidence alternatives on a checklist row (when API provides them). */
export function evaluatedAlternatives(item: RequirementChecklistItem): Array<{
  alternative_code?: string
  evidence_variant_code?: string
  status?: string
  document_type_codes?: string[]
}> {
  const raw = (item as { evaluated_alternatives?: unknown; alternatives?: unknown }).evaluated_alternatives
    ?? (item as { alternatives?: unknown }).alternatives
  return Array.isArray(raw) ? (raw as Array<{
    alternative_code?: string
    evidence_variant_code?: string
    status?: string
    document_type_codes?: string[]
  }>) : []
}

export function hasExtractionBlockers(item: RequirementChecklistItem): boolean {
  const docs = (item.candidate_evidence?.documents || []) as Array<{
    missing_extraction_fields?: string[]
  }>
  return docs.some((doc) => (doc.missing_extraction_fields?.length || 0) > 0)
}

export function formatExtractionValue(value: unknown): string {
  if (value == null || value === '') return '—'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}
