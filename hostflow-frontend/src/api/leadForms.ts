import { api } from './client'

export type TenantLeadForm = {
  id: string
  title: string
  public_slug: string | null
  is_active: boolean
  lifecycle_status?: 'draft' | 'active' | 'archived'
  purpose?: string | null
  target_entity_profile_code?: string | null
  created_at: string
  updated_at: string
}

export async function listLeadForms(): Promise<TenantLeadForm[]> {
  const { data } = await api.get<TenantLeadForm[]>('/settings/lead-forms')
  return data
}

export async function createLeadForm(payload: { title?: string }): Promise<TenantLeadForm> {
  const { data } = await api.post<TenantLeadForm>('/settings/lead-forms', payload)
  return data
}

export async function patchLeadForm(
  formId: string,
  patch: { title?: string; is_active?: boolean; public_slug?: string | null },
): Promise<TenantLeadForm> {
  const { data } = await api.patch<TenantLeadForm>(`/settings/lead-forms/${formId}`, patch)
  return data
}
