import { api } from './client'

export type CandidateListAvailableStatuses = {
  schema_version: 1
  stages: string[]
  statuses: string[]
  vacancy_ids?: string[]
  assignee_ids?: string[]
}

/** Distinct ``stage`` / ``status`` column values for the tenant list scope (same ACL as ``GET /candidates``). */
export async function fetchCandidateListAvailableStatuses(params?: { scope_tenant_id?: string | null }) {
  const qs = params?.scope_tenant_id ? { scope_tenant_id: params.scope_tenant_id } : undefined
  const { data } = await api.get<CandidateListAvailableStatuses>('/candidates/available-statuses', { params: qs })
  return data
}
