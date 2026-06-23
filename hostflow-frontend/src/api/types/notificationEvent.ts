export type NotificationEventStatus = 'open' | 'resolved' | 'ignored'

export type NotificationEventCode = 'document_expiring_soon' | 'document_expired'

export type NotificationEventOut = {
  id: string
  tenant_id: string
  event_key: string
  evaluation_version: string
  event_code: NotificationEventCode | string
  source_layer: string
  owner_type: string
  owner_id: string
  document_id?: string | null
  document_type_code?: string | null
  severity: string
  document_runtime: Record<string, unknown>
  metadata: Record<string, unknown>
  evaluated_at?: string | null
  status: NotificationEventStatus | string
  created_at?: string | null
  updated_at?: string | null
}

export type NotificationEventSyncOut = {
  tenant_id: string
  evaluated_owners: number
  evaluated_documents: number
  events_evaluated: number
  created: number
  updated: number
  skipped: number
  event_codes: Record<string, number>
}

export type ListNotificationEventsParams = {
  status?: NotificationEventStatus | string
  source_layer?: string
  event_type?: NotificationEventCode | string
}
