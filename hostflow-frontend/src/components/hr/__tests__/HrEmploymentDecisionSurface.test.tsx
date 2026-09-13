import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from '../../../i18n'
import HrEmploymentDecisionSurface from '../HrEmploymentDecisionSurface'

describe('HrEmploymentDecisionSurface', () => {
  it('employable + formalizeBound hands off without Formalize CTA / Employee', () => {
    render(
      <I18nProvider>
        <HrEmploymentDecisionSurface
          formalizeBound
          employability={{
            policy_id: 'early_employability.v1',
            decision: 'employable',
            next_step: { code: 'proceed_to_formalize', label: 'Proceed to Formalize' },
            employee_created: false,
            legal_pathway: { pathway_id: 'pl_eu_eea_free_movement', selection_required: false },
            pathway_selection_required: false,
          }}
          onResolve={() => undefined}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-decision-employable')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-decision-handed-formalize')).toBeTruthy()
    expect(screen.queryByTestId('hr-employment-decision-ready-formalize')).toBeNull()
    expect(screen.queryByRole('button', { name: /Formalize|Create employee/i })).toBeNull()
    expect(screen.queryByRole('combobox')).toBeNull()
    expect(screen.getByTestId('hr-employment-decision-zero-choice')).toBeTruthy()
  })

  it('insufficient_facts shows one missing + resolve; no recheck button', async () => {
    const user = userEvent.setup()
    const onResolve = vi.fn()
    render(
      <I18nProvider>
        <HrEmploymentDecisionSurface
          employability={{
            policy_id: 'early_employability.v1',
            decision: 'insufficient_facts',
            next_step: {
              code: 'provide_citizenship',
              label: 'Provide citizenship (ISO alpha-2)',
            },
            employee_created: false,
          }}
          onResolve={onResolve}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-decision-insufficient')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /check again|re-?eval|recheck/i })).toBeNull()
    await user.type(screen.getByTestId('hr-employment-decision-citizenship'), 'DE')
    await user.click(screen.getByTestId('hr-employment-decision-resolve'))
    expect(onResolve).toHaveBeenCalledWith({ facts: { citizenship: 'DE' } })
  })

  it('blocked explains reason without fake resolve action', () => {
    render(
      <I18nProvider>
        <HrEmploymentDecisionSurface
          employability={{
            policy_id: 'early_employability.v1',
            decision: 'blocked',
            blockers: [{ code: 'invalid_package', message: 'Package missing fits_decision' }],
            next_step: { code: 'fix_package', label: 'Fix package' },
            employee_created: false,
          }}
          onResolve={() => undefined}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-decision-blocked')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-decision-blocker').textContent).toMatch(/fits_decision|Package/i)
    expect(screen.queryByTestId('hr-employment-decision-resolve')).toBeNull()
    expect(screen.getByTestId('hr-employment-decision-no-fake-action')).toBeTruthy()
  })
})
