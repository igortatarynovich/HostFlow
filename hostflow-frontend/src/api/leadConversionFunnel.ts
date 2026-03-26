import { api } from './client'

export interface LeadConversionFunnelStage {
  stage: string
  count: number
  at_or_beyond: number
  dwell_avg_days?: number | null
  dwell_p50_days?: number | null
  dwell_sample_size?: number
}

export interface LeadConversionFunnelEdge {
  from_stage: string
  to_stage: string
  progressed_share: number | null
}

export interface LeadConversionFunnelLostFromStage {
  from_stage: string
  lead_count: number
}

export interface LeadConversionFunnelLostReasonRow {
  reason_code: string
  lead_count: number
}

export interface LeadConversionFunnelResponse {
  generated_at: string
  own_company_id?: string | null
  filter_source?: string | null
  filter_vacancy_id?: string | null
  filter_funnel_id?: string | null
  filter_assignee_user_id?: string | null
  status_new_count: number
  lost_processed_count: number
  lost_dwell_avg_days?: number | null
  lost_dwell_p50_days?: number | null
  lost_dwell_sample_size?: number
  total_win_path_processed: number
  lost_from_stage?: LeadConversionFunnelLostFromStage[]
  lost_reason_breakdown?: LeadConversionFunnelLostReasonRow[]
  stages: LeadConversionFunnelStage[]
  edges: LeadConversionFunnelEdge[]
}

export type LeadConversionFunnelSliceQuery = {
  source?: string
  vacancyId?: string
  funnelId?: string
  assigneeUserId?: string
}

export async function fetchLeadConversionFunnel(
  slices?: LeadConversionFunnelSliceQuery | null,
): Promise<LeadConversionFunnelResponse> {
  const params: Record<string, string> = {}
  if (slices?.source?.trim()) params.source = slices.source.trim()
  if (slices?.vacancyId?.trim()) params.vacancy_id = slices.vacancyId.trim()
  if (slices?.funnelId?.trim()) params.funnel_id = slices.funnelId.trim()
  if (slices?.assigneeUserId?.trim()) params.assignee_user_id = slices.assigneeUserId.trim()
  const { data } = await api.get<LeadConversionFunnelResponse>('/leads/conversion-funnel', {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}
