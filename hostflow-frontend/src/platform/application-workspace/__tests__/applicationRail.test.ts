import { describe, expect, it } from 'vitest'

import type { Application } from '../../api/types/application'
import { applicationComments, applicationRodoState, applicationStageCode } from '../applicationRail'
import { resolveRecruitmentApplicationDecision } from '../resolveRecruitmentApplicationDecision'

function app(overrides: Partial<Application> = {}): Application {
  return {
    id: 'app-1',
    module: 'recruitment',
    contact: { name: 'Anna', phone: '+48111', email: 'a@example.com' },
    title: 'Anna',
    status: 'new',
    tab_bucket: 'new',
    extensions: {},
    ...overrides,
  }
}

const t = (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue || key

describe('applicationRail helpers', () => {
  it('reads unsatisfied RODO from extensions', () => {
    const state = applicationRodoState(
      app({ extensions: { rodo: { status: 'manual_required', satisfied: false, policy_blocked: false } } }),
    )
    expect(state.satisfied).toBe(false)
    expect(state.status).toBe('manual_required')
  })

  it('treats converted applications as RODO satisfied', () => {
    const state = applicationRodoState(
      app({ outcome_entity_type: 'candidate', outcome_entity_id: 'cand-1' }),
    )
    expect(state.satisfied).toBe(true)
  })

  it('maps comments newest-first payload', () => {
    const rows = applicationComments(
      app({
        extensions: {
          comments: [{ note: 'First', at: '2026-08-20T10:00:00Z' }],
        },
      }),
    )
    expect(rows).toEqual([{ note: 'First', at: '2026-08-20T10:00:00Z', by: null }])
  })

  it('falls back stage from application status', () => {
    expect(applicationStageCode(app({ status: 'rejected' }))).toBe('lost')
    expect(applicationStageCode(app({ extensions: { stage: 'contacted' } }))).toBe('contacted')
  })
})

describe('resolveRecruitmentApplicationDecision', () => {
  it('puts RODO/stage/comments blocks on the open application rail', () => {
    const decision = resolveRecruitmentApplicationDecision({
      application: app(),
      patching: false,
      busy: false,
      rodoSatisfied: false,
      onStage: () => undefined,
      onCreateCandidate: () => undefined,
      onFollowUp: () => undefined,
      onReject: () => undefined,
      t,
    })
    expect(decision.requiredContext).toEqual(['contacts', 'workflow', 'vacancy', 'assignee', 'summary'])
    expect(decision.primaryAction?.disabled).toBe(true)
    expect(decision.variant).toBe('blocker')
  })

  it('enables create-candidate when RODO is satisfied', () => {
    const decision = resolveRecruitmentApplicationDecision({
      application: app({ status: 'in_progress', contact: { name: 'Anna' } }),
      patching: false,
      busy: false,
      rodoSatisfied: true,
      onStage: () => undefined,
      onCreateCandidate: () => undefined,
      onFollowUp: () => undefined,
      onReject: () => undefined,
      t,
    })
    expect(decision.primaryAction?.id).toBe('create_candidate')
    expect(decision.primaryAction?.disabled).toBe(false)
  })
})
