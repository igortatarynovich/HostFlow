import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import { ToastProvider } from '../../Toast'
import LeadQualificationSuggestionPanel from '../LeadQualificationSuggestionPanel'
import { manualProcessBlockHint } from '../../../utils/intakeResolution'

function renderPanel(lead: Lead) {
  render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">
        <ToastProvider>
          <LeadQualificationSuggestionPanel lead={lead} onProcess={vi.fn()} />
        </ToastProvider>
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('LeadQualificationSuggestionPanel intake gating', () => {
  it('duplicate_review: panel visible (context) and Process CTA disabled with intake tooltip', () => {
    const lead = {
      id: '00000000-0000-4000-8000-000000000001',
      tenant_id: '00000000-0000-4000-8000-000000000002',
      source: 'meta',
      status: 'duplicate_review',
      payload: {},
      created_at: '2026-01-01T00:00:00.000Z',
    } as Lead

    expect(manualProcessBlockHint(lead)).toBe('DUPLICATE_REVIEW_PENDING')
    renderPanel(lead)

    expect(screen.getByText('Qualification suggestion')).toBeInTheDocument()

    const btn = screen.getByRole('button', { name: 'Create candidate' })
    expect(btn).toBeDisabled()
    expect(btn.getAttribute('title')).toContain('Resolve duplicate review')
  })

  it('reject at intake: Process CTA disabled; title explains intake reject', () => {
    const lead = {
      id: '00000000-0000-4000-8000-000000000003',
      tenant_id: '00000000-0000-4000-8000-000000000002',
      source: 'meta',
      status: 'new',
      payload: {},
      created_at: '2026-01-01T00:00:00.000Z',
      normalized: {
        intake_resolution_v1: { status: 'rejected', reason_code: 'not_interested' },
      },
    } as Lead

    expect(manualProcessBlockHint(lead)).toBe('INTAKE_REJECTED')
    renderPanel(lead)

    const btn = screen.getByRole('button', { name: 'Create candidate' })
    expect(btn).toBeDisabled()
    expect(btn.getAttribute('title')).toContain('rejected at intake')
  })

  it('request_info: Process CTA disabled', () => {
    const lead = {
      id: '00000000-0000-4000-8000-000000000006',
      tenant_id: '00000000-0000-4000-8000-000000000002',
      source: 'meta',
      status: 'new',
      payload: {},
      created_at: '2026-01-01T00:00:00.000Z',
      normalized: {
        intake_resolution_v1: { status: 'info_requested' },
      },
    } as Lead

    expect(manualProcessBlockHint(lead)).toBe('INTAKE_INFO_REQUESTED')
    renderPanel(lead)

    const btn = screen.getByRole('button', { name: 'Create candidate' })
    expect(btn).toBeDisabled()
    expect(btn.getAttribute('title')).toContain('Information was requested at intake')
  })

  it('vacancy not confirmed: Process CTA disabled', () => {
    const lead = {
      id: '00000000-0000-4000-8000-000000000004',
      tenant_id: '00000000-0000-4000-8000-000000000002',
      source: 'meta',
      status: 'new',
      payload: {},
      created_at: '2026-01-01T00:00:00.000Z',
      vacancy_id: '00000000-0000-4000-8000-000000000099',
      vacancy_routing_confirmed: false,
    } as Lead

    expect(manualProcessBlockHint(lead)).toBe('VACANCY_NOT_CONFIRMED')
    renderPanel(lead)

    const btn = screen.getByRole('button', { name: 'Create candidate' })
    expect(btn).toBeDisabled()
    expect(btn.getAttribute('title')).toContain('Confirm vacancy routing')
  })

  it('vacancy confirmed: Process CTA enabled (no intake tooltip)', () => {
    const lead = {
      id: '00000000-0000-4000-8000-000000000005',
      tenant_id: '00000000-0000-4000-8000-000000000002',
      source: 'meta',
      status: 'new',
      payload: {},
      created_at: '2026-01-01T00:00:00.000Z',
      vacancy_id: '00000000-0000-4000-8000-000000000099',
      vacancy_routing_confirmed: true,
    } as Lead

    expect(manualProcessBlockHint(lead)).toBeNull()
    renderPanel(lead)

    const btn = screen.getByRole('button', { name: 'Create candidate' })
    expect(btn).not.toBeDisabled()
    expect(btn.getAttribute('title')).toBeNull()
  })
})
