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
