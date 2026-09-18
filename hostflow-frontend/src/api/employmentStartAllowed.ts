import { api } from './client'

export type StartAllowedPrimaryItem = {
  code: string
  kind?: string
  message?: string
}

export type EmploymentStartAllowedOut = {
  policy_id: string
  handoff_id?: string | null
  employee_id?: string | null
  linked_handoff_id?: string | null
  decision: string
  start_allowed: boolean
  required_actions?: StartAllowedPrimaryItem[]
  active_missing?: StartAllowedPrimaryItem[]
  primary_item?: StartAllowedPrimaryItem | null
  ui_primary_item?: StartAllowedPrimaryItem | null
  blockers?: Array<{ code?: string; message?: string }>
  rejection_reason?: string | null
  exceptions?: Array<Record<string, unknown>>
  employment_context?: Record<string, unknown> | null
  evidence_nav?: {
    documents_anchor?: string
    employee_documents_anchor?: string
    contract_preview_anchor?: string
  } | null
  authority_write_confirmed?: boolean | null
  planned_start_date?: string | null
  manual_override?: boolean
  llm_start_allowed?: boolean
  started?: boolean
}

export type EmploymentStartAllowedIn = {
  employment_context?: Record<string, unknown>
  resolution_patch?: Record<string, unknown>
}

export async function evaluateHandoffEmploymentStartAllowed(
  handoffId: string,
  body?: EmploymentStartAllowedIn,
) {
  const { data } = await api.post<EmploymentStartAllowedOut>(
    `/handoffs/${encodeURIComponent(handoffId)}/employment-start-allowed`,
    body || {},
  )
  return data
}

export async function applyHandoffEmploymentStartAllowed(
  handoffId: string,
  body: EmploymentStartAllowedIn,
) {
  const { data } = await api.post<EmploymentStartAllowedOut>(
    `/handoffs/${encodeURIComponent(handoffId)}/employment-start-allowed`,
    body,
  )
  return data
}
