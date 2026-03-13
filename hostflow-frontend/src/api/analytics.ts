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

export type ServicesAnalyticsOverview = {
  generated_at: string
  totals: {
    orders_total: number
    delivered_orders: number
    cancelled_orders: number
    revenue: number
    estimated_cost: number
    actual_cost: number
    gross_profit: number
    gross_margin: number
    cost_coverage: number
  }
  last30: {
    total: number
    delivered: number
    cancelled: number
    cancellation_rate: number
  }
  data_quality: {
    confirmed_items: number
    estimated_items: number
    missing_items: number
  }
  status_breakdown: Array<{ status: string; count: number }>
  top_items: Array<{ label: string; total: number; pending: number; revenue: number; profit: number }>
  top_clients: Array<{ label: string; revenue: number; profit: number; orders: number }>
  hot_orders: Array<{ order_id: string; label: string; reason: string; owner_kind: string; status: string; updated_at?: string | null }>
  trends: Array<{ bucket: string; orders: number; delivered: number; revenue: number; profit: number }>
  slices: Array<{ label: string; orders: number; revenue: number; profit: number }>
}

export type TrialRetentionEventPayload = {
  event: 'trial_retention_nudge'
  action: 'impression' | 'cta_click' | 'dismiss'
  day_bucket: 'd1' | 'd2' | 'd3' | 'd7'
  step_key?: string | null
  target_href?: string | null
  activation_done?: boolean | null
}

export type TrialRetentionReport = {
  period: { from: string | null; to: string | null }
  totals: {
    impression: number
    cta_click: number
    dismiss: number
    ctr_percent: number
  }
  buckets: Array<{
    day_bucket: 'd1' | 'd2' | 'd3' | 'd7'
    impression: number
    cta_click: number
    dismiss: number
    ctr_percent: number
    dismiss_percent: number
  }>
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

export async function getServicesAnalyticsOverview(params?: {
  days?: number
  trend_bucket?: 'week' | 'month'
  slice_by?: 'client' | 'item' | 'status' | 'manager'
}): Promise<ServicesAnalyticsOverview> {
  const { data } = await api.get<ServicesAnalyticsOverview>('/analytics/services-overview', {
    params,
  })
  return data
}

export async function recordTrialRetentionEvent(payload: TrialRetentionEventPayload): Promise<void> {
  await api.post('/analytics/events', payload)
}

export async function getTrialRetentionReport(params?: { days?: number }): Promise<TrialRetentionReport> {
  const q: Record<string, string> = {}
  if (params?.days != null) q.days = String(params.days)
  const { data } = await api.get<TrialRetentionReport>('/analytics/trial-retention', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}
