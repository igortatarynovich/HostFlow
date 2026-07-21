/** C2.1 Template Platform client — thin wrapper over `/communications/templates`. */

import api from '../client'

export type CommunicationTemplateVariable = {
  id?: string
  name: string
  var_type: string
  required: boolean
  description?: string | null
  default_value?: string | null
}

export type CommunicationTemplateVersion = {
  id: string
  template_id: string
  version_number: number
  status: string
  locale: string
  channels: string[]
  intent_keys: string[]
  variables: CommunicationTemplateVariable[]
  subject?: string | null
  body_text?: string | null
  body_html?: string | null
  meta?: Record<string, unknown>
  published_at?: string | null
  published_by?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type CommunicationTemplateBundle = {
  id: string
  key: string
  name: string
  description?: string | null
  status: string
  created_at?: string | null
  updated_at?: string | null
  draft: CommunicationTemplateVersion | null
  latest_published: CommunicationTemplateVersion | null
  published_version?: CommunicationTemplateVersion
}

export type CommunicationTemplateCreateInput = {
  key: string
  name: string
  description?: string | null
  locale?: string
  subject?: string | null
  body_text?: string | null
  body_html?: string | null
  channels?: string[]
  intent_keys?: string[]
  variables?: CommunicationTemplateVariable[]
}

export type CommunicationTemplateDraftPatch = {
  subject?: string | null
  body_text?: string | null
  body_html?: string | null
  locale?: string | null
  meta?: Record<string, unknown> | null
  channels?: string[] | null
  intent_keys?: string[] | null
  variables?: CommunicationTemplateVariable[] | null
}

export type CommunicationTemplatePreviewResult = {
  ok: boolean
  template_version_id: string
  subject?: string | null
  body_text?: string | null
  body_html?: string | null
  diagnostics?: Array<{ code?: string; severity?: string; message?: string }>
}

export type CommunicationTemplateDiff = {
  from_version_id: string
  to_version_id: string
  identical: boolean
  changed: Record<string, unknown>
}

export async function listCommunicationTemplates(params?: {
  includeArchived?: boolean
}): Promise<CommunicationTemplateBundle[]> {
  const res = await api.get('/communications/templates', {
    params: { include_archived: params?.includeArchived ? true : undefined },
  })
  const items = res.data?.items
  return Array.isArray(items) ? items : []
}

export async function getCommunicationTemplate(
  templateId: string,
): Promise<CommunicationTemplateBundle> {
  const res = await api.get(`/communications/templates/${templateId}`)
  return res.data
}

export async function createCommunicationTemplate(
  body: CommunicationTemplateCreateInput,
): Promise<CommunicationTemplateBundle> {
  const res = await api.post('/communications/templates', body)
  return res.data
}

export async function updateCommunicationTemplateDraft(
  templateId: string,
  body: CommunicationTemplateDraftPatch,
): Promise<CommunicationTemplateBundle> {
  const res = await api.patch(`/communications/templates/${templateId}/draft`, body)
  return res.data
}

export async function publishCommunicationTemplate(
  templateId: string,
): Promise<CommunicationTemplateBundle> {
  const res = await api.post(`/communications/templates/${templateId}/publish`)
  return res.data
}

export async function archiveCommunicationTemplate(
  templateId: string,
): Promise<CommunicationTemplateBundle> {
  const res = await api.post(`/communications/templates/${templateId}/archive`)
  return res.data
}

export async function listCommunicationTemplateVersions(
  templateId: string,
): Promise<CommunicationTemplateVersion[]> {
  const res = await api.get(`/communications/templates/${templateId}/versions`)
  const items = res.data?.items
  return Array.isArray(items) ? items : []
}

export async function previewCommunicationTemplate(
  templateId: string,
  body: {
    variables?: Record<string, unknown>
    channel?: string
    locale?: string | null
    version_id?: string | null
  },
): Promise<CommunicationTemplatePreviewResult> {
  const res = await api.post(`/communications/templates/${templateId}/preview`, body)
  return res.data
}

export async function diffCommunicationTemplateVersions(
  templateId: string,
  fromVersionId: string,
  toVersionId: string,
): Promise<CommunicationTemplateDiff> {
  const res = await api.get(`/communications/templates/${templateId}/diff`, {
    params: { from: fromVersionId, to: toVersionId },
  })
  return res.data
}
