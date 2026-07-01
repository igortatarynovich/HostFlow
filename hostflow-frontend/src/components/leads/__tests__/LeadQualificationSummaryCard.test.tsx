import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import type { Lead } from '../../../api/types'
import { I18nProvider } from '../../../i18n'
import LeadQualificationSummaryCard from '../LeadQualificationSummaryCard'

function renderCard(lead: Lead, isServicesTenant = false) {
  render(
    <I18nProvider initialLocale="en">
      <LeadQualificationSummaryCard
        lead={lead}
        isServicesTenant={isServicesTenant}
        formatAt={(iso) => (iso ? String(iso).slice(0, 10) : '—')}
      />
    </I18nProvider>,
  )
}

const agencyMetaBase = {
  id: '00000000-0000-4000-8000-000000000001',
  tenant_id: '00000000-0000-4000-8000-000000000002',
  source: 'meta',
  status: 'needs_routing' as const,
  payload: {},
  created_at: '2026-01-01T00:00:00.000Z',
} as Lead

describe('LeadQualificationSummaryCard', () => {
  describe('gating', () => {
    it('renders nothing for services tenant', () => {
      const lead = { ...agencyMetaBase, normalized: { email: 'a@b.co', phone: '+48111222333' } } as Lead
      const { container } = render(
        <I18nProvider initialLocale="en">
          <LeadQualificationSummaryCard
            lead={lead}
            isServicesTenant
            formatAt={(iso) => String(iso ?? '')}
          />
        </I18nProvider>,
      )
      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when lead already has candidate_id', () => {
      const lead = {
        ...agencyMetaBase,
        candidate_id: '00000000-0000-4000-8000-000000000099',
        normalized: { email: 'a@b.co', phone: '+48111222333' },
      } as Lead
      const { container } = render(
        <I18nProvider initialLocale="en">
          <LeadQualificationSummaryCard lead={lead} formatAt={() => '—'} />
        </I18nProvider>,
      )
      expect(container.firstChild).toBeNull()
    })

    it('renders nothing for non-meta non-csv source even if normalized has contact', () => {
      const lead = {
        ...agencyMetaBase,
        source: 'referral',
        normalized: { email: 'a@b.co', phone: '+48111222333' },
      } as Lead
      const { container } = render(
        <I18nProvider initialLocale="en">
          <LeadQualificationSummaryCard lead={lead} formatAt={() => '—'} />
        </I18nProvider>,
      )
      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when meta lead has no qualification signals', () => {
      const lead = { ...agencyMetaBase, normalized: {} } as Lead
      const { container } = render(
        <I18nProvider initialLocale="en">
          <LeadQualificationSummaryCard lead={lead} formatAt={() => '—'} />
        </I18nProvider>,
      )
      expect(container.firstChild).toBeNull()
    })

    it('allows csv_import same as meta when signals exist', () => {
      const lead = {
        ...agencyMetaBase,
        source: 'csv_import',
        normalized: { email: 'x@y.pl', phone: '+48123456789' },
      } as Lead
      renderCard(lead)
      expect(screen.getByText('Qualification summary')).toBeInTheDocument()
    })
  })

  it('renders fit snapshot and a translated reason from lead_qualification_preview_v1', () => {
    const lead = {
      ...agencyMetaBase,
      vacancy_title: 'Driver PL',
      normalized: {
        email: 'driver@example.com',
        phone: '+48111222333',
        lead_qualification_preview_v1: {
          suggested_vacancy_id: '00000000-0000-4000-8000-0000000000aa',
          fit_status: 'needs_info',
          fit_reasons: ['missing_documents'],
          evaluated_at: '2026-05-09T12:00:00.000Z',
        },
        lead_fit_evaluation_effective_v1: true,
      },
    } as Lead

    renderCard(lead)

    expect(screen.getByText('Qualification summary')).toBeInTheDocument()
    expect(screen.getByText('Needs more data')).toBeInTheDocument()
    expect(screen.getByText('Why')).toBeInTheDocument()
    expect(screen.getByText('Documents list missing or empty')).toBeInTheDocument()
    expect(screen.getByText('Driver PL')).toBeInTheDocument()
  })
})
