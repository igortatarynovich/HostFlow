import { api } from './client'

export interface EffectiveCardLayoutField {
  id: string
  qualified_code: string
  module: string
  entity_type: string
  field_type: string
  label_key?: string | null
  name: string
  ownership: string
  reference_domain?: string | null
  pii_class?: string | null
  storage?: Record<string, unknown> | null
  legacy_aliases?: string[]
  registry_version: string
  status: string
  section_code: string
  sort_order: number
  visible: boolean
  required: boolean
  label_override?: string | null
}

export interface EffectiveCardLayoutSection {
  code: string
  order: number
  fields: EffectiveCardLayoutField[]
}

export interface EffectiveCardLayout {
  entity_type: string
  layout_code?: string | null
  layout_name?: string | null
  module?: string | null
  is_default?: boolean | null
  resolution_source: string
  registry_version?: string | null
  sections: EffectiveCardLayoutSection[]
  fields: EffectiveCardLayoutField[]
  candidate_id?: string | null
  candidate_profile_id?: string | null
  candidate_profile_code?: string | null
  process_profile_id?: string | null
  process_profile_code?: string | null
  process_profile_source?: string | null
  bridge_source?: string | null
}

export interface EffectiveCardLayoutQuery {
  entity_type: string
  layout_code?: string
  module?: string
  candidate_id?: string
  candidate_profile_id?: string
}

export const DEFAULT_CANDIDATE_LAYOUT_CODE = 'recruitment.candidate.default'
export const DEFAULT_VACANCY_LAYOUT_CODE = 'recruitment.vacancy.default'
export const DEFAULT_CLIENT_LAYOUT_CODE = 'crm.client.default'

export async function getEffectiveCardLayout(
  query: EffectiveCardLayoutQuery,
): Promise<EffectiveCardLayout> {
  const params: Record<string, string> = {
    entity_type: query.entity_type,
  }
  if (query.layout_code) params.layout_code = query.layout_code
  if (query.module) params.module = query.module
  if (query.candidate_id) params.candidate_id = query.candidate_id
  if (query.candidate_profile_id) params.candidate_profile_id = query.candidate_profile_id
  const { data } = await api.get<EffectiveCardLayout>('/platform/field-registry/effective-layout', {
    params,
  })
  return data
}

export async function listCanonicalFields(params?: {
  entity_type?: string
  module?: string
}): Promise<{ items: EffectiveCardLayoutField[]; count: number }> {
  const { data } = await api.get<{ items: EffectiveCardLayoutField[]; count: number }>(
    '/platform/field-registry/fields',
    { params },
  )
  return data
}
