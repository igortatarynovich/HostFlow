import { describe, expect, it, vi } from 'vitest'
import type { Application } from '../../../api/types/application'
import { resolveRecruitmentApplicationDecision } from '../resolveRecruitmentApplicationDecision'

function t(key: string, options?: { defaultValue?: string }) {
  return options?.defaultValue || key
}

function app(overrides: Partial<Application> = {}): Application {
  return {
    id: 'app-1',
    module: 'recruitment',
    contact: { name: 'Ada', phone: '+48111' },
    title: 'Ada',
    status: 'in_progress',
    tab_bucket: 'in_progress',
    ...overrides,
  }
}

const handlers = {
  patching: false,
  busy: false,
  onStage: vi.fn(),
  onCreateCandidate: vi.fn(),
  onFollowUp: vi.fn(),
  onReject: vi.fn(),
  onPool: vi.fn(),
  t,
}

describe('resolveRecruitmentApplicationDecision', () => {
  it('keeps create-candidate as a secondary action, not the primary', () => {
    const decision = resolveRecruitmentApplicationDecision({
      ...handlers,
      application: app(),
    })
    expect(decision.stateId).toBe('recruitment.triage')
    expect(decision.primaryAction?.id).toBe('call')
    expect(decision.primaryAction?.href).toBe('tel:+48111')
    expect(decision.secondaryActions?.map((row) => row.id)).toEqual([
      'create_candidate',
      'follow_up',
      'pool',
      'reject',
    ])
  })

  it('does not offer convert when the application is already a candidate', () => {
    const decision = resolveRecruitmentApplicationDecision({
      ...handlers,
      application: app({
        status: 'completed',
        tab_bucket: 'completed',
        outcome_entity_type: 'candidate',
        outcome_entity_id: 'cand-1',
      }),
    })
    expect(decision.primaryAction?.id).toBe('open_candidate')
    expect(decision.secondaryActions?.some((row) => row.id === 'create_candidate')).toBeFalsy()
  })
})
