import { describe, expect, it, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import { ToastProvider } from '../../Toast'
import SalesInquiryQuestionnaireSection from '../SalesInquiryQuestionnaireSection'

const getLead = vi.fn()
const createLeadQuestionnaireInvite = vi.fn()

vi.mock('../../../api/client', () => ({
  getLead: (...args: unknown[]) => getLead(...args),
  createLeadQuestionnaireInvite: (...args: unknown[]) => createLeadQuestionnaireInvite(...args),
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
  payload: { phone: '+48111222333' },
  normalized: {
    phone: '+48111222333',
    sales_questionnaire_status: 'not_sent',
  },
  created_at: '2026-07-14T10:00:00.000Z',
} as Lead

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

    renderSection()

    expect(await screen.findByTestId('sales-inquiry-questionnaire')).toBeInTheDocument()
    expect(screen.getByText(/Ankieta klienta/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Wyślij ankietę/i })).toBeInTheDocument()
  })

  it('does not hydrate invite on load while status is not_sent', async () => {
    getLead.mockResolvedValue(clientLead)

    renderSection()
    await screen.findByTestId('sales-inquiry-questionnaire')

    expect(createLeadQuestionnaireInvite).not.toHaveBeenCalled()
  })

  it('creates invite link from sales workspace', async () => {
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
    await screen.findByRole('button', { name: /Wyślij ankietę/i })

    await userEvent.click(screen.getByRole('button', { name: /Wyślij ankietę/i }))

    await waitFor(() => {
      expect(createLeadQuestionnaireInvite).toHaveBeenCalledWith(clientLead.id, { mark_sent: true })
    })
    expect(await screen.findByText(/\/public\/apply\/abc/)).toBeInTheDocument()
  })

  it('shows view answers as primary action after submit without hydrating invite', async () => {
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

    renderSection()

    expect(await screen.findByRole('button', { name: /Przeglądaj odpowiedzi/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Wyślij ankietę/i })).not.toBeInTheDocument()
    expect(await screen.findByTestId('sales-questionnaire-answers')).toBeInTheDocument()
    expect(createLeadQuestionnaireInvite).not.toHaveBeenCalled()
  })
})
