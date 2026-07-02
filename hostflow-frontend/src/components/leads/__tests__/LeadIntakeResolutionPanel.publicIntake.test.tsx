import { describe, expect, it, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import { PlanLimitModalProvider } from '../../../contexts/PlanLimitModalContext'
import { ToastProvider } from '../../Toast'
import LeadIntakeResolutionPanel from '../LeadIntakeResolutionPanel'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('LeadIntakeResolutionPanel — public-intake', () => {
  it('shows read-only public intake notice instead of interactive intake shell', async () => {
    const lead = {
      id: '00000000-0000-4000-8000-000000000011',
      tenant_id: '00000000-0000-4000-8000-000000000002',
      source: 'public-intake',
      status: 'needs_routing' as const,
      payload: {},
      created_at: '2026-01-01T00:00:00.000Z',
      vacancy_routing_confirmed: false,
    } as Lead

    render(
      <MemoryRouter>
        <I18nProvider initialLocale="en">
          <PlanLimitModalProvider>
            <ToastProvider>
              <LeadIntakeResolutionPanel lead={lead} isServicesTenant={false} onLeadUpdated={vi.fn()} />
            </ToastProvider>
          </PlanLimitModalProvider>
        </I18nProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('status')).toHaveTextContent('Public client inquiry')
    expect(screen.queryByRole('button', { name: /Send to pool/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Confirm vacancy$/i })).not.toBeInTheDocument()
  })
})
