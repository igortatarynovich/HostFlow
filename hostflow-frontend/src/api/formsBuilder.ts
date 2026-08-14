import { api } from './client'
import axios from 'axios'

export type BuilderPaletteItem = {
  component_id: string
  component_version: string
  category: string | null
  tags: string[]
  label_key: string | null
  icon: string | null
  supports_preview: boolean
}

export type BuilderConfigField = {
  key: string
  value_type: string
  required: boolean
  enum_values: string[] | null
  default: unknown
  label_key: string | null
}

export type BuilderComponentView = {
  component_id: string
  component_version: string
  category: string | null
  tags: string[]
  label_key: string | null
  icon: string | null
  supports_preview: boolean
  config_fields: BuilderConfigField[]
}

export type CompositionInstance = {
  instance_id: string
  component_id: string
  component_version: string
  config: Record<string, unknown>
}

export type FormComposition = {
  contract: string
  draft_id: string
  instances: CompositionInstance[]
}

export type BuilderDraft = {
  contract: string
  tenant_id: string
  draft_id: string
  form_id: string | null
  revision: number
  status: string
  composition_contract: string
  composition: FormComposition
  exists: boolean
  definition_id?: string
  builder_state?: string
}

export async function fetchBuilderPalette(params?: {
  query?: string
  category?: string
}): Promise<BuilderPaletteItem[]> {
  const { data } = await api.get<{ items: BuilderPaletteItem[] }>(
    '/platform/forms/builder/palette',
    { params },
  )
  return data.items || []
}

export async function fetchBuilderComponent(
  componentId: string,
  version: string,
): Promise<BuilderComponentView> {
  const { data } = await api.get<BuilderComponentView>(
    `/platform/forms/builder/components/${encodeURIComponent(componentId)}`,
    { params: { version } },
  )
  return data
}

export async function fetchFormBuilderDraft(formId: string): Promise<BuilderDraft> {
  const { data } = await api.get<BuilderDraft>(
    `/platform/forms/builder/forms/${encodeURIComponent(formId)}/draft`,
  )
  return data
}

export async function saveFormBuilderDraft(
  formId: string,
  payload: { composition: FormComposition; expected_revision?: number | null },
): Promise<BuilderDraft> {
  const { data } = await api.put<BuilderDraft>(
    `/platform/forms/builder/forms/${encodeURIComponent(formId)}/draft`,
    payload,
  )
  return data
}

export function isDraftRevisionConflict(err: unknown): boolean {
  if (!axios.isAxiosError(err)) return false
  if (err.response?.status !== 409) return false
  const detail = err.response.data?.detail
  if (typeof detail === 'object' && detail && 'error' in detail) {
    if (detail.error === 'forms_builder_draft_revision_conflict') return true
    const state = (detail as { details?: { builder_state?: string } }).details?.builder_state
    if (state === 'conflict') return true
    return false
  }
  return true
}

export function newInstanceId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `inst-${Date.now()}-${Math.random().toString(16).slice(2)}`
}
