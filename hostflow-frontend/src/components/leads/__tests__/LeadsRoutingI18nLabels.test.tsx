import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import type { Lead } from '../../../api/types'
import { I18nProvider, useI18n } from '../../../i18n'
import { leadRoutingTableAction } from '../../../utils/intakeResolution'

function RoutingLabelInner({ lead }: { lead: Lead }) {
  const { t } = useI18n()
  const act = leadRoutingTableAction(lead, false)
  if (act.kind === 'confirm_suggested' || act.kind === 'confirm_current') {
    return <button type="button">{t('app.leads.routing.confirm_and_process')}</button>
  }
  if (act.kind === 'pick_vacancy') {
    return <button type="button">{t('app.leads.routing.pick_vacancy')}</button>
  }
  return <span>none</span>
}

function ProbeWithLocale({ lead, locale }: { lead: Lead; locale: 'en' | 'pl' }) {
  return (
    <I18nProvider initialLocale={locale}>
      <RoutingLabelInner lead={lead} />
    </I18nProvider>
  )
}

describe('Lead routing table — i18n labels (en / pl)', () => {
  const vac = '00000000-0000-4000-8000-0000000000aa'

  const leadSuggested = {
    id: '1',
    tenant_id: '2',
    source: 'meta',
    status: 'needs_routing' as const,
    payload: {},
    created_at: '2026-01-01T00:00:00.000Z',
    suggested_vacancy_id: vac,
    vacancy_routing_confirmed: false,
  } as Lead

  const leadPick = {
    id: '1',
    tenant_id: '2',
    source: 'meta',
    status: 'needs_routing' as const,
    payload: {},
    created_at: '2026-01-01T00:00:00.000Z',
    suggested_vacancy_id: null,
    vacancy_id: null,
  } as Lead

  it('en: needs_routing + suggested → Confirm route and create candidate', () => {
    render(
      <MemoryRouter>
        <ProbeWithLocale lead={leadSuggested} locale="en" />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: 'Confirm route and create candidate' })).toBeInTheDocument()
  })

  it('pl: needs_routing + suggested → Potwierdź routing i utwórz kandydata', () => {
    render(
      <MemoryRouter>
        <ProbeWithLocale lead={leadSuggested} locale="pl" />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: 'Potwierdź routing i utwórz kandydata' })).toBeInTheDocument()
  })

  it('en: pick_vacancy → Choose vacancy', () => {
    render(
      <MemoryRouter>
        <ProbeWithLocale lead={leadPick} locale="en" />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: 'Choose vacancy' })).toBeInTheDocument()
  })

  it('pl: pick_vacancy → Wybierz ofertę', () => {
    render(
      <MemoryRouter>
        <ProbeWithLocale lead={leadPick} locale="pl" />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: 'Wybierz ofertę' })).toBeInTheDocument()
  })
})
