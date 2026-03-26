import { api } from './client'

export interface LeadStageHealthRow {
  stage: string
  processed_total: number
  no_next_action: number
  overdue: number
  stuck: number
}

export interface LeadStageHealthResponse {
  generated_at: string
  own_company_id?: string | null
  stages: LeadStageHealthRow[]
}

export async function fetchLeadStageHealth(): Promise<LeadStageHealthResponse> {
  const { data } = await api.get<LeadStageHealthResponse>('/leads/stage-health')
  return data
}
