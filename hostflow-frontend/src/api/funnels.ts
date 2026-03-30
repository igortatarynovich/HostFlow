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
  type: 'candidate' | 'lead' | 'deal'
  name: string
  is_default: boolean
  stages: FunnelStage[]
}

export interface FunnelCreate {
  type: 'candidate' | 'lead' | 'deal'
  name: string
  is_default?: boolean
}

export interface FunnelUpdate {
  type?: 'candidate' | 'lead' | 'deal'
  name?: string
  is_default?: boolean
}

export interface ListFunnelsOptions {
  type?: 'candidate' | 'lead' | 'deal'
}

export async function listFunnels(options?: ListFunnelsOptions): Promise<Funnel[]> {
  const params: Record<string, string> = {}
  if (options?.type) params.type = options.type

  const { data } = await api.get<Funnel[]>('/funnels', { params })
  return data
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
