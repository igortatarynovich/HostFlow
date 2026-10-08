import axios from 'axios'
import { api } from './client'

export type FieldRequirementLevel = 'hidden' | 'optional' | 'required'
export type DocumentRequirementLevel = 'hidden' | 'preferred' | 'required'

export interface RecruitmentProfileFieldBinding {
  canonical_field_id: string
  qualified_code: string
  requirement_level: FieldRequirementLevel
  sort_order: number
}

export interface RecruitmentProfileDocumentBinding {
  document_type_version_id: string
  requirement_level: DocumentRequirementLevel
  sort_order: number
}

export interface RecruitmentProfileDocumentPolicy extends RecruitmentProfileDocumentBinding {
  document_type_id: string
  document_type_code: string
  document_type_version_code: string
}

export interface RecruitmentProfilePublication {
  entity_profile_id: string
  profile_version_id: string
  profile_code: string
  version: number
  tenant_id: string
  module_owner: 'recruitment'
  entity_type: 'candidate'
  is_system: boolean
  name: string
  description: string | null
  default_layout_code: string | null
  config: Record<string, unknown>
  published_at: string
  fields: RecruitmentProfileFieldBinding[]
  documents: RecruitmentProfileDocumentPolicy[]
}

export interface CurrentDocumentTypeVersion {
  document_type_id: string
  document_type_code: string
  public_name: string
  description: string | null
  category_code: string
  subcategory_code: string | null
  document_type_status: string
  document_type_version_id: string
  version_code: string
  valid_from: string
  valid_to: string | null
  status_model: string
  deprecation_reason: string | null
}

export interface RecruitmentProfileCreateInput {
  profile_code?: string
  name: string
  description: string | null
  default_layout_code: string | null
  config: Record<string, unknown>
  fields: RecruitmentProfileFieldBinding[]
  documents: RecruitmentProfileDocumentBinding[]
}

export interface RecruitmentProfileRevisionInput {
  expected_published_version: number
  name: string
  description: string | null
  default_layout_code: string | null
  config: Record<string, unknown>
  fields: RecruitmentProfileFieldBinding[]
  documents: RecruitmentProfileDocumentBinding[]
}

export class RecruitmentProfileVersionConflictError extends Error {
  readonly expectedVersion: number
  readonly currentVersion: number

  constructor(expectedVersion: number, currentVersion: number, message?: string) {
    super(message || `Profile changed in another session (current version ${currentVersion}). Reload and try again.`)
    this.name = 'RecruitmentProfileVersionConflictError'
    this.expectedVersion = expectedVersion
    this.currentVersion = currentVersion
  }
}

function rethrowVersionConflict(error: unknown): never {
  if (axios.isAxiosError(error) && error.response?.status === 409) {
    const detail = error.response.data?.detail
    if (detail?.code === 'recruitment_profile_version_conflict') {
      throw new RecruitmentProfileVersionConflictError(
        Number(detail.expected_version),
        Number(detail.current_version),
        detail.message,
      )
    }
  }
  throw error
}

export async function listCurrentDocumentTypeVersions(): Promise<CurrentDocumentTypeVersion[]> {
  const { data } = await api.get<{ items: CurrentDocumentTypeVersion[]; count: number }>(
    '/platform/reference/document-type-versions',
  )
  return data.items
}

export async function getRecruitmentProfileForCandidateProfile(
  candidateProfileCode: string,
): Promise<RecruitmentProfilePublication | null> {
  try {
    const { data } = await api.get<RecruitmentProfilePublication>(
      `/platform/entity-profiles/recruitment/by-legacy-candidate-profile/${encodeURIComponent(candidateProfileCode)}`,
    )
    return data
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null
    throw error
  }
}

export async function createRecruitmentProfile(
  payload: RecruitmentProfileCreateInput,
): Promise<RecruitmentProfilePublication> {
  const { data } = await api.post<RecruitmentProfilePublication>(
    '/platform/entity-profiles/recruitment',
    payload,
  )
  return data
}

export async function publishRecruitmentProfileRevision(
  entityProfileId: string,
  payload: RecruitmentProfileRevisionInput,
): Promise<RecruitmentProfilePublication> {
  try {
    const { data } = await api.post<RecruitmentProfilePublication>(
      `/platform/entity-profiles/recruitment/${entityProfileId}/versions`,
      payload,
    )
    return data
  } catch (error) {
    rethrowVersionConflict(error)
  }
}
