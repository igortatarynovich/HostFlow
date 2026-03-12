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

export type LegalDocumentCreate = {
  type: 'rodo_clause' | 'privacy_policy'
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

export async function getActiveLegalDocs(): Promise<{ rodo_clause: LegalDocumentOut | null; privacy_policy: LegalDocumentOut | null }> {
  const { data } = await api.get<{ rodo_clause: LegalDocumentOut | null; privacy_policy: LegalDocumentOut | null }>('/legal-documents/active')
  return data
}

export type RodoStatusOut = {
  sent: boolean
  sent_at: string | null
  sent_by_user_id: string | null
  recipient: string | null
  rodo_version_id: string | null
  can_send: boolean
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
