import http from './http'

export type BillingSubscription = {
  provider: 'mock' | 'stripe'
  status: string
  plan_code: 'starter' | 'team' | 'pro'
  pending_plan_code: 'starter' | 'team' | 'pro' | null
  pending_update: boolean
  pending_invoice_id: string | null
  pending_invoice_url: string | null
  customer_id: string | null
  subscription_id: string | null
  checkout_session_id: string | null
  current_period_start: string | null
  current_period_end: string | null
  activated_at: string | null
  trial_ends_at: string | null
  cancel_at_period_end: boolean
  canceled_at: string | null
  updated_at: string | null
}

export type BillingCheckoutSession = {
  provider: 'mock' | 'stripe'
  mode: 'subscription'
  status: string
  session_id: string
  checkout_url: string
}

export type BillingPortalLink = {
  provider: 'mock' | 'stripe'
  url: string
}

export type BillingUsage = {
  recruiter_count: number
  supervisor_count: number
  client_manager_count: number
  viewer_count: number
  storage_used_gb: number
}

export type BillingLicense = {
  id: string
  tenant_id: string
  plan: string
  max_recruiters: number
  max_supervisors: number
  max_client_managers: number
  max_viewers: number
  max_storage_gb: number
  max_companies: number
  expires_at: string | null
  auto_renew: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export type BillingPlan = {
  code: 'starter' | 'team' | 'pro'
  name: string
  monthly_price_usd: number
  limits: Record<string, number>
}

export type BillingHistoryItem = {
  id: string
  occurred_at: string
  event_type: string
  status: string
  title: string
  description: string | null
  source: 'app' | 'stripe'
  plan_code: string | null
  amount_minor: number | null
  currency: string | null
  invoice_id: string | null
  hosted_invoice_url: string | null
  invoice_pdf_url: string | null
}

export type BillingInvoice = {
  id: string
  number: string | null
  status: string
  currency: string | null
  total_minor: number | null
  amount_paid_minor: number | null
  amount_due_minor: number | null
  created_at: string | null
  paid_at: string | null
  period_start: string | null
  period_end: string | null
  hosted_invoice_url: string | null
  invoice_pdf_url: string | null
}

export type BillingSummary = {
  subscription: BillingSubscription
  license: BillingLicense | null
  usage: BillingUsage
  company_slots?: {
    included_limit: number
    extra_slots: number
    effective_limit: number
    used: number
    available: number
    unlimited: boolean
  } | null
  available_plans: BillingPlan[]
  history: BillingHistoryItem[]
  invoices: BillingInvoice[]
}

export async function getBillingSubscription() {
  const { data } = await http.get<BillingSubscription>('/settings/billing/subscription')
  return data
}

export async function getBillingSummary() {
  const { data } = await http.get<BillingSummary>('/settings/billing/summary')
  return data
}

export async function createBillingCheckoutSession(payload: {
  plan_code: 'starter' | 'team' | 'pro'
  success_url?: string
  cancel_url?: string
}) {
  const { data } = await http.post<BillingCheckoutSession>('/settings/billing/checkout-session', payload)
  return data
}

export async function simulateBillingCheckoutResolution(
  sessionId: string,
  outcome: 'success' | 'cancel' | 'error',
) {
  const { data } = await http.post<BillingSubscription>(`/settings/billing/checkout-session/${sessionId}/simulate`, {
    outcome,
  })
  return data
}

export async function createBillingPortalLink() {
  const { data } = await http.post<BillingPortalLink>('/settings/billing/portal')
  return data
}

export async function changeBillingPlan(payload: {
  plan_code: 'starter' | 'team' | 'pro'
  success_url?: string
  cancel_url?: string
}) {
  const { data } = await http.post<BillingSummary>('/settings/billing/change-plan', payload)
  return data
}

export async function cancelBillingSubscription(immediate = false) {
  const { data } = await http.post<BillingSummary>('/settings/billing/cancel', { immediate })
  return data
}

export async function reactivateBillingSubscription() {
  const { data } = await http.post<BillingSummary>('/settings/billing/reactivate')
  return data
}
