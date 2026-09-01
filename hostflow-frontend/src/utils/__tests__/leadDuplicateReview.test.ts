import { describe, expect, it } from 'vitest'

import type { Lead } from '../../api/types'
import {
  leadInDuplicateReviewContext,
  leadShowsDuplicateMark,
  readDuplicatePrior,
} from '../leadDuplicateReview'

function metaLead(overrides: Partial<Lead> & Record<string, unknown> = {}): Lead {
  return {
    id: '00000000-0000-4000-8000-000000000011',
    tenant_id: '00000000-0000-4000-8000-000000000022',
    source: 'meta',
    status: 'needs_routing',
    payload: {},
    created_at: '2026-09-01T00:00:00.000Z',
    ...overrides,
  } as Lead
}

describe('lead duplicate mark and prior', () => {
  it('marks duplicate_review and duplicated', () => {
    expect(leadShowsDuplicateMark(metaLead({ status: 'duplicate_review' }))).toBe(true)
    expect(leadShowsDuplicateMark(metaLead({ status: 'duplicated' }))).toBe(true)
    expect(leadInDuplicateReviewContext(metaLead({ status: 'new' }))).toBe(false)
  })

  it('reads durable prior snapshot', () => {
    const prior = readDuplicatePrior({
      duplicate_prior_v1: {
        candidate_created: true,
        candidate_id: 'c1',
        display_name: 'Jan Kowalski',
        stage: 'rejected',
        reason: 'insufficient_experience',
        outcome: 'rejected',
      },
    })
    expect(prior?.display_name).toBe('Jan Kowalski')
    expect(prior?.reason).toBe('insufficient_experience')
    expect(prior?.outcome).toBe('rejected')
  })

  it('falls back to match.prior', () => {
    const prior = readDuplicatePrior({
      duplicate_match_v1: {
        suggested_candidate_id: 'c2',
        prior: { candidate_created: true, candidate_id: 'c2', stage: 'contacted' },
      },
    })
    expect(prior?.candidate_id).toBe('c2')
    expect(prior?.stage).toBe('contacted')
  })
})
