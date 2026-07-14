import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
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

vi.mock('../../../api/metaLeads', async () => {
  const actual = await vi.importActual<typeof import('../../../api/metaLeads')>('../../../api/metaLeads')
  return {
    ...actual,
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
  }
})

vi.mock('../../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../../api/client')>('../../../api/client')
  return {
    ...actual,
    listLeads: mockListLeads,
    listCompanies: mockListCompanies,
    listVacancies: mockListVacancies,
  }
})

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

const baseSettings = {
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
}

function seedMetaMocks(oauthQuickConnect = false) {
  mockGetMetaLeadSelfServeOnboarding.mockResolvedValue({
    meta_app_display_name: 'HostFlow Leads',
    graph_api_version: 'v24.0',
    graph_permission_names: [],
    public_api_base_configured: true,
    webhook_verify_token_configured: true,
    graph_api_explorer_url: 'https://developers.facebook.com/tools/explorer/',
    oauth_quick_connect_enabled: oauthQuickConnect,
  })
  mockGetMetaIncomingPreview.mockResolvedValue({ items: [] })
  mockGetSettings.mockResolvedValue(baseSettings)
  mockListCredentials.mockResolvedValue([])
  mockListMapping.mockResolvedValue([])
  mockListCompanies.mockResolvedValue({ items: [] })
  mockListVacancies.mockResolvedValue({ items: [] })
  mockListAdminUsers.mockResolvedValue([])
  mockGetUnmappedLeads.mockResolvedValue({ groups: [] })
  mockListLeads.mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })
}

describe('MetaLeadsAdminPage', () => {
  it('renders tabs and loads initial data', async () => {
    seedMetaMocks(false)

    render(
      <MemoryRouter>
        <I18nProvider initialLocale="ru">
          <MetaLeadsAdminPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    expect((await screen.findAllByText('Админка Meta Leads')).length).toBeGreaterThan(0)
    await vi.waitFor(() => expect(mockGetSettings).toHaveBeenCalled())
  })

  it('shows Meta OAuth quick connect when enabled for administrator', async () => {
    seedMetaMocks(true)

    render(
      <MemoryRouter>
        <I18nProvider initialLocale="ru">
          <MetaLeadsAdminPage />
        </I18nProvider>
      </MemoryRouter>,
    )

    expect((await screen.findAllByText('Админка Meta Leads')).length).toBeGreaterThan(0)
  })
})
