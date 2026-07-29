/** Marketing Source Diagnostics API — list + case (+ PR2 filters). */
import { api } from './client'

export type DiagnosticsSubmission = {
  lead_id: string
  created_at?: string | null
  full_name?: string | null
  phone?: string | null
  email?: string | null
  lead_status: string
  disposition?: string | null
  status_label: string
  candidate_id?: string | null
  vacancy_id?: string | null
  route_intent?: string | null
  routing_status?: string | null
  source?: string | null
}

export type DiagnosticsTimelineEvent = {
  id: string
  event_type: string
  occurred_at: string
  campaign_id: string
  flight_id?: string | null
  submission_id?: string | null
  payload: Record<string, unknown>
}

export type DiagnosticsDuplicate = {
  active: boolean
  lead_status: string
  disposition?: string | null
  match_level?: string | null
  suggested_candidate_id?: string | null
  attach_candidate_id?: string | null
  reasons: string[]
  hr_blockers: string[]
  error_code?: string | null
  needs_duplicate_review: boolean
  stamped_at?: string | null
}

export type DiagnosticsMapping = {
  active: boolean
  source_id?: string | null
  display_name?: string | null
  provider?: string | null
  mapping_health?: string | null
  mapping_rules_count: number
  rules_source?: string | null
  meta_form_id?: string | null
  mapping_path?: string | null
  profile_updated_at?: string | null
  historical_version_available: boolean
  profile_missing: boolean
}

export type DiagnosticsCase = DiagnosticsSubmission & {
  submission_id?: string | null
  campaign_id?: string | null
  flight_id?: string | null
  routing: Record<string, unknown>
  decision: Record<string, unknown>
  payload: Record<string, unknown>
  normalized: Record<string, unknown>
  lead_error?: string | null
  duplicate: DiagnosticsDuplicate
  mapping: DiagnosticsMapping
  timeline: DiagnosticsTimelineEvent[]
}

export type DiagnosticsListResponse = {
  items: DiagnosticsSubmission[]
  next_cursor?: { created_at: string; id: string } | null
}

export type DiagnosticsListParams = {
  limit?: number
  after_created_at?: string
  after_id?: string
  source?: string
  flight_id?: string
  failed_only?: boolean
}

export async function listDiagnosticsSubmissions(
  params?: DiagnosticsListParams,
): Promise<DiagnosticsListResponse> {
  const { data } = await api.get<DiagnosticsListResponse>(
    '/platform/marketing/diagnostics/submissions',
    { params },
  )
  return data
}

export async function getDiagnosticsCase(leadId: string): Promise<DiagnosticsCase> {
  const { data } = await api.get<DiagnosticsCase>(
    `/platform/marketing/diagnostics/submissions/${encodeURIComponent(leadId)}`,
  )
  return data
}
