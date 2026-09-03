import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../../../i18n'
import type { Application } from '../../../../api/types/application'
import { ToastProvider } from '../../../../components/Toast'
import { PlanLimitModalProvider } from '../../../../contexts/PlanLimitModalContext'
import { RecruitmentIntakeContribution } from '../intake'

const { logRecruitmentApplicationCallResult } = vi.hoisted(() => ({
  logRecruitmentApplicationCallResult: vi.fn(() => Promise.resolve({ id: 'app-1' })),
}))

vi.mock('../../../../api/applications', () => ({
  logRecruitmentApplicationCallResult,
}))

const application: Application = {
  id: 'app-1',
  module: 'recruitment',
  contact: { name: 'Ada', phone: '+48111' },
  title: 'Ada',
  status: 'new',
  tab_bucket: 'new',
  extensions: {
    meta_form_answers: [{ name: 'kategoria', values: ['C+E'], label: 'Jaką masz kategorię?' }],
  },
}

function renderIntake() {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">
        <ToastProvider>
          <PlanLimitModalProvider>
            <RecruitmentIntakeContribution
              application={application}
              patching={false}
              onClose={() => undefined}
              onRefresh={() => undefined}
            />
          </PlanLimitModalProvider>
        </ToastProvider>
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('RecruitmentIntakeContribution', () => {
  beforeEach(() => {
    logRecruitmentApplicationCallResult.mockClear()
  })

  it('shows Application form answers without calling Lead APIs', () => {
    renderIntake()
    expect(screen.getByText('Jaką masz kategorię?')).toBeTruthy()
    expect(screen.getByText('C+E')).toBeTruthy()
    expect(document.querySelector('[data-capability-id="recruitment.intake"]')).toBeTruthy()
  })

  it('saves the call result as soon as an outcome is chosen', async () => {
    const user = userEvent.setup()
    renderIntake()
    await user.click(screen.getByRole('button', { name: 'Interested' }))
    await waitFor(() => {
      expect(logRecruitmentApplicationCallResult).toHaveBeenCalledWith('app-1', {
        result: 'interested',
        note: null,
        next_contact_at: null,
      })
    })
  })
})
