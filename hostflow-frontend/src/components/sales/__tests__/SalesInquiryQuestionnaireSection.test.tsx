import { describe, expect, it, vi, afterEach, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import { ToastProvider } from '../../Toast'
import SalesInquiryQuestionnaireSection from '../SalesInquiryQuestionnaireSection'

const getLead = vi.fn()
const createLeadQuestionnaireInvite = vi.fn()
const getLeadQuestionnaireInvite = vi.fn()
const listLeadQuestionnaireForms = vi.fn()
const previewLeadQuestionnaireInviteEmail = vi.fn()
const sendLeadQuestionnaireInviteEmail = vi.fn()

vi.mock('../../../api/client', () => ({
  getLead: (...args: unknown[]) => getLead(...args),
  createLeadQuestionnaireInvite: (...args: unknown[]) => createLeadQuestionnaireInvite(...args),
  getLeadQuestionnaireInvite: (...args: unknown[]) => getLeadQuestionnaireInvite(...args),
  listLeadQuestionnaireForms: (...args: unknown[]) => listLeadQuestionnaireForms(...args),
  previewLeadQuestionnaireInviteEmail: (...args: unknown[]) => previewLeadQuestionnaireInviteEmail(...args),
  sendLeadQuestionnaireInviteEmail: (...args: unknown[]) => sendLeadQuestionnaireInviteEmail(...args),
}))

beforeEach(() => {
  listLeadQuestionnaireForms.mockResolvedValue([
    { id: 'form-1', title: 'B2B intake', purpose: 'questionnaire' },
  ])
  getLeadQuestionnaireInvite.mockResolvedValue(null)
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
  })
})

afterEach(() => {
  vi.clearAllMocks()
})

const clientLead = {
  id: 'b39f30a0-099d-421d-8b6d-eff67b42bac6',
  tenant_id: '11111111-1111-1111-1111-111111111111',
  lead_type: 'client',
  lead_target_type: 'client_lead',
  source: 'meta_ads',
  status: 'processed',
  payload: { phone: '+48111222333' },
  normalized: {
    phone: '+48111222333',
    sales_questionnaire_status: 'not_sent',
  },
  created_at: '2026-07-14T10:00:00.000Z',
} as Lead

function renderSection() {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">
        <ToastProvider>
          <SalesInquiryQuestionnaireSection leadId={clientLead.id} />
        </ToastProvider>
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('SalesInquiryQuestionnaireSection', () => {
  it('renders questionnaire block for client lead in sales workspace surface', async () => {
    getLead.mockResolvedValue(clientLead)

    renderSection()

    expect(await screen.findByTestId('sales-inquiry-questionnaire')).toBeInTheDocument()
    expect(screen.getByTestId('sales-questionnaire-panel')).toBeInTheDocument()
    expect(screen.getByText(/B2B questionnaire/i)).toBeInTheDocument()
    expect(screen.getByTestId('sales-questionnaire-email-open')).toBeInTheDocument()
  })

  it('does not hydrate invite on load while status is not_sent', async () => {
    getLead.mockResolvedValue(clientLead)

    renderSection()
    await screen.findByTestId('sales-inquiry-questionnaire')

    expect(createLeadQuestionnaireInvite).not.toHaveBeenCalled()
  })

  it('creates invite link from sales workspace More menu', async () => {
    getLead.mockResolvedValue(clientLead)
    createLeadQuestionnaireInvite.mockResolvedValue({
      id: 'invite-1',
      lead_id: clientLead.id,
      token: 'abc',
      apply_url: '/public/apply/abc',
      status: 'sent',
      sent_at: '2026-07-14T12:00:00.000Z',
    })

    renderSection()
    await screen.findByTestId('sales-questionnaire-more')
    await userEvent.click(screen.getByTestId('sales-questionnaire-more'))
    await userEvent.click(screen.getByRole('button', { name: /Copy link/i }))

    await waitFor(() => {
      expect(createLeadQuestionnaireInvite).toHaveBeenCalledWith(
        clientLead.id,
        expect.objectContaining({ mark_sent: true }),
      )
    })
  })

  it('shows answers view after submit without hydrating invite', async () => {
    getLead.mockResolvedValue({
      ...clientLead,
      normalized: {
        ...clientLead.normalized,
        sales_questionnaire_status: 'submitted',
        sales_questionnaire: {
          need_type: 'client_acquisition',
          primary_outcome: 'more_inquiries',
        },
        submissions_v1: [
          {
            submission_id: 'sub-1',
            submitted_at: '2026-07-14T13:00:00.000Z',
            target_entity_profile_code: 'service_sales.targeted_advertising',
            normalized_values: {
              'service_sales.targeted_advertising.need_type': 'client_acquisition',
              'service_sales.targeted_advertising.primary_outcome': 'more_inquiries',
            },
          },
        ],
      },
    })

    renderSection()

    expect(await screen.findByTestId('sales-questionnaire-answers')).toBeInTheDocument()
    expect(createLeadQuestionnaireInvite).not.toHaveBeenCalled()
  })
})
