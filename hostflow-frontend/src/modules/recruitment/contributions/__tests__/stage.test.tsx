import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../../../i18n'
import type { Application } from '../../../../api/types/application'
import { ToastProvider } from '../../../../components/Toast'
import { RecruitmentStageContribution } from '../stage'

const { updateRecruitmentApplicationStage } = vi.hoisted(() => ({
  updateRecruitmentApplicationStage: vi.fn(() =>
    Promise.resolve({ id: 'app-1', status: 'in_progress', extensions: { stage: 'qualified' } }),
  ),
}))

vi.mock('../../../../api/applications', () => ({
  updateRecruitmentApplicationStage,
  processRecruitmentApplication: vi.fn(),
  submitRecruitmentApplicationIntakeDecision: vi.fn(),
  createRecruitmentApplicationFollowUp: vi.fn(),
}))

const application: Application = {
  id: 'app-1',
  module: 'recruitment',
  contact: { name: 'Ada', phone: '+48111' },
  title: 'Ada',
  status: 'new',
  tab_bucket: 'new',
  extensions: { stage: 'new' },
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
  beforeEach(() => {
    updateRecruitmentApplicationStage.mockClear()
  })

  it('persists a CRM stage change from New', async () => {
    const user = userEvent.setup()
    renderStage()
    const select = screen.getByLabelText('Stage')
    expect(select).toHaveValue('new')
    await user.selectOptions(select, 'qualified')
    await waitFor(() => {
      expect(updateRecruitmentApplicationStage).toHaveBeenCalledWith('app-1', { stage: 'qualified' })
    })
  })
})
