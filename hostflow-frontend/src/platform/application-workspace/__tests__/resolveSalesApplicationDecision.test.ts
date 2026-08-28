import { describe, expect, it, vi } from 'vitest'
import type { Application } from '../../../api/types/application'
import { resolveSalesApplicationDecision } from '../resolveSalesApplicationDecision'

function t(key: string, options?: { defaultValue?: string }) {
  return options?.defaultValue || key
}

function app(overrides: Partial<Application>): Application {
  return {
    id: 'si-1',
    module: 'sales',
    contact: { name: 'Jane', phone: '+48111' },
    title: 'Acme',
    status: 'new',
    tab_bucket: 'new',
    ...overrides,
  }
}

describe('resolveSalesApplicationDecision', () => {
  it('rejected inquiry only offers stage change, not convert or call', () => {
    const onStage = vi.fn()
    const onConvert = vi.fn()
    const decision = resolveSalesApplicationDecision({
      application: app({ status: 'rejected', tab_bucket: 'completed' }),
      converting: false,
      patching: false,
      onStage,
      onConvert,
      t,
    })
    expect(decision.terminal).toBe(true)
    expect(decision.primaryAction).toBeNull()
    expect(decision.contactActions).toBeUndefined()
    expect(decision.secondaryActions?.map((row) => row.id)).toEqual(['interested_later', 'reopen'])
    decision.secondaryActions?.[0]?.onClick?.()
    expect(onStage).toHaveBeenCalledWith('qualified')
    expect(onConvert).not.toHaveBeenCalled()
  })

  it('open inquiry still allows close and convert-adjacent actions', () => {
    const decision = resolveSalesApplicationDecision({
      application: app({ status: 'in_progress', tab_bucket: 'in_progress', extensions: { workflow_step: 3 } }),
      converting: false,
      patching: false,
      onStage: vi.fn(),
      onConvert: vi.fn(),
      t,
    })
    expect(decision.terminal).toBeFalsy()
    expect(decision.primaryAction?.id).toBe('convert')
    expect(decision.secondaryActions?.some((row) => row.id === 'close')).toBe(true)
  })

  it('open inquiry with an existing client opens the card instead of creating', () => {
    const onConvert = vi.fn()
    const decision = resolveSalesApplicationDecision({
      application: app({
        status: 'waiting',
        tab_bucket: 'waiting',
        title: 'Synergia Kadry',
        extensions: {
          workflow_step: 3,
          existing_client: {
            company_id: 'co-synergia',
            name: 'SYNERGIA KADRY sp. z o.o.',
          },
        },
      }),
      converting: false,
      patching: false,
      onStage: vi.fn(),
      onConvert,
      t,
    })
    expect(decision.stateId).toBe('sales.existing_client')
    expect(decision.primaryAction?.id).toBe('open_existing_client')
    expect(decision.primaryAction?.href).toContain('co-synergia')
    expect(decision.secondaryActions?.map((row) => row.id)).toContain('link_existing')
    expect(decision.primaryAction?.id).not.toBe('convert')
  })
})
