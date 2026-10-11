import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../../../i18n'
import type { Application } from '../../../../api/types/application'
import { ToastProvider } from '../../../../components/Toast'
import { RecruitmentStageContribution } from '../stage'

vi.mock('../../../../api/applications', () => ({
  updateRecruitmentApplicationStage: vi.fn(),
  processRecruitmentApplication: vi.fn(),
  submitRecruitmentApplicationIntakeDecision: vi.fn(),
  createRecruitmentApplicationFollowUp: vi.fn(),
  recruitmentApplicationFits: vi.fn(),
  recruitmentApplicationTransferToEmployment: vi.fn(),
}))

const application: Application = {
  id: 'app-1',
  module: 'recruitment',
  contact: { name: 'Ada', phone: '+48111' },
  title: 'Ada',
  status: 'new',
  tab_bucket: 'new',
  extensions: { stage: 'new', vacancy_id: 'vac-1' },
}

function renderStage() {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">
        <ToastProvider>
          <RecruitmentStageContribution
            application={application}
            patching={false}
            onClose={() => undefined}
            onRefresh={() => undefined}
            onStage={() => undefined}
          />
        </ToastProvider>
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('RecruitmentStageContribution', () => {
  it('does not show a stage dropdown on the happy path', () => {
    renderStage()
    expect(screen.queryByLabelText('Stage')).toBeNull()
    expect(screen.getByRole('link', { name: /call/i })).toBeTruthy()
  })
})
