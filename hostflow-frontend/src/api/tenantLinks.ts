import { api } from './client'

export type ContactPolicy = {
  enabled: boolean
  max_attempts: number
  post_action: 'auto_reject' | 'stage_change'
  stage_code?: string | null
}

export type TenantLink = {
  id: string
  agency_tenant_id: string
  client_company_id: string | null
  client_tenant_id: string | null
  handoff_include_company_id: string | null
  status: string
  features_json: Record<string, unknown> | null
  company_name: string | null
  handoff_enabled?: boolean
  see_vacancies?: boolean
  see_reduced_profiles?: boolean
  portal_token?: string | null
  portal_expires_at?: string | null
}

export type TenantLinkUpdate = {
  handoff_enabled?: boolean
  handoff_to_client?: boolean
  handoff_to_internal_hr?: boolean
  contact_policy?: ContactPolicy
  see_vacancies?: boolean
  see_reduced_profiles?: boolean
}

export type CompanySearchHit = {
  id: string
  name: string
  tenant_id: string
  website: string | null
}

export type TenantLinkCreate = {
  display_name?: string
  client_company_id?: string
  client_tenant_id?: string
  handoff_include_company_id?: string
  handoff_enabled?: boolean
  see_vacancies?: boolean
  see_reduced_profiles?: boolean
}

export async function searchCompaniesForLink(tenantId: string, q: string): Promise<CompanySearchHit[]> {
  const { data } = await api.get<CompanySearchHit[]>(`/tenants/${tenantId}/links/search-companies`, {
    params: { q: q.trim() },
  })
  return data
}

export type PortalLinkOut = {
  url: string
  token: string
  expires_at: string | null
}

export async function createPortalLink(tenantId: string, linkId: string): Promise<PortalLinkOut> {
  const { data } = await api.post<PortalLinkOut>(`/tenants/${tenantId}/links/${linkId}/portal-link`)
  return data
}

export async function revokePortalLink(tenantId: string, linkId: string): Promise<void> {
  await api.delete(`/tenants/${tenantId}/links/${linkId}/portal-link`)
}

export type ClientPortalPresentedBy =
  | { kind: 'generic' }
  | { kind: 'named'; first_name: string }

export type ClientPortalHandoff = {
  id: string
  status: string
  requested_at: string | null
  waiting_hours: number | null
  presented_by: ClientPortalPresentedBy
}

export type ClientPortalActivityRow = {
  handoff_id: string
  candidate_id: string
  status: string
  at: string | null
}

export type ClientPortalData = {
  company_name: string | null
  summary?: {
    pending_decisions: number
    candidates_in_progress: number
  }
  activity?: ClientPortalActivityRow[]
  candidates: Array<{
    id: string
    short_id?: string
    first_name?: string | null
    last_name?: string | null
    stage?: string | null
    status?: string | null
    email?: string | null
    phone?: string | null
    handoff?: ClientPortalHandoff
  }>
}

export async function getClientPortalByToken(token: string): Promise<ClientPortalData> {
  const { data } = await api.get<ClientPortalData>('/public/client-portal', { params: { token } })
  return data
}

export async function portalAcceptHandoff(token: string, handoffId: string): Promise<void> {
  await api.post(`/public/client-portal/handoffs/${encodeURIComponent(handoffId)}/accept`, {}, { params: { token } })
}

export async function portalRejectHandoff(token: string, handoffId: string, reason: string): Promise<void> {
  await api.post(
    `/public/client-portal/handoffs/${encodeURIComponent(handoffId)}/reject`,
    { reason },
    { params: { token } },
  )
}

export async function portalRequestClarification(token: string, handoffId: string, message: string): Promise<void> {
  await api.post(
    `/public/client-portal/handoffs/${encodeURIComponent(handoffId)}/request-clarification`,
    { message },
    { params: { token } },
  )
}

export function getContactPolicy(link: TenantLink): ContactPolicy {
  const features = link.features_json as Record<string, unknown> | null | undefined
  const policy = (features?.contact_policy || {}) as Partial<ContactPolicy>
  return {
    enabled: Boolean(policy.enabled),
    max_attempts: policy.max_attempts ?? 3,
    post_action: policy.post_action === 'stage_change' ? 'stage_change' : 'auto_reject',
    stage_code: policy.stage_code ?? null,
  }
}

/** Matches backend `TenantLink.get_handoff_to_client` (default true). */
export function getHandoffToClient(link: TenantLink): boolean {
  const features = link.features_json as Record<string, unknown> | null | undefined
  return features?.handoff_to_client !== false
}

/** Matches backend `TenantLink.get_handoff_to_internal_hr`. */
export function getHandoffToInternalHr(link: TenantLink): boolean {
  const features = link.features_json as Record<string, unknown> | null | undefined
  return Boolean(features?.handoff_to_internal_hr)
}

export type PrimaryHandoffDestination = 'client_portal' | 'internal_hr'

/**
 * Single primary handoff lane for the candidate card when both destinations are enabled
 * defaults to the client portal; turn off "to client" in the link to use internal HR only.
 */
export function resolvePrimaryHandoffDestination(link: TenantLink | null): PrimaryHandoffDestination | null {
  if (!link || !link.handoff_enabled) return null
  const toClient = getHandoffToClient(link)
  const toHr = getHandoffToInternalHr(link)
  if (toHr && !toClient) return 'internal_hr'
  if (toClient) return 'client_portal'
  return null
}

export function tenantLinkAppliesToCompany(link: TenantLink, companyId: string): boolean {
  const cid = String(companyId || '').trim()
  if (!cid) return false
  return (
    String(link.client_company_id || '').trim() === cid ||
    String(link.handoff_include_company_id || '').trim() === cid
  )
}

export function isHandoffEnabledForCompany(links: TenantLink[], companyId: string): boolean {
  return links.some((link) => tenantLinkAppliesToCompany(link, companyId) && Boolean(link.handoff_enabled))
}

export async function listTenantLinks(tenantId: string): Promise<TenantLink[]> {
  const { data } = await api.get<TenantLink[]>(`/tenants/${tenantId}/links`)
  return data
}

export async function createTenantLink(
  tenantId: string,
  payload: TenantLinkCreate
): Promise<TenantLink> {
  const { data } = await api.post<TenantLink>(`/tenants/${tenantId}/links`, payload)
  return data
}

export async function updateTenantLink(
  tenantId: string,
  linkId: string,
  payload: TenantLinkUpdate
): Promise<TenantLink> {
  const { data } = await api.patch<TenantLink>(`/tenants/${tenantId}/links/${linkId}`, payload)
  return data
}
