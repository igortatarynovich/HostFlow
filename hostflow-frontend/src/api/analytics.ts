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

export type DocumentRuntimeKpisResponse = {
  evaluation_version: string
  source: 'runtime' | 'no_runtime' | string
  kpis: Record<
    | 'expired'
    | 'expiring_soon'
    | 'expiring_7d'
    | 'pending_review'
    | 'rejected'
    | 'missing_required'
    | 'ready_documents',
    number
  >
  candidates_scanned: number
  runtime_candidates: number
  runtime_items_scanned: number
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
  /** Active tasks assigned to current user without resolvable entity link. */
  unlinked_tasks?: number
  overview_pipeline_total?: number
  overview_stuck?: number
  overview_active_today?: number
  /** Open vacancies (status open, not archived); ACL-aligned with list. */
  open_vacancies?: number
  /** Candidates linked to those vacancies (same scope). */
  open_vacancies_candidates?: number
  /** Service orders excluding completed/cancelled (tenant-wide). */
  open_service_orders?: number
  leads_no_next_action?: number
  leads_overdue?: number
  leads_with_next_action?: number
  leads_total?: number
  leads_sla_no_next_action_reminders?: number
  leads_sla_stuck_stage_reminders?: number
  leads_needs_routing: number
  leads_failed: number
  leads_new_untouched_24h?: number
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

export type RiskIntelligenceStageAgg = {
  count: number
  avg_risk_score: number
  high_plus_count: number
}

export type RiskIntelligenceResponse = {
  generated_at: string
  risk_version: string
  candidates_evaluated: number
  high_risk_volume: number
  avg_risk_score: number
  band_distribution: Record<string, number>
  risk_distribution_by_stage: Record<string, RiskIntelligenceStageAgg>
  first_response_hours_histogram: Record<string, number>
  effective_weights: Record<string, number>
}

export type RiskIntelTrendPoint = {
  bucket_start: string | null
  avg_risk_score: number
  high_risk_volume: number
  candidates_evaluated: number
  band_low: number
  band_medium: number
  band_high: number
  band_critical: number
}

export type RiskIntelTrendsResponse = {
  generated_at: string
  days: number
  points: RiskIntelTrendPoint[]
}

export type RiskIntelValidationResponse = {
  generated_at: string
  cohort_window: { from: string; to: string }
  lag_days_after_cohort: number
  samples: number
  forward_stage_progression_count: number
  forward_stage_progression_rate: number | null
  interpretation?: string | null
  note?: string | null
}

export type RiskIntelShadowSnapshotItem = {
  entity_id: string
  score: number
  band: string
  stage_at_score?: string | null
  drivers: string[]
  scored_at?: string | null
  short_id?: string | null
  display_name?: string | null
  /** Candidate owner when known — used for digest handoff (reminder assignee / claim). */
  recruiter_id?: string | null
}

export type RiskIntelShadowSnapshotResponse = {
  bucket_start: string | null
  scored_at: string | null
  risk_version: string
  min_band: string
  total_matching: number
  items: RiskIntelShadowSnapshotItem[]
  note?: string | null
}

export type RiskIntelDigestQueueItem = {
  bucket_start: string
  total_matching: number
  scored_at?: string | null
  unread: boolean
}

export type RiskIntelDigestQueueResponse = {
  generated_at: string
  min_band: string
  last_ack_bucket_start?: string | null
  unread_count: number
  buckets: RiskIntelDigestQueueItem[]
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

/**
 * G-6 Stage 2c — aggregate "who owns how many candidates" per recruiter/
 * legacy manager. Backend: `backend/app/api/v1/analytics.py::by_manager`.
 *
 * `recruiter_id` is the canonical user UUID (when the row has
 * `Candidate.recruiter_id` FK; null for legacy rows with only a
 * `Candidate.manager` free-text label). UI drill-downs should prefer
 * `?recruiter_id=<uuid>` when present and fall back to `?manager=<label>`
 * otherwise — matches `useCandidatesUrlSync` precedence.
 */
export type AnalyticsByManagerItem = {
  manager: string
  recruiter_id: string | null
  total: number
  hired: number
  by_stage: Record<string, number>
}

export type AnalyticsByManagerResponse = {
  period: { from: string | null; to: string | null }
  by: 'created' | 'updated'
  items: AnalyticsByManagerItem[]
}

export async function getAnalyticsByManager(params?: {
  from?: string
  to?: string
  by?: 'created' | 'updated'
  stage_view?: 'all' | 'agency' | 'client'
}): Promise<AnalyticsByManagerResponse> {
  const q: Record<string, string> = {}
  if (params?.from) q.from = params.from
  if (params?.to) q.to = params.to
  if (params?.by) q.by = params.by
  if (params?.stage_view) q.stage_view = params.stage_view
  const { data } = await api.get<AnalyticsByManagerResponse>('/analytics/by-manager', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
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
  companyId?: string
  vacancyId?: string
}): Promise<DocumentStatsResponse> {
  const q: Record<string, string> = {}
  if (params?.from) q.from = params.from
  if (params?.to) q.to = params.to
  if (params?.companyId) q.company_id = params.companyId
  if (params?.vacancyId) q.vacancy_id = params.vacancyId
  const { data } = await api.get<DocumentStatsResponse>('/analytics/document-stats', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getDocumentRuntimeKpis(params?: {
  from?: string
  to?: string
}): Promise<DocumentRuntimeKpisResponse> {
  const q: Record<string, string> = {}
  if (params?.from) q.from = params.from
  if (params?.to) q.to = params.to
  const { data } = await api.get<DocumentRuntimeKpisResponse>('/analytics/document-runtime-kpis', {
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

export async function getRiskIntelligence(params?: { limit?: number }): Promise<RiskIntelligenceResponse> {
  const { data } = await api.get<RiskIntelligenceResponse>('/analytics/risk-intelligence', {
    params: params?.limit != null ? { limit: params.limit } : undefined,
  })
  return data
}

export async function getRiskIntelligenceTrends(params?: { days?: number }): Promise<RiskIntelTrendsResponse> {
  const q: Record<string, string> = {}
  if (params?.days != null) q.days = String(params.days)
  const { data } = await api.get<RiskIntelTrendsResponse>('/analytics/risk-intelligence/trends', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getRiskIntelligenceValidation(params?: {
  cohort_days?: number
  lag_days?: number
}): Promise<RiskIntelValidationResponse> {
  const q: Record<string, string> = {}
  if (params?.cohort_days != null) q.cohort_days = String(params.cohort_days)
  if (params?.lag_days != null) q.lag_days = String(params.lag_days)
  const { data } = await api.get<RiskIntelValidationResponse>('/analytics/risk-intelligence/validation', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getRiskIntelligenceShadowSnapshot(params?: {
  limit?: number
  min_band?: string
  bucket_start?: string | null
}): Promise<RiskIntelShadowSnapshotResponse> {
  const q: Record<string, string> = {}
  if (params?.limit != null) q.limit = String(params.limit)
  if (params?.min_band != null) q.min_band = String(params.min_band)
  if (params?.bucket_start != null && String(params.bucket_start).trim() !== '') {
    q.bucket_start = String(params.bucket_start).trim()
  }
  const { data } = await api.get<RiskIntelShadowSnapshotResponse>('/analytics/risk-intelligence/shadow-snapshot', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function getRiskIntelligenceManagerDigestQueue(params?: {
  min_band?: string
  limit_buckets?: number
}): Promise<RiskIntelDigestQueueResponse> {
  const q: Record<string, string> = {}
  if (params?.min_band != null) q.min_band = String(params.min_band)
  if (params?.limit_buckets != null) q.limit_buckets = String(params.limit_buckets)
  const { data } = await api.get<RiskIntelDigestQueueResponse>('/analytics/risk-intelligence/manager-digest-queue', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}

export async function ackRiskIntelligenceManagerDigest(body: { bucket_start: string }): Promise<{
  ok: boolean
  bucket_start?: string
}> {
  const { data } = await api.post<{ ok: boolean; bucket_start?: string }>(
    '/analytics/risk-intelligence/manager-digest-queue/ack',
    body,
  )
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
