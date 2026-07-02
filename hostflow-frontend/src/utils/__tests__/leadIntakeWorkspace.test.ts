import { describe, expect, it } from 'vitest'

import type { Lead } from '../../api/types'
import {
  intakeStickyVacancySummary,
  intakeWorkspaceHeader,
  leadIntakeColumnStatusKey,
  leadIntakeWorkspaceSuppressesCrmChrome,
  leadQueueIntakeShellOk,
  recruitmentAgencyIntakeFirstLayout,
} from '../leadIntakeWorkspace'

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

const t = (key: string, opts?: { values?: Record<string, string | number> }) => {
  if (opts?.values?.title) return `pending:${opts.values.title}`
  return key
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

  it('shows intake shell for meta lead awaiting routing decision', () => {
    const lead = metaLead({ status: 'needs_routing', vacancy_id: 'vac-1', vacancy_title: 'Driver' })
    expect(leadQueueIntakeShellOk(lead, false)).toBe(true)
  })
})

describe('recruitmentAgencyIntakeFirstLayout', () => {
  it('is true for recruitment agency leads only', () => {
    expect(recruitmentAgencyIntakeFirstLayout(false, false)).toBe(true)
    expect(recruitmentAgencyIntakeFirstLayout(true, false)).toBe(false)
    expect(recruitmentAgencyIntakeFirstLayout(false, true)).toBe(false)
  })
})

describe('leadIntakeWorkspaceSuppressesCrmChrome', () => {
  it('suppresses CRM chrome for active intake leads', () => {
    const lead = metaLead({ status: 'needs_routing' })
    expect(leadIntakeWorkspaceSuppressesCrmChrome(lead, false)).toBe(true)
  })

  it('does not suppress after conversion', () => {
    const lead = metaLead({ candidate_id: 'cand-1' })
    expect(leadIntakeWorkspaceSuppressesCrmChrome(lead, false)).toBe(false)
  })
})

describe('intakeWorkspaceHeader', () => {
  it('returns routing_unconfirmed when vacancy not confirmed', () => {
    const lead = metaLead({ vacancy_id: 'v1', vacancy_title: 'Driver', vacancy_routing_confirmed: false })
    expect(intakeWorkspaceHeader(lead, false)).toEqual({ tone: 'routing_unconfirmed' })
  })

  it('returns converted tone when candidate exists', () => {
    const lead = metaLead({ candidate_id: 'c1' })
    expect(intakeWorkspaceHeader(lead, false)).toEqual({ tone: 'converted' })
  })
})

describe('leadIntakeColumnStatusKey', () => {
  it('maps info_requested intake to column key', () => {
    const lead = metaLead({
      status: 'processed',
      normalized: { intake_resolution_v1: { status: 'info_requested' } },
    })
    expect(leadIntakeColumnStatusKey(lead, false)).toBe('app.leads.intake_workspace.col.info_requested')
  })
})

describe('intakeStickyVacancySummary', () => {
  it('shows pending route when vacancy exists but is unconfirmed', () => {
    const lead = metaLead({ vacancy_id: 'v1', vacancy_title: 'CE Driver', vacancy_routing_confirmed: false })
    expect(intakeStickyVacancySummary(lead, t)).toBe('pending:CE Driver')
  })
})
