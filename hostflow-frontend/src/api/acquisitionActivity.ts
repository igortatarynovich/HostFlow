import { api } from './client'

export type AcquisitionActivityEvent = {
  id: string
  tenant_id: string
  campaign_id: string
  flight_id?: string | null
  endpoint_id?: string | null
  submission_id?: string | null
  result_id?: string | null
  outcome_id?: string | null
  event_type: string
  event_version: string
  occurred_at: string
  recorded_at: string
  actor_type: string
  actor_id?: string | null
  provider?: string | null
  source_event_id?: string | null
  correlation_id?: string | null
  causation_id?: string | null
  payload: Record<string, unknown>
}

export type AcquisitionActivityCursor = {
  occurred_at: string
  id: string
}

export type AcquisitionActivityListResponse = {
  items: AcquisitionActivityEvent[]
  next_cursor: AcquisitionActivityCursor | null
  order: [string, string]
}

export type ListAcquisitionActivityParams = {
  campaign_id?: string
  flight_id?: string
  endpoint_id?: string
  submission_id?: string
  result_id?: string
  outcome_id?: string
  event_type?: string | string[]
  occurred_after?: string
  occurred_before?: string
  after_occurred_at?: string
  after_id?: string
  limit?: number
}

export async function listAcquisitionActivity(
  params: ListAcquisitionActivityParams = {},
): Promise<AcquisitionActivityListResponse> {
  const { data } = await api.get<AcquisitionActivityListResponse>('/platform/acquisition-activity', {
    params,
  })
  return {
    items: Array.isArray(data?.items) ? data.items : [],
    next_cursor: data?.next_cursor ?? null,
    order: data?.order ?? ['occurred_at', 'id'],
  }
}
