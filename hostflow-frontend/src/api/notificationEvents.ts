import { api } from './client'
import type { ListNotificationEventsParams, NotificationEventOut, NotificationEventStatus } from './types/notificationEvent'

export async function listNotificationEvents(
  params: ListNotificationEventsParams = {},
): Promise<NotificationEventOut[]> {
  const { data } = await api.get<NotificationEventOut[]>('/platform/notification-events', { params })
  return Array.isArray(data) ? data : []
}

export async function getNotificationEvent(eventId: string): Promise<NotificationEventOut> {
  const { data } = await api.get<NotificationEventOut>(
    `/platform/notification-events/${encodeURIComponent(eventId)}`,
  )
  return data
}

export async function patchNotificationEventStatus(
  eventId: string,
  status: NotificationEventStatus,
): Promise<NotificationEventOut> {
  const { data } = await api.patch<NotificationEventOut>(
    `/platform/notification-events/${encodeURIComponent(eventId)}/status`,
    { status },
  )
  return data
}
