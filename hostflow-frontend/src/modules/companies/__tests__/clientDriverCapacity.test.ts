import { describe, expect, it } from 'vitest'
import {
  blockingReasonsForOrder,
  buildBlockingOrders,
  employedCandidatesCount,
} from '../clientDriverCapacity'

describe('employedCandidatesCount', () => {
  it('reads recruitment_candidates_employed from company metrics', () => {
    expect(employedCandidatesCount({ recruitment_candidates_employed: 7 })).toBe(7)
    expect(employedCandidatesCount({ recruitment_candidates_employed: 0 })).toBe(0)
    expect(employedCandidatesCount({})).toBe(0)
  })
})

describe('blockingReasonsForOrder', () => {
  it('flags capacity when employed headcount is below required_drivers', () => {
    const reasons = blockingReasonsForOrder(
      { starts_at: '2024-01-01', ends_at: '2024-12-31', status: 'active', required_drivers: 60 },
      0,
    )
    expect(reasons).toContain('capacity')
  })

  it('does not flag capacity when employed candidates cover the order', () => {
    const reasons = blockingReasonsForOrder(
      { starts_at: '2024-01-01', ends_at: '2024-12-31', status: 'active', required_drivers: 2 },
      2,
    )
    expect(reasons).not.toContain('capacity')
  })

  it('ignores manual hired_drivers on the order payload', () => {
    const reasons = blockingReasonsForOrder(
      {
        starts_at: '2024-01-01',
        ends_at: '2024-12-31',
        status: 'active',
        required_drivers: 60,
        hired_drivers: 60,
      },
      0,
    )
    expect(reasons).toContain('capacity')
  })
})

describe('buildBlockingOrders', () => {
  it('returns empty when employed count covers the order and other fields are set', () => {
    expect(
      buildBlockingOrders(
        [
          {
            id: '1',
            title: 'Kierowcy CE',
            starts_at: '2024-01-01',
            ends_at: '2024-12-31',
            status: 'active',
            required_drivers: 2,
          },
        ],
        2,
        'unnamed',
      ),
    ).toEqual([])
  })
})
