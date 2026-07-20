import { describe, expect, it } from 'vitest'
import type { NotificationEventOut } from '../api/types/notificationEvent'
import {
  filterNotificationEventsByEventType,
  notificationEventDocumentLabel,
  notificationEventExpiresOn,
  notificationEventOwnerLabel,
} from '../notificationEventPresentation'

const sampleEvent = (overrides: Partial<NotificationEventOut> = {}): NotificationEventOut => ({
  id: 'evt-1',
  tenant_id: 'tenant-1',
  event_key: 'key-1',
  evaluation_version: 'notification_event_v1',
  event_code: 'document_expired',
  source_layer: 'document_expiry_notifications',
  owner_type: 'candidate',
  owner_id: 'cand-1',
  document_type_code: 'passport',
  severity: 'critical',
  document_runtime: { expires_on: '2026-01-01' },
  metadata: {},
  status: 'open',
  ...overrides,
})

describe('notificationEventPresentation', () => {
  it('extracts expires_on from document_runtime', () => {
    expect(notificationEventExpiresOn(sampleEvent())).toBe('2026-01-01')
  })

  it('filters by event type', () => {
    const rows = [
      sampleEvent({ id: '1', event_code: 'document_expired' }),
      sampleEvent({ id: '2', event_code: 'document_expiring_soon' }),
    ]
    expect(filterNotificationEventsByEventType(rows, 'document_expired')).toHaveLength(1)
    expect(filterNotificationEventsByEventType(rows, 'all')).toHaveLength(2)
  })

  it('formats owner and document labels', () => {
    const event = sampleEvent()
    expect(notificationEventOwnerLabel(event)).toBe('candidate · cand-1')
    expect(notificationEventDocumentLabel(event)).toBe('passport')
  })
})
