import { describe, expect, it, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import { ToastProvider } from '../../Toast'
import SalesInquiryQuestionnaireSection from '../SalesInquiryQuestionnaireSection'

const getLead = vi.fn()
const createLeadQuestionnaireInvite = vi.fn()
const listLeadQuestionnaireForms = vi.fn()
const getLeadQuestionnaireInvite = vi.fn()
const previewLeadQuestionnaireInviteEmail = vi.fn()
const sendLeadQuestionnaireInviteEmail = vi.fn()

vi.mock('../../../api/client', () => ({
  getLead: (...args: unknown[]) => getLead(...args),
  createLeadQuestionnaireInvite: (...args: unknown[]) => createLeadQuestionnaireInvite(...args),
  listLeadQuestionnaireForms: (...args: unknown[]) => listLeadQuestionnaireForms(...args),
  getLeadQuestionnaireInvite: (...args: unknown[]) => getLeadQuestionnaireInvite(...args),
  previewLeadQuestionnaireInviteEmail: (...args: unknown[]) => previewLeadQuestionnaireInviteEmail(...args),
  sendLeadQuestionnaireInviteEmail: (...args: unknown[]) => sendLeadQuestionnaireInviteEmail(...args),
}))

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
  payload: { phone: '+48111222333', email: 'client@example.com' },
  normalized: {
    phone: '+48111222333',
    sales_questionnaire_status: 'not_sent',
  },
  created_at: '2026-07-14T10:00:00.000Z',
} as Lead

const sampleForm = {
  id: 'form-1',
  name: 'B2B intake',
  locale: 'pl',
}

function renderSection() {
  return render(
    <I18nProvider initialLocale="pl">
      <ToastProvider>
        <SalesInquiryQuestionnaireSection leadId={clientLead.id} />
      </ToastProvider>
    </I18nProvider>,
  )
}

describe('SalesInquiryQuestionnaireSection', () => {
  it('renders questionnaire block for client lead in sales workspace surface', async () => {
    getLead.mockResolvedValue(clientLead)
    listLeadQuestionnaireForms.mockResolvedValue([sampleForm])
    getLeadQuestionnaireInvite.mockResolvedValue(null)

    renderSection()

    expect(await screen.findByTestId('sales-inquiry-questionnaire')).toBeInTheDocument()
    expect(screen.getByTestId('sales-questionnaire-panel')).toBeInTheDocument()
    expect(await screen.findByTestId('sales-questionnaire-email-open')).toBeInTheDocument()
  })

  it('does not hydrate invite on load while status is not_sent', async () => {
    getLead.mockResolvedValue(clientLead)
    listLeadQuestionnaireForms.mockResolvedValue([sampleForm])
    getLeadQuestionnaireInvite.mockResolvedValue(null)

    renderSection()
    await screen.findByTestId('sales-inquiry-questionnaire')

    expect(createLeadQuestionnaireInvite).not.toHaveBeenCalled()
    expect(previewLeadQuestionnaireInviteEmail).not.toHaveBeenCalled()
  })

  it('prepares email invite from sales workspace', async () => {
    getLead.mockResolvedValue(clientLead)
    listLeadQuestionnaireForms.mockResolvedValue([sampleForm])
    getLeadQuestionnaireInvite.mockResolvedValue(null)
    previewLeadQuestionnaireInviteEmail.mockResolvedValue({
      invite: {
        id: 'invite-1',
        lead_id: clientLead.id,
        token: 'abc',
        apply_url: '/public/apply/abc',
        status: 'sent',
        sent_at: '2026-07-14T12:00:00.000Z',
      },
      questionnaire_url: '/public/apply/abc',
      recipient_email: 'client@example.com',
      subject: 'Questionnaire',
      body: 'Please fill',
      email_configured: true,
      clarification_required: false,
      invite_reused: false,
      form_locale: 'pl',
    })

    renderSection()
    const openBtn = await screen.findByTestId('sales-questionnaire-email-open')
    await userEvent.click(openBtn)

    await waitFor(() => {
      expect(previewLeadQuestionnaireInviteEmail).toHaveBeenCalled()
    })
    expect(await screen.findByTestId('sales-questionnaire-email-compose')).toBeInTheDocument()
  })

  it('shows answers view after submit without creating a new invite on load', async () => {
    getLead.mockResolvedValue({
      ...clientLead,
      normalized: {
        ...clientLead.normalized,
        sales_questionnaire_status: 'submitted',
        sales_questionnaire: {
          need_type: 'client_acquisition',
          primary_outcome: 'more_inquiries',
        },
      },
    })
    listLeadQuestionnaireForms.mockResolvedValue([sampleForm])
    getLeadQuestionnaireInvite.mockResolvedValue(null)

    renderSection()

    expect(await screen.findByTestId('sales-questionnaire-answers')).toBeInTheDocument()
    expect(createLeadQuestionnaireInvite).not.toHaveBeenCalled()
    expect(previewLeadQuestionnaireInviteEmail).not.toHaveBeenCalled()
  })
})
