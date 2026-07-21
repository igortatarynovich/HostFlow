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
