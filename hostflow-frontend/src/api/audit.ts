import { api } from './client'

export type AuditEntry = {
  id: string
  tenant_id: string
  user_id: string | null
  user_label: string
  actor_id: string | null
  actor_label: string
  action: string
  payload: Record<string, unknown> | null
  created_at: string
}

export type AuditListResponse = {
  items: AuditEntry[]
  total: number
}

export type ListAuditParams = {
  user_id?: string
  action?: string
  from?: string
  to?: string
  limit?: number
  offset?: number
}

export async function listAudit(params?: ListAuditParams): Promise<AuditListResponse> {
  const q: Record<string, string | number> = {}
  if (params?.user_id) q.user_id = params.user_id
  if (params?.action) q.action = params.action
  if (params?.from) q.from = params.from
  if (params?.to) q.to = params.to
  if (params?.limit != null) q.limit = params.limit
  if (params?.offset != null) q.offset = params.offset
  const { data } = await api.get<AuditListResponse>('/admin/audit', {
    params: Object.keys(q).length ? q : undefined,
  })
  return data
}
