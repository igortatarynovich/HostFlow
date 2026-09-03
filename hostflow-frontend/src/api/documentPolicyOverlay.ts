import { api } from './client'

export type DocumentPolicyOverlay = {
  pack_version: string
  tenant_delta: Record<string, unknown>
  reason: string | null
  resolved_policy: Record<string, unknown>
  updated_at?: string | null
  updated_by_user_id?: string | null
}

export async function getDocumentPolicyOverlay(): Promise<DocumentPolicyOverlay> {
  const { data } = await api.get<DocumentPolicyOverlay>('/platform/document-policy-overlay')
  return data
}

export async function putDocumentPolicyOverlay(payload: {
  tenant_delta: Record<string, unknown>
  reason: string
}): Promise<DocumentPolicyOverlay> {
  const { data } = await api.put<DocumentPolicyOverlay>(
    '/platform/document-policy-overlay',
    payload,
  )
  return data
}
