import { api } from './client'

export type ClientAccount = {
  id: string
  tenant_id: string
  own_company_id?: string | null
  display_name: string
  status: string
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
