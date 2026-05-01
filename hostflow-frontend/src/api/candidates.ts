import { api } from './client'
import type { Candidate } from './types'

export interface CandidateSearchParams {
  q: string
  limit?: number
}

export async function searchCandidates({ q, limit = 10 }: CandidateSearchParams) {
  if (!q.trim()) return []

  const { data } = await api.get<{ items?: Candidate[] } | { total?: number; items?: Candidate[] }>(
    '/candidates',
    {
      params: {
        q: q.trim(),
        limit,
        offset: 0,
      },
    },
  )

  const items = (data as any)?.items
  if (Array.isArray(items)) {
    return items as Candidate[]
  }
  return []
}

export type CandidateUploadLinkResponse = {
  apply_url: string
  documents_url?: string | null
  status_url?: string | null
  intake_token: string
  status_share_token?: string | null
  expires_at?: string | null
}

export async function createCandidateUploadLink(candidateId: string): Promise<CandidateUploadLinkResponse> {
  if (!candidateId) {
    throw new Error('candidateId is required')
  }
  const { data } = await api.post(`/candidates/${candidateId}/upload-link`)
  return data
}

export type NotifyCandidateResponse = {
  sent: boolean
  reason?: string | null
}

/** Send email to candidate with link to upload requested documents. */
export async function notifyCandidate(candidateId: string): Promise<NotifyCandidateResponse> {
  if (!candidateId) {
    throw new Error('candidateId is required')
  }
  const { data } = await api.post<NotifyCandidateResponse>(`/candidates/${candidateId}/notify`)
  return data
}

// ----- G-8: per-candidate primary "next action" -----------------------------
//
// Stage 1a shipped the candidate variant; stage 2 lifted the shared shape
// into `./nextAction` so leads/vacancies/documents/threads can render
// through the same badge component. The aliases below stay around so older
// imports compile unchanged.

import type {
  NextActionDTO,
  NextActionKind,
  NextActionPriority,
} from './nextAction'

export type CandidateNextActionKind = NextActionKind
export type CandidateNextActionPriority = NextActionPriority
/** Candidate-narrowed view of the shared {@link NextActionDTO}. */
export type CandidateNextActionDTO = NextActionDTO & { entity_type: 'candidate' }

/**
 * Fetch the canonical "what to do next" CTA for a candidate.
 *
 * The backend always returns a DTO (never 200-with-empty-body): even on
 * "nothing to do" it returns `kind: idle`. Callers should treat a non-200
 * response as a hard failure, not as "no action".
 */
export async function getCandidateNextAction(candidateId: string): Promise<CandidateNextActionDTO> {
  if (!candidateId) {
    throw new Error('candidateId is required')
  }
  const { data } = await api.get<CandidateNextActionDTO>(
    `/candidates/${candidateId}/next-action`,
  )
  return data
}
