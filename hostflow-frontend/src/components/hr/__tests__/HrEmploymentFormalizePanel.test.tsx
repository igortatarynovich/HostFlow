import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from '../../../i18n'
import HrEmploymentFormalizePanel from '../HrEmploymentFormalizePanel'

describe('HrEmploymentFormalizePanel', () => {
  it('missing contract basis → one confirm → no rates/pathway menus', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <I18nProvider>
        <HrEmploymentFormalizePanel
          formalize={{
            policy_id: 'employment_formalize.v1',
            decision: 'missing',
            ready_to_formalize: true,
            ready_to_create_employee: false,
            employee_created: false,
            hr_employee_card: false,
            pathway_id: 'pl_eu_eea_free_movement',
            primary_item: {
              code: 'confirm_employment_contract_basis',
              kind: 'confirmation',
              message: 'Confirm employment contract basis for this PL EU/EEA hire',
            },
            active_missing: [
              {
                code: 'confirm_employment_contract_basis',
                kind: 'confirmation',
                message: 'Confirm employment contract basis for this PL EU/EEA hire',
              },
            ],
          }}
          onConfirm={onConfirm}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-formalize-missing')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-formalize-primary').textContent).toMatch(/contract basis/i)
    expect(screen.queryByRole('combobox')).toBeNull()
    expect(screen.getByTestId('hr-employment-formalize-zero-choice')).toBeTruthy()
    await user.click(screen.getByTestId('hr-employment-formalize-confirm'))
    expect(onConfirm).toHaveBeenCalledWith({
      confirmed_actions: ['confirm_employment_contract_basis'],
    })
  })

  it('formalization_complete shows ready_to_create_employee without Create/Started CTAs', () => {
    render(
      <I18nProvider>
        <HrEmploymentFormalizePanel
          formalize={{
            policy_id: 'employment_formalize.v1',
            decision: 'formalization_complete',
            ready_to_create_employee: true,
            employee_created: false,
            hr_employee_card: false,
            employee_id: null,
            active_missing: [],
            primary_item: {
              code: 'ready_to_create_employee',
              kind: 'threshold',
              message: 'Formalization complete — Employee creation allowed (not Created)',
            },
          }}
          onConfirm={() => undefined}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-formalize-complete')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-formalize-ready-create')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-formalize-no-employee-mint')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-formalize-no-create-cta')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-formalize-no-started')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /create employee|started|hr.?card/i })).toBeNull()
    expect(screen.queryByTestId('hr-employment-formalize-confirm')).toBeNull()
  })

  it('blocked explains without fake Formalize confirm', () => {
    render(
      <I18nProvider>
        <HrEmploymentFormalizePanel
          formalize={{
            policy_id: 'employment_formalize.v1',
            decision: 'blocked',
            ready_to_formalize: false,
            ready_to_create_employee: false,
            blockers: [{ code: 'not_ready_to_formalize', message: 'Formalize requires ready_to_formalize' }],
          }}
          onConfirm={() => undefined}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-formalize-blocked')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-formalize-blocker').textContent).toMatch(/ready_to_formalize/i)
    expect(screen.queryByTestId('hr-employment-formalize-confirm')).toBeNull()
    expect(screen.getByTestId('hr-employment-formalize-no-fake-action')).toBeTruthy()
  })
})
