import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { I18nProvider } from '../../../i18n'
import HrEmploymentAcceptPanel from '../HrEmploymentAcceptPanel'
import { shouldShowRitualAcceptButton } from '../../../utils/employmentAcceptUi'

describe('HrEmploymentAcceptPanel', () => {
  it('shows accepted Employment state without ritual Accept', () => {
    render(
      <I18nProvider>
        <HrEmploymentAcceptPanel
          policy={{
            policy_id: 'employment_accept_policy.v1',
            decision: 'auto_accept',
            ritual_accept_forbidden: true,
            accepted: true,
            employment_started: true,
            blockers: [],
            message: 'Employment started',
          }}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-accept-accepted')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Take into HR review/i })).toBeNull()
    expect(shouldShowRitualAcceptButton({ decision: 'auto_accept', accepted: true })).toBe(false)
  })

  it('shows concrete blocker and retry — not ritual Accept', () => {
    render(
      <I18nProvider>
        <HrEmploymentAcceptPanel
          policy={{
            policy_id: 'employment_accept_policy.v1',
            decision: 'review_required',
            accepted: false,
            employment_started: false,
            blockers: [{ code: 'handoff_disabled', message: 'Handoff is not enabled for this client link' }],
          }}
          onRetry={() => undefined}
        />
      </I18nProvider>,
    )
    expect(screen.getByTestId('hr-employment-accept-blocked')).toBeTruthy()
    expect(screen.getByTestId('hr-employment-accept-blocker').textContent).toMatch(/not enabled/i)
    expect(screen.getByTestId('hr-employment-accept-retry')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Take into HR review/i })).toBeNull()
  })
})
