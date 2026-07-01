import { describe, expect, it, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import * as apiClient from '../../../api/client'
import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import { PlanLimitModalProvider } from '../../../contexts/PlanLimitModalContext'
import { ToastProvider } from '../../Toast'
import LeadIntakeDecisionRail from '../LeadIntakeDecisionRail'

afterEach(() => {
  vi.restoreAllMocks()
})

function baseLead(over: Partial<Lead> = {}): Lead {
  return {
    id: '00000000-0000-4000-8000-000000000001',
    tenant_id: '00000000-0000-4000-8000-000000000002',
    source: 'meta',
    status: 'duplicate_review',
    payload: {},
    created_at: '2026-01-01T00:00:00.000Z',
    vacancy_routing_confirmed: true,
    vacancy_id: '00000000-0000-4000-8000-0000000000aa',
    normalized: {
      duplicate_match_v1: { suggested_candidate_id: '00000000-0000-4000-8000-000000000099' },
    },
    ...over,
  } as Lead
}

function renderRail(opts: {
  lead: Lead
  onLeadUpdated?: (l: Lead) => void
  onRequestProcess?: () => void | Promise<void>
}) {
  const onLeadUpdated = opts.onLeadUpdated ?? vi.fn()
  const onRequestProcess = opts.onRequestProcess ?? vi.fn().mockResolvedValue(undefined)
  return render(
    <I18nProvider initialLocale="en">
      <PlanLimitModalProvider>
        <ToastProvider>
          <LeadIntakeDecisionRail
            lead={opts.lead}
            processing={false}
            routingBusy={false}
            poolBusy={false}
            onLeadUpdated={onLeadUpdated}
            onRequestProcess={() => void onRequestProcess()}
            onConfirmRouting={vi.fn()}
            onPool={vi.fn()}
            layout="panel"
          />
        </ToastProvider>
      </PlanLimitModalProvider>
    </I18nProvider>,
  )
}

describe('LeadIntakeDecisionRail', () => {
  it('duplicate_review: “Not a duplicate” calls submitLeadDuplicateDecision create_new', async () => {
    const user = userEvent.setup()
    const onLeadUpdated = vi.fn()
    const updated = {
      ...baseLead(),
      status: 'needs_routing' as const,
      normalized: {},
    } as Lead
    const spy = vi.spyOn(apiClient, 'submitLeadDuplicateDecision').mockResolvedValue(updated)

    renderRail({ lead: baseLead(), onLeadUpdated })

    const btn = await screen.findByRole('button', { name: /Not a duplicate/i })
    await user.click(btn)

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith('00000000-0000-4000-8000-000000000001', { decision: 'create_new' })
      expect(onLeadUpdated).toHaveBeenCalledWith(updated)
    })
  })

  it('public-intake: shows read-only notice, no pool / reject intake actions', async () => {
    const lead = baseLead({
      source: 'public-intake',
      status: 'needs_routing',
      normalized: {},
    })

    renderRail({ lead })

    expect(await screen.findByText(/Public intake lead/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Send to pool/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Reject/i })).not.toBeInTheDocument()
  })
})
