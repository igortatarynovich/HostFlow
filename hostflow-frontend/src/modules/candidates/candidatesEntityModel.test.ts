import { describe, expect, it } from 'vitest'
import { entityPassportAllowsAction, entityPassportHasTerminalOutcome } from '../../platform/entity-model'
import { resolveCandidateEntityPassport } from './candidatesEntityModel'

const t = (key: string, options?: Record<string, unknown>) => {
  const dv = options?.defaultValue
  if (typeof dv === 'string' && options?.values && typeof options.values === 'object') {
    return Object.entries(options.values as Record<string, string>).reduce(
      (acc, [k, v]) => acc.replace(`{${k}}`, v),
      dv,
    )
  }
  return typeof dv === 'string' ? dv : key
}

const emptyBlockers = { missing: [], problematic: [], inProgress: [] }

describe('resolveCandidateEntityPassport', () => {
  it('terminal rejected — no call capability, outcome set', () => {
    const passport = resolveCandidateEntityPassport({
      t,
      locale: 'ru',
      candidate: {
        id: 'c1',
        first_name: 'Jan',
        last_name: 'Kowalski',
        stage: 'rejected',
        row_status: 'rejected',
        phone: '+48123456789',
      },
      stageLabel: 'Отклонён',
      rowStatusLabel: 'Отклонён',
      docsBlockers: emptyBlockers,
      phoneHref: 'tel:+48123456789',
    })

    expect(passport.sections.state.phaseId).toBe('candidate.rejected')
    expect(passport.sections.state.recruiterWorkActive).toBe(false)
    expect(passport.sections.actions.workAllowed).toBe(false)
    expect(passport.sections.outcome?.title).toContain('rejected')
    expect(entityPassportHasTerminalOutcome(passport)).toBe(true)
    expect(entityPassportAllowsAction(passport, 'call')).toBe(false)
    expect(passport.sections.actions.capabilities).toHaveLength(0)
  })

  it('recruitment complete / HR handoff — terminal, no recruiter work', () => {
    const passport = resolveCandidateEntityPassport({
      t,
      locale: 'ru',
      candidate: {
        id: 'c2',
        first_name: 'Anna',
        last_name: 'Nowak',
        stage: 'ready_for_handoff',
        row_status: 'handed_off',
      },
      stageLabel: 'Handoff',
      handoffStatus: {
        client_owns: true,
        accepted: null,
        pending: null,
      },
      docsBlockers: emptyBlockers,
    })

    expect(passport.sections.state.phaseId).toBe('candidate.recruitment_complete')
    expect(passport.sections.actions.workAllowed).toBe(false)
    expect(passport.sections.outcome?.title).toMatch(/HR|Рекрутинг/i)
    expect(entityPassportAllowsAction(passport, 'call')).toBe(false)
  })

  it('new candidate — active contact work, call allowed', () => {
    const passport = resolveCandidateEntityPassport({
      t,
      locale: 'ru',
      candidate: {
        id: 'c3',
        first_name: 'Piotr',
        last_name: 'Test',
        stage: 'new',
        phone: '+48111111111',
      },
      stageLabel: 'Новый',
      docsBlockers: emptyBlockers,
      phoneHref: 'tel:+48111111111',
      contactAttemptCount: 0,
    })

    expect(passport.sections.state.phaseId).toBe('candidate.contact')
    expect(passport.sections.state.recruiterWorkActive).toBe(true)
    expect(passport.sections.actions.workAllowed).toBe(true)
    expect(passport.sections.outcome).toBeNull()
    expect(entityPassportAllowsAction(passport, 'call')).toBe(true)
  })
})
