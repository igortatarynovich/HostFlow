/**
 * Application facade API — UI Constitution v1: module pages use ONLY this layer.
 */
import type { Application, ApplicationListResponse, ApplicationTab } from './types/application'
import { api } from './client'

export type ApplicationStage = 'contacted' | 'qualified' | 'lost'

export type ApplicationIntakeDecision =
  | 'qualify'
  | 'reject'
  | 'pool'
  | 'request_info'
  | 'duplicate_review'

export type ApplicationProcessResult = {
  application: Application
  candidate_id?: string | null
  message?: string | null
}

export async function listSalesInquiries(opts?: { limit?: number }): Promise<ApplicationListResponse> {
  const { data } = await api.get<ApplicationListResponse>('/sales/inquiries', {
    params: { limit: opts?.limit ?? 200 },
  })
  return data
}

export async function getSalesInquiry(applicationId: string): Promise<Application> {
  const { data } = await api.get<Application>(`/sales/inquiries/${encodeURIComponent(applicationId)}`)
  return data
}

export async function updateSalesInquiryStage(
  applicationId: string,
  payload: { stage: ApplicationStage; lost_reason_code?: string; lost_reason_note?: string },
): Promise<Application> {
  const { data } = await api.patch<Application>(`/sales/inquiries/${encodeURIComponent(applicationId)}`, payload)
  return data
}

export async function convertSalesInquiryToClient(applicationId: string): Promise<Application> {
  const { data } = await api.post<Application>(`/sales/inquiries/${encodeURIComponent(applicationId)}/convert-client`)
  return data
}

export type SalesCapabilitySpine = {
  contract: string
  sales_inquiry_id: string | null
  transport_lead_id: string | null
  inquiry_status: string | null
  capability: {
    code: string | null
    source: 'entity_profile' | 'undecided'
    decided: boolean
  }
  review: {
    status: string | null
    decision: Record<string, unknown> | null
    candidates: unknown[]
    convert_allowed: boolean
    blocks_convert: boolean
    present: boolean
    reason?: string | null
    version?: number | null
  }
  convert: {
    available: boolean
    reason: string | null
    inquiry_status: string | null
    client_account_id: string | null
    mapping_present: boolean
    mapping: {
      client_account_id: string | null
      flights_ledger_id: string | null
      destination: string | null
      converted_at?: unknown
    } | null
  }
  traceability: {
    present: boolean
    lineage: {
      sales_inquiry_id: string | null
      client_account_id: string | null
      flights_ledger_id: string | null
      company_id: string | null
      destination: string | null
      recorded_at?: unknown
      chain: unknown[]
    } | null
  }
  missing_sales_inquiry: boolean
}

/** Display-only Pipeline v1 spine (Capability / Review / Convert / Traceability). */
export async function getSalesInquiryCapabilitySpine(
  applicationId: string,
): Promise<SalesCapabilitySpine> {
  const { data } = await api.get<SalesCapabilitySpine>(
    `/sales/inquiries/${encodeURIComponent(applicationId)}/capability-spine`,
  )
  return data
}

export type SalesInquiryDuplicateMatchReason = 'phone' | 'email' | 'phone_and_email'

export type SalesInquiryDuplicateHint = {
  application: Application
  match_reason: SalesInquiryDuplicateMatchReason
}

export type SalesInquiryDuplicateListResponse = {
  items: SalesInquiryDuplicateHint[]
  total: number
}

export async function listSalesInquiryPossibleDuplicates(
  applicationId: string,
  opts?: { limit?: number },
): Promise<SalesInquiryDuplicateListResponse> {
  const { data } = await api.get<SalesInquiryDuplicateListResponse>(
    `/sales/inquiries/${encodeURIComponent(applicationId)}/possible-duplicates`,
    { params: { limit: opts?.limit ?? 10 } },
  )
  return data
}

export async function listRecruitmentApplications(opts?: {
  limit?: number
  offset?: number
  vacancyId?: string
  tab?: ApplicationTab
  /** `open` = pending only (search home counters); `all` = inbox including completed */
  scope?: 'open' | 'all'
  includeCounts?: boolean
}): Promise<ApplicationListResponse> {
  const { data } = await api.get<ApplicationListResponse>('/recruitment/applications', {
    params: {
      limit: opts?.limit ?? 200,
      offset: opts?.offset ?? 0,
      vacancy_id: opts?.vacancyId,
      tab: opts?.tab,
      scope: opts?.scope ?? 'all',
      include_counts: opts?.includeCounts ? true : undefined,
    },
  })
  return data
}

export async function getRecruitmentApplication(applicationId: string): Promise<Application> {
  const { data } = await api.get<Application>(`/recruitment/applications/${encodeURIComponent(applicationId)}`)
  return data
}

export async function updateRecruitmentApplicationStage(
  applicationId: string,
  payload: { stage: ApplicationStage; lost_reason_code?: string; lost_reason_note?: string },
): Promise<Application> {
  const { data } = await api.patch<Application>(
    `/recruitment/applications/${encodeURIComponent(applicationId)}`,
    payload,
  )
  return data
}

export async function submitRecruitmentApplicationIntakeDecision(
  applicationId: string,
  payload: {
    decision: ApplicationIntakeDecision
    reason_code?: string | null
    note?: string | null
    funnel_id?: string | null
  },
): Promise<Application> {
  const { data } = await api.post<Application>(
    `/recruitment/applications/${encodeURIComponent(applicationId)}/intake-decision`,
    payload,
  )
  return data
}

export async function confirmRecruitmentApplicationVacancy(
  applicationId: string,
  payload: { vacancy_id: string },
): Promise<Application> {
  const { data } = await api.post<Application>(
    `/recruitment/applications/${encodeURIComponent(applicationId)}/confirm-vacancy`,
    payload,
  )
  return data
}

export async function processRecruitmentApplication(applicationId: string): Promise<ApplicationProcessResult> {
  const { data } = await api.post<ApplicationProcessResult>(
    `/recruitment/applications/${encodeURIComponent(applicationId)}/process`,
  )
  return data
}

export async function createRecruitmentApplicationFollowUp(
  applicationId: string,
  payload: { title: string; due_at?: string; note?: string },
): Promise<Application> {
  const { data } = await api.post<Application>(
    `/recruitment/applications/${encodeURIComponent(applicationId)}/follow-up`,
    payload,
  )
  return data
}

export async function assignRecruitmentApplication(
  applicationId: string,
  payload: { assignee_id: string },
): Promise<Application> {
  const { data } = await api.post<Application>(
    `/recruitment/applications/${encodeURIComponent(applicationId)}/assign`,
    payload,
  )
  return data
}

export type ApplicationCallResultCode =
  | 'no_answer'
  | 'answered'
  | 'callback_requested'
  | 'interested'
  | 'not_interested'
  | 'wrong_number'
  | 'unavailable'

export async function logRecruitmentApplicationCallResult(
  applicationId: string,
  payload: {
    result: ApplicationCallResultCode
    note?: string | null
    next_contact_at?: string | null
  },
): Promise<Application> {
  const { data } = await api.post<Application>(
    `/recruitment/applications/${encodeURIComponent(applicationId)}/call-result`,
    payload,
  )
  return data
}
