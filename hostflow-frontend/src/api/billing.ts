import http from './http'

export type BillingPlanCode = 'starter' | 'team' | 'pro' | 'enterprise'

export type BillingGate = {
  side_effects_blocked: boolean
  block_reason: 'past_due' | 'trial_expired' | null
  trial_active: boolean
  trial_grace_active: boolean
  trial_hours_remaining: number | null
  trial_urgent: boolean
  side_effect_grace_hours_remaining: number | null
}

export type BillingSubscription = {
  provider: 'mock' | 'stripe'
  status: string
  plan_code: BillingPlanCode
  pending_plan_code: BillingPlanCode | null
  pending_update: boolean
  pending_invoice_id: string | null
  pending_invoice_url: string | null
  customer_id: string | null
  subscription_id: string | null
  checkout_session_id: string | null
  billing_interval?: 'month' | 'year' | null
  current_period_start: string | null
  current_period_end: string | null
  activated_at: string | null
  trial_ends_at: string | null
  cancel_at_period_end: boolean
  canceled_at: string | null
  updated_at: string | null
  gate?: BillingGate
}

export type BillingCheckoutSession = {
  provider: 'mock' | 'stripe'
  mode: 'subscription'
  status: string
  session_id: string
  checkout_url: string
}

export type BillingPortalPackCheckoutSession = {
  provider: 'mock' | 'stripe'
  mode: 'payment'
  status: string
  session_id: string
  checkout_url: string
  pack_increment: number
}

export type BillingAddonPackCheckoutSession = {
  provider: 'mock' | 'stripe'
  mode: 'payment'
  status: string
  session_id: string
  checkout_url: string
  sku: string
  pack_increment: number
}

export type BillingAddonCheckoutOffer = {
  sku: string
  label: string
  configured: boolean
  pack_increment: number | null
  /** Legacy alias of effect_ready */
  checkout_ready: boolean
  effect_ready: boolean
  purchase_allowed: boolean
  purchase_block_reason: string | null
}

export type BillingPortalLink = {
  provider: 'mock' | 'stripe'
  url: string
}

export type BillingUsage = {
  administrator_count?: number
  employee_count?: number
  viewer_count: number
  portal_guest_count?: number
  /** @deprecated alias of employee_count */
  recruiter_count: number
  /** @deprecated alias of administrator_count */
  supervisor_count: number
  /** @deprecated alias of portal_guest_count */
  client_manager_count: number
  storage_used_gb: number
  leads_created_this_month: number
  candidates_active_count: number
  documents_count: number
  vacancies_open_count: number
  portal_links_active_count: number
}

export type BillingUsageCaps = {
  max_leads_created_per_month: number
  max_candidates_active: number
  max_vacancies_active: number
  max_documents: number
  max_public_portal_links: number
}

export type BillingPortalCandidatesUsage = {
  used_this_month_utc: number
  cap: number
  base_cap?: number
  pack_addon?: number
  pack_increment_offer?: number
  /** Legacy: API currently returns false — new portal candidates are blocked at cap (402) on upload-link/notify. */
  soft_limit: boolean
  warning_level: 'none' | 'warn_80' | 'warn_100'
}

export type BillingFounderProgram = {
  tenant_enrolled: boolean
  tenant_revoked: boolean
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
  max_candidates_active: number
  max_vacancies_active: number
  max_documents: number
  max_public_portal_links: number
  expires_at: string | null
  auto_renew: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export type BillingPlan = {
  code: BillingPlanCode
  name: string
  currency?: string
  monthly_price_usd: number
  yearly_equivalent_monthly_eur?: number | null
  limits: Record<string, number>
  /** Stripe monthly price id configured in backend env */
  stripe_month_configured?: boolean
  /** Stripe yearly price id configured in backend env */
  stripe_year_configured?: boolean
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

export type BillingLeadFormsUsage = {
  active_count: number
  cap: number
  base_cap: number
  pack_addon: number
  pack_increment_offer: number
}

export type BillingSummary = {
  subscription: BillingSubscription
  license: BillingLicense | null
  usage: BillingUsage
  usage_caps: BillingUsageCaps
  portal_candidates?: BillingPortalCandidatesUsage | null
  founder_program?: BillingFounderProgram | null
  lead_forms?: BillingLeadFormsUsage | null
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
  addon_checkout_offers?: BillingAddonCheckoutOffer[]
}

export type BillingPlanMatrixFeature = {
  key: string
  label: string
  unit: string | null
  values: Record<string, number | boolean | string | null>
  upgrade_checkout_allowed: boolean
}

export type BillingPlanMatrix = {
  plans: BillingPlan[]
  current_plan_code: string
  features: BillingPlanMatrixFeature[]
}

/** Minimal usage vs caps for quota banners (any tenant member). SSOT with billing summary caps. */
export type BillingQuotaHeadroom = {
  leads_created_this_month: number
  max_leads_created_per_month: number
  candidates_active_count: number
  max_candidates_active: number
  storage_used_gb: number
  max_storage_gb: number
}

export async function getBillingSubscription() {
  const { data } = await http.get<BillingSubscription>('/settings/billing/subscription')
  return data
}

export async function getBillingSummary() {
  const { data } = await http.get<BillingSummary>('/settings/billing/summary')
  return data
}

export async function getBillingQuotaHeadroom() {
  const { data } = await http.get<BillingQuotaHeadroom>('/settings/billing/quota-headroom')
  return data
}

export async function getBillingPlanMatrix() {
  const { data } = await http.get<BillingPlanMatrix>('/settings/billing/plan-matrix')
  return data
}

export async function createBillingCheckoutSession(payload: {
  plan_code: Exclude<BillingPlanCode, 'enterprise'>
  billing_interval?: 'month' | 'year'
  success_url?: string
  cancel_url?: string
}) {
  const { data } = await http.post<BillingCheckoutSession>('/settings/billing/checkout-session', payload)
  return data
}

export async function createPortalCandidatesPackCheckout(payload?: { success_url?: string; cancel_url?: string }) {
  const { data } = await http.post<BillingPortalPackCheckoutSession>(
    '/settings/billing/portal-candidates-pack/checkout',
    payload ?? {},
  )
  return data
}

export async function createAddonPackCheckout(payload: {
  sku: string
  success_url?: string
  cancel_url?: string
}) {
  const { data } = await http.post<BillingAddonPackCheckoutSession>(
    '/settings/billing/addon-pack/checkout',
    payload,
  )
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
  plan_code: Exclude<BillingPlanCode, 'enterprise'>
  billing_interval?: 'month' | 'year'
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

export async function updateBillingCompanySlots(payload: { extra_slots: number }) {
  const { data } = await http.post<BillingSummary>('/settings/billing/company-slots', payload)
  return data
}
