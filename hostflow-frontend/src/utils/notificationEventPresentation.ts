import type { NotificationEventOut } from '../api/types/notificationEvent'

export function notificationEventExpiresOn(event: NotificationEventOut): string | null {
  const runtime = (event.document_runtime || {}) as Record<string, unknown>
  const direct = runtime.expires_on ?? runtime.expire_date
  if (direct != null && String(direct).trim()) return String(direct).trim()
  return null
}

export function notificationEventOwnerLabel(event: NotificationEventOut): string {
  const ownerType = String(event.owner_type || 'owner').trim()
  const ownerId = String(event.owner_id || '').trim()
  if (!ownerId) return ownerType
  return `${ownerType} · ${ownerId}`
}

export function notificationEventDocumentLabel(event: NotificationEventOut): string {
  return String(event.document_type_code || event.document_id || '—').trim()
}

export function notificationEventSortTs(event: NotificationEventOut): number {
  const raw = event.evaluated_at || event.created_at
  if (!raw) return 0
  const ts = Date.parse(String(raw))
  return Number.isFinite(ts) ? ts : 0
}

export function filterNotificationEventsByEventType(
  events: NotificationEventOut[],
  eventType: string,
): NotificationEventOut[] {
  const normalized = String(eventType || '').trim()
  if (!normalized || normalized === 'all') return events
  return events.filter((row) => String(row.event_code || '') === normalized)
}
