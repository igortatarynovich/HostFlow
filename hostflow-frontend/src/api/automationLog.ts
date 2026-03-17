import { api } from './client'

export type AutomationLogEntry = {
  id: string
  tenant_id: string
  actor_id: string | null
  action: string
  target_type: string | null
  target_id: string | null
  payload: Record<string, unknown> | null
  created_at: string
}

export type AutomationLogListResponse = {
  items: AutomationLogEntry[]
  total: number
}

export type ListAutomationLogParams = {
  target_type?: string
  target_id?: string
  action_prefix?: string
  from?: string
  to?: string
  limit?: number
  offset?: number
}

export async function listAutomationLog(params?: ListAutomationLogParams): Promise<AutomationLogListResponse> {
  const q: Record<string, string | number> = {}
  if (params?.target_type) q.target_type = params.target_type
  if (params?.target_id) q.target_id = params.target_id
  if (params?.action_prefix) q.action_prefix = params.action_prefix
  if (params?.from) q.from = params.from
  if (params?.to) q.to = params.to
  if (params?.limit != null) q.limit = params.limit
  if (params?.offset != null) q.offset = params.offset
  const { data } = await api.get<AutomationLogListResponse>('/automation-log', { params: Object.keys(q).length ? q : undefined })
  return data
}

