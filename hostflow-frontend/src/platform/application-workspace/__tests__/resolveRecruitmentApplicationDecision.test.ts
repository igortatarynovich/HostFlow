import { describe, expect, it, vi } from 'vitest'
import type { Application } from '../../../api/types/application'
import { resolveRecruitmentApplicationDecision, applicationEmploymentSpinePhase } from '../resolveRecruitmentApplicationDecision'

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

  it('makes Подходит the primary action when intake next_action is fits', () => {
    const onCreateCandidate = vi.fn()
    const decision = resolveRecruitmentApplicationDecision({
      ...handlers,
      onCreateCandidate,
      application: app({
        next_action: 'fits',
        extensions: { vacancy_id: 'vac-1' },
      }),
    })
    expect(decision.stateId).toBe('recruitment.fits_to_candidate')
    expect(decision.primaryAction?.id).toBe('run_fits')
    expect(decision.primaryAction?.onClick).toBe(onCreateCandidate)
    expect(decision.secondaryActions?.map((row) => row.id)).toEqual(['follow_up', 'reject'])
    expect(decision.secondaryActions?.some((row) => row.id === 'transfer_to_employment')).toBeFalsy()
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

  it('opens the candidate instead of offering employment transfer', () => {
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
    expect(decision.stateId).toBe('recruitment.candidate_created')
    expect(decision.primaryAction?.id).toBe('open_candidate')
    expect(decision.primaryAction?.id).not.toBe('transfer_to_employment')
  })

  it('opens the candidate after a previous handoff record', () => {
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
    expect(decision.stateId).toBe('recruitment.candidate_created')
    expect(decision.primaryAction?.id).toBe('open_candidate')
  })
})

describe('applicationEmploymentSpinePhase', () => {
  it('is recruitment until Transfer', () => {
    expect(applicationEmploymentSpinePhase(app({ extensions: { vacancy_id: 'vac-1' } }))).toBe('recruitment')
  })

  it('is employment after Transfer, from existing handoff prep only', () => {
    expect(
      applicationEmploymentSpinePhase(
        app({
          extensions: {
            ready_for_employment_prep_v1: { next_action: 'handed_off', handoff_id: 'h-1' },
          },
        }),
      ),
    ).toBe('employment')
  })

  it('does not treat Employment Started as a Recruitment prep next_action', () => {
    expect(
      applicationEmploymentSpinePhase(
        app({
          extensions: {
            ready_for_employment_prep_v1: {
              next_action: 'started',
              started: true,
              start_date: '2026-09-09',
              handoff_id: 'h-1',
            },
          },
        }),
      ),
    ).toBe('employment')
  })
})
