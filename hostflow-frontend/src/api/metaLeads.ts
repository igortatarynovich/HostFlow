import { api } from './client'
import type {
  GenericInboundWebhookRotateResponse,
  MetaAdsMapCreatePayload,
  MetaAdsMapEntry,
  MetaAdsMapUpdatePayload,
  MetaCredentialCreatePayload,
  MetaCredentialRotateResponse,
  MetaCredentialUpdatePayload,
  MetaGraphFieldDataPreviewResponse,
  MetaIncomingLeadsPreviewResponse,
  MetaLeadAdminResponse,
  MetaLeadCredential,
  MetaLeadReroutePayload,
  MetaLeadSelfServeOnboarding,
  MetaLeadFormListResponse,
  MetaLeadFormMapping,
  MetaFormRoute,
  MetaFormRouteUpdate,
  LeadTargetType,
  MetaLeadSettings,
  MetaLeadSettingsPatch,
  LeadMessageTemplate,
  LeadMessageTemplatePayload,
} from './types'

const BASE = '/settings/leads'

export async function getMetaLeadSettings(): Promise<MetaLeadSettings> {
  const { data } = await api.get(`${BASE}/settings`)
  return data
}

export async function getMetaLeadSelfServeOnboarding(): Promise<MetaLeadSelfServeOnboarding> {
  const { data } = await api.get(`${BASE}/meta/self-serve-onboarding`)
  return data
}

export type MetaOAuthPageOption = { id: string; name: string }

export type MetaOAuthStartResponse = { authorize_url: string; state: string }

export type MetaOAuthCompleteResponse = { pending_id: string; pages: MetaOAuthPageOption[] }

export type MetaOAuthFinalizeResponse = {
  credential: MetaLeadCredential
  subscribed_leadgen: boolean
  warning?: string | null
}

export async function startMetaOAuth(): Promise<MetaOAuthStartResponse> {
  const { data } = await api.post<MetaOAuthStartResponse>(`${BASE}/meta/oauth/start`)
  return data
}

export async function completeMetaOAuth(payload: {
  code: string
  state: string
}): Promise<MetaOAuthCompleteResponse> {
  const { data } = await api.post<MetaOAuthCompleteResponse>(`${BASE}/meta/oauth/complete`, payload)
  return data
}

export async function finalizeMetaOAuth(payload: {
  pending_id: string
  page_id: string
  label: string
  subscribe_leadgen?: boolean
}): Promise<MetaOAuthFinalizeResponse> {
  const { data } = await api.post<MetaOAuthFinalizeResponse>(`${BASE}/meta/oauth/finalize`, payload)
  return data
}

export async function updateMetaLeadSettings(payload: MetaLeadSettingsPatch): Promise<MetaLeadSettings> {
  const { data } = await api.patch(`${BASE}/settings`, payload)
  return data
}

export async function listLeadMessageTemplates(): Promise<LeadMessageTemplate[]> {
  const { data } = await api.get<LeadMessageTemplate[]>(`${BASE}/message-templates`)
  return data
}

export async function createLeadMessageTemplate(payload: LeadMessageTemplatePayload): Promise<LeadMessageTemplate> {
  const { data } = await api.post<LeadMessageTemplate>(`${BASE}/message-templates`, payload)
  return data
}

export async function updateLeadMessageTemplate(
  templateId: string,
  payload: LeadMessageTemplatePayload,
): Promise<LeadMessageTemplate> {
  const { data } = await api.patch<LeadMessageTemplate>(`${BASE}/message-templates/${encodeURIComponent(templateId)}`, payload)
  return data
}

export async function deleteLeadMessageTemplate(templateId: string): Promise<void> {
  await api.delete(`${BASE}/message-templates/${encodeURIComponent(templateId)}`)
}

export async function rotateGenericInboundWebhook(): Promise<GenericInboundWebhookRotateResponse> {
  const { data } = await api.post(`${BASE}/inbound-webhook/rotate`)
  return data
}

export async function listMetaLeadCredentials(): Promise<MetaLeadCredential[]> {
  const { data } = await api.get(`${BASE}/credentials`)
  return data
}

export async function createMetaLeadCredential(payload: MetaCredentialCreatePayload): Promise<MetaLeadCredential> {
  const { data } = await api.post(`${BASE}/credentials`, payload)
  return data
}

export async function updateMetaLeadCredential(
  credentialId: string,
  payload: MetaCredentialUpdatePayload,
): Promise<MetaLeadCredential> {
  const { data } = await api.patch(`${BASE}/credentials/${credentialId}`, payload)
  return data
}

export async function deleteMetaLeadCredential(credentialId: string): Promise<void> {
  await api.delete(`${BASE}/credentials/${credentialId}`)
}

export async function rotateMetaLeadCredential(credentialId: string): Promise<MetaCredentialRotateResponse> {
  const { data } = await api.post(`${BASE}/credentials/${credentialId}/rotate`)
  return data
}

export async function listMetaAdsMap(opts?: { search?: string; limit?: number }): Promise<MetaAdsMapEntry[]> {
  const params: Record<string, any> = {}
  if (opts?.search) params.search = opts.search
  if (opts?.limit) params.limit = opts.limit
  const { data } = await api.get(`${BASE}/mapping`, { params })
  return data
}

export async function createMetaAdsMap(payload: MetaAdsMapCreatePayload): Promise<MetaAdsMapEntry> {
  const { data } = await api.post(`${BASE}/mapping`, payload)
  return data
}

export async function updateMetaAdsMap(adId: string, payload: MetaAdsMapUpdatePayload): Promise<MetaAdsMapEntry> {
  const { data } = await api.patch(`${BASE}/mapping/${adId}`, payload)
  return data
}

export async function deleteMetaAdsMap(adId: string): Promise<void> {
  await api.delete(`${BASE}/mapping/${adId}`)
}

export async function rerouteMetaLead(leadId: string, payload: MetaLeadReroutePayload): Promise<MetaLeadAdminResponse> {
  const { data } = await api.post(`${BASE}/leads/${leadId}/reroute`, payload)
  return data
}

export type UnmappedAdGroup = {
  ad_id: string
  count: number
  leads: Array<{
    id: string
    ad_id?: number | null
    status: string
    vacancy_id?: string | null
    error?: string | null
    normalized?: Record<string, unknown> | null
    created_at: string
    [key: string]: unknown
  }>
}

export type UnmappedLeadsResponse = {
  groups: UnmappedAdGroup[]
}

export async function getUnmappedLeads(opts?: {
  status?: string
  limit_per_ad?: number
}): Promise<UnmappedLeadsResponse> {
  const params: Record<string, string | number> = {}
  if (opts?.status) params.status = opts.status
  if (opts?.limit_per_ad != null) params.limit_per_ad = opts.limit_per_ad
  const { data } = await api.get<UnmappedLeadsResponse>(`${BASE}/unmapped-leads`, { params })
  return data
}

export type RetryLeadsPayload = {
  lead_ids?: string[]
  statuses?: string[]
  limit?: number
  refresh_graph?: boolean
}

export type RetryLeadItem = {
  lead_id: string
  status_before: string
  status_after: string
  candidate_id?: string | null
  error_before?: string | null
  error_after?: string | null
  processed: boolean
  message?: string | null
}

export type RetryLeadsResponse = {
  items: RetryLeadItem[]
  processed: number
  failed: number
  skipped: number
}

export async function retryLeads(payload: RetryLeadsPayload): Promise<RetryLeadsResponse> {
  const { data } = await api.post<RetryLeadsResponse>(`${BASE}/leads/retry`, payload)
  return data
}

export async function getMetaIncomingPreview(opts?: {
  limit?: number
  /** Lead.source: meta | webhook */
  source?: 'meta' | 'webhook'
}): Promise<MetaIncomingLeadsPreviewResponse> {
  const params: Record<string, number | string> = {}
  if (opts?.limit != null) params.limit = opts.limit
  if (opts?.source) params.source = opts.source
  const { data } = await api.get<MetaIncomingLeadsPreviewResponse>(`${BASE}/meta/incoming-preview`, {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}

export async function listMetaLeadForms(opts?: {
  source?: 'meta' | 'webhook'
}): Promise<MetaLeadFormListResponse> {
  const params: Record<string, string> = {}
  if (opts?.source) params.source = opts.source
  const { data } = await api.get<MetaLeadFormListResponse>(`${BASE}/meta/forms`, {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}

export async function getMetaLeadFormMapping(
  formId: string,
  opts?: { page_id?: string | null; source?: 'meta' | 'webhook' },
): Promise<MetaLeadFormMapping> {
  const params: Record<string, string> = {}
  if (opts?.page_id) params.page_id = opts.page_id
  if (opts?.source) params.source = opts.source
  const { data } = await api.get<MetaLeadFormMapping>(`${BASE}/meta/forms/${encodeURIComponent(formId)}/mapping`, {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}

export async function getMetaFormRoute(
  formId: string,
  opts?: { page_id?: string; source?: 'meta' | 'webhook' },
): Promise<MetaFormRoute> {
  const params: Record<string, string> = {}
  if (opts?.page_id) params.page_id = opts.page_id
  if (opts?.source) params.source = opts.source
  const { data } = await api.get<MetaFormRoute>(`${BASE}/meta/forms/${encodeURIComponent(formId)}/route`, {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}

export async function putMetaFormRoute(formId: string, payload: MetaFormRouteUpdate): Promise<MetaFormRoute> {
  const { data } = await api.put<MetaFormRoute>(
    `${BASE}/meta/forms/${encodeURIComponent(formId)}/route`,
    payload,
  )
  return data
}

export async function fetchMetaGraphFieldPreview(payload: {
  leadgen_id?: string
  page_id?: string
  form_id?: string
  hostflow_lead_id?: string
}): Promise<MetaGraphFieldDataPreviewResponse> {
  const { data } = await api.post<MetaGraphFieldDataPreviewResponse>(`${BASE}/meta/graph-field-preview`, payload)
  return data
}
