import { api } from './client'

export type HandoffStatsResponse = {
  total_requested: number
  total_accepted: number
  total_rejected: number
  total_returned: number
  by_client: Array<{ client_id: string; requested: number; accepted: number; rejected: number; returned: number }>
  period: { from: string | null; to: string | null }
}

export type ContactAttemptStatsResponse = {
  total_attempts: number
  candidates_with_attempts: number
  avg_per_candidate: number
  limit_reached_count: number
  by_result: Record<string, number>
  period: { from: string | null; to: string | null }
}

export type DocumentStatsResponse = {
  total_docs: number
  by_status: Record<string, number>
  by_kind: Record<string, number>
  candidates_with_complete_docs: number
  period: { from: string | null; to: string | null }
}

export type AnalyticsProfileSummary = {
  business_type: 'agency' | 'employer' | 'services'
  generated_at: string
  kpis: Record<string, number>
  datasets: {
    primary_entities: string[]
    unknown_company_classification?: number
  }
}

export async function getHandoffStats(params?: {
  from?: string
  to?: string
}): Promise<HandoffStatsResponse> {
  const q: Record<string, string> = {}
  if (params?.from) q.from = params.from
  if (params?.to) q.to = params.to
  const { data } = await api.get<HandoffStatsResponse>('/analytics/handoff-stats', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getContactAttemptStats(params?: {
  from?: string
  to?: string
}): Promise<ContactAttemptStatsResponse> {
  const q: Record<string, string> = {}
  if (params?.from) q.from = params.from
  if (params?.to) q.to = params.to
  const { data } = await api.get<ContactAttemptStatsResponse>('/analytics/contact-attempt-stats', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getDocumentStats(params?: {
  from?: string
  to?: string
}): Promise<DocumentStatsResponse> {
  const q: Record<string, string> = {}
  if (params?.from) q.from = params.from
  if (params?.to) q.to = params.to
  const { data } = await api.get<DocumentStatsResponse>('/analytics/document-stats', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getAnalyticsProfileSummary(): Promise<AnalyticsProfileSummary> {
  const { data } = await api.get<AnalyticsProfileSummary>('/analytics/profile-summary')
  return data
}
