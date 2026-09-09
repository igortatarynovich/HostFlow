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
  it('puts Fits on the happy path instead of Create candidate', () => {
    const onRunFits = vi.fn()
    const decision = resolveRecruitmentApplicationDecision({
      ...handlers,
      onRunFits,
      application: app({ extensions: { vacancy_id: 'vac-1' } }),
    })
    expect(decision.stateId).toBe('recruitment.triage')
    expect(decision.primaryAction?.id).toBe('call')
    expect(decision.secondaryActions?.map((row) => row.id)).toEqual([
      'run_fits',
      'follow_up',
      'pool',
      'reject',
    ])
    expect(decision.requiredContext).toEqual([])
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

  it('offers transfer after Fits prep, without create_candidate', () => {
    const onTransfer = vi.fn()
    const decision = resolveRecruitmentApplicationDecision({
      ...handlers,
      onTransferToEmployment: onTransfer,
      application: app({
        outcome_entity_type: 'candidate',
        outcome_entity_id: 'cand-1',
        extensions: {
          ready_for_employment_prep_v1: {
            next_action: 'offer_handoff',
            package_valid: true,
          },
        },
      }),
    })
    expect(decision.stateId).toBe('recruitment.offer_handoff')
    expect(decision.primaryAction?.id).toBe('transfer_to_employment')
    expect(decision.secondaryActions?.some((row) => row.id === 'create_candidate')).toBeFalsy()
    expect(decision.secondaryActions?.some((row) => row.id === 'open_candidate')).toBeFalsy()
  })

  it('stays on the same card after Transfer instead of open_candidate', () => {
    const decision = resolveRecruitmentApplicationDecision({
      ...handlers,
      application: app({
        status: 'completed',
        tab_bucket: 'completed',
        outcome_entity_type: 'candidate',
        outcome_entity_id: 'cand-1',
        extensions: {
          ready_for_employment_prep_v1: {
            next_action: 'handed_off',
            handoff_id: 'handoff-1',
          },
        },
      }),
    })
    expect(decision.stateId).toBe('recruitment.handed_off')
    expect(decision.primaryAction).toBeNull()
    expect(decision.terminal).toBeFalsy()
  })
})
