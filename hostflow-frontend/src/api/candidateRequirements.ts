import { api } from './client'
import type {
  CandidateEvidenceSnapshot,
  RequirementsChecklistResponse,
  RequirementsWorkspaceResponse,
} from './types/candidateRequirements'

export type {
  AcceptedEvidenceVariant,
  CandidateEvidenceSnapshot,
  CandidateEvidenceStatus,
  RequirementChecklistItem,
  RequirementEvaluationStatus,
  RequirementEvidenceDocument,
  RequirementPipelineBlockers,
  RequirementsWorkspaceResponse,
  WorkspaceFieldRequirement,
  WorkspaceFieldRequirementsSection,
  WorkspaceSummary,
  WorkspaceTransferReadiness,
  OperationalRequirementRow,
} from './types/candidateRequirements'

export async function getCandidateRequirementsChecklist(
  candidateId: string,
): Promise<RequirementsChecklistResponse> {
  const { data } = await api.get<RequirementsChecklistResponse>(
    `/candidates/${candidateId}/requirements/checklist`,
  )
  return data
}

export async function getCandidateRequirementsWorkspace(
  candidateId: string,
): Promise<RequirementsWorkspaceResponse> {
  const { data } = await api.get<RequirementsWorkspaceResponse>(
    `/candidates/${candidateId}/requirements/workspace`,
  )
  return data
}

export async function selectRequirementEvidence(
  candidateId: string,
  requirementCode: string,
  body: { evidence_variant_code: string },
): Promise<CandidateEvidenceSnapshot> {
  const { data } = await api.post<CandidateEvidenceSnapshot>(
    `/candidates/${candidateId}/requirements/${requirementCode}/select-evidence`,
    body,
  )
  return data
}

export async function linkRequirementEvidenceDocument(
  candidateId: string,
  evidenceId: string,
  body: { document_id: string; role?: string | null },
): Promise<{ linked: boolean; document_id: string; evidence_id: string }> {
  const { data } = await api.post<{ linked: boolean; document_id: string; evidence_id: string }>(
    `/candidates/${candidateId}/requirements/evidence/${evidenceId}/documents`,
    body,
  )
  return data
}

export async function approveRequirementEvidence(
  candidateId: string,
  evidenceId: string,
): Promise<CandidateEvidenceSnapshot> {
  const { data } = await api.post<CandidateEvidenceSnapshot>(
    `/candidates/${candidateId}/requirements/evidence/${evidenceId}/approve`,
  )
  return data
}

export async function rejectRequirementEvidence(
  candidateId: string,
  evidenceId: string,
  body?: { reason?: string | null },
): Promise<CandidateEvidenceSnapshot> {
  const { data } = await api.post<CandidateEvidenceSnapshot>(
    `/candidates/${candidateId}/requirements/evidence/${evidenceId}/reject`,
    body ?? {},
  )
  return data
}

export async function replaceRequirementEvidence(
  candidateId: string,
  requirementCode: string,
  body: { evidence_variant_code: string },
): Promise<CandidateEvidenceSnapshot> {
  const { data } = await api.post<CandidateEvidenceSnapshot>(
    `/candidates/${candidateId}/requirements/${requirementCode}/replace-evidence`,
    body,
  )
  return data
}

export async function completeOperationalRequirementActivity(
  candidateId: string,
  requirementCode: string,
  body: { activity_id: string },
): Promise<OperationalRequirementRow> {
  const { data } = await api.post<OperationalRequirementRow>(
    `/candidates/${candidateId}/requirements/${requirementCode}/complete-activity`,
    body,
  )
  return data
}
