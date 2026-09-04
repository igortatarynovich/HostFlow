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
  page_id?: string | null
  page_name?: string | null
  provider_form?: string | null
  destination?: string | null
  destination_label?: string | null
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

export type MarketingSourceMappingRule = {
  source: string
  target?: string
  qualified_field_code?: string
  action?: string
  format?: string
  overwrite?: boolean
  option_map?: Record<string, string>
}

export type MappingWorkspaceRow = {
  source: string
  label: string
  options: string[]
  sample_example: string | null
  binding: string
  destination_code: string | null
  destination_label: string | null
  destination_type: string | null
  choice: boolean
  option_map: Record<string, string>
  in_schema: boolean
  drift: string | null
  destination_options?: Array<{ value: string; label: string }>
}

export type MappingDestination = {
  code: string
  label: string
  field_type: string
  choice: boolean
  aliases?: string[]
  options: Array<{ value: string; label: string }>
}

export type MappingWorkspaceSummary = {
  headline: string
  configured_count: number
  total_count: number
  mapped_count?: number
  ignored_count?: number
  unmapped_count: number
  new_question_count: number
  option_drift_count: number
  human: string
  contract_health: string
}

export type MappingProjection = {
  source: string
  destination_label: string
  example_in: string | null
  example_out: string | null
  sentence: string
}

export type MarketingSourceMapping = {
  source_id: string
  provider: string
  display_name: string
  meta_form_id: string | null
  mapping_rules: MarketingSourceMappingRule[]
  profile_mapping_rules: MarketingSourceMappingRule[]
  rules_source: string
  mapping_rules_count: number
  mapping_health: MarketingSourceMappingHealth | string
  destination: string | null
  destination_label: string | null
  route_intent: string | null
  schema_source?: string
  has_schema?: boolean
  has_sample?: boolean
  schema_fields?: MappingWorkspaceRow[]
  summary?: MappingWorkspaceSummary
  contract_health?: string | null
  destinations?: MappingDestination[]
  projection?: MappingProjection[]
}

export type MarketingSourceRoutingPreview = {
  source_id: string
  creates_entities: boolean
  destination: string | null
  destination_label: string | null
  route_intent: string | null
  mapping_health: string | null
  mapping_rules_count: number | null
  unmapped_fields: string[]
  ignored_fields: string[]
  needs_review: boolean
  preview: Record<string, unknown>
  note: string
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

export async function getMarketingSourceMapping(
  sourceId: string,
): Promise<MarketingSourceMapping> {
  const { data } = await http.get<MarketingSourceMapping>(
    `/platform/marketing/sources/${encodeURIComponent(sourceId)}/mapping`,
  )
  return data
}

export async function putMarketingSourceMapping(
  sourceId: string,
  mappingRules: MarketingSourceMappingRule[],
  schemaSnapshot?: { fields: Array<{ source: string; label: string; options?: string[] }> } | null,
): Promise<MarketingSourceMapping> {
  const { data } = await http.put<MarketingSourceMapping>(
    `/platform/marketing/sources/${encodeURIComponent(sourceId)}/mapping`,
    {
      mapping_rules: mappingRules,
      ...(schemaSnapshot ? { schema_snapshot: schemaSnapshot } : {}),
    },
  )
  return data
}

export async function postMarketingSourceRoutingPreview(
  sourceId: string,
  samplePayload?: Record<string, unknown> | null,
): Promise<MarketingSourceRoutingPreview> {
  const body =
    samplePayload === undefined || samplePayload === null
      ? {}
      : { sample_payload: samplePayload }
  const { data } = await http.post<MarketingSourceRoutingPreview>(
    `/platform/marketing/sources/${encodeURIComponent(sourceId)}/mapping/routing-preview`,
    body,
  )
  return data
}
