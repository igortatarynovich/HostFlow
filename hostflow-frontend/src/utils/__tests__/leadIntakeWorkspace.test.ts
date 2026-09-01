import { describe, expect, it } from 'vitest'

import type { Lead } from '../../api/types'
import { leadIntakeColumnStatusKey, leadQueueIntakeShellOk } from '../leadIntakeWorkspace'

function metaLead(overrides: Partial<Lead> & Record<string, unknown> = {}): Lead {
  return {
    id: '00000000-0000-4000-8000-000000000011',
    tenant_id: '00000000-0000-4000-8000-000000000022',
    source: 'meta',
    status: 'new',
    payload: {},
    created_at: '2026-01-01T00:00:00.000Z',
    ...overrides,
  } as Lead
}

describe('leadQueueIntakeShellOk', () => {
  it('does not show intake shell for rejected intake resolution', () => {
    const lead = metaLead({
      status: 'rejected',
      normalized: {
        intake_resolution_v1: { status: 'rejected', reason_code: 'other' },
      },
    })
    expect(leadQueueIntakeShellOk(lead, false)).toBe(false)
  })
})

describe('leadIntakeColumnStatusKey', () => {
  it('shows in progress when a call result exists', () => {
    const lead = metaLead({
      status: 'needs_routing',
      source: 'meta',
      normalized: {
        call_result_v1: { result: 'no_answer', at: '2026-09-01T10:00:00Z' },
      },
    })
    expect(leadIntakeColumnStatusKey(lead, false)).toBe('app.leads.intake_workspace.lifecycle.in_progress')
  })

  it('shows new when nobody has worked the lead', () => {
    const lead = metaLead({
      status: 'needs_routing',
      source: 'meta',
      normalized: { intake_resolution_v1: { status: 'new' } },
    })
    expect(leadIntakeColumnStatusKey(lead, false)).toBe('app.leads.intake_workspace.lifecycle.new')
  })
})
