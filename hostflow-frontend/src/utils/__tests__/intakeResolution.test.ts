import { describe, expect, it } from 'vitest'

import type { Lead } from '../../api/types'
import {
  leadIntakeWorkspaceBlocking,
  leadRoutingTableAction,
  manualProcessBlockHint,
  manualProcessBlockedUserMessage,
  type ManualProcessBlockCode,
} from '../intakeResolution'

/** Minimal CRM lead row for gating tests (mirrors GET /leads shape). */
function metaLead(overrides: Partial<Lead> & Record<string, unknown> = {}): Lead {
  return {
    id: '00000000-0000-4000-8000-000000000001',
    tenant_id: '00000000-0000-4000-8000-000000000002',
    source: 'meta',
    status: 'new',
    payload: {},
    created_at: '2026-01-01T00:00:00.000Z',
    ...overrides,
  } as Lead
}

describe('manualProcessBlockHint', () => {
  it('returns null when lead is missing, converted, or source does not support manual process', () => {
    expect(manualProcessBlockHint(null)).toBeNull()
    expect(manualProcessBlockHint(metaLead({ candidate_id: 'c-1' }))).toBeNull()
    expect(manualProcessBlockHint(metaLead({ source: 'webhook' }))).toBeNull()
  })

  it('reject (intake_resolution_v1.rejected) → INTAKE_REJECTED', () => {
    const lead = metaLead({
      normalized: {
        intake_resolution_v1: { status: 'rejected', reason_code: 'not_interested' },
      },
    })
    expect(manualProcessBlockHint(lead)).toBe('INTAKE_REJECTED')
  })

  it('request_info (intake_resolution_v1.info_requested) → INTAKE_INFO_REQUESTED', () => {
    const lead = metaLead({
      normalized: {
        intake_resolution_v1: { status: 'info_requested' },
      },
    })
    expect(manualProcessBlockHint(lead)).toBe('INTAKE_INFO_REQUESTED')
  })

  it('lead.status duplicate_review → DUPLICATE_REVIEW_PENDING (before vacancy checks)', () => {
    const lead = metaLead({
      status: 'duplicate_review',
      vacancy_id: '00000000-0000-4000-8000-000000000099',
      vacancy_routing_confirmed: false,
    })
    expect(manualProcessBlockHint(lead)).toBe('DUPLICATE_REVIEW_PENDING')
  })

  it('vacancy set but not confirmed → VACANCY_NOT_CONFIRMED (no pool intent)', () => {
    const lead = metaLead({
      status: 'new',
      vacancy_id: '00000000-0000-4000-8000-000000000099',
      vacancy_routing_confirmed: false,
    })
    expect(manualProcessBlockHint(lead)).toBe('VACANCY_NOT_CONFIRMED')
  })

  it('vacancy confirmed without RODO compliance → LEAD_RODO_REQUIRED', () => {
    const lead = metaLead({
      status: 'new',
      vacancy_id: '00000000-0000-4000-8000-000000000099',
      vacancy_routing_confirmed: true,
    })
    expect(manualProcessBlockHint(lead)).toBe('LEAD_RODO_REQUIRED')
  })

  it('vacancy confirmed + RODO sent → no client-side process block', () => {
    const lead = metaLead({
      status: 'new',
      vacancy_id: '00000000-0000-4000-8000-000000000099',
      vacancy_routing_confirmed: true,
      normalized: { rodo: { status: 'sent', sent_at: '2026-01-02T00:00:00+00:00' } },
    })
    expect(manualProcessBlockHint(lead)).toBeNull()
  })

  it('applies the same rules for csv_import as meta', () => {
    const lead = metaLead({
      source: 'csv_import',
      normalized: {
        intake_resolution_v1: { status: 'rejected', reason_code: 'other' },
      },
    })
    expect(manualProcessBlockHint(lead)).toBe('INTAKE_REJECTED')
  })
})

describe('leadRoutingTableAction', () => {
  const vac = '00000000-0000-4000-8000-0000000000aa'
  const vac2 = '00000000-0000-4000-8000-0000000000bb'

  it('needs_routing + suggested_vacancy_id + not confirmed → confirm_suggested', () => {
    const lead = metaLead({
      status: 'needs_routing',
      suggested_vacancy_id: vac,
      vacancy_routing_confirmed: false,
    })
    expect(leadRoutingTableAction(lead, false)).toEqual({ kind: 'confirm_suggested', vacancyId: vac })
  })

  it('VACANCY_NOT_CONFIRMED without suggested but vacancy_id → confirm_current', () => {
    const lead = metaLead({
      status: 'new',
      vacancy_id: vac2,
      vacancy_routing_confirmed: false,
    })
    expect(manualProcessBlockHint(lead)).toBe('VACANCY_NOT_CONFIRMED')
    expect(leadRoutingTableAction(lead, false)).toEqual({ kind: 'confirm_current', vacancyId: vac2 })
  })

  it('needs_routing + no vacancy + no suggested → pick_vacancy', () => {
    const lead = metaLead({
      status: 'needs_routing',
      suggested_vacancy_id: null,
      vacancy_id: null,
    })
    expect(leadRoutingTableAction(lead, false)).toEqual({ kind: 'pick_vacancy' })
  })

  it('services tenant or candidate → none', () => {
    const lead = metaLead({
      status: 'needs_routing',
      suggested_vacancy_id: vac,
      vacancy_routing_confirmed: false,
    })
    expect(leadRoutingTableAction(lead, true)).toEqual({ kind: 'none' })
    expect(leadRoutingTableAction(metaLead({ ...lead, candidate_id: 'c-1' }), false)).toEqual({ kind: 'none' })
  })

  it('duplicate_review → none (panel handles)', () => {
    const lead = metaLead({
      status: 'duplicate_review',
      suggested_vacancy_id: vac,
      vacancy_routing_confirmed: false,
    })
    expect(leadRoutingTableAction(lead, false)).toEqual({ kind: 'none' })
  })
})

describe('leadIntakeWorkspaceBlocking', () => {
  it('needs_routing + recruitment lead → blocking', () => {
    const lead = metaLead({ status: 'needs_routing' })
    expect(leadIntakeWorkspaceBlocking(lead, false)).toBe(true)
  })

  it('no block hint and not needs_routing → not blocking', () => {
    const lead = metaLead({
      status: 'new',
      vacancy_id: '00000000-0000-4000-8000-000000000099',
      vacancy_routing_confirmed: true,
    })
    expect(leadIntakeWorkspaceBlocking(lead, false)).toBe(false)
  })

  it('manualProcessBlockHint (e.g. duplicate_review) → blocking', () => {
    const lead = metaLead({ status: 'duplicate_review' })
    expect(leadIntakeWorkspaceBlocking(lead, false)).toBe(true)
  })

  it('candidate converted or services tenant → not blocking', () => {
    expect(leadIntakeWorkspaceBlocking(metaLead({ status: 'needs_routing', candidate_id: 'c-1' }), false)).toBe(false)
    expect(leadIntakeWorkspaceBlocking(metaLead({ status: 'needs_routing' }), true)).toBe(false)
  })
})

describe('manualProcessBlockedUserMessage', () => {
  it('falls back to the raw code when ``t`` does not resolve the key', () => {
    const t = (key: string) => key
    const code = 'INTAKE_REJECTED' as ManualProcessBlockCode
    expect(manualProcessBlockedUserMessage(t, code)).toBe('INTAKE_REJECTED')
  })

  it('returns translated copy when ``t`` resolves the key', () => {
    const code = 'VACANCY_NOT_CONFIRMED' as ManualProcessBlockCode
    const t = (key: string) => (key === `app.leads.messages.process_blocked.${code}` ? 'Confirm vacancy first.' : key)
    expect(manualProcessBlockedUserMessage(t, code)).toBe('Confirm vacancy first.')
  })
})
