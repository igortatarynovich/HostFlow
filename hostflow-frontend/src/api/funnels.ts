import { api } from './client'

/** §2.3 optional per-stage pipeline contract (stored as JSON on backend). */
export interface FunnelStageContractV1 {
  owner_role?: string | null
  required_actions?: string[] | null
  sla_hours?: number | null
  auto_rules?: Record<string, unknown> | null
}

export interface FunnelStage {
  id: string
  funnel_id: string
  code: string
  label: string
  system_stage: 'new' | 'in_progress' | 'hired' | 'declined_rejected'
  order: number
  is_terminal: boolean
  /** Lead funnels: §2.12 root bucket for conversion analytics. */
  conversion_root_v1?: string | null
  stage_contract?: FunnelStageContractV1 | null
}

export interface FunnelStageCreate {
  code: string
  label: string
  system_stage?: 'new' | 'in_progress' | 'hired' | 'declined_rejected'
  order?: number
  is_terminal?: boolean
  /** Lead funnels: send `null` on update to clear; omit on create to infer from code. */
  conversion_root_v1?: string | null
  /** Omit on create if unused; send `null` on update to clear. */
  stage_contract?: FunnelStageContractV1 | null
}

export interface Funnel {
  id: string
  tenant_id: string
  company_id?: string | null
  module_key?: string | null
  type: 'candidate' | 'lead' | 'deal' | 'employee'
  name: string
  is_default: boolean
  is_legacy_readonly?: boolean
  template_key?: string | null
  vacancy_usage_count?: number
  stages: FunnelStage[]
  transitions?: FunnelTransition[]
}

export interface FunnelTransition {
  id: string
  funnel_id: string
  catalog_key: string
  label: string
  from_stage_id?: string | null
  order: number
  config_json?: Record<string, unknown> | null
  locks_semantics?: boolean
}

export interface SystemTransitionCatalogItem {
  key: string
  label: string
  source_module: string
  source_object_type: string
  target_module?: string | null
  target_object_type?: string | null
  requires_enabled_module?: string | null
  locks_semantics: boolean
}

export interface FunnelCreate {
  company_id: string
  type: 'candidate' | 'lead' | 'deal' | 'employee'
  name: string
  is_default?: boolean
}

export interface FunnelUpdate {
  type?: 'candidate' | 'lead' | 'deal' | 'employee'
  name?: string
  is_default?: boolean
}

export interface ListFunnelsOptions {
  companyId: string
  type?: 'candidate' | 'lead' | 'deal' | 'employee'
  moduleKey?: string
}

export async function listFunnels(options: ListFunnelsOptions): Promise<Funnel[]> {
  const params: Record<string, string> = {
    company_id: options.companyId,
  }
  if (options.type) params.type = options.type
  if (options.moduleKey) params.module_key = options.moduleKey

  const { data } = await api.get<Funnel[]>('/funnels', { params })
  return (data || []).filter((f) => !f.is_legacy_readonly)
}

export async function getFunnel(funnelId: string): Promise<Funnel> {
  const { data } = await api.get<Funnel>(`/funnels/${funnelId}`)
  return data
}

export async function createFunnel(payload: FunnelCreate): Promise<Funnel> {
  const { data } = await api.post<Funnel>('/funnels', payload)
  return data
}

export async function updateFunnel(funnelId: string, payload: FunnelUpdate): Promise<Funnel> {
  const { data } = await api.patch<Funnel>(`/funnels/${funnelId}`, payload)
  return data
}

export async function deleteFunnel(funnelId: string): Promise<void> {
  await api.delete(`/funnels/${funnelId}`)
}

export async function addFunnelStage(
  funnelId: string,
  payload: FunnelStageCreate
): Promise<FunnelStage> {
  const { data } = await api.post<FunnelStage>(`/funnels/${funnelId}/stages`, payload)
  return data
}

export async function updateFunnelStage(
  funnelId: string,
  stageId: string,
  payload: FunnelStageCreate
): Promise<FunnelStage> {
  const { data } = await api.patch<FunnelStage>(
    `/funnels/${funnelId}/stages/${stageId}`,
    payload
  )
  return data
}

export async function deleteFunnelStage(funnelId: string, stageId: string): Promise<void> {
  await api.delete(`/funnels/${funnelId}/stages/${stageId}`)
}

export async function listSystemTransitionCatalog(params: {
  sourceModule: string
  sourceObjectType: string
  enabledModules?: string[]
}): Promise<SystemTransitionCatalogItem[]> {
  const q: Record<string, string> = {
    source_module: params.sourceModule,
    source_object_type: params.sourceObjectType,
  }
  if (params.enabledModules?.length) {
    q.enabled_modules = params.enabledModules.join(',')
  }
  const { data } = await api.get<SystemTransitionCatalogItem[]>('/funnels/meta/system-transitions', {
    params: q,
  })
  return data || []
}

export async function addFunnelTransition(
  funnelId: string,
  payload: { catalog_key: string; from_stage_id?: string | null; order?: number; config_json?: Record<string, unknown> },
): Promise<FunnelTransition> {
  const { data } = await api.post<FunnelTransition>(`/funnels/${funnelId}/transitions`, payload)
  return data
}

export async function deleteFunnelTransition(funnelId: string, transitionId: string): Promise<void> {
  await api.delete(`/funnels/${funnelId}/transitions/${transitionId}`)
}
