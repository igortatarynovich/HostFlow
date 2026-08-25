/** C2.3 Campaign Orchestrator client — thin wrapper over `/communications/campaigns`. */

import api from '../client'

export type CommunicationCampaignAudienceDefinition = {
  id?: string
  definition_type: string
  definition: Record<string, unknown>
  meta?: Record<string, unknown>
}

export type CommunicationCampaignVersion = {
  id: string
  campaign_id: string
  version_number: number
  status: string
  intent_key: string
  preferred_template_key?: string | null
  channel?: string | null
  plan?: Record<string, unknown>
  meta?: Record<string, unknown>
  audience_definition?: CommunicationCampaignAudienceDefinition | null
  published_at?: string | null
  published_by?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type CommunicationCampaignBundle = {
  id: string
  key: string
  name: string
  description?: string | null
  status: string
  created_at?: string | null
  updated_at?: string | null
  draft: CommunicationCampaignVersion | null
  latest_published: CommunicationCampaignVersion | null
  published_version?: CommunicationCampaignVersion
}

export type CommunicationCampaignRunItem = {
  id: string
  recipient_id: string
  status: string
  reason_codes?: string[]
  reason_message?: string | null
  intent_key?: string | null
}

export type CommunicationCampaignRun = {
  id: string
  campaign_id: string
  campaign_version_id: string
  idempotency_key: string
  status: string
  audience_snapshot?: Record<string, unknown>
  recipient_count?: number
  recipients?: Array<{
    id: string
    entity_type: string
    entity_id: string
    address: string
    label?: string | null
  }>
  items?: CommunicationCampaignRunItem[]
  started_at?: string | null
  completed_at?: string | null
  meta?: Record<string, unknown>
  created_at?: string | null
}

export type CommunicationCampaignCreateInput = {
  key: string
  name: string
  description?: string | null
  intent_key: string
  preferred_template_key?: string | null
  channel?: string | null
  plan?: Record<string, unknown>
  audience?: {
    definition_type?: string
    definition?: Record<string, unknown>
    meta?: Record<string, unknown>
  }
}

export type CommunicationCampaignDraftPatch = {
  intent_key?: string | null
  preferred_template_key?: string | null
  channel?: string | null
  plan?: Record<string, unknown> | null
  meta?: Record<string, unknown> | null
  audience?: {
    definition_type?: string
    definition?: Record<string, unknown>
    meta?: Record<string, unknown>
  } | null
  clear_preferred_template_key?: boolean
  clear_channel?: boolean
}

export async function listCommunicationCampaigns(params?: {
  includeArchived?: boolean
}): Promise<CommunicationCampaignBundle[]> {
  const res = await api.get('/communications/campaigns', {
    params: { include_archived: params?.includeArchived ? true : undefined },
  })
  const items = res.data?.items
  return Array.isArray(items) ? items : []
}

export async function getCommunicationCampaign(
  campaignId: string,
): Promise<CommunicationCampaignBundle> {
  const res = await api.get(`/communications/campaigns/${campaignId}`)
  return res.data
}

export async function createCommunicationCampaign(
  body: CommunicationCampaignCreateInput,
): Promise<CommunicationCampaignBundle> {
  const res = await api.post('/communications/campaigns', body)
  return res.data
}

export async function updateCommunicationCampaignDraft(
  campaignId: string,
  body: CommunicationCampaignDraftPatch,
): Promise<CommunicationCampaignBundle> {
  const res = await api.patch(`/communications/campaigns/${campaignId}/draft`, body)
  return res.data
}

export async function publishCommunicationCampaign(
  campaignId: string,
): Promise<CommunicationCampaignBundle> {
  const res = await api.post(`/communications/campaigns/${campaignId}/publish`)
  return res.data
}

export async function archiveCommunicationCampaign(
  campaignId: string,
): Promise<CommunicationCampaignBundle> {
  const res = await api.post(`/communications/campaigns/${campaignId}/archive`)
  return res.data
}

export async function listCommunicationCampaignVersions(
  campaignId: string,
): Promise<CommunicationCampaignVersion[]> {
  const res = await api.get(`/communications/campaigns/${campaignId}/versions`)
  const items = res.data?.items
  return Array.isArray(items) ? items : []
}

export async function dryRunCommunicationCampaignAudience(
  campaignId: string,
  body?: { version_id?: string; entities?: unknown[] },
): Promise<{
  ok: boolean
  recipients: Array<{ address: string; entity_type?: string; entity_id?: string }>
  skipped?: unknown[]
  diagnostics?: Array<{ code?: string; message?: string }>
}> {
  const res = await api.post(
    `/communications/campaigns/${campaignId}/audience/dry-run`,
    body || {},
  )
  return res.data
}

export async function listCommunicationCampaignRuns(
  campaignId: string,
  limit = 20,
): Promise<CommunicationCampaignRun[]> {
  const res = await api.get(`/communications/campaigns/${campaignId}/runs`, {
    params: { limit },
  })
  const items = res.data?.items
  return Array.isArray(items) ? items : []
}

export async function createCommunicationCampaignRun(
  campaignId: string,
  body: { idempotency_key: string; campaign_version_id?: string },
): Promise<CommunicationCampaignRun> {
  const res = await api.post(`/communications/campaigns/${campaignId}/runs`, body)
  return res.data
}

export async function executeCommunicationCampaignRun(
  campaignId: string,
  runId: string,
  body?: { mode?: 'request_only' | 'render' | 'execute'; skip_transport?: boolean },
): Promise<{
  orchestration: {
    status: string
    summary: { total: number; emitted: number; skipped: number; failed: number }
  }
  run: CommunicationCampaignRun
}> {
  const res = await api.post(
    `/communications/campaigns/${campaignId}/runs/${runId}/execute`,
    body || { mode: 'request_only' },
  )
  return res.data
}

export async function cancelCommunicationCampaignRun(
  campaignId: string,
  runId: string,
  reason?: string,
): Promise<CommunicationCampaignRun> {
  const res = await api.post(
    `/communications/campaigns/${campaignId}/runs/${runId}/cancel`,
    { reason },
  )
  return res.data
}
