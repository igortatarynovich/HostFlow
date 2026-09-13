import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from '../../../i18n'
import HrEmploymentStartedPanel from '../HrEmploymentStartedPanel'

describe('HrEmploymentStartedPanel', () => {
  it('awaiting confirm → Confirm physical start (human only, no auto)', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <I18nProvider>
        <HrEmploymentStartedPanel
          started={{
            policy_id: 'employment_started.v1',
            decision: 'not_started',
            started: false,
            ready_to_create_employee: true,
            start_date: '2026-09-15',
            employee_created: true,
            employee_created_implies_started: false,
            formalization_complete_implies_started: false,
            primary_item: {
              code: 'confirm_physical_start',
              kind: 'confirmation',
              message: 'Confirm physical first day at work',
            },
            active_missing: [{ code: 'confirm_physical_start', kind: 'confirmation' }],
          }}
          onConfirm={onConfirm}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-started-awaiting-confirm')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-started-known-date').textContent).toMatch(/2026-09-15/)
    expect(screen.getByTestId('hr-employment-started-human-confirm')).toBeTruthy()
    expect(screen.queryByRole('combobox')).toBeNull()
    await user.click(screen.getByTestId('hr-employment-started-confirm'))
    expect(onConfirm).toHaveBeenCalledWith({ confirmed: true })
  })

  it('missing start_date shows only date fact + confirm with date', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <I18nProvider>
        <HrEmploymentStartedPanel
          started={{
            policy_id: 'employment_started.v1',
            decision: 'not_started',
            started: false,
            ready_to_create_employee: true,
            primary_item: {
              code: 'start_date',
              kind: 'fact',
              message: 'Start date is required to confirm physical start',
            },
            active_missing: [{ code: 'start_date', kind: 'fact' }],
          }}
          onConfirm={onConfirm}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-started-missing-date')).toBeTruthy()
    expect(screen.queryByTestId('hr-employment-started-confirm')).toBeNull()
    fireEvent.change(screen.getByTestId('hr-employment-started-date-input'), {
      target: { value: '2026-09-20' },
    })
    await user.click(screen.getByTestId('hr-employment-started-confirm-with-date'))
    expect(onConfirm).toHaveBeenCalledWith({ confirmed: true, start_date: '2026-09-20' })
  })

  it('started terminal stays on host — no employee redirect / HR-card CTA', () => {
    render(
      <I18nProvider>
        <HrEmploymentStartedPanel
          started={{
            policy_id: 'employment_started.v1',
            decision: 'started',
            started: true,
            start_date: '2026-09-15',
            start_event_emitted: true,
            idempotent_replay: false,
            hr_employee_card: false,
            active_missing: [],
          }}
          onConfirm={() => undefined}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-started-terminal')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-started-terminal-title').textContent).toMatch(/Started/i)
    expect(screen.getByTestId('hr-employment-started-event')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-started-no-employee-redirect')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-started-no-hr-card-cta')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /create employee|open employee|hr.?card/i })).toBeNull()
    expect(screen.queryByTestId('hr-employment-started-confirm')).toBeNull()
  })

  it('already_started replay shows idempotent — no second start CTA', () => {
    render(
      <I18nProvider>
        <HrEmploymentStartedPanel
          started={{
            policy_id: 'employment_started.v1',
            decision: 'already_started',
            started: true,
            start_event_emitted: false,
            idempotent_replay: true,
            start_date: '2026-09-15',
            active_missing: [],
          }}
          onConfirm={() => undefined}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-started-terminal')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-started-replay').textContent).toMatch(/already_started/i)
    expect(screen.queryByTestId('hr-employment-started-confirm')).toBeNull()
  })
})
