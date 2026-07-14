import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../i18n'
import NotificationAlertsPage from '../NotificationAlertsPage'
import type { NotificationEventOut } from '../../api/types/notificationEvent'

const { mockListNotificationEvents, mockPatchNotificationEventStatus, mockGetNotificationEvent } = vi.hoisted(
  () => ({
    mockListNotificationEvents: vi.fn(),
    mockPatchNotificationEventStatus: vi.fn(),
    mockGetNotificationEvent: vi.fn(),
  }),
)

vi.mock('../../api/notificationEvents', () => ({
  listNotificationEvents: mockListNotificationEvents,
  patchNotificationEventStatus: mockPatchNotificationEventStatus,
  getNotificationEvent: mockGetNotificationEvent,
}))

vi.mock('../../components/Toast', () => ({
  useToast: () => ({ notify: vi.fn() }),
}))

vi.mock('../../components/nav/PageHeader', () => ({
  PageHeader: ({ title }: { title?: string }) => (title ? <h1>{title}</h1> : null),
}))

const sampleRows: NotificationEventOut[] = [
  {
    id: 'evt-expired',
    tenant_id: 'tenant-1',
    event_key: 'k1',
    evaluation_version: 'notification_event_v1',
    event_code: 'document_expired',
    source_layer: 'document_expiry_notifications',
    owner_type: 'candidate',
    owner_id: 'cand-1',
    document_type_code: 'passport',
    severity: 'critical',
    document_runtime: { expires_on: '2026-01-01', expiry_status: 'expired' },
    metadata: {},
    status: 'open',
    evaluated_at: '2026-06-01T10:00:00Z',
  },
  {
    id: 'evt-soon',
    tenant_id: 'tenant-1',
    event_key: 'k2',
    evaluation_version: 'notification_event_v1',
    event_code: 'document_expiring_soon',
    source_layer: 'document_expiry_notifications',
    owner_type: 'candidate',
    owner_id: 'cand-2',
    document_type_code: 'code95',
    severity: 'warning',
    document_runtime: { expires_on: '2026-07-01', expiry_status: 'expiring_soon' },
    metadata: {},
    status: 'open',
    evaluated_at: '2026-06-01T11:00:00Z',
  },
]

function renderPage(initialEntry = '/app/notifications/alerts?status=open') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <I18nProvider>
        <NotificationAlertsPage />
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('NotificationAlertsPage', () => {
  beforeEach(() => {
    mockListNotificationEvents.mockReset()
    mockPatchNotificationEventStatus.mockReset()
    mockGetNotificationEvent.mockReset()
    mockListNotificationEvents.mockResolvedValue(sampleRows)
  })

  it('lists open expiry events', async () => {
    renderPage()
    expect(await screen.findByText('Document expired')).toBeInTheDocument()
    expect(screen.getByText('Document expiring soon')).toBeInTheDocument()
    expect(mockListNotificationEvents).toHaveBeenCalledWith({
      status: 'open',
      source_layer: 'document_expiry_notifications',
    })
  })

  it('filters expired events client-side', async () => {
    renderPage('/app/notifications/alerts?status=open&event_type=document_expired')
    await screen.findByText('Document expired')
    expect(screen.queryByText('Document expiring soon')).not.toBeInTheDocument()
  })

  it('shows detail and marks event resolved', async () => {
    mockPatchNotificationEventStatus.mockResolvedValue({
      ...sampleRows[0],
      status: 'resolved',
    })
    renderPage('/app/notifications/alerts?status=open&event_id=evt-expired')

    await screen.findByRole('heading', { name: 'Document expired' })
    expect(await screen.findByText('passport')).toBeInTheDocument()
    expect(screen.getByText('candidate · cand-1')).toBeInTheDocument()
    expect(screen.getByText('2026-01-01')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Mark resolved' }))

    await waitFor(() => {
      expect(mockPatchNotificationEventStatus).toHaveBeenCalledWith('evt-expired', 'resolved')
    })
  })
})
