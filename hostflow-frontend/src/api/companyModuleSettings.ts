import { api } from './client'

export type CompanyModuleKey = 'recruitment' | 'hr' | 'fleet' | 'services' | 'finance'

export type CompanyModuleSettingsDTO = {
  id: string
  tenant_id: string
  company_id: string
  module_key: string
  settings_json: Record<string, unknown>
  is_enabled: boolean
  configured_at: string | null
  created_at: string
  updated_at: string
}

export async function getCompanyModuleSettings(
  companyId: string,
  moduleKey: CompanyModuleKey,
): Promise<CompanyModuleSettingsDTO> {
  const { data } = await api.get<CompanyModuleSettingsDTO>(
    `/companies/${encodeURIComponent(companyId)}/module-settings/${encodeURIComponent(moduleKey)}`,
  )
  return data
}

export async function listCompanyModuleSettings(companyId: string): Promise<CompanyModuleSettingsDTO[]> {
  const { data } = await api.get<CompanyModuleSettingsDTO[]>(
    `/companies/${encodeURIComponent(companyId)}/module-settings`,
  )
  return Array.isArray(data) ? data : []
}

export async function patchCompanyModuleSettings(
  companyId: string,
  moduleKey: CompanyModuleKey,
  body: { settings_json?: Record<string, unknown>; is_enabled?: boolean },
): Promise<CompanyModuleSettingsDTO> {
  const { data } = await api.patch<CompanyModuleSettingsDTO>(
    `/companies/${encodeURIComponent(companyId)}/module-settings/${encodeURIComponent(moduleKey)}`,
    body,
  )
  return data
}
