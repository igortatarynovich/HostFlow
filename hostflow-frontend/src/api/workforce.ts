import http from './http'
import { normalizeDocument } from './documents/normalize'
import type { Document } from './types'

export type WorkforceEmployee = {
  id: string
  tenant_id: string
  own_company_id?: string | null
  candidate_id?: string | null
  company_id?: string | null
  vacancy_id?: string | null
  recruiter_user_id?: string | null
  display_name: string
  status: string
  hire_date?: string | null
  probation_end?: string | null
  termination_date?: string | null
  handoff_at?: string | null
  handoff_by_user_id?: string | null
  notes?: string | null
  candidate_snapshot?: Record<string, unknown> | null
  meta?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type WorkforceEmployeeCreate = {
  display_name: string
  status?: string
  own_company_id?: string | null
  company_id?: string | null
  candidate_id?: string | null
  vacancy_id?: string | null
  recruiter_user_id?: string | null
  candidate_snapshot?: Record<string, unknown> | null
  hire_date?: string | null
  probation_end?: string | null
  notes?: string | null
  meta?: Record<string, unknown> | null
}

export type WorkforceEmployment = {
  id: string
  employee_id: string
  contract_type: string
  rate_model?: Record<string, unknown> | null
  schedule?: Record<string, unknown> | null
  start_date?: string | null
  end_date?: string | null
  conditions_text?: string | null
  vacancy_id?: string | null
  meta?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type WorkforcePayrollProfile = {
  id: string
  employee_id: string
  pay_type: string
  base_rate?: string | null
  currency?: string | null
  calculation_system?: string | null
  pay_day_note?: string | null
  bank_account?: string | null
  tax_status?: string | null
  pit_declarations?: Record<string, unknown> | null
  allowances?: Record<string, unknown> | null
  deductions?: Record<string, unknown> | null
  payroll_status: string
  external_refs?: Record<string, unknown> | null
  meta?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type WorkforceZusProfile = {
  id: string
  employee_id: string
  registration_status: string
  submitted_at?: string | null
  employment_basis?: string | null
  responsible_party?: string | null
  insurance_coverage?: Record<string, unknown> | null
  forms?: unknown[] | null
  meta?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type WorkforceOnboardingTask = {
  id: string
  employee_id: string
  title: string
  sort_order: number
  status: string
  due_at?: string | null
  completed_at?: string | null
  assignee_user_id?: string | null
  meta?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type WorkforceAbsence = {
  id: string
  employee_id: string
  absence_type: string
  start_date: string
  end_date?: string | null
  source: string
  status: string
  payer?: string | null
  payroll_impact?: string | null
  comment?: string | null
  meta?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type WorkforceLeaveRequest = {
  id: string
  employee_id: string
  leave_type: string
  start_date: string
  end_date: string
  status: string
  year_entitlement_days?: string | null
  used_days_before?: string | null
  conflict_flags?: Record<string, unknown> | null
  approver_user_id?: string | null
  decided_at?: string | null
  comment?: string | null
  meta?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type WorkforceHrBundle = {
  employments: WorkforceEmployment[]
  payroll_profile: WorkforcePayrollProfile | null
  zus_profile: WorkforceZusProfile | null
  onboarding_tasks: WorkforceOnboardingTask[]
  absences: WorkforceAbsence[]
  leave_requests: WorkforceLeaveRequest[]
}

export async function listWorkforceEmployees(params?: { status?: string }): Promise<WorkforceEmployee[]> {
  const { data } = await http.get<WorkforceEmployee[]>('/workforce/employees', { params })
  return data
}

export async function getWorkforceEmployee(id: string): Promise<WorkforceEmployee> {
  const { data } = await http.get<WorkforceEmployee>(`/workforce/employees/${encodeURIComponent(id)}`)
  return data
}

export async function createWorkforceEmployee(payload: WorkforceEmployeeCreate): Promise<WorkforceEmployee> {
  const { data } = await http.post<WorkforceEmployee>('/workforce/employees', payload)
  return data
}

export async function patchWorkforceEmployee(
  id: string,
  payload: Partial<WorkforceEmployeeCreate> & { termination_date?: string | null },
): Promise<WorkforceEmployee> {
  const { data } = await http.patch<WorkforceEmployee>(`/workforce/employees/${encodeURIComponent(id)}`, payload)
  return data
}

export async function getWorkforceHrBundle(employeeId: string): Promise<WorkforceHrBundle> {
  const { data } = await http.get<WorkforceHrBundle>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/hr-bundle`,
  )
  return data
}

/** Row from GET `/workforce/employees/:id/documents` (CandDoc-shaped JSON). */
export type WorkforceEmployeeDocumentRow = {
  document: Document
  /** Presigned or API download URL when present. */
  downloadUrl: string | null
  /** From API `days_left` when present. */
  daysLeft: number | null
}

function pickCandDocDownloadUrl(raw: Record<string, unknown>): string | null {
  const top = raw.file_url
  if (typeof top === 'string' && top.trim()) return top.trim()
  const list = raw.file_list
  if (Array.isArray(list)) {
    for (const item of list) {
      if (item && typeof item === 'object') {
        const u = (item as Record<string, unknown>).url
        if (typeof u === 'string' && u.trim()) return u.trim()
      }
    }
  }
  const files = raw.files
  if (files && typeof files === 'object' && !Array.isArray(files)) {
    for (const v of Object.values(files)) {
      if (v && typeof v === 'object') {
        const u = (v as Record<string, unknown>).url
        if (typeof u === 'string' && u.trim()) return u.trim()
      }
    }
  }
  return null
}

export async function listWorkforceEmployeeDocuments(
  employeeId: string,
): Promise<WorkforceEmployeeDocumentRow[]> {
  const { data } = await http.get<Array<Record<string, unknown>>>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/documents`,
  )
  return (data || []).map((raw) => {
    const doc = normalizeDocument(raw)
    let downloadUrl = pickCandDocDownloadUrl(raw)
    if (!downloadUrl && Array.isArray(doc.files)) {
      const u = doc.files[0]?.url
      if (typeof u === 'string' && u.trim()) downloadUrl = u.trim()
    }
    const dl = raw.days_left
    const daysLeft = typeof dl === 'number' && Number.isFinite(dl) ? dl : null
    return { document: doc, downloadUrl, daysLeft }
  })
}

export async function patchWorkforcePayrollProfile(
  employeeId: string,
  payload: Partial<Omit<WorkforcePayrollProfile, 'id' | 'employee_id' | 'created_at' | 'updated_at'>>,
): Promise<WorkforcePayrollProfile> {
  const { data } = await http.patch<WorkforcePayrollProfile>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/payroll-profile`,
    payload,
  )
  return data
}

export async function patchWorkforceZusProfile(
  employeeId: string,
  payload: Partial<Omit<WorkforceZusProfile, 'id' | 'employee_id' | 'created_at' | 'updated_at'>>,
): Promise<WorkforceZusProfile> {
  const { data } = await http.patch<WorkforceZusProfile>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/zus-profile`,
    payload,
  )
  return data
}

export async function createWorkforceEmployment(
  employeeId: string,
  payload: Partial<Omit<WorkforceEmployment, 'id' | 'employee_id' | 'created_at' | 'updated_at'>>,
): Promise<WorkforceEmployment> {
  const { data } = await http.post<WorkforceEmployment>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/employments`,
    payload,
  )
  return data
}

export async function patchWorkforceEmployment(
  employmentId: string,
  payload: Partial<Omit<WorkforceEmployment, 'id' | 'employee_id' | 'created_at' | 'updated_at'>>,
): Promise<WorkforceEmployment> {
  const { data } = await http.patch<WorkforceEmployment>(
    `/workforce/employments/${encodeURIComponent(employmentId)}`,
    payload,
  )
  return data
}

export async function patchWorkforceOnboardingTask(
  taskId: string,
  payload: Partial<
    Pick<
      WorkforceOnboardingTask,
      'title' | 'sort_order' | 'status' | 'due_at' | 'completed_at' | 'assignee_user_id' | 'meta'
    >
  >,
): Promise<WorkforceOnboardingTask> {
  const { data } = await http.patch<WorkforceOnboardingTask>(
    `/workforce/onboarding-tasks/${encodeURIComponent(taskId)}`,
    payload,
  )
  return data
}

export async function createWorkforceAbsence(
  employeeId: string,
  payload: Pick<WorkforceAbsence, 'absence_type' | 'start_date'> &
    Partial<
      Omit<WorkforceAbsence, 'id' | 'employee_id' | 'absence_type' | 'start_date' | 'created_at' | 'updated_at'>
    >,
): Promise<WorkforceAbsence> {
  const { data } = await http.post<WorkforceAbsence>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/absences`,
    payload,
  )
  return data
}

export async function patchWorkforceAbsence(
  absenceId: string,
  payload: Partial<
    Omit<WorkforceAbsence, 'id' | 'employee_id' | 'created_at' | 'updated_at'>
  >,
): Promise<WorkforceAbsence> {
  const { data } = await http.patch<WorkforceAbsence>(
    `/workforce/absences/${encodeURIComponent(absenceId)}`,
    payload,
  )
  return data
}

export async function createWorkforceLeaveRequest(
  employeeId: string,
  payload: Pick<WorkforceLeaveRequest, 'leave_type' | 'start_date' | 'end_date'> &
    Partial<
      Omit<
        WorkforceLeaveRequest,
        'id' | 'employee_id' | 'leave_type' | 'start_date' | 'end_date' | 'created_at' | 'updated_at'
      >
    >,
): Promise<WorkforceLeaveRequest> {
  const { data } = await http.post<WorkforceLeaveRequest>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/leave-requests`,
    payload,
  )
  return data
}

export async function patchWorkforceLeaveRequest(
  leaveId: string,
  payload: Partial<
    Omit<WorkforceLeaveRequest, 'id' | 'employee_id' | 'created_at' | 'updated_at'>
  >,
): Promise<WorkforceLeaveRequest> {
  const { data } = await http.patch<WorkforceLeaveRequest>(
    `/workforce/leave-requests/${encodeURIComponent(leaveId)}`,
    payload,
  )
  return data
}

export async function handoffFromCandidate(
  candidateId: string,
  body: { hire_date?: string | null } = {},
): Promise<WorkforceEmployee> {
  const { data } = await http.post<WorkforceEmployee>(
    `/workforce/employees/from-candidate/${encodeURIComponent(candidateId)}`,
    body,
  )
  return data
}
