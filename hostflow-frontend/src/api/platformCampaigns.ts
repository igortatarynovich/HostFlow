import { api } from './client'

export type CampaignTarget = {
  id: string
  target_type: string
  target_id: string
  target_module: string
  route_intent: string
  role: string
  sort_order: number
}

export type CampaignFormLink = {
  id: string
  form_id: string
  role: string
  is_active: boolean
  title?: string | null
  public_slug?: string | null
}

export type CampaignIntakeSourceLink = {
  id: string
  intake_source_profile_id: string
  role: string
  is_active: boolean
  provider?: string | null
  code?: string | null
  name?: string | null
}

export type CampaignFlight = {
  id: string
  code: string
  name: string
  status: string
  starts_at?: string | null
  ends_at?: string | null
  is_current: boolean
  forms: CampaignFormLink[]
  intake_sources: CampaignIntakeSourceLink[]
}

export type Campaign = {
  id: string
  tenant_id: string
  own_company_id: string
  name: string
  description?: string | null
  status: string
  goal_type: string
  primary_kpi: string
  current_flight_id?: string | null
  created_at?: string | null
  updated_at?: string | null
  targets: CampaignTarget[]
  flights: CampaignFlight[]
}

export type CampaignCreateInput = {
  name: string
  goal_type: string
  primary_kpi: string
  description?: string
  own_company_id?: string
  targets?: Array<{
    target_type: string
    target_id: string
    route_intent: string
    role?: string
    sort_order?: number
  }>
}

export type FlightCommandResult = {
  command: string
  campaign: Campaign
  flight_id: string
  flight_status: string
  campaign_status: string
  flight_event_id: string
  flight_event_type: string
  campaign_event_id?: string | null
  campaign_event_type?: string | null
}

export type IntakeSourceOption = {
  id: string
  name: string
  provider: string
  code: string
  is_active: boolean
}

export async function listCampaigns(params?: {
  limit?: number
  offset?: number
}): Promise<Campaign[]> {
  const { data } = await api.get<Campaign[]>('/platform/campaigns', { params })
  return Array.isArray(data) ? data : []
}

export async function getCampaign(campaignId: string): Promise<Campaign> {
  const { data } = await api.get<Campaign>(`/platform/campaigns/${encodeURIComponent(campaignId)}`)
  return data
}

export async function createCampaign(payload: CampaignCreateInput): Promise<Campaign> {
  const { data } = await api.post<Campaign>('/platform/campaigns', payload)
  return data
}

export async function attachCampaignForm(
  campaignId: string,
  formId: string,
  role = 'primary',
): Promise<Campaign> {
  const { data } = await api.post<Campaign>(`/platform/campaigns/${encodeURIComponent(campaignId)}/forms`, {
    form_id: formId,
    role,
  })
  return data
}

export async function attachCampaignIntakeSource(
  campaignId: string,
  intakeSourceProfileId: string,
  role = 'primary',
): Promise<Campaign> {
  const { data } = await api.post<Campaign>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/intake-sources`,
    { intake_source_profile_id: intakeSourceProfileId, role },
  )
  return data
}

export async function launchFlight(
  campaignId: string,
  flightId: string,
  reason?: string,
): Promise<FlightCommandResult> {
  const { data } = await api.post<FlightCommandResult>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}/launch`,
    reason ? { reason } : {},
  )
  return data
}

export async function pauseFlight(
  campaignId: string,
  flightId: string,
  reason?: string,
): Promise<FlightCommandResult> {
  const { data } = await api.post<FlightCommandResult>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}/pause`,
    reason ? { reason } : {},
  )
  return data
}

export async function resumeFlight(
  campaignId: string,
  flightId: string,
  reason?: string,
): Promise<FlightCommandResult> {
  const { data } = await api.post<FlightCommandResult>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}/resume`,
    reason ? { reason } : {},
  )
  return data
}

export async function completeFlight(
  campaignId: string,
  flightId: string,
  reason?: string,
): Promise<FlightCommandResult> {
  const { data } = await api.post<FlightCommandResult>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}/complete`,
    reason ? { reason } : {},
  )
  return data
}

export async function completeCampaign(campaignId: string, reason?: string): Promise<Campaign> {
  const { data } = await api.post<Campaign>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/complete`,
    reason ? { reason } : {},
  )
  return data
}

export async function archiveCampaign(campaignId: string, reason?: string): Promise<Campaign> {
  const { data } = await api.post<Campaign>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/archive`,
    reason ? { reason } : {},
  )
  return data
}

export type FlightKpi = {
  tenant_id: string
  campaign_id: string
  flight_id: string
  currency?: string | null
  spend: string
  leads: number
  qualified: number
  converted: number
  outcomes_completed: number
  cost_per_lead?: string | null
  cost_per_qualified?: string | null
  cost_per_outcome?: string | null
}

export type CampaignKpi = Omit<FlightKpi, 'flight_id'> & {
  flights: FlightKpi[]
}

export type FlightRuntime = {
  tenant_id: string
  campaign_id: string
  flight_id: string
  campaign_status: string
  flight_status: string
  flight_name: string
  flight_code: string
  starts_at?: string | null
  ends_at?: string | null
  is_current: boolean
  endpoints: {
    forms_total: number
    forms_active: number
    intake_sources_total: number
    intake_sources_active: number
  }
  kpi: FlightKpi
  generated_at: string
}

export type LiveIntakeCounters = {
  submissions: number
  leads_activity: number
  candidates: number
  routing_completed: number
  routing_failed: number
  rejected: number
  kpi_leads: number
  spend: string
  cost_per_lead?: string | null
  currency?: string | null
}

export type LiveIntakeMonitorEvent = {
  id: string
  campaign_id: string
  flight_id?: string | null
  event_type: string
  occurred_at: string
  submission_id?: string | null
  payload?: Record<string, unknown>
}

export type LiveIntakeMonitor = {
  tenant_id: string
  campaign_id: string
  flight_id: string
  campaign_status: string
  flight_status: string
  counters: LiveIntakeCounters
  items: LiveIntakeMonitorEvent[]
  next_cursor?: { occurred_at: string; id: string } | null
  order: [string, string] | string[]
  event_types: string[]
}

export async function getCampaignKpi(campaignId: string): Promise<CampaignKpi> {
  const { data } = await api.get<CampaignKpi>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/kpi`,
  )
  return data
}

export async function getFlightKpi(campaignId: string, flightId: string): Promise<FlightKpi> {
  const { data } = await api.get<FlightKpi>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}/kpi`,
  )
  return data
}

export async function getFlightRuntime(campaignId: string, flightId: string): Promise<FlightRuntime> {
  const { data } = await api.get<FlightRuntime>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}/runtime`,
  )
  return data
}

export async function getLiveIntakeMonitor(
  campaignId: string,
  flightId: string,
  params?: {
    limit?: number
    event_type?: string[]
    after_occurred_at?: string
    after_id?: string
  },
): Promise<LiveIntakeMonitor> {
  const { data } = await api.get<LiveIntakeMonitor>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}/monitor/live-intake`,
    { params },
  )
  return data
}

export type FlightOptimizationSignal = {
  code: string
  severity: string
  message: string
}

export type FlightOptimization = {
  tenant_id: string
  campaign_id: string
  flight_id: string
  campaign_status: string
  flight_status: string
  assessment: 'insufficient_data' | 'healthy' | 'suggest_pause' | string
  recommended_action: 'none' | 'suggest_pause' | string
  reason_codes: string[]
  signals: FlightOptimizationSignal[]
  window_hours: number
  window_start: string
  window_end: string
  counters: {
    submissions: number
    routing_completed: number
    routing_failed: number
    delivery_errors: number
    routing_sample: number
    decision_volume: number
  }
  kpi_leads: number
  spend: string
  generated_at: string
  thresholds: {
    min_decision_volume: number
    routing_fail_rate_threshold: number
    min_routing_sample: number
    delivery_error_threshold: number
  }
}

export async function getFlightOptimization(
  campaignId: string,
  flightId: string,
  params?: { window_hours?: number },
): Promise<FlightOptimization> {
  const { data } = await api.get<FlightOptimization>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}/optimization`,
    { params },
  )
  return data
}

export async function updateFlight(
  campaignId: string,
  flightId: string,
  payload: {
    name?: string
    starts_at?: string | null
    ends_at?: string | null
  },
): Promise<CampaignFlight> {
  const { data } = await api.patch<CampaignFlight>(
    `/platform/campaigns/${encodeURIComponent(campaignId)}/flights/${encodeURIComponent(flightId)}`,
    payload,
  )
  return data
}

export async function listIntakeSourceOptions(provider?: string): Promise<IntakeSourceOption[]> {
  const { data } = await api.get<IntakeSourceOption[]>('/platform/campaigns/intake-source-options', {
    params: provider ? { provider } : undefined,
  })
  return Array.isArray(data) ? data : []
}

export function currentFlight(campaign: Campaign): CampaignFlight | null {
  if (!campaign.flights?.length) return null
  const currentId = campaign.current_flight_id
  if (currentId) {
    const found = campaign.flights.find((f) => f.id === currentId)
    if (found) return found
  }
  return campaign.flights[0] ?? null
}
