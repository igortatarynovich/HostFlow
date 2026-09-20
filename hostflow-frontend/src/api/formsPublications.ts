import { api } from './client'

export type FormOperatorState =
  | 'draft'
  | 'published'
  | 'live'
  | 'inactive'
  | 'never_published'

export type FormPublication = {
  publication_id: string
  title: string
  public_slug: string | null
  is_active: boolean
  lifecycle_status: string | null
  published_version: number | null
  published_at: string | null
  operator_state: FormOperatorState
  public_form_url: string | null
}

export async function fetchFormPublication(formId: string): Promise<FormPublication> {
  const { data } = await api.get<FormPublication>('/platform/forms/publications/resolve', {
    params: { form_id: formId },
  })
  return data
}

export async function publishFormPublication(formId: string): Promise<FormPublication> {
  const { data } = await api.post<FormPublication>(
    `/platform/forms/${encodeURIComponent(formId)}/publish`,
    {},
  )
  return data
}

export async function unpublishFormPublication(formId: string): Promise<FormPublication> {
  const { data } = await api.post<FormPublication>(
    `/platform/forms/${encodeURIComponent(formId)}/unpublish`,
    {},
  )
  return data
}
