import { api } from './client'
import type { UUID } from './types'

export type HandoffOut = {
  id: string
  candidate_id: string
  agency_tenant_id: string
  client_company_id: string | null
  client_tenant_id: string | null
  destination?: string | null
  requested_by_user_id: string
  requested_at: string
  assigned_to_user_id: string | null
  status: string
  reviewed_by_user_id: string | null
  reviewed_at: string | null
  rejection_reason: string | null
  return_reason: string | null
  requested_by_user_name?: string | null
  assigned_to_user_name?: string | null
}

export type AvailableClientOut = {
  link_id: string
  client_company_id: string | null
  client_tenant_id: string | null
  client_name: string
}

export type HandoffStatusResponse = {
  pending: HandoffOut | null
  accepted: HandoffOut | null
  client_owns: boolean
}

export async function getAvailableClients(): Promise<AvailableClientOut[]> {
  const { data } = await api.get<AvailableClientOut[]>('/handoffs/available-clients')
  return data
}

export async function createHandoff(
  candidateId: UUID,
  payload: {
    client_company_id?: string
    client_tenant_id?: string
    assigned_to_user_id?: string
    destination?: 'client_portal' | 'internal_hr'
  },
): Promise<HandoffOut> {
  const { data } = await api.post<HandoffOut>(`/handoffs/candidates/${candidateId}`, payload)
  return data
}

export type HandoffBulkResult = {
  created: number
  failed: number
  errors: Array<{
    candidate_id: string
    error: string
    detail?: Record<string, unknown>
  }>
}

export async function createBulkHandoff(
  payload: { candidate_ids: UUID[]; client_company_id: UUID; assigned_to_user_id?: UUID }
): Promise<HandoffBulkResult> {
  const { data } = await api.post<HandoffBulkResult>('/handoffs/bulk', payload)
  return data
}

export async function getHandoffStatus(
  candidateId: UUID,
  clientCompanyId?: UUID
): Promise<HandoffStatusResponse> {
  const params = clientCompanyId ? { client_company_id: clientCompanyId } : {}
  const { data } = await api.get<HandoffStatusResponse>(
    `/handoffs/candidates/${candidateId}/handoff-status`,
    { params }
  )
  return data
}

export async function acceptHandoff(handoffId: UUID): Promise<HandoffOut> {
  const { data } = await api.post<HandoffOut>(`/handoffs/${handoffId}/accept`)
  return data
}

export async function rejectHandoff(handoffId: UUID, rejectionReason: string): Promise<HandoffOut> {
  const { data } = await api.post<HandoffOut>(`/handoffs/${handoffId}/reject`, {
    rejection_reason: rejectionReason,
  })
  return data
}

export async function returnHandoff(handoffId: UUID, returnReason: string): Promise<HandoffOut> {
  const { data } = await api.post<HandoffOut>(`/handoffs/${handoffId}/return`, {
    return_reason: returnReason,
  })
  return data
}

export async function changeProcessor(handoffId: UUID, processorUserId: string): Promise<HandoffOut> {
  const { data } = await api.patch<HandoffOut>(`/handoffs/${handoffId}/processor`, {
    processor_user_id: processorUserId,
  })
  return data
}

export type PendingHandoffWithCandidate = {
  handoff: HandoffOut
  candidate: {
    id: string
    first_name: string
    last_name: string
    first_name_latin?: string | null
    last_name_latin?: string | null
    email: string
    phone?: string
    short_id?: string | null
    stage?: string | null
    citizenship?: string | null
    created_at?: string | null
    vacancy_title?: string | null
    manager_id?: string | null
    extra?: Record<string, any>
    docs_progress?: Record<string, any>
    experience?: Array<{
      company?: string
      position?: string
      years?: string
      employer?: string
      [key: string]: any
    }>
  }
}

export type HandoffsWithCandidatesResponse = {
  total: number
  items: PendingHandoffWithCandidate[]
}

export async function getPendingWithCandidates(
  clientCompanyId?: string,
  clientTenantId?: string
): Promise<PendingHandoffWithCandidate[]> {
  const params: Record<string, string> = {}
  if (clientCompanyId) params.client_company_id = clientCompanyId
  if (clientTenantId) params.client_tenant_id = clientTenantId
  if (!params.client_company_id && !params.client_tenant_id) return []
  const { data } = await api.get<PendingHandoffWithCandidate[]>(
    '/handoffs/pending-with-candidates',
    { params }
  )
  return data
}

export async function getHandoffsWithCandidates(params: {
  clientCompanyId?: string
  clientTenantId?: string
  status?: string[]
  fromDays?: number
  dateFrom?: string
  dateTo?: string
  stageCodes?: string[]
  q?: string
  orderBy?: string
  desc?: boolean
  limit?: number
  offset?: number
}): Promise<HandoffsWithCandidatesResponse> {
  const query: Record<string, string | number | boolean> = {}
  if (params.clientCompanyId) query.client_company_id = params.clientCompanyId
  if (params.clientTenantId) query.client_tenant_id = params.clientTenantId
  if (!query.client_company_id && !query.client_tenant_id) {
    return { total: 0, items: [] }
  }
  if (params.status && params.status.length > 0) {
    query.status = params.status.join(',')
  }
  if (typeof params.fromDays === 'number') {
    query.from_days = params.fromDays
  }
  if (params.dateFrom) {
    query.date_from = params.dateFrom
  }
  if (params.dateTo) {
    query.date_to = params.dateTo
  }
  if (params.stageCodes && params.stageCodes.length > 0) {
    query.stage_codes = params.stageCodes.join(',')
  }
  if (params.q && params.q.trim().length >= 2) {
    query.q = params.q.trim()
  }
  if (params.orderBy) {
    query.order_by = params.orderBy
  }
  if (typeof params.desc === 'boolean') {
    query.desc = params.desc
  }
  if (typeof params.limit === 'number') {
    query.limit = params.limit
  }
  if (typeof params.offset === 'number') {
    query.offset = params.offset
  }
  const { data } = await api.get<HandoffsWithCandidatesResponse>('/handoffs/with-candidates', {
    params: query,
  })
  return data
}
