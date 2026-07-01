import { api } from './client'

export type PipelineOverrideScope = 'pipeline' | 'both'
export type PipelineOverrideStatus = 'pending' | 'approved' | 'rejected' | 'revoked'

export type CandidatePipelineOverride = {
  id: string
  doc_type_code?: string | null
  requirement_code?: string | null
  status: PipelineOverrideStatus
  requested_scope: PipelineOverrideScope
  granted_scope?: PipelineOverrideScope | null
  reason: string
  review_note?: string | null
  requested_by_user_id?: string | null
  reviewed_by_user_id?: string | null
  reviewed_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export async function listCandidatePipelineOverrides(candidateId: string): Promise<CandidatePipelineOverride[]> {
  if (!candidateId) return []
  const { data } = await api.get<{ items?: CandidatePipelineOverride[] }>(
    `/candidates/${candidateId}/pipeline-overrides`,
  )
  return Array.isArray((data as any)?.items) ? ((data as any).items as CandidatePipelineOverride[]) : []
}

export async function createCandidatePipelineOverride(
  candidateId: string,
  body: {
    doc_type_code?: string
    requirement_code?: string
    reason: string
    requested_scope: PipelineOverrideScope
  },
): Promise<CandidatePipelineOverride> {
  const { data } = await api.post<CandidatePipelineOverride>(`/candidates/${candidateId}/pipeline-overrides`, body)
  return data
}

export async function approveCandidatePipelineOverride(
  candidateId: string,
  overrideId: string,
  body: { granted_scope: PipelineOverrideScope; review_note?: string | null },
): Promise<CandidatePipelineOverride> {
  const { data } = await api.post<CandidatePipelineOverride>(
    `/candidates/${candidateId}/pipeline-overrides/${overrideId}/approve`,
    body,
  )
  return data
}

export async function rejectCandidatePipelineOverride(
  candidateId: string,
  overrideId: string,
  body?: { review_note?: string | null },
): Promise<CandidatePipelineOverride> {
  const { data } = await api.post<CandidatePipelineOverride>(
    `/candidates/${candidateId}/pipeline-overrides/${overrideId}/reject`,
    body ?? {},
  )
  return data
}
