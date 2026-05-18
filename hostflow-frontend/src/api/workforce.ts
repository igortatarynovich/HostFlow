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

/** PR-1/2: legal tax row (not payroll calculation). */
export type WorkforceTaxProfile = {
  id: string
  tenant_id: string
  employee_id: string
  tax_residency_country?: string | null
  tax_office?: string | null
  pit2_submitted: boolean
  pit2_monthly_amount?: string | number | null
  tax_deductible_costs_type?: string | null
  young_person_relief: boolean
  created_at: string
  updated_at: string
}

/** PR-1/2: social / ZUS legal materialisation (distinct from `zus_profile` registration row). */
export type WorkforceInsuranceProfile = {
  id: string
  tenant_id: string
  employee_id: string
  zus_title_code?: string | null
  social_insurance?: string | null
  health_insurance?: string | null
  sickness_insurance?: string | null
  accident_insurance?: string | null
  zus_registration_type?: string | null
  registered_at?: string | null
  deregistered_at?: string | null
  status: string
  created_at: string
  updated_at: string
}

export type WorkforceComplianceState = {
  id: string
  tenant_id: string
  employee_id: string
  status: string
  missing_count: number
  expired_count: number
  expiring_soon_count: number
  high_risk_count: number
  cannot_work: boolean
  last_evaluated_at?: string | null
  reasons?: unknown
  created_at: string
  updated_at: string
}

export type WorkforceHrDocumentContextRow = {
  id: string
  tenant_id: string
  employee_id: string
  document_id: string
  context_type: string
  legal_category?: string | null
  document_group?: string | null
  required: boolean
  verified: boolean
  verification_status?: string | null
  expires_at?: string | null
  source?: string | null
  created_at: string
  updated_at: string
}

export type WorkforceHrDocumentContextSummary = {
  total: number
  by_context_type: Record<string, number>
  items: WorkforceHrDocumentContextRow[]
}

export type WorkforceWorkEligibilityProfile = {
  id: string
  tenant_id: string
  employee_id: string
  citizenship?: string | null
  residence_status?: string | null
  legal_stay_document_type?: string | null
  legal_stay_valid_to?: string | null
  requires_work_permit?: boolean | null
  work_permit_type?: string | null
  work_permit_submission_method?: string | null
  work_permit_application_status?: string | null
  work_permit_submitted_at?: string | null
  work_permit_received_at?: string | null
  work_permit_valid_to?: string | null
  red_paper_required?: boolean | null
  red_paper_status?: string | null
  eligibility_status: string
  position_category?: string | null
  work_country?: string | null
  employer_country?: string | null
  contract_type?: string | null
  meta?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type WorkforceWorkEligibilityPaymentRequirement = {
  id: string
  tenant_id: string
  employee_id: string
  requirement_type: string
  amount?: string | null
  currency: string
  payment_status: string
  due_at?: string | null
  paid_at?: string | null
  payment_reference?: string | null
  receipt_document_id?: string | null
  blocks_step?: string | null
  created_at: string
  updated_at: string
}

export type JourneyAction = {
  code: string
  label: string
  href?: string | null
  document_type?: string | null
  payment_requirement_id?: string | null
}

export type WorkEligibilityJourneyStep = {
  step_code: string
  label: string
  status: string
  blockers: string[]
  required_documents: string[]
  linked_payment_requirement_id?: string | null
  linked_document_id?: string | null
  action_label?: string | null
  action_url?: string | null
  external_submission_url?: string | null
  decision_reason?: string | null
  rule_code?: string | null
  input_facts?: Record<string, unknown> | null
  confidence?: number | null
  cannot_determine_reason?: string | null
  primary_action?: JourneyAction | null
  secondary_actions?: JourneyAction[]
  document_actions?: JourneyAction[]
  payment_actions?: JourneyAction[]
}

export type NextHrAction = {
  title: string
  step_code?: string | null
  step_status?: string | null
  reason?: string | null
  blockers: string[]
  cannot_determine_reason?: string | null
  primary_cta?: JourneyAction | null
  secondary_ctas: JourneyAction[]
}

export type WorkEligibilityJourney = {
  steps: WorkEligibilityJourneyStep[]
  recommended_next_action: string
  next_hr_action?: NextHrAction | null
}

export type HrReviewChecklistItem = {
  item_code: string
  label: string
  status: string
  source: string
  required: boolean
  blockers: string[]
  basis: Record<string, unknown>
  verified_by_user_id?: string | null
  verified_at?: string | null
}

export type HrDocumentFieldReview = {
  field_code: string
  label: string
  downstream_use?: string[]
  current_profile_values?: Record<string, unknown>
  needs_manual_confirmation?: boolean
  reviewed_value?: unknown
  review_comment?: string | null
  confirmed?: boolean
}

export type HrDocumentVerificationActions = {
  can_open?: boolean
  can_verify?: boolean
  can_reject?: boolean
  can_request_correction?: boolean
}

export type HrReviewDocumentRow = {
  document_key: string
  label: string
  status: string
  context_type?: string | null
  document_id?: string | null
  verified: boolean
  expires_at?: string | null
  basis?: string | null
  open_url?: string | null
  file_url?: string | null
  document_open_context?: string | null
  document_type?: string | null
  required?: boolean
  verification_status?: string | null
  verification_id?: string | null
  linked_checklist_item?: string | null
  fields_to_review?: HrDocumentFieldReview[]
  reviewed_fields?: Record<string, unknown>
  rejection_reason?: string | null
  correction_note?: string | null
  actions?: HrDocumentVerificationActions | null
}

export type HrReviewProcessStage = {
  code: string
  label: string
  state: 'done' | 'current' | 'blocked' | 'pending' | 'skipped' | string
}

export type HrReviewHero = {
  candidate_display_name?: string | null
  handoff_id?: string | null
  handoff_status?: string | null
  review_status: string
  vacancy_label?: string | null
  transferred_at?: string | null
  transferred_by?: string | null
  employee_status?: string | null
  has_employee?: boolean
  current_stage_code?: string | null
  current_stage_label?: string | null
  state_message?: string
  process_stages?: HrReviewProcessStage[]
}

export type HrReviewNextAction = {
  title: string
  reason?: string
  blockers?: string[]
  primary_label?: string | null
  primary_anchor?: string | null
  secondary_label?: string | null
  secondary_anchor?: string | null
}

export type HrReviewDecisionReadiness = {
  checklist_done: number
  checklist_total: number
  can_approve: boolean
  approve_blocked_reason?: string | null
  post_approve_effects?: string[]
}

export type HrReviewTimelineEvent = {
  at?: string | null
  kind: string
  label: string
}

export type HrReviewEligibilitySummary = {
  current_step_code?: string | null
  current_step_title?: string | null
  current_step_status?: string | null
  recommended_next_action?: string | null
  blockers?: string[]
  decision_basis?: Record<string, unknown> | null
}

export type HrReviewTaskAction = {
  label: string
  anchor?: string | null
}

export type HrReviewRelatedDocument = {
  document_key?: string | null
  document_id?: string | null
  label?: string | null
  status?: string | null
}

export type HrReviewTaskPriorityStep = {
  step: number
  task_type: string
  label: string
  summary?: string
  state?: string
}

export type HrReviewCurrentTask = {
  task_type: string
  title: string
  description: string
  why: string
  priority: string
  priority_step?: number
  priority_total?: number
  priority_catalog_label?: string | null
  blocks_approval: boolean
  primary_action: HrReviewTaskAction
  secondary_actions?: HrReviewTaskAction[]
  target_anchor?: string | null
  related_documents?: HrReviewRelatedDocument[]
  related_checklist_items?: string[]
  completion_condition: string
}

export type HrReviewPanel = {
  review_id: string
  employee_id?: string | null
  candidate_id?: string | null
  handoff_id?: string | null
  status: string
  checklist: HrReviewChecklistItem[]
  blockers: string[]
  failed_required_items: string[]
  can_approve: boolean
  next_required_action?: string | null
  decision_basis?: Record<string, unknown> | null
  documents_for_approval: HrReviewDocumentRow[]
  corrections_note?: string | null
  return_reason?: string | null
  reject_reason?: string | null
  decided_by_user_id?: string | null
  decided_at?: string | null
  mode?: 'hr_review_case' | 'employee_profile' | string | null
  hero?: HrReviewHero | null
  next_action?: HrReviewNextAction | null
  decision_readiness?: HrReviewDecisionReadiness | null
  recent_timeline?: HrReviewTimelineEvent[]
  work_eligibility_summary?: HrReviewEligibilitySummary | null
  current_task?: HrReviewCurrentTask | null
  task_priority_v1?: HrReviewTaskPriorityStep[]
}

export type WorkforceHrBundle = {
  employments: WorkforceEmployment[]
  payroll_profile: WorkforcePayrollProfile | null
  zus_profile: WorkforceZusProfile | null
  onboarding_tasks: WorkforceOnboardingTask[]
  absences: WorkforceAbsence[]
  leave_requests: WorkforceLeaveRequest[]
  tax_profile: WorkforceTaxProfile | null
  insurance_profile: WorkforceInsuranceProfile | null
  compliance_state: WorkforceComplianceState | null
  work_eligibility_profile: WorkforceWorkEligibilityProfile | null
  work_eligibility_payment_requirements: WorkforceWorkEligibilityPaymentRequirement[]
  hr_document_context_summary: WorkforceHrDocumentContextSummary
}

/** GET `/workforce/employees/:id/operational-profile` (HR workspace read-model). */
export type WorkforceOperationalSummary = {
  employee_status: string
  full_name: string
  employer?: string | null
  client?: string | null
  position?: string | null
  start_date?: string | null
  probation_end?: string | null
  assigned_hr?: string | null
  assigned_hr_user_id?: string | null
  handoff_id?: string | null
  compliance_status: string
  missing_documents_count: number
  expiring_documents_count: number
  risk_level: string
}

export type WorkforceTransferMetadata = {
  handoff_id?: string | null
  handoff_at?: string | null
  handoff_by_user_id?: string | null
  handoff_by_name?: string | null
  candidate_id?: string | null
  vacancy_id?: string | null
}

export type WorkforceRecruiterSummary = {
  captured_at?: string | null
  candidate_id?: string | null
  first_name?: string | null
  last_name?: string | null
  email?: string | null
  phone?: string | null
  stage?: string | null
  status?: string | null
}

export type WorkforceProfileAlert = { code: string; message: string }

export type WorkforceTimelineEvent = {
  id: string
  occurred_at: string
  kind: string
  title: string
  detail?: string | null
  actor_id?: string | null
}

export type WorkforceEmploymentOperational = {
  id: string
  contract_type: string
  start_date?: string | null
  end_date?: string | null
  is_active: boolean
  probation_end?: string | null
  position?: string | null
}

export type WorkforceEmployeeOperationalProfile = {
  employee: WorkforceEmployee
  operational_summary: WorkforceOperationalSummary
  transfer: WorkforceTransferMetadata
  recruiter_summary: WorkforceRecruiterSummary
  documents_linked: Array<Record<string, unknown>>
  documents_missing: Array<Record<string, unknown>>
  documents_expiring: Array<Record<string, unknown>>
  risks: Array<Record<string, unknown>>
  alerts: WorkforceProfileAlert[]
  onboarding_overdue_count: number
  timeline: WorkforceTimelineEvent[]
  employment_operational: WorkforceEmploymentOperational[]
  hire_snapshot: Record<string, unknown> | null
  hr_bundle: WorkforceHrBundle
}

export async function listWorkforceEmployees(params?: { status?: string }): Promise<WorkforceEmployee[]> {
  const { data } = await http.get<WorkforceEmployee[]>('/workforce/employees', { params })
  return data
}

/** Read-model: GET `/workforce/employees/directory` (single batch for HR directory UI). */
export type WorkforceEmployeeDirectoryRow = {
  employee_id: string
  full_name: string
  status: string
  employer?: string | null
  client?: string | null
  position?: string | null
  start_date?: string | null
  assigned_hr?: string | null
  assigned_hr_user_id?: string | null
  handoff_id?: string | null
  candidate_id?: string | null
  compliance_status: string
  missing_documents_count: number
  expiring_documents_count: number
  risk_level: string
}

export type WorkforceEmployeeDirectoryPage = {
  items: WorkforceEmployeeDirectoryRow[]
  total: number
}

export async function listWorkforceEmployeesDirectory(params?: {
  status?: string
  compliance_status?: string
  risk_level?: string
  missing_docs?: boolean
  expiring_docs?: boolean
  search?: string
  limit?: number
  offset?: number
}): Promise<WorkforceEmployeeDirectoryPage> {
  const { data } = await http.get<WorkforceEmployeeDirectoryPage>('/workforce/employees/directory', {
    params: {
      status: params?.status || undefined,
      compliance_status: params?.compliance_status || undefined,
      risk_level: params?.risk_level || undefined,
      missing_docs: params?.missing_docs === true ? true : undefined,
      expiring_docs: params?.expiring_docs === true ? true : undefined,
      search: params?.search?.trim() || undefined,
      limit: params?.limit,
      offset: params?.offset,
    },
  })
  return data
}

export async function getWorkforceEmployeeOperationalProfile(
  employeeId: string,
): Promise<WorkforceEmployeeOperationalProfile> {
  const { data } = await http.get<WorkforceEmployeeOperationalProfile>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/operational-profile`,
  )
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
  const open = raw.open_url
  if (typeof open === 'string' && open.trim()) return open.trim()
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

/** Map CandDoc-shaped API JSON to document table rows (same as listWorkforceEmployeeDocuments). */
export function candDocRecordsToEmployeeDocumentRows(
  data: Array<Record<string, unknown>>,
): WorkforceEmployeeDocumentRow[] {
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

const parseContentDispositionFilename = (value: string | null | undefined): string | null => {
  if (!value) return null
  const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(value)
  if (!match?.[1]) return null
  try {
    return decodeURIComponent(match[1].replace(/["']/g, ''))
  } catch {
    return match[1].replace(/["']/g, '')
  }
}

/** Stream file for HR workspace (no viewer-channel filter; all linked candidate docs). */
export async function downloadWorkforceEmployeeDocumentFile(
  employeeId: string,
  documentId: string,
): Promise<{ blob: Blob; filename: string | null; contentType: string | null }> {
  const response = await http.get<Blob>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/documents/${encodeURIComponent(documentId)}/file`,
    { responseType: 'blob' },
  )
  const headers = response.headers as Record<string, unknown>
  const getHeader = (name: string): string | undefined => {
    const direct = headers[name] ?? headers[name.toLowerCase()]
    return typeof direct === 'string' ? direct : undefined
  }
  return {
    blob: response.data,
    filename: parseContentDispositionFilename(getHeader('content-disposition')),
    contentType: getHeader('content-type') ?? null,
  }
}

export async function listWorkforceEmployeeDocuments(
  employeeId: string,
): Promise<WorkforceEmployeeDocumentRow[]> {
  const { data } = await http.get<Array<Record<string, unknown>>>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/documents`,
  )
  return candDocRecordsToEmployeeDocumentRows(data || [])
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

export async function patchWorkforceTaxProfile(
  employeeId: string,
  payload: Partial<
    Omit<WorkforceTaxProfile, 'id' | 'tenant_id' | 'employee_id' | 'created_at' | 'updated_at'>
  > & { pit2_monthly_amount?: string | null },
): Promise<WorkforceTaxProfile> {
  const { data } = await http.patch<WorkforceTaxProfile>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/tax-profile`,
    payload,
  )
  return data
}

export async function patchWorkforceInsuranceProfile(
  employeeId: string,
  payload: Partial<
    Omit<WorkforceInsuranceProfile, 'id' | 'tenant_id' | 'employee_id' | 'created_at' | 'updated_at'>
  >,
): Promise<WorkforceInsuranceProfile> {
  const { data } = await http.patch<WorkforceInsuranceProfile>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/insurance-profile`,
    payload,
  )
  return data
}

export async function patchWorkforceWorkEligibility(
  employeeId: string,
  payload: Record<string, unknown>,
): Promise<WorkforceWorkEligibilityProfile> {
  const { data } = await http.patch<WorkforceWorkEligibilityProfile>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/work-eligibility`,
    payload,
  )
  return data
}

export async function getWorkEligibilityJourney(employeeId: string): Promise<WorkEligibilityJourney> {
  const { data } = await http.get<WorkEligibilityJourney>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/work-eligibility/journey`,
  )
  return data
}

export async function getWorkforceHrReview(employeeId: string): Promise<HrReviewPanel> {
  const { data } = await http.get<HrReviewPanel>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/hr-review`,
  )
  return data
}

type DocVerifyScope = { employeeId?: string; handoffId?: string; documentKey: string }

function docVerifyBase(scope: DocVerifyScope): string {
  const key = encodeURIComponent(scope.documentKey)
  if (scope.handoffId) {
    return `/handoffs/${encodeURIComponent(scope.handoffId)}/hr-review/document-verifications/${key}`
  }
  if (scope.employeeId) {
    return `/workforce/employees/${encodeURIComponent(scope.employeeId)}/hr-review/document-verifications/${key}`
  }
  throw new Error('employeeId or handoffId required')
}

export async function postHrDocumentOpened(scope: DocVerifyScope): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(`${docVerifyBase(scope)}/opened`)
  return data
}

export async function postHrDocumentReviewed(
  scope: DocVerifyScope & { reviewed_fields: Record<string, unknown> },
): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(`${docVerifyBase(scope)}/reviewed`, {
    reviewed_fields: scope.reviewed_fields,
  })
  return data
}

export async function postHrDocumentVerify(
  scope: DocVerifyScope & { reviewed_fields?: Record<string, unknown> },
): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(`${docVerifyBase(scope)}/verify`, {
    reviewed_fields: scope.reviewed_fields ?? {},
  })
  return data
}

export async function postHrDocumentReject(
  scope: DocVerifyScope & { reason: string },
): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(`${docVerifyBase(scope)}/reject`, { reason: scope.reason })
  return data
}

export async function postHrDocumentRequestCorrection(
  scope: DocVerifyScope & { note: string },
): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(`${docVerifyBase(scope)}/request-correction`, { note: scope.note })
  return data
}

export async function patchWorkforceHrReviewChecklistItem(
  employeeId: string,
  itemCode: string,
  satisfied: boolean,
): Promise<HrReviewPanel> {
  const { data } = await http.patch<HrReviewPanel>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/hr-review/checklist/${encodeURIComponent(itemCode)}`,
    { satisfied },
  )
  return data
}

export async function approveWorkforceHrReview(employeeId: string): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/hr-review/approve`,
  )
  return data
}

export async function returnWorkforceHrReviewToRecruitment(
  employeeId: string,
  reason: string,
): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/hr-review/return-to-recruitment`,
    { reason },
  )
  return data
}

export async function requestWorkforceHrReviewCorrections(
  employeeId: string,
  note: string,
): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/hr-review/request-corrections`,
    { note },
  )
  return data
}

export async function rejectWorkforceHrReview(employeeId: string, reason: string): Promise<HrReviewPanel> {
  const { data } = await http.post<HrReviewPanel>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/hr-review/reject`,
    { reason },
  )
  return data
}

export async function patchWorkforceWorkEligibilityPaymentRequirement(
  employeeId: string,
  requirementId: string,
  payload: Record<string, unknown>,
): Promise<WorkforceWorkEligibilityPaymentRequirement> {
  const { data } = await http.patch<WorkforceWorkEligibilityPaymentRequirement>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/work-eligibility/payment-requirements/${encodeURIComponent(requirementId)}`,
    payload,
  )
  return data
}

export async function patchWorkforceComplianceState(
  employeeId: string,
  payload: Partial<
    Omit<WorkforceComplianceState, 'id' | 'tenant_id' | 'employee_id' | 'created_at' | 'updated_at'>
  >,
): Promise<WorkforceComplianceState> {
  const { data } = await http.patch<WorkforceComplianceState>(
    `/workforce/employees/${encodeURIComponent(employeeId)}/compliance-state`,
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
