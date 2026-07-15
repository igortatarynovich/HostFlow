import { api } from './client'

export type PresentationFieldInput = {
  qualified_code: string
  label_override?: string | null
  intake_level: 'required' | 'optional' | 'hidden'
  sort_order?: number | null
  widget_hint?: string | null
  presentation_rules?: {
    show_if?: { source_field: string; operator?: string; value?: unknown }
    hide_if?: { source_field: string; operator?: string; value?: unknown }
    required_if?: { source_field: string; operator?: string; value?: unknown }
    readonly_if?: { source_field: string; operator?: string; value?: unknown }
  }
}

export type EntityProfileOption = {
  code: string
  name: string
  entity_type: string
  scope: string
}

export type EntityProfileFieldOption = {
  qualified_code: string
  label: string
  intake_level: string
  field_type?: string | null
  sort_order: number
  options?: Array<{ value: string; label: string }>
}

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
    presentation_code?: string | null
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
  form_definition?: {
    purpose?: string
    target_entity_profile_code?: string
    submission_policy?: {
      mode?: string
      match_policy?: Record<string, unknown>
    }
    published_version?: number
    is_system_preset?: boolean
  } | null
}

export type IntakeFormCreateInput = {
  title: string
  public_slug: string
  entity_profile_code: string
  fields: PresentationFieldInput[]
  is_active?: boolean
}

export type IntakeFormPatchInput = {
  title?: string
  public_slug?: string
  is_active?: boolean
  entity_profile_code?: string
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

export async function listIntakeFormEntityProfiles(): Promise<EntityProfileOption[]> {
  const { data } = await api.get<EntityProfileOption[]>('/settings/intake-forms/entity-profiles')
  return data
}

export async function getEntityProfileFields(profileCode: string): Promise<{
  code: string
  name: string | null
  fields: EntityProfileFieldOption[]
}> {
  const { data } = await api.get(`/settings/intake-forms/entity-profiles/${encodeURIComponent(profileCode)}/fields`)
  return data
}

export async function getEntityProfilePresentationPreset(
  profileCode: string,
  presentationCode?: string,
): Promise<{
  entity_profile_code: string
  presentation_code: string
  profile_name?: string | null
  fields: PresentationFieldInput[]
}> {
  const params = presentationCode ? { presentation_code: presentationCode } : undefined
  const { data } = await api.get(
    `/settings/intake-forms/entity-profiles/${encodeURIComponent(profileCode)}/presentation-preset`,
    { params },
  )
  return data
}

export async function createIntakeForm(payload: IntakeFormCreateInput): Promise<IntakeFormDetail> {
  const { data } = await api.post<IntakeFormDetail>('/settings/intake-forms', payload)
  return data
}

export async function patchIntakeForm(formId: string, payload: IntakeFormPatchInput): Promise<IntakeFormDetail> {
  const { data } = await api.patch<IntakeFormDetail>(`/settings/intake-forms/${formId}`, payload)
  return data
}

export async function putIntakeFormPresentation(
  formId: string,
  payload: { entity_profile_code: string; fields: PresentationFieldInput[] },
): Promise<IntakeFormDetail> {
  const { data } = await api.put<IntakeFormDetail>(`/settings/intake-forms/${formId}/presentation`, payload)
  return data
}

export async function getIntakeFormDetail(formId: string): Promise<IntakeFormDetail> {
  const { data } = await api.get<IntakeFormDetail>(`/settings/intake-forms/${formId}`)
  return data
}

export async function smokeTestIntakeForm(formId: string): Promise<IntakeFormSmokeTestResult> {
  const { data } = await api.post<IntakeFormSmokeTestResult>(`/settings/intake-forms/${formId}/smoke-test`)
  return data
}

export type MappingRuleInput = {
  source: string | string[]
  qualified_field_code?: string | null
  target?: string
  format?: 'string' | 'lower' | 'upper' | 'csv'
  overwrite?: boolean
}

export type IntakeFormMappingContext = {
  form_id: string
  public_slug: string | null
  entity_profile_code: string | null
  provider: string
  intake_source_profile_id: string | null
  mapping_rules: MappingRuleInput[]
  provider_bindings: Array<{
    id: string
    provider: string
    external_key: string
    external_key_secondary: string | null
    priority: number
    is_active: boolean
  }>
  validation?: Record<string, unknown> | null
}

export type IntakeFormMappingPreviewResult = {
  source_fields: Array<{ source: string; sample_value: string }>
  normalized_payload: Record<string, unknown>
  ingest_envelope_v1: Record<string, unknown>
  mapping_validation: Record<string, unknown>
  accepted_rules: MappingRuleInput[]
}

export type IntakeFormMappingTestResult = {
  lead_id: string
  candidate_id: string | null
  token: string
  expires_at: string
  normalized_payload: Record<string, unknown>
  ingest_envelope_v1: Record<string, unknown>
  mapping_validation: Record<string, unknown>
  message: string
}

export async function getIntakeFormMapping(formId: string): Promise<IntakeFormMappingContext> {
  const { data } = await api.get<IntakeFormMappingContext>(`/settings/intake-forms/${formId}/mapping`)
  return data
}

export async function putIntakeFormMapping(
  formId: string,
  payload: { mapping_rules: MappingRuleInput[] },
): Promise<IntakeFormMappingContext> {
  const { data } = await api.put<IntakeFormMappingContext>(`/settings/intake-forms/${formId}/mapping`, payload)
  return data
}

export async function previewIntakeFormMapping(
  formId: string,
  payload: { sample_payload: Record<string, unknown>; mapping_rules?: MappingRuleInput[] },
): Promise<IntakeFormMappingPreviewResult> {
  const { data } = await api.post<IntakeFormMappingPreviewResult>(
    `/settings/intake-forms/${formId}/mapping/preview`,
    payload,
  )
  return data
}

export async function testIntakeFormMappingIngest(
  formId: string,
  payload: { sample_payload: Record<string, unknown>; mapping_rules?: MappingRuleInput[] },
): Promise<IntakeFormMappingTestResult> {
  const { data } = await api.post<IntakeFormMappingTestResult>(
    `/settings/intake-forms/${formId}/mapping/test-ingest`,
    payload,
  )
  return data
}
