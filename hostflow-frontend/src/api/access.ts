import { api } from './client'
import type { CompanyAccessEntry } from './types'

function normalizeList(payload: any): CompanyAccessEntry[] {
  if (Array.isArray(payload)) return payload as CompanyAccessEntry[]
  if (payload && Array.isArray(payload.items)) return payload.items as CompanyAccessEntry[]
  return []
}

export async function listCompanyAccess(companyId: string): Promise<CompanyAccessEntry[]> {
  const { data } = await api.get(`/admin/companies/${companyId}/access`)
  return normalizeList(data)
}

export async function grantCompanyAccess(
  companyId: string,
  payload: { user_id: string; can_edit: boolean },
): Promise<CompanyAccessEntry> {
  const { data } = await api.post(`/admin/companies/${companyId}/access`, payload)
  return data as CompanyAccessEntry
}

export async function revokeCompanyAccess(companyId: string, userId: string): Promise<void> {
  await api.delete(`/admin/companies/${companyId}/access/${userId}`)
}
