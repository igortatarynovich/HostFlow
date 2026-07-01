import { api } from './client'

export type MergeDocumentTemplate = {
  id: string
  tenant_id: string
  own_company_id: string | null
  code: string
  name: string
  description: string | null
  body_text: string
  output_mime: string
  variable_bindings: Record<string, unknown> | null
  output_filename_pattern: string | null
  doc_type: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type MergeTemplateCreatePayload = {
  code: string
  name: string
  description?: string | null
  body_text: string
  output_mime?: string
  variable_bindings?: Record<string, unknown> | null
  output_filename_pattern?: string | null
  doc_type?: string
  own_company_id?: string | null
  is_active?: boolean
}

export type MergeTemplatePatchPayload = Partial<MergeTemplateCreatePayload>

export async function listMergeDocumentTemplates(params?: {
  include_inactive?: boolean
  own_company_id?: string | null
}): Promise<MergeDocumentTemplate[]> {
  const { data } = await api.get<MergeDocumentTemplate[]>('/document-merge/templates', {
    params: {
      include_inactive: params?.include_inactive ?? false,
      own_company_id: params?.own_company_id || undefined,
    },
  })
  return data
}

export async function createMergeDocumentTemplate(
  payload: MergeTemplateCreatePayload,
): Promise<MergeDocumentTemplate> {
  const { data } = await api.post<MergeDocumentTemplate>('/document-merge/templates', payload)
  return data
}

export async function patchMergeDocumentTemplate(
  id: string,
  payload: MergeTemplatePatchPayload,
): Promise<MergeDocumentTemplate> {
  const { data } = await api.patch<MergeDocumentTemplate>(`/document-merge/templates/${id}`, payload)
  return data
}

export async function deleteMergeDocumentTemplate(id: string): Promise<void> {
  await api.delete(`/document-merge/templates/${id}`)
}

export type MergeGeneratePayload = {
  template_id?: string | null
  template_code?: string | null
  candidate_id?: string | null
  workforce_employee_id?: string | null
  variable_bindings?: Record<string, unknown> | null
}

export type MergeGenerateResponse = {
  log_id: string
  document_id: string
  template_id: string | null
  status: string
}

export async function generateMergeDocument(payload: MergeGeneratePayload): Promise<MergeGenerateResponse> {
  const { data } = await api.post<MergeGenerateResponse>('/document-merge/generate', payload)
  return data
}
