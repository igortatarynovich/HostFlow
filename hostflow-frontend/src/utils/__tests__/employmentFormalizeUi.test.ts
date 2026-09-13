// @vitest-environment node
import { describe, expect, it } from 'vitest'
import {
  assertFormalizeNoEmployeeSideEffects,
  buildFormalizePatchForPrimary,
  formalizeSurfaceMode,
  isFormalizeTerminalAllowCreate,
  operatorCanConfirmCurrentFormalItem,
  shouldEnterFormalizeFromEmployability,
  shouldShowFormalizeRuntimeChoice,
} from '../employmentFormalizeUi'

describe('employmentFormalizeUi (ESO-4 Formalize)', () => {
  it('named proof: ready_to_formalize → missing → resolve → complete → ready_to_create_employee', () => {
    expect(shouldEnterFormalizeFromEmployability({ decision: 'employable' })).toBe(true)
    expect(shouldEnterFormalizeFromEmployability({ decision: 'blocked' })).toBe(false)

    const missing = {
      decision: 'missing' as const,
      ready_to_formalize: true,
      ready_to_create_employee: false,
      employee_created: false,
      primary_item: {
        code: 'confirm_employment_contract_basis',
        kind: 'confirmation',
        message: 'Confirm employment contract basis',
      },
      active_missing: [
        {
          code: 'confirm_employment_contract_basis',
          kind: 'confirmation',
          message: 'Confirm employment contract basis',
        },
      ],
    }
    expect(formalizeSurfaceMode(missing).mode).toBe('missing')
    expect(operatorCanConfirmCurrentFormalItem(missing)).toBe(true)
    expect(buildFormalizePatchForPrimary('confirm_employment_contract_basis')).toEqual({
      confirmed_actions: ['confirm_employment_contract_basis'],
    })

    const complete = {
      decision: 'formalization_complete' as const,
      ready_to_create_employee: true,
      employee_created: false,
      hr_employee_card: false,
      employee_id: null,
      primary_item: {
        code: 'ready_to_create_employee',
        kind: 'threshold',
        message: 'Formalization complete',
      },
      active_missing: [],
    }
    expect(formalizeSurfaceMode(complete).mode).toBe('complete')
    expect(isFormalizeTerminalAllowCreate(complete)).toBe(true)
    expect(assertFormalizeNoEmployeeSideEffects(complete)).toBe(true)
    expect(operatorCanConfirmCurrentFormalItem(complete)).toBe(false)
  })

  it('zero-choice: no pathway/person/vacancy/employer/rates/subtype/position menus', () => {
    expect(shouldShowFormalizeRuntimeChoice('pathway')).toBe(false)
    expect(shouldShowFormalizeRuntimeChoice('person')).toBe(false)
    expect(shouldShowFormalizeRuntimeChoice('vacancy')).toBe(false)
    expect(shouldShowFormalizeRuntimeChoice('employer')).toBe(false)
    expect(shouldShowFormalizeRuntimeChoice('rates')).toBe(false)
    expect(shouldShowFormalizeRuntimeChoice('contract_subtype')).toBe(false)
    expect(shouldShowFormalizeRuntimeChoice('position')).toBe(false)
  })

  it('identity reuse is not operator-confirmable; work auth may be confirmed when missing', () => {
    expect(
      operatorCanConfirmCurrentFormalItem({
        decision: 'missing',
        primary_item: { code: 'identity_facts_present', kind: 'reuse_check' },
        active_missing: [{ code: 'identity_facts_present' }],
      }),
    ).toBe(false)
    expect(
      operatorCanConfirmCurrentFormalItem({
        decision: 'missing',
        primary_item: { code: 'work_authorization_evidence', kind: 'evidence' },
        active_missing: [{ code: 'work_authorization_evidence' }],
      }),
    ).toBe(true)
  })

  it('complete without ready_to_create_employee is not terminal allow', () => {
    expect(
      isFormalizeTerminalAllowCreate({
        decision: 'formalization_complete',
        ready_to_create_employee: false,
      }),
    ).toBe(false)
  })

  it('employee side-effects fail the ESO-4 assert', () => {
    expect(
      assertFormalizeNoEmployeeSideEffects({
        decision: 'formalization_complete',
        ready_to_create_employee: true,
        employee_created: true,
      }),
    ).toBe(false)
    expect(
      assertFormalizeNoEmployeeSideEffects({
        decision: 'formalization_complete',
        ready_to_create_employee: true,
        hr_employee_card: true,
      }),
    ).toBe(false)
  })
})
