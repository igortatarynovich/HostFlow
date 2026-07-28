import { api } from './client'

export type SalesOrderStatus = 'open' | 'in_progress' | 'completed' | 'cancelled'

export type BillingTrigger =
  | 'candidate_hired'
  | 'candidate_started_work'
  | 'guarantee_period_passed'
  | 'milestone_accepted'
  | 'headcount_completed'
  | 'monthly_service_period_closed'

export const BILLING_TRIGGERS: BillingTrigger[] = [
  'candidate_hired',
  'candidate_started_work',
  'guarantee_period_passed',
  'milestone_accepted',
  'headcount_completed',
  'monthly_service_period_closed',
]

export type SalesOrderLine = {
  id: string
  tenant_id: string
  sales_order_id: string
  title: string
  role_label?: string | null
  location?: string | null
  quantity_needed: number
  unit_rate?: number | null
  charge_unit?: string | null
  billing_trigger: BillingTrigger | string
  guarantee_days?: number | null
  status: SalesOrderStatus | string
  sort_order: number
  vacancy_id?: string | null
  company_id?: string | null
}

export type SalesOrder = {
  id: string
  tenant_id: string
  own_company_id?: string | null
  client_account_id?: string | null
  company_id: string
  payer_company_id?: string | null
  title: string
  status: SalesOrderStatus | string
  currency?: string | null
  payment_term_days?: number | null
  payment_model?: string | null
  vat_rate?: number | null
  guarantee_days?: number | null
  invoice_right_policy?: string | null
  billing_notes?: string | null
  commercial_snapshot?: Record<string, unknown> | null
  lines: SalesOrderLine[]
}

export type SalesOrderCreatePayload = {
  company_id: string
  title: string
  client_account_id?: string
  currency?: string
  payment_term_days?: number
  payment_model?: string
  vat_rate?: number
  guarantee_days?: number
  invoice_right_policy?: string
  billing_notes?: string
}

export type SalesOrderLineCreatePayload = {
  title: string
  quantity_needed: number
  role_label?: string
  location?: string
  unit_rate?: number
  charge_unit?: string
  billing_trigger?: BillingTrigger | string
  guarantee_days?: number
}

export async function listSalesOrders(params?: {
  company_id?: string
  status?: string
  limit?: number
}) {
  const { data } = await api.get<{ items: SalesOrder[]; total: number }>('/sales-orders', {
    params: {
      company_id: params?.company_id,
      status: params?.status,
      limit: params?.limit ?? 100,
    },
  })
  return Array.isArray(data?.items) ? data.items : []
}

export async function getSalesOrder(orderId: string) {
  const { data } = await api.get<SalesOrder>(`/sales-orders/${encodeURIComponent(orderId)}`)
  return data
}

export async function createSalesOrder(payload: SalesOrderCreatePayload) {
  const { data } = await api.post<SalesOrder>('/sales-orders', payload)
  return data
}

export async function updateSalesOrder(
  orderId: string,
  payload: Partial<{
    title: string
    status: SalesOrderStatus | string
    currency: string
    payment_term_days: number
    payment_model: string
    vat_rate: number
    guarantee_days: number
    invoice_right_policy: string
    billing_notes: string
  }>,
) {
  const { data } = await api.patch<SalesOrder>(`/sales-orders/${encodeURIComponent(orderId)}`, payload)
  return data
}

export async function createSalesOrderLine(orderId: string, payload: SalesOrderLineCreatePayload) {
  const { data } = await api.post<SalesOrderLine>(`/sales-orders/${encodeURIComponent(orderId)}/lines`, payload)
  return data
}

export async function updateSalesOrderLine(
  lineId: string,
  payload: Partial<{
    title: string
    quantity_needed: number
    role_label: string
    location: string
    unit_rate: number
    charge_unit: string
    billing_trigger: BillingTrigger | string
    guarantee_days: number
    status: SalesOrderStatus | string
  }>,
) {
  const { data } = await api.patch<SalesOrderLine>(
    `/sales-order-lines/${encodeURIComponent(lineId)}`,
    payload,
  )
  return data
}

export async function listSalesOrderLines(params?: {
  company_id?: string
  sales_order_id?: string
  unlinked?: boolean
  status?: string
  limit?: number
}) {
  const { data } = await api.get<{ items: SalesOrderLine[]; total: number }>('/sales-order-lines', {
    params: {
      company_id: params?.company_id,
      sales_order_id: params?.sales_order_id,
      unlinked: params?.unlinked ? true : undefined,
      status: params?.status,
      limit: params?.limit ?? 100,
    },
  })
  return Array.isArray(data?.items) ? data.items : []
}
