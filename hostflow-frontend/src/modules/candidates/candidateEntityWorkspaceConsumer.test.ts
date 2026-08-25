import { describe, expect, it } from 'vitest'
import { entityPassportAllowsAction, entityPassportHasTerminalOutcome } from '../../platform/entity-model'
import { augmentCandidateForEntityPassport, buildCandidateEntityWorkspaceActionConfig } from './candidateEntityWorkspaceUtils'
import { resolveCandidateEntityPassport } from './candidatesEntityModel'

const t = (key: string, options?: Record<string, unknown>) => {
  const dv = options?.defaultValue
  return typeof dv === 'string' ? dv : key
}

const emptyBlockers = { missing: [], problematic: [], inProgress: [] }

describe('Candidate Entity Workspace consumer', () => {
  it('augment + passport — rejected candidate has outcome, no actions in config', () => {
    const augmented = augmentCandidateForEntityPassport({
      id: 'c1',
      first_name: 'Jan',
      last_name: 'Kowalski',
      stage: 'rejected',
      row_status: 'rejected',
      phone: '+48123456789',
    } as never)

    const passport = resolveCandidateEntityPassport({
      t,
      locale: 'ru',
      candidate: augmented,
      stageLabel: 'Отклонён',
      rowStatusLabel: 'Отклонён',
      docsBlockers: emptyBlockers,
      phoneHref: 'tel:+48123456789',
    })

    expect(entityPassportHasTerminalOutcome(passport)).toBe(true)
    expect(entityPassportAllowsAction(passport, 'call')).toBe(false)

    const actionConfig = buildCandidateEntityWorkspaceActionConfig({
      passport,
      phoneHref: 'tel:+48123456789',
    })
    expect(actionConfig.contextActions).toBeUndefined()
  })

  it('augment + passport — active candidate gets context primary action', () => {
    const augmented = augmentCandidateForEntityPassport({
      id: 'c2',
      first_name: 'Piotr',
      last_name: 'Test',
      stage: 'new',
      phone: '+48111111111',
    } as never)

    const passport = resolveCandidateEntityPassport({
      t,
      locale: 'ru',
      candidate: augmented,
      stageLabel: 'Новый',
      docsBlockers: emptyBlockers,
      phoneHref: 'tel:+48111111111',
    })

    const actionConfig = buildCandidateEntityWorkspaceActionConfig({
      passport,
      phoneHref: 'tel:+48111111111',
    })

    expect(actionConfig.contextActions?.primary?.href).toBe('tel:+48111111111')
    expect(passport.sections.outcome).toBeNull()
  })
})
