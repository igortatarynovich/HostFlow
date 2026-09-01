import { type ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import LeadIntakeFormAnswers from '../LeadIntakeFormAnswers'
import LeadIntakeIdentityBar from '../LeadIntakeIdentityBar'

function metaLead(over: Partial<Lead> = {}): Lead {
  return {
    id: '00000000-0000-4000-8000-000000000011',
    tenant_id: '00000000-0000-4000-8000-000000000022',
    source: 'meta',
    status: 'needs_routing',
    payload: {},
    created_at: '2026-01-01T12:32:00.000Z',
    vacancy_title: 'Kierowca C+E',
    normalized: {
      full_name: 'Jan Kowalski',
      phone: '+48123456789',
      field_answers: [
        { name: 'full_name', values: ['Jan Kowalski'] },
        { name: 'какая_категория_водительских_прав_у_вас_открыта?', values: ['C+E'] },
      ],
    },
    ...over,
  } as Lead
}

function wrap(ui: ReactNode) {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">{ui}</I18nProvider>
    </MemoryRouter>,
  )
}

describe('recruitment intake decision surface', () => {
  it('shows submitted answers as the primary information', () => {
    wrap(<LeadIntakeFormAnswers lead={metaLead()} />)
    expect(screen.getByRole('heading', { name: /candidate answers/i })).toBeInTheDocument()
    expect(screen.getByText('какая категория водительских прав у вас открыта?')).toBeInTheDocument()
    expect(screen.getByText('C+E')).toBeInTheDocument()
  })

  it('keeps Call as the only primary action; Create is not a filled CTA', () => {
    wrap(
      <LeadIntakeIdentityBar
        lead={metaLead()}
        displayName="Jan Kowalski"
        formatDate={() => '12:32'}
        createLabel="Create candidate"
        rejectLabel="Reject"
        poolLabel="Pool"
        onCreate={() => undefined}
        onReject={() => undefined}
        onPool={() => undefined}
      />,
    )
    const call = screen.getByRole('link', { name: /call/i })
    expect(call).toHaveClass('btn-primary')
    const create = screen.getByRole('button', { name: 'Create candidate' })
    expect(create).not.toHaveClass('btn-primary')
    expect(create.className).not.toMatch(/bg-slate-900/)
  })
})
