// @vitest-environment node
import { describe, expect, it } from 'vitest'
import {
  assertReplayEmitsNoSecondStartEvent,
  assertStartedNoAutoTransition,
  buildPhysicalStartConfirmation,
  formalizationCompleteImpliesStartedEntry,
  isStartedTerminal,
  needsStartDateInput,
  operatorCanConfirmPhysicalStart,
  shouldEnterStartedFromFormalize,
  shouldRedirectToEmployeeCardFromHandoffHost,
  shouldShowStartedRuntimeChoice,
  startedSurfaceMode,
} from '../employmentStartedUi'

describe('employmentStartedUi (ESO-5 Started)', () => {
  it('named proof: ready_to_create_employee → required start fact if missing → confirm → Started', () => {
    expect(
      shouldEnterStartedFromFormalize({
        decision: 'formalization_complete',
        ready_to_create_employee: true,
      }),
    ).toBe(true)
    expect(
      shouldEnterStartedFromFormalize({
        decision: 'formalization_complete',
        ready_to_create_employee: false,
      }),
    ).toBe(false)
    expect(
      shouldEnterStartedFromFormalize({
        decision: 'missing',
        ready_to_create_employee: false,
      }),
    ).toBe(false)
    expect(
      formalizationCompleteImpliesStartedEntry({
        decision: 'formalization_complete',
        ready_to_create_employee: true,
      }),
    ).toBe(false)

    const missingDate = {
      decision: 'not_started' as const,
      started: false,
      ready_to_create_employee: true,
      primary_item: {
        code: 'start_date',
        kind: 'fact',
        message: 'Start date is required to confirm physical start',
      },
      active_missing: [{ code: 'start_date', kind: 'fact' }],
      formalization_complete_implies_started: false,
      employee_created_implies_started: false,
    }
    expect(startedSurfaceMode(missingDate).mode).toBe('missing_fact')
    expect(needsStartDateInput(missingDate)).toBe(true)
    expect(operatorCanConfirmPhysicalStart(missingDate)).toBe(false)

    const awaiting = {
      decision: 'not_started' as const,
      started: false,
      ready_to_create_employee: true,
      start_date: '2026-09-15',
      primary_item: {
        code: 'confirm_physical_start',
        kind: 'confirmation',
        message: 'Confirm physical first day at work',
      },
      active_missing: [{ code: 'confirm_physical_start', kind: 'confirmation' }],
      formalization_complete_implies_started: false,
      employee_created_implies_started: false,
    }
    expect(startedSurfaceMode(awaiting).mode).toBe('awaiting_confirm')
    expect(operatorCanConfirmPhysicalStart(awaiting)).toBe(true)
    expect(buildPhysicalStartConfirmation()).toEqual({ confirmed: true })
    expect(buildPhysicalStartConfirmation({ startDate: '2026-09-16' })).toEqual({
      confirmed: true,
      start_date: '2026-09-16',
    })

    const started = {
      decision: 'started' as const,
      started: true,
      start_date: '2026-09-15',
      start_event_emitted: true,
      idempotent_replay: false,
      active_missing: [],
      formalization_complete_implies_started: false,
      employee_created_implies_started: false,
      hr_employee_card: false,
    }
    expect(startedSurfaceMode(started).mode).toBe('started')
    expect(isStartedTerminal(started)).toBe(true)
    expect(assertStartedNoAutoTransition(started)).toBe(true)
    expect(operatorCanConfirmPhysicalStart(started)).toBe(false)
  })

  it('named proof: replay → already_started → one employee_physical_start event', () => {
    const replay = {
      decision: 'already_started' as const,
      started: true,
      start_event_emitted: false,
      idempotent_replay: true,
      audit_event_type: 'employee_physical_start',
      active_missing: [],
      formalization_complete_implies_started: false,
      employee_created_implies_started: false,
    }
    expect(startedSurfaceMode(replay).mode).toBe('already_started')
    expect(isStartedTerminal(replay)).toBe(true)
    expect(assertReplayEmitsNoSecondStartEvent(replay)).toBe(true)
    expect(
      assertReplayEmitsNoSecondStartEvent({
        ...replay,
        start_event_emitted: true,
      }),
    ).toBe(false)
  })

  it('locks: no employee-card redirect; zero-choice; no auto from employee/formalize', () => {
    expect(
      shouldRedirectToEmployeeCardFromHandoffHost({
        workforceEmployeeId: 'emp-1',
        showStartedSurface: true,
        started: { decision: 'started', started: true },
      }),
    ).toBe(false)
    expect(shouldShowStartedRuntimeChoice('pathway')).toBe(false)
    expect(shouldShowStartedRuntimeChoice('employer')).toBe(false)
    expect(shouldShowStartedRuntimeChoice('vacancy')).toBe(false)
    expect(
      assertStartedNoAutoTransition({
        decision: 'not_started',
        started: false,
        employee_created: true,
        formalization_complete_implies_started: false,
        employee_created_implies_started: false,
      }),
    ).toBe(true)
    expect(
      assertStartedNoAutoTransition({
        decision: 'not_started',
        started: true,
        formalization_complete_implies_started: false,
        employee_created_implies_started: false,
      }),
    ).toBe(false)
  })
})
