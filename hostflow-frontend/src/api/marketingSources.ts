import { api } from './http'

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

export async function listMarketingSources(): Promise<MarketingSourceSummary[]> {
  const { data } = await api.get<MarketingSourceListResponse>('/platform/marketing/sources')
  return Array.isArray(data?.items) ? data.items : []
}
