import { describe, expect, it, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import * as apiClient from '../../../api/client'
import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import { PlanLimitModalProvider } from '../../../contexts/PlanLimitModalContext'
import { ToastProvider } from '../../Toast'
import LeadIntakeResolutionPanel from '../LeadIntakeResolutionPanel'

afterEach(() => {
  vi.restoreAllMocks()
})

function renderPanel(opts: {
  lead: Lead
  onLeadUpdated: (l: Lead) => void
  onRequestProcess: () => void | Promise<void>
}) {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">
        <PlanLimitModalProvider>
          <ToastProvider>
            <LeadIntakeResolutionPanel
              lead={opts.lead}
              isServicesTenant={false}
              onLeadUpdated={opts.onLeadUpdated}
              onRequestProcess={opts.onRequestProcess}
            />
          </ToastProvider>
        </PlanLimitModalProvider>
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('LeadIntakeResolutionPanel — confirm + optional process', () => {
  const vacId = '00000000-0000-4000-8000-0000000000aa'

  it('after confirm calls onRequestProcess when “Then run Process” is on', async () => {
    const user = userEvent.setup()
    const onRequestProcess = vi.fn().mockResolvedValue(undefined)
    const onLeadUpdated = vi.fn()
    const lead = {
      id: '00000000-0000-4000-8000-000000000001',
      tenant_id: '00000000-0000-4000-8000-000000000002',
      source: 'meta',
      status: 'needs_routing' as const,
      payload: {},
      created_at: '2026-01-01T00:00:00.000Z',
      suggested_vacancy_id: vacId,
      vacancy_routing_confirmed: false,
    } as Lead

    const updated = { ...lead, vacancy_routing_confirmed: true as boolean }
    const confirmSpy = vi.spyOn(apiClient, 'confirmLeadVacancy').mockResolvedValue(updated as Lead)
    vi.spyOn(apiClient, 'listVacancies').mockResolvedValue({ items: [{ id: vacId, title: 'Vacancy A' }] } as never)

    renderPanel({ lead, onLeadUpdated, onRequestProcess })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Confirm route and create candidate/i })).toBeEnabled()
    })

    await user.click(screen.getByRole('button', { name: /Confirm route and create candidate/i }))

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalledWith(lead.id, { vacancy_id: vacId })
      expect(onLeadUpdated).toHaveBeenCalledWith(updated)
      expect(onRequestProcess).toHaveBeenCalledTimes(1)
    })
  })

  it('after confirm does not call onRequestProcess when checkbox is off', async () => {
    const user = userEvent.setup()
    const onRequestProcess = vi.fn().mockResolvedValue(undefined)
    const onLeadUpdated = vi.fn()
    const lead = {
      id: '00000000-0000-4000-8000-000000000003',
      tenant_id: '00000000-0000-4000-8000-000000000002',
      source: 'meta',
      status: 'needs_routing' as const,
      payload: {},
      created_at: '2026-01-01T00:00:00.000Z',
      suggested_vacancy_id: vacId,
      vacancy_routing_confirmed: false,
    } as Lead

    vi.spyOn(apiClient, 'confirmLeadVacancy').mockResolvedValue({ ...lead, vacancy_routing_confirmed: true } as Lead)
    vi.spyOn(apiClient, 'listVacancies').mockResolvedValue({ items: [{ id: vacId, title: 'Vacancy A' }] } as never)

    renderPanel({ lead, onLeadUpdated, onRequestProcess })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Confirm route and create candidate/i })).toBeEnabled()
    })

    const toggle = screen.getByRole('checkbox', { name: /Then run Process automatically/i })
    await user.click(toggle)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^Confirm vacancy$/i })).toBeEnabled()
    })

    await user.click(screen.getByRole('button', { name: /^Confirm vacancy$/i }))

    await waitFor(() => {
      expect(onLeadUpdated).toHaveBeenCalled()
    })
    expect(onRequestProcess).not.toHaveBeenCalled()
  })
})
