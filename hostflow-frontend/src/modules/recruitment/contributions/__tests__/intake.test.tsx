import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { I18nProvider } from '../../../../i18n'
import type { Application } from '../../../../api/types/application'
import { ToastProvider } from '../../../../components/Toast'
import { PlanLimitModalProvider } from '../../../../contexts/PlanLimitModalContext'
import { RecruitmentIntakeContribution } from '../intake'

const application: Application = {
  id: 'app-1',
  module: 'recruitment',
  contact: { name: 'Ada', phone: '+48111' },
  title: 'Ada',
  status: 'in_progress',
  tab_bucket: 'in_progress',
  extensions: {
    meta_form_answers: [{ name: 'kategoria', values: ['C+E'], label: 'Jaką masz kategorię?' }],
  },
}

describe('RecruitmentIntakeContribution', () => {
  it('shows Application form answers without calling Lead APIs', () => {
    render(
      <MemoryRouter>
        <I18nProvider>
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
    expect(screen.getByText('Jaką masz kategorię?')).toBeTruthy()
    expect(screen.getByText('C+E')).toBeTruthy()
    expect(document.querySelector('[data-capability-id="recruitment.intake"]')).toBeTruthy()
  })
})
