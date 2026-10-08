/** @vitest-environment node */
import { readFileSync } from 'node:fs'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}))

vi.mock('../client', () => ({
  api: { get: mockGet, post: mockPost },
}))

import {
  createRecruitmentProfile,
  getRecruitmentProfileForCandidateProfile,
  listCurrentDocumentTypeVersions,
  publishRecruitmentProfileRevision,
  RecruitmentProfileVersionConflictError,
} from '../recruitmentProfiles'
import { listCanonicalFields } from '../fieldRegistry'

describe('Recruitment Profile canonical API', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockPost.mockReset()
  })

  it('uses the canonical document version catalog', async () => {
    mockGet.mockResolvedValue({ data: { items: [{ document_type_version_id: 'dv-1' }], count: 1 } })
    await expect(listCurrentDocumentTypeVersions()).resolves.toEqual([{ document_type_version_id: 'dv-1' }])
    expect(mockGet).toHaveBeenCalledWith('/platform/reference/document-type-versions')
  })

  it('uses the canonical candidate Recruitment Field Registry catalog', async () => {
    mockGet.mockResolvedValue({ data: { items: [{ id: 'field-1' }], count: 1 } })
    await listCanonicalFields({ entity_type: 'candidate', module: 'recruitment' })
    expect(mockGet).toHaveBeenCalledWith('/platform/field-registry/fields', {
      params: { entity_type: 'candidate', module: 'recruitment' },
    })
  })

  it('reads the immutable publication through the supported legacy relationship', async () => {
    mockGet.mockResolvedValue({ data: { entity_profile_id: 'ep-1', version: 3 } })
    await getRecruitmentProfileForCandidateProfile('driver profile')
    expect(mockGet).toHaveBeenCalledWith(
      '/platform/entity-profiles/recruitment/by-legacy-candidate-profile/driver%20profile',
    )
  })

  it('creates with canonical field and document binding identities', async () => {
    const payload = {
      name: 'Driver',
      description: null,
      default_layout_code: null,
      config: { legacy_candidate_profile_code: 'driver' },
      fields: [{ canonical_field_id: 'field-1', qualified_code: 'recruitment.candidate.name', requirement_level: 'required' as const, sort_order: 10 }],
      documents: [{ document_type_version_id: 'doc-version-1', requirement_level: 'preferred' as const, sort_order: 10 }],
    }
    mockPost.mockResolvedValue({ data: { version: 1 } })
    await createRecruitmentProfile(payload)
    expect(mockPost).toHaveBeenCalledWith('/platform/entity-profiles/recruitment', payload)
  })

  it('keeps all page creation paths free of frontend-generated canonical profile codes', () => {
    const source = readFileSync(
      new URL('../../pages/admin/CandidateProfilesPage.tsx', import.meta.url),
      'utf8',
    )
    expect(source).not.toContain('canonicalProfileCode')
    expect(source).not.toContain('recruitment.candidate.legacy.')
    expect(source).not.toMatch(/^\s*profile_code\s*:/m)
    expect(source.match(/createRecruitmentProfile\(/g)?.length).toBeGreaterThanOrEqual(2)
  })

  it('revises complete metadata with optimistic concurrency', async () => {
    const payload = {
      expected_published_version: 4,
      name: 'Driver v5',
      description: null,
      default_layout_code: null,
      config: { legacy_candidate_profile_code: 'driver' },
      fields: [],
      documents: [],
    }
    mockPost.mockResolvedValue({ data: { version: 5 } })
    await publishRecruitmentProfileRevision('ep-1', payload)
    expect(mockPost).toHaveBeenCalledWith('/platform/entity-profiles/recruitment/ep-1/versions', payload)
  })

  it('surfaces stale publication conflicts without retrying', async () => {
    mockPost.mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 409,
        data: { detail: { code: 'recruitment_profile_version_conflict', expected_version: 2, current_version: 3 } },
      },
    })
    await expect(publishRecruitmentProfileRevision('ep-1', {
      expected_published_version: 2,
      name: 'Driver',
      description: null,
      default_layout_code: null,
      config: {},
      fields: [],
      documents: [],
    })).rejects.toBeInstanceOf(RecruitmentProfileVersionConflictError)
    expect(mockPost).toHaveBeenCalledTimes(1)
  })
})
