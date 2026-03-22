import type { AxiosInstance } from 'axios'
import http from './http'
import { withTenant } from './client'
import type {
  PlatformTenant,
  PlatformTenantCreatePayload,
  PlatformTenantListResponse,
  PlatformTenantUpdatePayload,
  SeatRequest,
  SeatRequestCreatePayload,
  SeatRequestDecisionPayload,
  TeamOverviewResponse,
  TenantAdminInput,
  TenantAdminResponse,
  TenantBrandingPayload,
  TenantBrandingResponse,
  TenantRoleModuleMatrix,
  TenantRoleModuleMatrixPatch,
  EffectiveRoleModules,
  TenantModuleOverrideUser,
  TenantUserModuleOverrides,
  TenantUserModuleOverridesPatch,
  TenantImpersonationToken,
  TenantLicensePatchInput,
  TenantModuleSettings,
  TenantModuleSettingsPatch,
  TenantRecord,
  TenantStatus,
  TenantStatusChangePayload,
  TenantType,
  TenantVacancyAccessListResponse,
  TenantVacancyAccessUpdatePayload,
  TenantVacancyOption,
  HiringPipelineGatesPublic,
  HiringPipelineGatesPatch,
} from './types'

export type PlatformTenantFilters = {
  status?: TenantStatus[]
  tenantType?: TenantType[]
  plan?: string[]
  search?: string
  limit?: number
  offset?: number
}

export async function listPlatformTenants(params: PlatformTenantFilters = {}) {
  const query: Record<string, any> = {}
  if (params.status?.length) query.status = params.status
  if (params.tenantType?.length) query.tenant_type = params.tenantType
  if (params.plan?.length) query.plan = params.plan
  if (params.search) query.search = params.search
  if (typeof params.limit === 'number') query.limit = params.limit
  if (typeof params.offset === 'number') query.offset = params.offset

  const { data } = await http.get<PlatformTenantListResponse>('/platform/tenants', { params: query })
  return data
}

export async function getPlatformTenant(tenantId: string) {
  const { data } = await http.get<PlatformTenant>(`/platform/tenants/${tenantId}`)
  return data
}

export async function createPlatformTenant(payload: PlatformTenantCreatePayload) {
  const { data } = await http.post<PlatformTenant>('/platform/tenants', payload)
  return data
}

export async function updatePlatformTenantMetadata(tenantId: string, payload: PlatformTenantUpdatePayload) {
  const { data } = await http.patch<PlatformTenant>(`/platform/tenants/${tenantId}`, payload)
  return data
}

export async function updatePlatformTenantLicense(tenantId: string, payload: TenantLicensePatchInput) {
  const { data } = await http.patch<PlatformTenant>(`/platform/tenants/${tenantId}/license`, payload)
  return data
}

export async function uploadPlatformTenantLogo(tenantId: string, file: File | Blob) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<PlatformTenant>(`/platform/tenants/${tenantId}/logo`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getPlatformTenantModules(tenantId: string) {
  const { data } = await http.get<TenantModuleSettings>(`/platform/tenants/${tenantId}/modules`)
  return data
}

export async function updatePlatformTenantModules(tenantId: string, payload: TenantModuleSettingsPatch) {
  const { data } = await http.patch<TenantModuleSettings>(`/platform/tenants/${tenantId}/modules`, payload)
  return data
}

export async function getPlatformTenantRoleModuleMatrix(tenantId: string) {
  const { data } = await http.get<TenantRoleModuleMatrix>(`/platform/tenants/${tenantId}/module-matrix`)
  return data
}

export async function updatePlatformTenantRoleModuleMatrix(
  tenantId: string,
  payload: TenantRoleModuleMatrixPatch,
) {
  const { data } = await http.patch<TenantRoleModuleMatrix>(`/platform/tenants/${tenantId}/module-matrix`, payload)
  return data
}

export async function listPlatformTenantModuleOverrideUsers(tenantId: string) {
  const { data } = await http.get<TenantModuleOverrideUser[]>(
    `/platform/tenants/${tenantId}/module-overrides/users`,
  )
  return data
}

export async function getPlatformTenantUserModuleOverrides(tenantId: string) {
  const { data } = await http.get<TenantUserModuleOverrides>(`/platform/tenants/${tenantId}/module-overrides`)
  return data
}

export async function updatePlatformTenantUserModuleOverrides(
  tenantId: string,
  payload: TenantUserModuleOverridesPatch,
) {
  const { data } = await http.patch<TenantUserModuleOverrides>(
    `/platform/tenants/${tenantId}/module-overrides`,
    payload,
  )
  return data
}

export async function listPlatformSeatRequests(tenantId: string, params: { status?: string } = {}) {
  const { data } = await http.get<SeatRequest[]>(`/platform/tenants/${tenantId}/seat-requests`, {
    params,
  })
  return data
}

export async function decidePlatformSeatRequest(
  tenantId: string,
  requestId: string,
  payload: SeatRequestDecisionPayload,
) {
  const { data } = await http.post<SeatRequest>(
    `/platform/tenants/${tenantId}/seat-requests/${requestId}/decision`,
    payload,
  )
  return data
}

export async function changePlatformTenantStatus(tenantId: string, payload: TenantStatusChangePayload) {
  const { data } = await http.post<PlatformTenant>(`/platform/tenants/${tenantId}/suspend`, payload)
  return data
}

export async function impersonatePlatformTenant(tenantId: string) {
  const { data } = await http.post<TenantImpersonationToken>(`/platform/tenants/${tenantId}/impersonate`)
  return data
}

export async function listTenantVacancyAccess(tenantId: string) {
  const { data } = await http.get<TenantVacancyAccessListResponse>(`/platform/tenants/${tenantId}/vacancies`)
  return data
}

export async function updateTenantVacancyAccess(tenantId: string, vacancyIds: string[]) {
  const payload: TenantVacancyAccessUpdatePayload = { vacancy_ids: vacancyIds }
  const { data } = await http.put<TenantVacancyAccessListResponse>(`/platform/tenants/${tenantId}/vacancies`, payload)
  return data
}

export async function listTenantVacancyOptions(tenantId: string, params: { search?: string; limit?: number } = {}) {
  const query: Record<string, any> = {}
  if (params.search) query.search = params.search
  if (typeof params.limit === 'number') query.limit = params.limit
  const { data } = await http.get<TenantVacancyOption[]>(`/platform/tenants/${tenantId}/vacancy-options`, {
    params: query,
  })
  return data
}

export async function getCurrentTenant() {
  const { data } = await http.get<{ tenant: TenantRecord }>('/tenants/me')
  return data.tenant
}

function resolveTenantClient(tenantId?: string) {
  return tenantId ? withTenant(tenantId) : http
}

const HIRING_GATES_PRIMARY = '/settings/team/hiring-pipeline-gates'
const HIRING_GATES_FALLBACK = '/tenants/me/hiring-pipeline-gates'

/** Same handler on backend; fallback helps if an older proxy only routes `/tenants/*`. */
async function getHiringPipelineGatesWithFallback(
  client: AxiosInstance,
): Promise<HiringPipelineGatesPublic | null> {
  const primary = await client.get<HiringPipelineGatesPublic>(HIRING_GATES_PRIMARY, {
    validateStatus: (s) => s === 200 || s === 404,
  })
  if (primary.status === 200) return primary.data
  if (primary.status !== 404) {
    const err: any = new Error(`GET hiring-pipeline-gates failed: ${primary.status}`)
    err.response = primary
    throw err
  }
  const fb = await client.get<HiringPipelineGatesPublic>(HIRING_GATES_FALLBACK, {
    validateStatus: (s) => s === 200 || s === 404,
  })
  if (fb.status === 200) return fb.data
  return null
}

async function patchHiringPipelineGatesWithFallback(
  client: AxiosInstance,
  payload: HiringPipelineGatesPatch,
): Promise<HiringPipelineGatesPublic> {
  try {
    const { data } = await client.patch<HiringPipelineGatesPublic>(HIRING_GATES_PRIMARY, payload)
    return data
  } catch (e: any) {
    if (e?.response?.status !== 404) throw e
    const { data } = await client.patch<HiringPipelineGatesPublic>(HIRING_GATES_FALLBACK, payload)
    return data
  }
}

export async function getTeamOverview(opts?: { tenantId?: string }) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.get<TeamOverviewResponse>('/settings/team')
  return data
}

export async function getTenantModules(opts?: { tenantId?: string }) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.get<TenantModuleSettings>('/settings/team/modules')
  return data
}

export async function getHiringPipelineGates(opts?: { tenantId?: string }) {
  const client = resolveTenantClient(opts?.tenantId)
  return getHiringPipelineGatesWithFallback(client)
}

export async function patchHiringPipelineGates(
  payload: HiringPipelineGatesPatch,
  opts?: { tenantId?: string },
) {
  const client = resolveTenantClient(opts?.tenantId)
  return patchHiringPipelineGatesWithFallback(client, payload)
}

export type VacancyRequirementsPreset = {
  id: string
  label: string
  criteria: Record<string, any>
  updated_at?: string | null
}

export async function listVacancyRequirementsPresets(opts?: { tenantId?: string }) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.get<{ items: VacancyRequirementsPreset[] }>('/settings/team/vacancy-requirements-presets')
  return Array.isArray(data?.items) ? data.items : []
}

export async function upsertVacancyRequirementsPreset(
  preset: { id: string; label: string; criteria: Record<string, any> },
  opts?: { tenantId?: string },
) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.put<{ items: VacancyRequirementsPreset[] }>(
    `/settings/team/vacancy-requirements-presets/${preset.id}`,
    preset,
  )
  return Array.isArray(data?.items) ? data.items : []
}

export async function deleteVacancyRequirementsPreset(presetId: string, opts?: { tenantId?: string }) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.delete<{ items: VacancyRequirementsPreset[] }>(
    `/settings/team/vacancy-requirements-presets/${presetId}`,
  )
  return Array.isArray(data?.items) ? data.items : []
}

export async function updateTenantModules(
  payload: TenantModuleSettingsPatch,
  opts?: { tenantId?: string },
) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.patch<TenantModuleSettings>('/settings/team/modules', payload)
  return data
}

export async function getTenantEffectiveRoleModules(opts?: { tenantId?: string }) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.get<EffectiveRoleModules>('/settings/team/module-matrix/effective')
  return data
}

export async function listSeatRequests(opts?: { tenantId?: string }) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.get<SeatRequest[]>('/settings/team/seat-requests')
  return data
}

export async function createSeatRequest(
  payload: SeatRequestCreatePayload,
  opts?: { tenantId?: string },
) {
  const client = resolveTenantClient(opts?.tenantId)
  const { data } = await client.post<SeatRequest>('/settings/team/seat-requests', payload)
  return data
}

export async function createTenantAdmin(tenantId: string, payload: TenantAdminInput) {
  const { data } = await http.post<TenantAdminResponse>(`/platform/tenants/${tenantId}/admins`, payload)
  return data
}

export async function updateTenantBranding(payload: TenantBrandingPayload) {
  const { data } = await http.patch<TenantBrandingResponse>('/settings/team/branding', payload)
  return data
}

export async function uploadTenantBrandingLogo(file: File | Blob) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<TenantBrandingResponse>('/settings/team/branding/logo', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
