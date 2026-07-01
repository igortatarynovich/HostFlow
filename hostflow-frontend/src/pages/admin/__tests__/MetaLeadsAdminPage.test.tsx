import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../../i18n'

import MetaLeadsAdminPage from '../MetaLeadsAdminPage'

const {
  mockGetSettings,
  mockUpdateSettings,
  mockListCredentials,
  mockCreateCredential,
  mockRotateCredential,
  mockDeleteCredential,
  mockListMapping,
  mockCreateMapping,
  mockUpdateMapping,
  mockDeleteMapping,
  mockGetUnmappedLeads,
  mockReroute,
  mockListLeads,
  mockListCompanies,
  mockListVacancies,
  mockListAdminUsers,
  mockGetMetaIncomingPreview,
  mockGetMetaLeadSelfServeOnboarding,
} = vi.hoisted(() => ({
  mockGetSettings: vi.fn(),
  mockUpdateSettings: vi.fn(),
  mockListCredentials: vi.fn(),
  mockCreateCredential: vi.fn(),
  mockRotateCredential: vi.fn(),
  mockDeleteCredential: vi.fn(),
  mockListMapping: vi.fn(),
  mockCreateMapping: vi.fn(),
  mockUpdateMapping: vi.fn(),
  mockDeleteMapping: vi.fn(),
  mockGetUnmappedLeads: vi.fn(),
  mockReroute: vi.fn(),
  mockListLeads: vi.fn(),
  mockListCompanies: vi.fn(),
  mockListVacancies: vi.fn(),
  mockListAdminUsers: vi.fn(),
  mockGetMetaIncomingPreview: vi.fn(),
  mockGetMetaLeadSelfServeOnboarding: vi.fn(),
}))

vi.mock('../../../api/metaLeads', () => ({
  getMetaLeadSettings: mockGetSettings,
  updateMetaLeadSettings: mockUpdateSettings,
  listMetaLeadCredentials: mockListCredentials,
  createMetaLeadCredential: mockCreateCredential,
  rotateMetaLeadCredential: mockRotateCredential,
  deleteMetaLeadCredential: mockDeleteCredential,
  listMetaAdsMap: mockListMapping,
  createMetaAdsMap: mockCreateMapping,
  updateMetaAdsMap: mockUpdateMapping,
  deleteMetaAdsMap: mockDeleteMapping,
  getUnmappedLeads: mockGetUnmappedLeads,
  rerouteMetaLead: mockReroute,
  retryLeads: vi.fn(),
  getMetaIncomingPreview: mockGetMetaIncomingPreview,
  getMetaLeadSelfServeOnboarding: mockGetMetaLeadSelfServeOnboarding,
}))

vi.mock('../../../api/client', () => ({
  listLeads: mockListLeads,
  listCompanies: mockListCompanies,
  listVacancies: mockListVacancies,
}))

vi.mock('../../../api/leadCsvImport', () => ({
  listLeadImportJobs: vi.fn().mockResolvedValue([]),
  pollLeadImportJob: vi.fn(),
  postLeadCsvImport: vi.fn(),
}))

vi.mock('../../../api/custom_fields', () => ({
  createCustomFieldDefinition: vi.fn(),
  listCustomFieldDefinitions: vi.fn().mockResolvedValue([]),
}))

vi.mock('../../../api/users', () => ({
  listAdminUsers: mockListAdminUsers,
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

describe('MetaLeadsAdminPage', () => {
  it('renders tabs and loads initial data', async () => {
    mockGetMetaLeadSelfServeOnboarding.mockResolvedValue({
      meta_app_display_name: 'HostFlow Leads',
      graph_api_version: 'v24.0',
      graph_permission_names: [],
      public_api_base_configured: true,
      webhook_verify_token_configured: true,
      graph_api_explorer_url: 'https://developers.facebook.com/tools/explorer/',
      oauth_quick_connect_enabled: false,
    })
    mockGetMetaIncomingPreview.mockResolvedValue({ items: [] })
    mockGetSettings.mockResolvedValueOnce({
      tenant_id: '11111111-1111-1111-1111-111111111111',
      auto_create_enabled: true,
      leads_auto_convert_on_fit_v1: true,
      leads_processing_mode_v1: 'assisted',
      mask_pii_in_logs: true,
      reroute_after_hours: 6,
      webhook_url: 'https://example.com/meta',
      webhook_verify_token: 'verify-token',
      last_webhook_check_at: null,
      last_signature_status: 'ok',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    })
    mockListCredentials.mockResolvedValueOnce([
      {
        id: 'cred-1',
        label: 'Primary',
        status: 'active',
        has_secret: true,
        ad_account_last4: '6789',
        page_id_masked: '***1234',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        last_verified_at: null,
        last_rotation_at: null,
      },
    ])
    mockListMapping.mockResolvedValueOnce([
      {
        ad_id: '555555',
        vacancy_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        note: 'Test mapping',
        created_at: '2025-01-01T00:00:00Z',
      },
    ])
    mockListCompanies.mockResolvedValueOnce({ items: [] })
    mockListVacancies.mockResolvedValueOnce({ items: [] })
    mockListAdminUsers.mockResolvedValueOnce([])
    mockGetUnmappedLeads.mockResolvedValueOnce({ groups: [] })
    mockListLeads
      .mockResolvedValueOnce({
        items: [
          {
            id: 'lead-1',
            tenant_id: '11111111-1111-1111-1111-111111111111',
            company_id: 'comp-1',
            company_name: 'Company',
            vacancy_id: null,
            vacancy_title: null,
            source: 'meta',
            ad_id: 555555,
            status: 'needs_routing',
            candidate_id: null,
            candidate_name: null,
            recruiter_id: null,
            error: 'VACANCY_NOT_RESOLVED',
            payload: {},
            normalized: { full_name: 'Manual Lead', email: 'manual@example.com', phone: '+48123123001' },
            created_at: '2025-01-01T00:00:00Z',
            last_routed_at: null,
          },
        ],
        total: 1,
        limit: 100,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [],
        total: 0,
        limit: 100,
        offset: 0,
      })

    render(
      <MemoryRouter>
        <I18nProvider initialLocale="ru">
          <MetaLeadsAdminPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    await screen.findByText('Админка Meta Leads')

    const advancedTab = screen.getByRole('button', { name: /Advanced|Дополнительно/i })
    fireEvent.click(advancedTab)
    await screen.findByDisplayValue('https://example.com/meta')
    expect(screen.getByDisplayValue('verify-token')).toBeInTheDocument()

    await screen.findByText('Primary')
    expect(screen.getByText('6789')).toBeInTheDocument()

    await screen.findByText('555555')
    expect(screen.getByText('Test mapping')).toBeInTheDocument()

    const debugTab = screen.getByRole('button', { name: /Debug|Отладка/i })
    fireEvent.click(debugTab)
    await screen.findByText(/Manual Lead/)
    expect(screen.getByText('VACANCY_NOT_RESOLVED')).toBeInTheDocument()
  })

  it('shows Meta OAuth quick connect when enabled for administrator', async () => {
    mockGetMetaLeadSelfServeOnboarding.mockResolvedValue({
      meta_app_display_name: 'HostFlow Leads',
      graph_api_version: 'v24.0',
      graph_permission_names: [],
      public_api_base_configured: true,
      webhook_verify_token_configured: true,
      graph_api_explorer_url: 'https://developers.facebook.com/tools/explorer/',
      oauth_quick_connect_enabled: true,
    })
    mockGetMetaIncomingPreview.mockResolvedValue({ items: [] })
    mockGetSettings.mockResolvedValueOnce({
      tenant_id: '11111111-1111-1111-1111-111111111111',
      auto_create_enabled: true,
      leads_auto_convert_on_fit_v1: true,
      leads_processing_mode_v1: 'assisted',
      mask_pii_in_logs: true,
      reroute_after_hours: 6,
      webhook_url: 'https://example.com/meta',
      webhook_verify_token: 'verify-token',
      last_webhook_check_at: null,
      last_signature_status: 'ok',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    })
    mockListCredentials.mockResolvedValueOnce([])
    mockListMapping.mockResolvedValueOnce([])
    mockListCompanies.mockResolvedValueOnce({ items: [] })
    mockListVacancies.mockResolvedValueOnce({ items: [] })
    mockListAdminUsers.mockResolvedValueOnce([])
    mockGetUnmappedLeads.mockResolvedValueOnce({ groups: [] })
    mockListLeads.mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })

    render(
      <MemoryRouter>
        <I18nProvider initialLocale="ru">
          <MetaLeadsAdminPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    await screen.findByText('Админка Meta Leads')
    expect(
      screen.getAllByRole('button', { name: /Facebook|Meta|Подключить|Continue/i }).length,
    ).toBeGreaterThanOrEqual(1)
  })
})
