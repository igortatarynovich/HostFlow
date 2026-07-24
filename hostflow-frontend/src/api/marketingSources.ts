import http from './http'

export type MarketingSourceConnectionStatus = 'connected' | 'attention' | 'disconnected'
export type MarketingSourceMappingHealth = 'ready' | 'needs_review' | 'broken'

export type MarketingSourceSummary = {
  source_id: string
  provider: string
  display_name: string
  connection_status: MarketingSourceConnectionStatus | string
  mapping_health: MarketingSourceMappingHealth | string
  last_submission_at: string | null
  last_error_at: string | null
  last_error_code: string | null
  campaign_count: number
  flight_count: number
  mapping_path: string
  test_lead_path: string
  settings_path: string
  code?: string
  is_active?: boolean
  mapping_rules_count?: number
  active_binding_count?: number
  waiting_submissions?: number
  last_problematic_ad_id?: string | null
  routing_issue_code?: string | null
  routing_issue_message?: string | null
  setup_campaign_flight_path?: string | null
}

export type MarketingSourceListResponse = {
  items: MarketingSourceSummary[]
}

export type MarketingSourceDiscoveredField = {
  source: string
  sample_value_masked: string
  proposed_target: string | null
  status: string
}

export type MarketingSourceSample = {
  source_id: string
  sample_source: string
  lead_id: string | null
  captured_at: string | null
  capture_next_until: string | null
  has_sample: boolean
  fields: MarketingSourceDiscoveredField[]
  raw_payload_masked: Record<string, unknown>
  mapping_rules_count: number
}

export type MarketingSourceSamplePreview = {
  source_id: string
  fields: MarketingSourceDiscoveredField[]
  normalized_payload: Record<string, unknown>
  raw_payload_masked: Record<string, unknown>
  mapping_rules_count: number
  accepted_rules: Record<string, unknown>[]
  creates_entities: boolean
}

export type MarketingSourceCaptureNext = {
  source_id: string
  capture_next_armed_at: string
  capture_next_until: string
  message: string
}

export async function listMarketingSources(): Promise<MarketingSourceSummary[]> {
  const { data } = await http.get<MarketingSourceListResponse>('/platform/marketing/sources')
  return Array.isArray(data?.items) ? data.items : []
}

export async function getMarketingSourceSample(sourceId: string): Promise<MarketingSourceSample> {
  const { data } = await http.get<MarketingSourceSample>(
    `/platform/marketing/sources/${encodeURIComponent(sourceId)}/sample`,
  )
  return data
}

export async function postMarketingSourceSampleFromPayload(
  sourceId: string,
  samplePayload: Record<string, unknown>,
): Promise<MarketingSourceSample> {
  const { data } = await http.post<MarketingSourceSample>(
    `/platform/marketing/sources/${encodeURIComponent(sourceId)}/sample/from-payload`,
    { sample_payload: samplePayload },
  )
  return data
}

export async function postMarketingSourceCaptureNext(
  sourceId: string,
): Promise<MarketingSourceCaptureNext> {
  const { data } = await http.post<MarketingSourceCaptureNext>(
    `/platform/marketing/sources/${encodeURIComponent(sourceId)}/sample/capture-next`,
  )
  return data
}

export async function postMarketingSourceSamplePreview(
  sourceId: string,
  samplePayload?: Record<string, unknown> | null,
): Promise<MarketingSourceSamplePreview> {
  const body =
    samplePayload === undefined || samplePayload === null
      ? {}
      : { sample_payload: samplePayload }
  const { data } = await http.post<MarketingSourceSamplePreview>(
    `/platform/marketing/sources/${encodeURIComponent(sourceId)}/sample/preview`,
    body,
  )
  return data
}
