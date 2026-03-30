import http from './http'

export type IntakeContacts = {
  phone_country_code?: string | null
  phone?: string | null
  email?: string | null
  preferred_messenger?: string | null
}

export type IntakePersonal = {
  full_name?: string | null
  citizenship?: string | null
  residency_status?: string | null
  in_poland?: boolean | null
  birth_date?: string | null  // ISO date string 'YYYY-MM-DD'
  current_location?: string | null  // 'in_poland' | 'not_in_poland' | 'other'
  frigo_experience?: boolean | null
  has_adr?: boolean | null
}

export type IntakeExperience = {
  years_ce?: number | null
  intl_experience?: boolean | null
  trailer_types?: string[]
  route_types?: string[]
}

export type IntakeEmployment = {
  id?: string | null
  employer_name: string
  country?: string | null
  position?: string | null
  start_date: string
  end_date?: string | null
  trailer_types?: string[]
  route_types?: string[]
  truck_brands?: string[] | null
  eu_routes?: boolean | null
  reason_for_leaving?: string | null
  reference_contact?: string | null
}

export type IntakeAgreements = {
  general?: boolean
  employer_share?: boolean
  terms_acceptance?: boolean
  cookies_accepted?: boolean
  // legacy fallbacks
  privacy?: boolean
  contact?: boolean
}

export type IntakeData = {
  contacts: IntakeContacts
  personal: IntakePersonal
  experience: IntakeExperience
  employments: IntakeEmployment[]
  agreements: IntakeAgreements
}

export type PublicIntakeCreateRequest = {
  contacts: IntakeContacts
  vacancy_id?: string
  locale?: string
  source?: string
  /** Send at most one of these (backend rejects both set). */
  lead_form_id?: string | null
  lead_form_slug?: string | null
}

export type PublicLeadFormListItem = {
  id: string
  title: string
  public_slug: string
}

export type PublicIntakeCreateResponse = {
  apply_url: string
  token: string
  candidate_id: string
  expires_at: string
}

export type PublicChecklist = {
  requiredTypes?: string[]
  optionalTypes?: string[]
  profile?: Record<string, unknown>
  [key: string]: unknown
}

export type PublicDocumentSummary = {
  status?: string
  percent_ready?: number
  required?: {
    total?: number
    ready?: number
    in_progress?: number
    missing_count?: number
    problems?: number
    missing?: string[]
    problematic?: string[]
  }
  expiring_soon?: Array<{ type: string; expires_at: string }>
  checklist?: PublicChecklist
  [key: string]: unknown
}

export type PublicDocumentEntry = {
  id: string
  type: string
  doc_type: string
  status?: string
  expires_at?: string | null
  has_files?: boolean
  download_url?: string | null
  requested_from?: string | null
  process_type?: string | null
  ordered_at?: string | null
  valid_from?: string | null
}

export type PublicDocumentType = {
  doc_type: string
  title?: Record<string, string>
  i18n_key?: string | null
  required_files?: Record<string, any> | null
  metadata_schema?: Record<string, any> | null
  required_meta?: string[]
  requested_from?: string | null
  kind?: string | null
  process_type?: string | null
  orderable?: boolean
  requires_custom_name?: boolean
  duplicate_policy?: string | null
  expiry_rule?: Record<string, any> | null
}

export type PublicTimelineEntry = {
  key: string
  title: string
  status: string
  description?: string | null
  completed_at?: string | null
  meta?: Record<string, any>
}

export type PublicIntakeDocuments = {
  summary?: PublicDocumentSummary
  documents?: PublicDocumentEntry[]
  doc_types?: Record<string, PublicDocumentType>
}

export type PublicIntakeState = {
  token: string
  candidate_id: string
  status: string
  stage?: string | null
  created_at?: string | null
  expires_at?: string | null
  submitted_at?: string | null
  data: IntakeData
  checklist: PublicChecklist
  documents: PublicIntakeDocuments
  timeline?: PublicTimelineEntry[]
  status_share_token?: string | null
}

export type PublicStatusState = {
  candidate_id: string
  status: string
  stage?: string | null
  created_at?: string | null
  expires_at?: string | null
  submitted_at?: string | null
  candidate_name?: string | null
  contacts?: IntakeContacts
  checklist: PublicChecklist
  documents: PublicIntakeDocuments
  timeline?: PublicTimelineEntry[]
}

export type MagicLinkRequestPayload = {
  email?: string
  phone_country_code?: string
  phone?: string
}

export type PublicDocumentsAccessPayload = {
  email?: string
  phone_country_code?: string
  phone?: string
}

export type PublicDocumentsAccessResponse = {
  verified: boolean
  upload_url: string
  questionnaire_url: string
  expires_at: string
}

export type MagicLinkRequestResponse = {
  status: string
  cooldown_seconds: number
  daily_limit: number
}

export type MagicLinkRedeemResponse = {
  token: string
  apply_url: string
  status_share_token?: string | null
  expires_at?: string | null
  candidate_id: string
  cooldown_seconds: number
  daily_limit: number
}

export async function createPublicIntake(payload: PublicIntakeCreateRequest): Promise<PublicIntakeCreateResponse> {
  const { data } = await http.post('/public/intake', payload)
  return data
}

export async function listPublicIntakeLeadForms(): Promise<PublicLeadFormListItem[]> {
  const { data } = await http.get<PublicLeadFormListItem[]>('/public/intake/lead-forms')
  return data
}

export async function getPublicIntake(token: string): Promise<PublicIntakeState> {
  const { data } = await http.get(`/public/apply/${token}`)
  return data
}

export async function updatePublicIntake(token: string, dataPayload: IntakeData): Promise<PublicIntakeState> {
  const { data } = await http.put(`/public/apply/${token}`, { data: dataPayload })
  return data
}

export type PublicConsentFlags = {
  general: boolean
  employer_share: boolean
  terms_acceptance: boolean
}

export type PublicConsentVersions = {
  privacy: string
  terms: string
  cookies: string
}

export type PublicIntakeSubmitPayload = {
  consents: PublicConsentFlags
  documents_version: PublicConsentVersions
  cookies_accepted: boolean
}

export async function submitPublicIntake(token: string, payload: PublicIntakeSubmitPayload): Promise<PublicIntakeState> {
  const { data } = await http.post(`/public/apply/${token}/submit`, payload)
  return data
}

export async function getPublicStatus(token: string): Promise<PublicStatusState> {
  const { data } = await http.get(`/public/status/${token}`)
  return data
}

export async function requestMagicLink(payload: MagicLinkRequestPayload): Promise<MagicLinkRequestResponse> {
  const { data } = await http.post('/public/magic-link/request', payload)
  return data
}

export type RotateStatusResponse = {
  status_share_token: string
  expires_at: string
}

export async function rotateStatusToken(token: string): Promise<RotateStatusResponse> {
  const { data } = await http.post(`/public/status/${token}/rotate`)
  return data
}

export async function redeemMagicLink(token: string): Promise<MagicLinkRedeemResponse> {
  const { data } = await http.get(`/public/magic-link/${token}`)
  return data
}

export async function requestPublicDocumentsAccess(
  statusToken: string,
  payload: PublicDocumentsAccessPayload,
): Promise<PublicDocumentsAccessResponse> {
  const { data } = await http.post(`/public/status/${statusToken}/documents/access`, payload)
  return data
}

export type PublicPresignPayload = {
  doc_type: string
  filename: string
}

export type PublicPresignResponse = {
  key: string
  url: string
  method: string
  headers: Record<string, string>
  fields: Record<string, string>
}

export async function presignPublicDocument(token: string, payload: PublicPresignPayload): Promise<PublicPresignResponse> {
  const { data } = await http.post(`/public/apply/${token}/documents/presign`, payload)
  return data
}

export async function uploadPublicDocument(token: string, formData: FormData): Promise<PublicIntakeState> {
  const { data } = await http.post(`/public/apply/${token}/documents/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function presignStatusDocument(
  statusToken: string,
  payload: PublicPresignPayload & PublicDocumentsAccessPayload,
): Promise<PublicPresignResponse> {
  const { data } = await http.post(`/public/status/${statusToken}/documents/presign`, payload)
  return data
}

export async function uploadStatusDocument(statusToken: string, formData: FormData): Promise<PublicStatusState> {
  const { data } = await http.post(`/public/status/${statusToken}/documents/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
