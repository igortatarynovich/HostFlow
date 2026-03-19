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

export type OpsCounters = {
  no_next_action_candidates: number
  overdue_reminders: number
  leads_no_next_action?: number
  leads_overdue?: number
  leads_with_next_action?: number
  leads_total?: number
  leads_sla_no_next_action_reminders?: number
  leads_sla_stuck_stage_reminders?: number
  leads_needs_routing: number
  leads_failed: number
  draft_intake_stale: number
  automation_rules_enabled: number
  automation_events_24h: number
}

export type GoalsResponse = {
  generated_at: string
  goals: Array<{ key: string; op: string; target: number; label?: string | null }>
  metrics: Record<string, any>
  share_url?: string | null
}

export type StageTimeItem = {
  stage: string
  count: number
  avg_days: number
  p50_days: number
  p90_days: number
}

export type StageTransitionItem = {
  from_stage: string | null
  to_stage: string
  count: number
}

export type StageMetricsResponse = {
  generated_at: string
  stage_time: StageTimeItem[]
  transitions: StageTransitionItem[]
  readiness: Record<string, number>
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
    invoices_invoiced?: number
    invoices_paid?: number
    invoices_outstanding?: number
    invoices_overdue_count?: number
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
  top_items: Array<{ service_id?: string | null; label: string; total: number; pending: number; revenue: number; profit: number }>
  top_clients: Array<{ owner_kind: string; owner_id?: string | null; label: string; revenue: number; profit: number; orders: number }>
  hot_orders: Array<{ order_id: string; label: string; reason: string; owner_kind: string; status: string; updated_at?: string | null }>
  trends: Array<{
    bucket: string
    orders: number
    delivered: number
    revenue: number
    profit: number
    invoiced?: number
    paid?: number
    overdue_invoices?: number
  }>
  slices: Array<{ label: string; slice_kind?: string | null; slice_value?: string | null; owner_kind?: string | null; orders: number; revenue: number; profit: number }>
}

export type TrialRetentionEventPayload = {
  event: 'trial_retention_nudge'
  action: 'impression' | 'cta_click' | 'dismiss'
  day_bucket: 'd1' | 'd2' | 'd3' | 'd7'
  step_key?: string | null
  target_href?: string | null
  activation_done?: boolean | null
}

export type TtvStep =
  | 'signup'
  | 'plan_selected'
  | 'company_created'
  | 'first_client_created'
  | 'first_candidate_created'
  | 'email_connected'
  | 'first_email_sent'
  | 'first_invoice_sent'

export type PerfMeasurementEventPayload = {
  event: 'perf'
  action: 'measured'
  metric_key: string
  duration_ms: number
  route?: string | null
  meta?: Record<string, any> | null
}

export type PerfBaselineRow = {
  metric_key: string
  samples: number
  p50_ms: number
  p95_ms: number
  min_ms: number
  max_ms: number
}

export type PerfBaselineResponse = {
  period: { from: string | null; to: string | null }
  rows: PerfBaselineRow[]
}

export type PerfBudgetsResponse = {
  budgets_p95_ms: Record<string, number>
}

export type TtvStepEventPayload = {
  event: 'ttv_step'
  action: 'completed'
  step_key: TtvStep
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

export type TtvReportStep = {
  step_key: TtvStep
  samples: number
  p50_seconds: number
  p90_seconds: number
  min_seconds: number
  max_seconds: number
}

export type TtvReport = {
  period: { from: string | null; to: string | null }
  actors: number
  steps: TtvReportStep[]
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

export async function getOpsCounters(): Promise<OpsCounters> {
  const { data } = await api.get<OpsCounters>('/analytics/ops-counters')
  return data
}

export async function getGoals(): Promise<GoalsResponse> {
  const { data } = await api.get<GoalsResponse>('/analytics/goals')
  return data
}

export async function getStageMetrics(params?: { from?: string; to?: string; limit_transitions?: number }): Promise<StageMetricsResponse> {
  const { data } = await api.get<StageMetricsResponse>('/analytics/stage-metrics', { params })
  return data
}

export async function getPerfBaseline(params?: { days?: number; limit?: number }): Promise<PerfBaselineResponse> {
  const q: Record<string, string> = {}
  if (params?.days != null) q.days = String(params.days)
  if (params?.limit != null) q.limit = String(params.limit)
  const { data } = await api.get<PerfBaselineResponse>('/analytics/perf-baseline', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getPerfBudgets(): Promise<PerfBudgetsResponse> {
  const { data } = await api.get<PerfBudgetsResponse>('/analytics/perf-budgets')
  return data
}

export async function getServicesAnalyticsOverview(params?: {
  days?: number
  trend_bucket?: 'week' | 'month'
  slice_by?: 'client' | 'item' | 'status' | 'manager'
}): Promise<ServicesAnalyticsOverview> {
  try {
    const { data } = await api.get<ServicesAnalyticsOverview>('/analytics/services-overview', {
      params,
    })
    return data
  } catch (err: any) {
    if (err?.response?.status !== 404) throw err
    const { data } = await api.get<{
      totals?: { count?: number; sum?: number }
      by_status?: Record<string, number>
      by_code?: Array<{ service_code?: string; count?: number; sum?: number }>
    }>('/services-summary')
    const generatedAt = new Date().toISOString()
    const statusBreakdown = Object.entries(data?.by_status || {}).map(([status, count]) => ({
      status,
      count: Number(count || 0),
    }))
    const topItems = (Array.isArray(data?.by_code) ? data.by_code : [])
      .slice(0, 8)
      .map((row) => ({
        service_id: row?.service_code || null,
        label: row?.service_code || 'Service',
        total: Number(row?.count || 0),
        pending: 0,
        revenue: Number(row?.sum || 0),
        profit: 0,
      }))
    return {
      generated_at: generatedAt,
      totals: {
        orders_total: Number(data?.totals?.count || 0),
        delivered_orders: 0,
        cancelled_orders: 0,
        revenue: Number(data?.totals?.sum || 0),
        estimated_cost: 0,
        actual_cost: 0,
        gross_profit: 0,
        gross_margin: 0,
        cost_coverage: 0,
        invoices_invoiced: 0,
        invoices_paid: 0,
        invoices_outstanding: 0,
        invoices_overdue_count: 0,
      },
      last30: {
        total: 0,
        delivered: 0,
        cancelled: 0,
        cancellation_rate: 0,
      },
      data_quality: {
        confirmed_items: 0,
        estimated_items: 0,
        missing_items: 0,
      },
      status_breakdown: statusBreakdown,
      top_items: topItems,
      top_clients: [],
      hot_orders: [],
      trends: [],
      slices: [],
    }
  }
}

export async function recordTrialRetentionEvent(payload: TrialRetentionEventPayload): Promise<void> {
  await api.post('/analytics/events', payload)
}

export async function recordTtvStepCompleted(payload: TtvStepEventPayload): Promise<void> {
  await api.post('/analytics/events', payload)
}

export async function recordPerfMeasurement(payload: {
  metricKey: string
  durationMs: number
  route?: string
  meta?: Record<string, any>
}): Promise<void> {
  const eventPayload: PerfMeasurementEventPayload = {
    event: 'perf',
    action: 'measured',
    metric_key: payload.metricKey,
    duration_ms: payload.durationMs,
    route: payload.route ?? null,
    meta: payload.meta ?? null,
  }
  await api.post('/analytics/events', eventPayload)
}

export async function getTrialRetentionReport(params?: { days?: number }): Promise<TrialRetentionReport> {
  const q: Record<string, string> = {}
  if (params?.days != null) q.days = String(params.days)
  const { data } = await api.get<TrialRetentionReport>('/analytics/trial-retention', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getTtvReport(params?: { days?: number }): Promise<TtvReport> {
  const q: Record<string, string> = {}
  if (params?.days != null) q.days = String(params.days)
  const { data } = await api.get<TtvReport>('/analytics/ttv-report', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}
