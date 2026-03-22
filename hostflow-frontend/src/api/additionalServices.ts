import { api } from './client'
import type {
  AdditionalService,
  AdditionalServiceAttachment,
  AdditionalServiceItem,
  AdditionalServiceOrder,
  AdditionalServiceOrderSummary,
  AdditionalServiceSchedule,
  ServiceOrderStatus,
  ServiceScheduleStatus,
  ServiceUnit,
} from './types'

export interface CreateAdditionalServiceInput {
  code: string
  name: string
  description?: string | null
  category?: string | null
  unit?: ServiceUnit
  base_price?: number
  estimated_cost?: number
  cost_currency?: string
  currency?: string
  vat_rate?: number
  requires_schedule?: boolean
  requires_candidate?: boolean
  result_document_type?: string | null
  requires_documents?: string[]
  sla_hours?: number | null
  is_active?: boolean
  meta?: Record<string, any>
}

export type UpdateAdditionalServiceInput = Partial<CreateAdditionalServiceInput>

export async function listAdditionalServices(includeInactive = false, includeMetrics = false) {
  const params: Record<string, boolean> = {}
  if (includeInactive) params.include_inactive = true
  if (includeMetrics) params.include_metrics = true
  const { data } = await api.get<AdditionalService[]>(
    '/services',
    Object.keys(params).length ? { params } : undefined
  )
  return data
}

export async function createAdditionalService(payload: CreateAdditionalServiceInput) {
  const { data } = await api.post<AdditionalService>('/services', payload)
  return data
}

export async function updateAdditionalService(id: string, payload: UpdateAdditionalServiceInput) {
  const { data } = await api.patch<AdditionalService>(`/services/${id}`, payload)
  return data
}

export interface CreateServiceOrderItemInput {
  service_id?: string
  service_code?: string
  qty?: number
  unit_price?: number
  estimated_cost?: number
  actual_cost?: number
  cost_currency?: string
  cost_source?: string
  cost_status?: string
  vat_rate?: number
  required_documents?: string[]
  result_document_type?: string | null
  meta?: Record<string, any>
}

export interface CreateServiceOrderInput {
  candidate_id?: string | null
  vacancy_id?: string | null
  company_id?: string | null
  currency?: string
  notes?: string | null
  assigned_to?: string | null
  audit?: Record<string, any>
  items: CreateServiceOrderItemInput[]
}

export interface ServiceOrderQuery {
  candidateId?: string
  vacancyId?: string
  companyId?: string
  status?: ServiceOrderStatus | ServiceOrderStatus[]
}

export async function listServiceOrders(params: ServiceOrderQuery = {}) {
  const query: Record<string, any> = {}
  if (params.candidateId) query.candidate_id = params.candidateId
  if (params.vacancyId) query.vacancy_id = params.vacancyId
  if (params.companyId) query.company_id = params.companyId
  if (params.status) query.status = params.status

  const { data } = await api.get<AdditionalServiceOrder[]>('/service-orders', {
    params: Object.keys(query).length ? query : undefined,
  })
  return data
}

export async function getServiceOrder(orderId: string) {
  const { data } = await api.get<AdditionalServiceOrder>(`/service-orders/${orderId}`)
  return data
}

export async function getServiceOrderSummary(orderId: string) {
  const { data } = await api.get<AdditionalServiceOrderSummary>(
    `/service-orders/${orderId}/summary`
  )
  return data
}

export async function createServiceOrder(payload: CreateServiceOrderInput) {
  const { data } = await api.post<AdditionalServiceOrder>('/service-orders', payload)
  return data
}

export interface UpdateServiceOrderInput {
  status?: ServiceOrderStatus
  notes?: string | null
  assigned_to?: string | null
  audit?: Record<string, any> | null
}

export async function updateServiceOrder(orderId: string, payload: UpdateServiceOrderInput) {
  const { data } = await api.patch<AdditionalServiceOrder>(
    `/service-orders/${orderId}`,
    payload
  )
  return data
}

export async function addServiceOrderItem(
  orderId: string,
  payload: CreateServiceOrderItemInput
) {
  const { data } = await api.post<AdditionalServiceItem>(
    `/service-orders/${orderId}/items`,
    payload
  )
  return data
}

export interface CreateServiceScheduleInput {
  provider?: string | null
  slot_start?: string | null
  slot_end?: string | null
  location?: string | null
  status?: ServiceScheduleStatus
  meta?: Record<string, any>
}

export type UpdateServiceScheduleInput = Partial<CreateServiceScheduleInput>

export async function addServiceSchedule(
  itemId: string,
  payload: CreateServiceScheduleInput
) {
  const { data } = await api.post<AdditionalServiceSchedule>(
    `/service-items/${itemId}/schedule`,
    payload
  )
  return data
}

export async function updateServiceSchedule(
  scheduleId: string,
  payload: UpdateServiceScheduleInput
) {
  const { data } = await api.patch<AdditionalServiceSchedule>(
    `/service-schedule/${scheduleId}`,
    payload
  )
  return data
}

export interface DeliverServiceItemInput {
  status?: 'delivered' | 'in_progress' | 'cancelled'
  result_document?: {
    document_type: string
    status?: string
    issued_at?: string
    expires_at?: string
    number?: string
    file_id?: string
    extra?: Record<string, any>
  }
  attachments?: Array<{
    file_id: string
    label?: string | null
  }>
  meta?: Record<string, any>
}

export async function deliverServiceItem(itemId: string, payload: DeliverServiceItemInput) {
  const { data } = await api.post<AdditionalServiceItem>(
    `/service-items/${itemId}/deliver`,
    payload
  )
  return data
}

export async function addServiceAttachment(
  itemId: string,
  payload: { file_id: string; label?: string | null }
) {
  const { data } = await api.post<AdditionalServiceAttachment>(
    `/service-items/${itemId}/attachments`,
    payload
  )
  return data
}
