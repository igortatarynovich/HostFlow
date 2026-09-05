import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../../i18n'
import MarketingCampaignsPage from '../MarketingCampaignsPage'
import type { Campaign } from '../../../api/platformCampaigns'

const { mockList, mockPortfolio, mockMonitor } = vi.hoisted(() => ({
  mockList: vi.fn(),
  mockPortfolio: vi.fn(),
  mockMonitor: vi.fn(),
}))

vi.mock('../../../api/platformCampaigns', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/platformCampaigns')>()
  return {
    ...actual,
    listCampaigns: mockList,
    getCampaignPortfolio: mockPortfolio,
    getLiveIntakeMonitor: mockMonitor,
  }
})

vi.mock('../../../components/nav/PageHeader', () => ({
  PageHeader: ({ primaryAction, secondaryActions }: { primaryAction?: unknown; secondaryActions?: unknown }) => (
    <div>
      {primaryAction as never}
      {secondaryActions as never}
    </div>
  ),
}))

function campaign(partial: Partial<Campaign> = {}): Campaign {
  return {
    id: 'c1',
    tenant_id: 't1',
    own_company_id: 'co1',
    name: 'Drivers CE',
    status: 'active',
    goal_type: 'hiring',
    primary_kpi: 'applications',
    current_flight_id: 'f1',
    targets: [{ target_type: 'vacancy', target_id: 'v1', route_intent: 'candidate_application' }],
    flights: [
      {
        id: 'f1',
        code: 'F1',
        name: 'Wave 1',
        status: 'active',
        is_current: true,
        starts_at: '2026-08-01T10:00:00Z',
        forms: [
          {
            id: 'fl1',
            form_id: 'form1',
            role: 'primary',
            is_active: true,
            title: 'CE driver form',
          },
        ],
        intake_sources: [
          {
            id: 's1',
            intake_source_profile_id: 'p1',
            role: 'primary',
            is_active: true,
            provider: 'meta',
            name: 'Meta Lead Ads',
          },
        ],
      },
    ],
    ...partial,
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/app/marketing']}>
      <I18nProvider>
        <MarketingCampaignsPage />
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('MarketingCampaignsPage roster', () => {
  beforeEach(() => {
    mockList.mockReset()
    mockPortfolio.mockReset()
    mockMonitor.mockReset()
    mockList.mockResolvedValue([campaign()])
    mockPortfolio.mockResolvedValue({
      tenant_id: 't1',
      spend: '120',
      leads: 8,
      qualified: 0,
      converted: 0,
      outcomes_completed: 0,
      cost_per_lead: '15',
      currency: 'EUR',
      campaigns: [
        {
          campaign_id: 'c1',
          name: 'Drivers CE',
          status: 'active',
          spend: '120',
          leads: 8,
          qualified: 0,
          converted: 0,
          outcomes_completed: 0,
          cost_per_lead: '15',
          currency: 'EUR',
          is_best_cpl: true,
        },
      ],
      scan_capped: false,
    })
    mockMonitor.mockResolvedValue({ counters: { submissions: 8 } })
  })

  it('renders campaigns in the system DataTable', async () => {
    renderPage()
    const table = await screen.findByTestId('marketing-campaigns-table')
    expect(table.querySelector('table')).not.toBeNull()
    expect(table.querySelector('ul')).toBeNull()
    expect(await screen.findByTestId('marketing-campaign-name-c1')).toHaveTextContent('Drivers CE')
    expect(screen.getByRole('columnheader', { name: 'Campaign' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Status' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Applications' })).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByRole('columnheader', { name: 'Price' })).toBeInTheDocument()
    })
    expect(table.querySelector('[title="Active"]')).not.toBeNull()
    expect(screen.getByTestId('marketing-campaigns-search')).toBeInTheDocument()
  })
})
