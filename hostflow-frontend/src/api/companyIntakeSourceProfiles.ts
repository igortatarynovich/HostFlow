import { api } from './client'

export type CompanyIntakeSourceProfile = {
  id: string
  name: string
  tenant_id: string
  own_company_id: string
  own_company_name: string | null
  public_slug: string
  public_url_path: string
  lead_type: 'client'
  lead_target_type: 'client_lead'
  form_type: 'company_intake'
  source: string
  default_language: 'pl' | 'en' | 'ru'
  supported_languages: Array<'pl' | 'en' | 'ru'>
  default_assignee_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export type CompanyIntakeSourceProfileInput = {
  name: string
  own_company_id: string
  public_slug: string
  source: string
  default_language: 'pl' | 'en' | 'ru'
  supported_languages: Array<'pl' | 'en' | 'ru'>
  default_assignee_id?: string | null
  is_active: boolean
}

const BASE = '/settings/leads/company-intake-source-profiles'

export async function listCompanyIntakeSourceProfiles(): Promise<CompanyIntakeSourceProfile[]> {
  const { data } = await api.get<CompanyIntakeSourceProfile[]>(BASE)
  return data
}

export async function createCompanyIntakeSourceProfile(
  payload: CompanyIntakeSourceProfileInput,
): Promise<CompanyIntakeSourceProfile> {
  const { data } = await api.post<CompanyIntakeSourceProfile>(BASE, payload)
  return data
}

export async function patchCompanyIntakeSourceProfile(
  id: string,
  payload: Partial<CompanyIntakeSourceProfileInput>,
): Promise<CompanyIntakeSourceProfile> {
  const { data } = await api.patch<CompanyIntakeSourceProfile>(`${BASE}/${encodeURIComponent(id)}`, payload)
  return data
}
