import { describe, expect, it, vi } from 'vitest'
import { resolveEmploymentSpineDecision } from '../employmentSpineDecision'

function t(key: string, options?: { defaultValue?: string }) {
  return options?.defaultValue || key
}

const handlers = {
  busy: false,
  onFormalize: vi.fn(),
  onConfirmStart: vi.fn(),
  t,
}

describe('resolveEmploymentSpineDecision', () => {
  it('offers formalize when ready_to_formalize', () => {
    const decision = resolveEmploymentSpineDecision({
      ...handlers,
      formalize: { ready_to_formalize: true, ready_to_create_employee: false },
    })
    expect(decision.stateId).toBe('employment.formalize')
    expect(decision.primaryAction?.id).toBe('formalize')
    expect(decision.primaryAction?.label).toBe('Оформить')
  })

  it('offers confirm start when ready_to_create_employee', () => {
    const decision = resolveEmploymentSpineDecision({
      ...handlers,
      formalize: { ready_to_formalize: true, ready_to_create_employee: true },
    })
    expect(decision.stateId).toBe('employment.confirm_start')
    expect(decision.primaryAction?.id).toBe('confirm_physical_start')
    expect(decision.primaryAction?.label).toBe('Подтвердить выход')
  })

  it('shows Started after physical confirm', () => {
    const decision = resolveEmploymentSpineDecision({
      ...handlers,
      started: { started: true, decision: 'started' },
    })
    expect(decision.stateId).toBe('employment.started')
    expect(decision.primaryAction).toBeNull()
    expect(decision.terminal).toBe(true)
  })
})
