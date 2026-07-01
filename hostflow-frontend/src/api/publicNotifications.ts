/**
 * API for candidate notification subscriptions
 */

import http from './http'

export interface NotificationSubscriptionRequest {
  token: string
  email?: string
  phone?: string
  subscribe_document_status?: boolean
  subscribe_stage_changes?: boolean
  subscribe_reminders?: boolean
}

export interface NotificationSubscriptionResponse {
  subscribed: boolean
  channels: string[]
  message: string
}

export interface NotificationUnsubscribeRequest {
  token: string
  channel?: 'email' | 'phone' | 'push' | 'all'
}

export interface PushSubscriptionRequest {
  token: string
  endpoint: string
  keys: {
    p256dh: string
    auth: string
  }
}

export async function subscribeToNotifications(
  payload: NotificationSubscriptionRequest
): Promise<NotificationSubscriptionResponse> {
  const response = await http.post<NotificationSubscriptionResponse>(
    '/api/v1/public/notifications/subscribe',
    payload
  )
  return response.data
}

export async function unsubscribeFromNotifications(
  payload: NotificationUnsubscribeRequest
): Promise<NotificationSubscriptionResponse> {
  const response = await http.post<NotificationSubscriptionResponse>(
    '/api/v1/public/notifications/unsubscribe',
    payload
  )
  return response.data
}

export async function subscribeToPush(
  payload: PushSubscriptionRequest
): Promise<NotificationSubscriptionResponse> {
  const response = await http.post<NotificationSubscriptionResponse>(
    '/api/v1/public/notifications/push/subscribe',
    payload
  )
  return response.data
}

export async function unsubscribeFromPush(
  token: string
): Promise<NotificationSubscriptionResponse> {
  const response = await http.post<NotificationSubscriptionResponse>(
    '/api/v1/public/notifications/push/unsubscribe',
    { token }
  )
  return response.data
}

