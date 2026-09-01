import { describe, expect, it } from 'vitest'

import type { Lead } from '../../api/types'
import { leadIntakeLifecycle, parseIntakeQueueFilter } from '../leadIntakeLifecycle'

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

describe('leadIntakeLifecycle', () => {
  it('stays new until someone works the lead', () => {
    expect(
      leadIntakeLifecycle(metaLead({ normalized: { intake_resolution_v1: { status: 'new' } } })),
    ).toBe('new')
  })

  it('treats a no-answer call as in progress, not a stage', () => {
    expect(
      leadIntakeLifecycle(
        metaLead({
          normalized: {
            intake_resolution_v1: { status: 'new' },
            call_result_v1: { result: 'no_answer' },
          },
        }),
      ),
    ).toBe('in_progress')
  })

  it('prefers the API projection when present', () => {
    expect(leadIntakeLifecycle(metaLead({ intake_lifecycle: 'converted' }))).toBe('converted')
  })
})

describe('parseIntakeQueueFilter', () => {
  it('accepts new queue names and legacy intake_lane aliases', () => {
    expect(parseIntakeQueueFilter('new')).toBe('new')
    expect(parseIntakeQueueFilter('to_call')).toBe('new')
    expect(parseIntakeQueueFilter('called')).toBe('in_progress')
    expect(parseIntakeQueueFilter('duplicate')).toBe('needs_decision')
    expect(parseIntakeQueueFilter('rejected')).toBe('completed')
    expect(parseIntakeQueueFilter('bogus')).toBe('')
  })
})
