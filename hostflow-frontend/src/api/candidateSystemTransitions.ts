import { api } from './client'
import type { FunnelTransition } from './funnels'

export type CandidateSystemTransitionResult = {
  candidate_id: string
  catalog_key: string
  lifecycle_status?: string | null
  stage?: string | null
  employee_id?: string | null
  handoff_id?: string | null
  handoff_warning?: string | null
}

export async function fireCandidateSystemTransition(
  candidateId: string,
  catalogKey: string,
): Promise<CandidateSystemTransitionResult> {
  const { data } = await api.post<CandidateSystemTransitionResult>(
    `/candidates/${encodeURIComponent(candidateId)}/system-transitions/${encodeURIComponent(catalogKey)}`,
  )
  return data
}

export type { FunnelTransition }
