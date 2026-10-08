/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockPost, mockPatch } = vi.hoisted(() => ({ mockPost: vi.fn(), mockPatch: vi.fn() }))
vi.mock('../client', () => ({ api: { post: mockPost, patch: mockPatch } }))

import { createCandidateProfile, updateCandidateProfile } from '../candidate_profiles'

describe('CandidateProfile compatibility shell writes', () => {
  beforeEach(() => { mockPost.mockReset(); mockPatch.mockReset() })

  it('strips legacy requirement fragments on create and update', async () => {
    const payload = {
      code: 'driver',
      name: 'Driver',
      config: { field_configs: [{ field_key: 'name' }], document_configs: [{ document_type_id: 'passport' }], stage_configs: [{ stage_code: 'new' }] },
    }
    mockPost.mockResolvedValue({ data: {} })
    mockPatch.mockResolvedValue({ data: {} })
    await createCandidateProfile(payload)
    await updateCandidateProfile('candidate-profile-1', payload)
    const expected = { code: 'driver', name: 'Driver', config: { stage_configs: [{ stage_code: 'new' }] } }
    expect(mockPost).toHaveBeenCalledWith('/candidate-profiles', expected)
    expect(mockPatch).toHaveBeenCalledWith('/candidate-profiles/candidate-profile-1', expected)
  })
})
