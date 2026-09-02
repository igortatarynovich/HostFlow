import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../../i18n'

import LeadLifecycleEmailSettingsPage from '../LeadLifecycleEmailSettingsPage'

const {
  mockListLeadMessageTemplates,
  mockCreateLeadMessageTemplate,
  mockListCompanies,
  mockListOwnCompanies,
  mockGetOwnCompanyPolicy,
  mockPutOwnCompanyPolicy,
  mockResolvePreview,
  mockGetActiveLegalDocs,
} = vi.hoisted(() => ({
  mockListLeadMessageTemplates: vi.fn(),
  mockCreateLeadMessageTemplate: vi.fn(),
  mockListCompanies: vi.fn(),
  mockListOwnCompanies: vi.fn(),
  mockGetOwnCompanyPolicy: vi.fn(),
  mockPutOwnCompanyPolicy: vi.fn(),
  mockResolvePreview: vi.fn(),
  mockGetActiveLegalDocs: vi.fn(),
}))

vi.mock('../../../api/metaLeads', async () => {
  const actual = await vi.importActual<typeof import('../../../api/metaLeads')>('../../../api/metaLeads')
  return {
    ...actual,
    listLeadMessageTemplates: mockListLeadMessageTemplates,
    createLeadMessageTemplate: mockCreateLeadMessageTemplate,
  }
})

vi.mock('../../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../../api/client')>('../../../api/client')
  return {
    ...actual,
    listCompanies: mockListCompanies,
    listOwnCompanies: mockListOwnCompanies,
  }
})

vi.mock('../../../api/leadLifecycleEmail', async () => {
  const actual = await vi.importActual<typeof import('../../../api/leadLifecycleEmail')>(
    '../../../api/leadLifecycleEmail',
  )
  return {
    ...actual,
    getOwnCompanyLeadLifecycleEmailPolicy: mockGetOwnCompanyPolicy,
    putOwnCompanyLeadLifecycleEmailPolicy: mockPutOwnCompanyPolicy,
    resolveLeadLifecycleEmailPreview: mockResolvePreview,
  }
})

vi.mock('../../../api/legalDocuments', () => ({
  getActiveLegalDocs: mockGetActiveLegalDocs,
}))

vi.mock('../../../api/vacancies', () => ({
  listVacancies: vi.fn().mockResolvedValue([]),
}))

vi.mock('../../../store/auth', () => ({
  useAuth: () => ({
    me: { role: 'administrator' },
    loading: false,
    refresh: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    preferences: null,
    security: null,
    sessionId: null,
    updateProfile: vi.fn(),
    updatePreferences: vi.fn(),
    updateSecurity: vi.fn(),
    beginImpersonation: vi.fn(),
    canReturnToPlatform: false,
    restorePlatformSession: vi.fn(),
  }),
}))

const emptyPolicy = {
  version: 1 as const,
  rodo_send_mode: 'auto_on_lead_created' as const,
  rodo_template_ref: null,
  ops_enabled: false,
  application_received: { enabled: false, template_ref: null },
  rejection: { enabled: false, template_ref: null },
  moving_forward: { enabled: false, template_ref: null },
  channels: ['email'],
}

function seedPage() {
  mockListLeadMessageTemplates.mockResolvedValue([])
  mockListCompanies.mockResolvedValue([])
  mockListOwnCompanies.mockResolvedValue({
    items: [{ id: 'own-1', name: 'DANEMA TSL' }],
    active_own_company_id: 'own-1',
  })
  mockGetOwnCompanyPolicy.mockResolvedValue({
    own_company_id: 'own-1',
    policy: emptyPolicy,
    source: 'own_company',
  })
  mockGetActiveLegalDocs.mockResolvedValue({
    rodo_clause: { id: 'doc-1', type: 'rodo_clause', version_id: 'v1', content_url: '/legal/rodo.html', is_active: true, published_at: null },
    privacy_policy: null,
    terms_of_service: null,
    cookie_policy: null,
    trial_terms: null,
    downgrade_cancellation: null,
    overage_autodebit: null,
    data_retention: null,
    automation_disclaimer: null,
    mapping_disclaimer: null,
  })
  mockResolvePreview.mockResolvedValue({
    purpose: 'gdpr_notice',
    send: false,
    template_ref: null,
    source_layer: 'own_company',
    block_code: 'policy_template_missing',
    enabled: true,
    reason: 'RODO auto-send enabled but template_id is missing.',
  })
}

describe('LeadLifecycleEmailSettingsPage', () => {
  it('shows a recruiter status and create-message action instead of Hub/debug jargon', async () => {
    seedPage()

    render(
      <MemoryRouter>
        <I18nProvider initialLocale="en">
          <LeadLifecycleEmailSettingsPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    expect(
      (await screen.findAllByText('RODO information obligation: Active — managed by HostFlow')).length,
    ).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Create message' }).length).toBeGreaterThan(0)
    expect(screen.queryByText('Effective policy (resolve-preview)')).not.toBeInTheDocument()
    expect(screen.queryByText('Master enabled')).not.toBeInTheDocument()
  })

  it('creates a message in-page and assigns it to RODO policy', async () => {
    seedPage()
    mockCreateLeadMessageTemplate.mockResolvedValue({
      id: 'lead_tpl_rodo1',
      name: 'RODO / art. 14',
      subject: 'RODO',
      body: 'Hello {first_name}',
      is_active: true,
      created_at: '2026-09-02T00:00:00Z',
      updated_at: '2026-09-02T00:00:00Z',
    })
    mockPutOwnCompanyPolicy.mockResolvedValue({
      own_company_id: 'own-1',
      policy: { ...emptyPolicy, rodo_template_ref: 'lead_tpl_rodo1' },
      source: 'own_company',
    })

    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <I18nProvider initialLocale="en">
          <LeadLifecycleEmailSettingsPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    await user.click((await screen.findAllByRole('button', { name: 'Create message' }))[0])
    expect(await screen.findByRole('heading', { name: 'RODO message' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save and use' }))
    await vi.waitFor(() => expect(mockCreateLeadMessageTemplate).toHaveBeenCalled())
    await vi.waitFor(() => expect(mockPutOwnCompanyPolicy).toHaveBeenCalled())
    const savedPolicy = mockPutOwnCompanyPolicy.mock.calls[0][1] as { rodo_template_ref?: string; rodo_send_mode?: string }
    expect(savedPolicy.rodo_template_ref).toBe('lead_tpl_rodo1')
    expect(savedPolicy.rodo_send_mode).toBe('auto_on_lead_created')
    expect(await screen.findByText(/Message saved and assigned/i)).toBeInTheDocument()
  })
})
