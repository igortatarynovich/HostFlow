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

export function requirementStatusBadgeClass(status: RequirementRowStatus): string {
  switch (status) {
    case 'approved':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'pending_review':
      return 'border-amber-200 bg-amber-50 text-amber-950'
    case 'selected':
      return 'border-sky-200 bg-sky-50 text-sky-900'
    case 'rejected':
      return 'border-rose-200 bg-rose-50 text-rose-900'
    case 'superseded':
      return 'border-slate-200 bg-slate-50 text-slate-600'
    case 'not_applicable':
      return 'border-slate-200 bg-white text-slate-500'
    default:
      return 'border-amber-200 bg-amber-50 text-amber-950'
  }
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

export function evaluatedAlternatives(item: RequirementChecklistItem): Array<{
  alternative_code?: string
  evidence_variant_code?: string
  status?: string
  partial?: boolean
  document_type_codes?: string[]
}> {
  const raw = item.evaluation?.alternatives_evaluated
  if (!Array.isArray(raw)) return []
  return raw.filter((row): row is NonNullable<typeof row> => typeof row === 'object' && row !== null)
}

export function hasExtractionBlockers(item: RequirementChecklistItem): boolean {
  if (item.evaluation?.extraction_incomplete) return true
  for (const doc of item.candidate_evidence?.documents || []) {
    const missing = doc.missing_extraction_fields
    if (Array.isArray(missing) && missing.length > 0) return true
  }
  return (item.evaluation?.blockers || []).some(
    (row) => String(row.code || '') === 'document_extraction_field_missing',
  )
}

export function formatExtractionValue(value: unknown): string {
  if (value == null) return '—'
  if (Array.isArray(value)) return value.join(', ')
  return String(value)
}
