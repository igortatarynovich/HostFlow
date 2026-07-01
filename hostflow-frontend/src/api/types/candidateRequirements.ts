export type CandidateEvidenceStatus =
  | 'missing'
  | 'selected'
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'superseded'

export type RequirementEvaluationStatus =
  | 'missing'
  | 'pending_evidence'
  | 'pending_verification'
  | 'satisfied'
  | 'not_applicable'
  | 'unknown'

export type RequirementEvidenceDocument = {
  document_id?: string
  id?: string
  document_type_code?: string
  type?: string
  status?: string
  has_files?: boolean
  expires_on?: string | null
  document_runtime?: Record<string, unknown> | null
}

export type CandidateEvidenceSnapshot = {
  evidence_id: string
  requirement_code: string
  evidence_variant_code: string
  status: CandidateEvidenceStatus | string
  selected_by?: string | null
  selected_at?: string | null
  approved_by?: string | null
  approved_at?: string | null
  rejected_by?: string | null
  rejected_at?: string | null
  rejection_reason?: string | null
  documents?: RequirementEvidenceDocument[]
}

export type AcceptedEvidenceVariant = {
  evidence_variant_code: string
  document_type_codes?: string[]
  any_of?: string[]
  all_of?: string[]
  all_of_flag?: boolean
}

export type RequirementChecklistItem = {
  requirement_code: string
  public_name?: string | null
  business_purpose?: string | null
  level?: string | null
  fulfilled: boolean
  accepted_evidence_variants: AcceptedEvidenceVariant[]
  candidate_evidence?: CandidateEvidenceSnapshot | null
  evaluation: {
    status?: RequirementEvaluationStatus | string
    blockers?: Array<Record<string, unknown>>
    evidence_status?: string | null
    evidence_variant_code?: string | null
    [key: string]: unknown
  }
}

export type RequirementsChecklistResponse = {
  candidate_id: string
  requirements: RequirementChecklistItem[]
  all_fulfilled: boolean
  pipeline_blockers?: RequirementPipelineBlockers
}

export type RequirementPipelineBlockers = {
  source?: string
  all_fulfilled?: boolean
  missing_requirements?: string[]
  problematic_requirements?: string[]
  pending_review_requirements?: string[]
  unfulfilled_requirements?: Array<{
    requirement_code: string
    public_name?: string | null
    evaluation_status?: string | null
    evidence_status?: string | null
    fulfilled?: boolean
  }>
}
