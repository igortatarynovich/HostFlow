import { api } from './client'
import type { UUID } from './types'

export type LegalDocumentOut = {
  id: string
  type: string
  version_id: string
  content_url: string | null
  is_active: boolean
  published_at: string | null
}

/** Stored `legal_documents.type` (core + §2.16 billing exhibits). */
export type LegalDocumentKind =
  | 'rodo_clause'
  | 'privacy_policy'
  | 'trial_terms'
  | 'downgrade_cancellation'
  | 'overage_autodebit'
  | 'data_retention'
  | 'automation_disclaimer'
  | 'mapping_disclaimer'

export type LegalDocumentCreate = {
  type: LegalDocumentKind
  version_id: string
  content_html?: string | null
  content_url?: string | null
  is_active?: boolean
}

export type LegalDocumentUpdate = {
  version_id?: string
  content_html?: string | null
  content_url?: string | null
  is_active?: boolean
}

export async function listLegalDocuments(): Promise<LegalDocumentOut[]> {
  const { data } = await api.get<LegalDocumentOut[]>('/legal-documents/')
  return data
}

export async function createLegalDocument(payload: LegalDocumentCreate): Promise<LegalDocumentOut> {
  const { data } = await api.post<LegalDocumentOut>('/legal-documents/', payload)
  return data
}

export async function updateLegalDocument(id: string, payload: LegalDocumentUpdate): Promise<LegalDocumentOut> {
  const { data } = await api.patch<LegalDocumentOut>(`/legal-documents/${id}`, payload)
  return data
}

export type ActiveLegalDocsResponse = {
  rodo_clause: LegalDocumentOut | null
  privacy_policy: LegalDocumentOut | null
  trial_terms: LegalDocumentOut | null
  downgrade_cancellation: LegalDocumentOut | null
  overage_autodebit: LegalDocumentOut | null
  data_retention: LegalDocumentOut | null
  automation_disclaimer: LegalDocumentOut | null
  mapping_disclaimer: LegalDocumentOut | null
}

export async function getActiveLegalDocs(): Promise<ActiveLegalDocsResponse> {
  const { data } = await api.get<ActiveLegalDocsResponse>('/legal-documents/active')
  return data
}

export async function fetchBillingLegalDrafts(): Promise<
  { type: string; version_id: string; content_html: string }[]
> {
  const { data } = await api.get<{ items: { type: string; version_id: string; content_html: string }[] }>(
    '/legal-documents/default-templates/billing-v1',
  )
  return data.items
}

export type RodoStatusOut = {
  sent: boolean
  sent_at: string | null
  sent_by_user_id: string | null
  recipient: string | null
  rodo_version_id: string | null
  can_send: boolean
  /** When sent=false: candidate card has an email (required to send RODO by email). */
  candidate_has_email?: boolean
  /** When sent=false: tenant has an active RODO clause document. */
  active_rodo_template?: boolean
}

export async function getRodoStatus(candidateId: UUID): Promise<RodoStatusOut> {
  const { data } = await api.get<RodoStatusOut>(
    `/legal-documents/candidates/${candidateId}/rodo-status`
  )
  return data
}

export async function sendRodo(candidateId: UUID): Promise<{ ok: boolean; message: string }> {
  const { data } = await api.post<{ ok: boolean; message: string }>(
    `/legal-documents/candidates/${candidateId}/send-rodo`
  )
  return data
}
