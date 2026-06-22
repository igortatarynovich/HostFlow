import { api } from './client'

export type IntakeFormDetail = {
  form: {
    id: string
    title: string
    public_slug: string | null
    is_active: boolean
    created_at: string
    updated_at: string
  }
  intake_source_profile: {
    id: string
    code: string
    name: string
    provider: string
    channel: string
    route_intent: string
    entity_profile_code: string | null
    default_assignee_id: string | null
    default_language: string | null
    is_active: boolean
  } | null
  intake_source_profile_id: string | null
  entity_profile: {
    code: string
    name: string | null
    entity_type: string | null
    resolution_source: string | null
  }
  presentation: {
    contract_version: string
    entity_profile_code: string
    presentation_code: string
    profile_name?: string | null
    fields: Array<{
      qualified_code: string
      sort_order: number
      intake_level: string
      label: string
      field_type?: string | null
      widget_hint?: string | null
    }>
    warnings: string[]
  }
  presentations_available: Array<{ presentation_code: string; field_subset: string[] }>
  submit_destination: {
    pipeline: string
    route_intent: string
    entity_profile_code: string
    creates_candidate_on_create: boolean
    creates_lead_draft_on_create: boolean
  }
}

export type IntakeFormSmokeTestResult = {
  lead_id: string
  candidate_id: string | null
  token: string
  expires_at: string
  contacts: Record<string, string>
  stage: string | null
  message: string
}

export async function getIntakeFormDetail(formId: string): Promise<IntakeFormDetail> {
  const { data } = await api.get<IntakeFormDetail>(`/settings/intake-forms/${formId}`)
  return data
}

export async function smokeTestIntakeForm(formId: string): Promise<IntakeFormSmokeTestResult> {
  const { data } = await api.post<IntakeFormSmokeTestResult>(`/settings/intake-forms/${formId}/smoke-test`)
  return data
}
