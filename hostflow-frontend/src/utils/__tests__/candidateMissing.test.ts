import { describe, expect, it } from 'vitest'
import { parseCandidateMissingError } from '../candidateMissing'

function axios404(detail: unknown) {
  return { response: { status: 404, data: { detail } } }
}

describe('parseCandidateMissingError', () => {
  it('returns null for non-404', () => {
    expect(parseCandidateMissingError({ response: { status: 500 } })).toBeNull()
    expect(parseCandidateMissingError(new Error('fail'))).toBeNull()
  })

  it('parses deleted + surviving application', () => {
    expect(
      parseCandidateMissingError(
        axios404({
          code: 'candidate_deleted',
          application_id: 'app-1',
          can_recreate: true,
        }),
      ),
    ).toEqual({
      code: 'candidate_deleted',
      applicationId: 'app-1',
      canRecreate: true,
    })
  })

  it('treats generic 404 as not found', () => {
    expect(parseCandidateMissingError(axios404('Candidate not found'))).toEqual({
      code: 'candidate_not_found',
      applicationId: null,
      canRecreate: false,
    })
  })

  it('does not offer recreate without application id', () => {
    expect(
      parseCandidateMissingError(
        axios404({ code: 'candidate_deleted', can_recreate: true }),
      ),
    ).toEqual({
      code: 'candidate_deleted',
      applicationId: null,
      canRecreate: false,
    })
  })
})
