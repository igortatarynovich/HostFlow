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

export type WorkspaceFieldRequirement = {
  qualified_code: string
  level?: string
  reason_code?: string | null
  satisfied: boolean
  current_value?: string | number | boolean | null
}

export type WorkspaceFieldRequirementsSection = {
  required_fields: WorkspaceFieldRequirement[]
  missing_count: number
  satisfied: boolean
}

export type WorkspaceSummary = {
  total_requirements: number
  fulfilled_count: number
  blocking_open_count: number
  pending_review_count: number
  all_fulfilled: boolean
  handoff_ready: boolean
}

export type WorkspaceTransferReadiness = {
  transfer_allowed: boolean
  handoff_create_allowed: boolean
  blocking_reasons: Array<Record<string, unknown>>
  warnings?: Array<Record<string, unknown>>
  destinations_allowed?: string[]
  policy_version?: string | null
  source_layers?: string[]
  requirement_engine?: Record<string, unknown> | null
  requirement_gate?: {
    applied?: boolean
    satisfied?: boolean
    [key: string]: unknown
  } | null
}

export type RequirementsWorkspaceResponse = {
  schema_version: string
  candidate_id: string
  entity_profile_code?: string | null
  vacancy_id?: string | null
  can_edit: boolean
  summary: WorkspaceSummary
  checklist: RequirementsChecklistResponse
  field_requirements: WorkspaceFieldRequirementsSection
  requirement_evaluation?: Record<string, unknown> | null
  transfer_readiness: WorkspaceTransferReadiness
  pipeline_blockers: RequirementPipelineBlockers
  operational_requirements: Array<Record<string, unknown>>
  evaluated_at: string
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
