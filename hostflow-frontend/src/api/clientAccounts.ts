import { api } from './client'

export type CommercialDefaults = {
  currency?: string | null
  payment_term_days?: number | null
  payment_model?: string | null
  vat_rate?: number | null
  guarantee_days?: number | null
  invoice_right_policy?: string | null
}

export type ClientAccount = {
  id: string
  tenant_id: string
  own_company_id?: string | null
  display_name: string
  status: string
  primary_company_id?: string | null
  commercial_defaults?: CommercialDefaults | null
}

export type ClientAccountListResponse = {
  items: ClientAccount[]
  total: number
}

export async function listClientAccounts(params?: {
  status?: string
  limit?: number
  offset?: number
}): Promise<ClientAccount[]> {
  const { data } = await api.get<ClientAccountListResponse>('/client-accounts', {
    params: {
      status: params?.status,
      limit: params?.limit ?? 200,
      offset: params?.offset ?? 0,
    },
  })
  return Array.isArray(data?.items) ? data.items : []
}

export async function getClientAccount(accountId: string) {
  const { data } = await api.get<ClientAccount>(`/client-accounts/${encodeURIComponent(accountId)}`)
  return data
}

export async function updateClientAccount(
  accountId: string,
  payload: Partial<{
    display_name: string
    status: string
    primary_company_id: string
    commercial_defaults: CommercialDefaults | null
  }>,
) {
  const { data } = await api.patch<ClientAccount>(
    `/client-accounts/${encodeURIComponent(accountId)}`,
    payload,
  )
  return data
}

/** Apply Client Account commercial defaults onto order create form fields (create-time only). */
export function applyCommercialDefaultsPrefill(defaults: CommercialDefaults | null | undefined): {
  currency?: string
  payment_term_days?: string
  payment_model?: string
  vat_rate?: string
  guarantee_days?: string
} {
  if (!defaults || typeof defaults !== 'object') return {}
  const out: {
    currency?: string
    payment_term_days?: string
    payment_model?: string
    vat_rate?: string
    guarantee_days?: string
  } = {}
  if (defaults.currency) out.currency = String(defaults.currency)
  if (defaults.payment_term_days != null && defaults.payment_term_days !== undefined) {
    out.payment_term_days = String(defaults.payment_term_days)
  }
  if (defaults.payment_model) out.payment_model = String(defaults.payment_model)
  if (defaults.vat_rate != null && defaults.vat_rate !== undefined) {
    out.vat_rate = String(defaults.vat_rate)
  }
  if (defaults.guarantee_days != null && defaults.guarantee_days !== undefined) {
    out.guarantee_days = String(defaults.guarantee_days)
  }
  return out
}
